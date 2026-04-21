# Architecture Deep Dive

Vellic is a three-service system built around an async job queue. This document covers the complete data flow, each service's internals, the LLM and VCS abstraction layers, and how the async pipeline handles retries, deduplication, and failure.

---

## Table of contents

1. [System overview](#system-overview)
2. [Webhook flow](#webhook-flow)
3. [4-stage pipeline](#4-stage-pipeline)
4. [Async job runner (Arq)](#async-job-runner-arq)
5. [LLM abstraction](#llm-abstraction)
6. [VCS platform abstraction](#vcs-platform-abstraction)
7. [Database schema](#database-schema)
8. [Admin service](#admin-service)
9. [Scaling](#scaling)
10. [Extending Vellic](#extending-vellic)

---

## System overview

```
GitHub (or any VCS)
        │
        │  POST /webhook/github
        ▼
┌─────────────┐
│     api     │  FastAPI · port 8000
│  (webhook   │  • HMAC validation
│  ingestion) │  • deduplication
└──────┬──────┘  • DB write + Arq enqueue
       │
       │  Redis / Arq
       ▼
┌─────────────┐
│   worker    │  Arq worker · port 8002 (health)
│  (pipeline) │  • 4-stage pipeline
│             │  • retry / dead-letter
└──────┬──────┘
       │
       │  GitHub Reviews API
       ▼
   GitHub PR ← inline comments + summary review
       │
       │  asyncpg
       ▼
┌─────────────┐    ┌─────────────┐
│  postgres   │    │    redis    │
│  (storage)  │    │  (job queue)│
└─────────────┘    └─────────────┘
       ▲
       │
┌─────────────┐
│    admin    │  FastAPI · port 8001
│   (REST)    │  • settings, stats, replay
└──────┬──────┘
       │
┌─────────────┐
│  frontend   │  nginx · port 80
│  (SPA)      │  • React + TypeScript
└─────────────┘
```

### Service responsibilities

| Service | Port | Single responsibility |
|---|---|---|
| `api` | 8000 | Receive webhooks, validate HMAC signatures, write to DB, enqueue jobs |
| `worker` | 8002 (health) | Execute the 4-stage analysis pipeline; post feedback to VCS |
| `admin` | 8001 | Replay deliveries, inspect jobs, configure LLM and per-repo settings |
| `frontend` | 80 | React SPA served by nginx; consumes the admin REST API |
| `postgres` | 5432 | Persistent storage — webhooks, jobs, reviews, config |
| `redis` | 6379 | Arq job queue and result cache |
| `ollama` | 11434 | Default local LLM inference (swappable via Admin UI) |

---

## Webhook flow

### Entry point: `api/app/webhook.py`

Every inbound webhook follows this path:

```
POST /webhook/github
        │
        ├── 1. Read raw body bytes (required for HMAC)
        │
        ├── 2. _verify_signature(body, X-Hub-Signature-256)
        │       secret = GITHUB_WEBHOOK_SECRET env var
        │       expected = "sha256=" + HMAC-SHA256(secret, body)
        │       constant-time compare (hmac.compare_digest)
        │       → 401 if mismatch
        │
        ├── 3. Filter event type
        │       only "pull_request" and "pull_request_review" proceed
        │       only PR actions: opened / synchronize / reopened
        │       others → 200 OK (logged, not enqueued)
        │
        ├── 4. Deduplication
        │       INSERT INTO webhook_deliveries(delivery_id, ...)
        │       ON CONFLICT(delivery_id) DO NOTHING
        │       duplicate → 200 OK (idempotent)
        │
        ├── 5. Enqueue
        │       arq.enqueue_job("process_webhook", delivery_id)
        │       job_id = delivery_id for correlation
        │
        └── 6. Return 202 Accepted
```

### Signature validation

GitHub signs every request with the webhook secret using HMAC-SHA256. The `api` service validates the `X-Hub-Signature-256` header against a locally computed HMAC over the raw request body. A timing-safe comparison (`hmac.compare_digest`) prevents timing attacks.

If `GITHUB_WEBHOOK_SECRET` is not set, the computed HMAC uses an empty string — all signatures will fail. Always set this variable.

---

## 4-stage pipeline

The pipeline lives in `worker/app/pipeline/`. It is orchestrated by `runner.py` and executed inside an Arq job.

```
process_webhook(ctx, delivery_id)
        │
        ├── Load webhook payload from DB
        ├── Check repo allow-list (installations table)
        ├── Load LLM config (DB → env fallback)
        │
        ▼
┌──────────────────┐
│ Stage 1          │  context_gatherer.py
│ gather_context   │  PREvent → PRContext
│                  │  (repo, pr_number, sha, title, body, base_branch)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Stage 2          │  diff_fetcher.py
│ fetch_diff       │  HTTP GET to VCS files API
│ _chunks          │  filter generated/binary files
│                  │  chunk patches to ≤500 lines each
└────────┬─────────┘  → list[DiffChunk]
         │
         ▼
┌──────────────────┐
│ Stage 3          │  llm_analyzer.py
│ analyze          │  build prompt (instructions + PR metadata + diffs)
│                  │  call llm.complete(prompt, max_tokens=2048)
│                  │  parse JSON: comments, summary, generic_ratio
└────────┬─────────┘  → AnalysisResult
         │
         ▼
┌──────────────────┐
│ Stage 4          │  result_persister.py
│ persist          │  INSERT INTO pr_reviews (UPSERT on repo+pr+sha)
│                  │  UPDATE pipeline_jobs status=done
│                  │  enqueue post_feedback(pr_review_id)
└──────────────────┘
         │
         ▼ (separate Arq job)
┌──────────────────┐
│ post_feedback    │  feedback_poster.py
│                  │  fetch pr_reviews row
│                  │  build inline comments list
│                  │  determine event: REQUEST_CHANGES or COMMENT
│                  │  POST /repos/{repo}/pulls/{pr}/reviews
│                  │  on 422 → retry without inline comments (summary only)
│                  │  on 429/rate-limit → retry 60s, 300s backoff
└──────────────────┘
```

### Stage 2: diff filtering

The diff fetcher (`worker/app/pipeline/diff_fetcher.py`) skips files that do not benefit from LLM review:

- **Binary files** — no `patch` field in the GitHub API response.
- **Generated files** — matched by suffix or path pattern: `*.lock`, `*.min.js`, `node_modules/`, `dist/`, `vendor/`, and similar.
- **Oversized patches** — each file's patch is chunked into segments of ≤ 500 lines to stay within LLM context windows.

### Stage 3: LLM response schema

The analyzer instructs the LLM to respond with structured JSON:

```json
{
  "comments": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "body": "Specific, actionable feedback",
      "confidence": 0.85,
      "rationale": "Why this matters"
    }
  ],
  "summary": "Overall PR assessment",
  "generic_ratio": 0.1
}
```

- `confidence` must be in `[0.0, 1.0]`. Comments with `confidence ≥ 0.8` trigger a `REQUEST_CHANGES` review event; lower-confidence comments are posted as `COMMENT`.
- `generic_ratio` measures how much of the feedback is non-specific. Values close to 1.0 indicate the LLM could not find meaningful issues.
- If JSON parsing fails entirely, the analyzer returns an empty `comments` list, the raw LLM output as `summary`, and `generic_ratio = 1.0`. The pipeline continues; the job does not fail.

### Stage 4b: feedback posting

`post_feedback` runs as a separate Arq job so a posting failure does not require re-running the expensive LLM stage.

GitHub's Reviews API can reject inline comments if a line number no longer matches the PR's diff (returns 422). In that case, the poster retries without inline comments, ensuring a summary review is always posted.

Rate-limit handling uses exponential backoff (60 s → 300 s) and inspects the `X-RateLimit-Remaining` header to proactively back off before hitting 429.

---

## Async job runner (Arq)

Arq is a Redis-backed async job queue for Python. The worker process is configured in `worker/app/main.py`.

### Worker settings

```python
class WorkerSettings:
    functions    = [process_webhook, post_feedback]
    max_jobs     = 10    # concurrent jobs per worker process
    max_tries    = 3     # retry attempts before dead-letter
    job_timeout  = 300   # seconds (5 minutes)
    keep_result  = 60    # seconds to hold job result in Redis
```

### Retry behaviour

**`process_webhook` (pipeline)**

| Attempt | Backoff |
|---|---|
| 1 → 2 | 5 seconds |
| 2 → 3 | 25 seconds |
| 3 (final) | dead-letter: write to `pipeline_failures` table, raise |

Any unhandled exception in the pipeline triggers a retry. The delivery is marked `processed_at = NOW()` only on success.

**`post_feedback` (VCS posting)**

| Condition | Behaviour |
|---|---|
| `RateLimitError` (429 or `X-RateLimit-Remaining < 100`) | Retry with 60 s → 300 s backoff |
| 422 Unprocessable Entity (invalid line numbers) | Retry once without inline comments |
| Other 4xx (terminal) | Log error, job completes silently (no retry) |
| 5xx | Standard Arq retry (up to `max_tries`) |

### Job correlation

Each pipeline job is tracked in the `pipeline_jobs` PostgreSQL table with a UUID that links to its `webhook_deliveries` row. This means every job — including retries — is visible in the Admin UI under `/jobs`, with status, retry count, duration, and error message if it failed.

### Horizontal scaling

Run multiple worker instances — Arq distributes jobs across all workers using Redis-based locking. Each job is processed exactly once. The Kubernetes HPA config (`infra/k8s/worker/hpa.yaml`) scales worker replicas 1→10 at 70% CPU utilisation.

---

## LLM abstraction

### Protocol

All LLM providers implement a two-method protocol (`worker/app/llm/protocol.py`):

```python
class LLMProvider(Protocol):
    async def complete(self, prompt: str, *, max_tokens: int) -> str: ...
    async def health(self) -> bool: ...
```

The pipeline calls `provider.complete(prompt, max_tokens=2048)`. It never inspects the provider type or calls any provider-specific method.

### Registry

The registry (`worker/app/llm/registry.py`) maps provider names to classes using a decorator:

```python
@register("ollama")
class OllamaProvider:
    ...
```

At runtime, `build_provider(name, **kwargs)` looks up the name and instantiates the class. Provider classes are imported when the worker starts.

### Config loading (priority order)

```
1. DB config    llm_settings table (row id=1), set via Admin UI
                api_key stored encrypted (Fernet, key in LLM_ENCRYPTION_KEY env var)
2. Env fallback LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL, LLM_API_KEY
3. Per-repo     installations table (org-wide or specific repo override)
```

Per-repo overrides win for a given repository but do not affect the global default.

### Available providers

| Name | Self-hosted | Notes |
|---|---|---|
| `ollama` | Yes | Default; ships in compose stack |
| `vllm` | Yes | OpenAI-compatible endpoint |
| `openai` | No | Requires `LLM_API_KEY`; data sent to OpenAI |
| `anthropic` | No | Requires `LLM_API_KEY`; data sent to Anthropic |
| `claude_code` | No | Wraps `claude --print` CLI; requires CLI installed in worker container |

The `openai` and `anthropic` providers are currently stubs that raise `NotImplementedError`. Implementing them requires adding the provider logic in `worker/app/llm/providers/` — the registry and config layer are already in place.

---

## VCS platform abstraction

The internal representation of a pull request event is `PREvent` (`worker/app/events.py`):

```python
@dataclass
class PREvent:
    platform:     str   # "github" | "gitlab" | "bitbucket" | …
    event_type:   str
    delivery_id:  str
    repo:         str   # "owner/repo"
    pr_number:    int
    action:       str   # "opened" | "synchronize" | "reopened"
    diff_url:     str   # VCS files API URL
    base_sha:     str
    head_sha:     str
    base_branch:  str
    title:        str
    description:  str
```

Each VCS adapter (`worker/app/adapters/<platform>.py`) converts a raw webhook payload into a `PREvent`. Everything downstream — diff fetching, LLM analysis, feedback posting — operates only on `PREvent`. No stage after the adapter sees platform-specific data.

The current GitHub adapter constructs `diff_url` as:

```
https://api.github.com/repos/{repo}/pulls/{pr_number}/files
```

A GitLab adapter would produce the equivalent GitLab MR API URL; the diff fetcher and analyzer would work without modification.

---

## Database schema

All tables are created by Alembic migrations in `api/alembic/versions/`. The migration runs automatically on `api` startup (`alembic upgrade head`).

### Tables

**`webhook_deliveries`** — raw inbound events

| Column | Type | Notes |
|---|---|---|
| `delivery_id` | TEXT PK | GitHub UUID; deduplication key |
| `event_type` | TEXT | `pull_request`, `pull_request_review`, etc. |
| `payload` | JSONB | Full webhook payload |
| `received_at` | TIMESTAMPTZ | |
| `processed_at` | TIMESTAMPTZ NULL | Set when pipeline job completes |

**`pipeline_jobs`** — one row per pipeline execution

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `delivery_id` | TEXT FK | Links to `webhook_deliveries` |
| `status` | TEXT | `running`, `done`, `failed` |
| `retry_count` | INT | |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | |

**`pipeline_failures`** — dead-letter for permanently failed jobs

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `job_id` | UUID FK | Links to `pipeline_jobs` |
| `payload` | JSONB | `{delivery_id, payload}` |
| `error` | TEXT | Exception message |
| `failed_at` | TIMESTAMPTZ | |

**`pr_reviews`** — analysis results

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `repo` | TEXT | `owner/repo` |
| `pr_number` | INT | |
| `commit_sha` | TEXT | |
| `feedback` | JSONB | `{comments, summary, generic_ratio}` |
| `github_review_id` | TEXT NULL | Set after posting; dedup for re-post |
| `posted_at` | TIMESTAMPTZ NULL | |
| UNIQUE | `(repo, pr_number, commit_sha)` | UPSERT on re-push to same commit |

**`installations`** — per-repo/per-org configuration

| Column | Type | Notes |
|---|---|---|
| `id` | UUID PK | |
| `platform` | TEXT | `github`, `gitlab`, etc. |
| `org` | TEXT | GitHub organisation or user |
| `repo` | TEXT NULL | NULL = org-wide; specific name = per-repo |
| `config_json` | JSONB | `{enabled, provider, model}` |
| `created_at` | TIMESTAMPTZ | |

**`llm_settings`** — single-row global LLM config

| Column | Type | Notes |
|---|---|---|
| `id` | INT PK | Always 1 |
| `provider` | TEXT | |
| `base_url` | TEXT NULL | |
| `model` | TEXT | |
| `api_key` | TEXT NULL | Fernet-encrypted |
| `extra` | JSONB NULL | Provider-specific extras |
| `updated_at` | TIMESTAMPTZ | |

---

## Admin service

The admin service (`admin/app/`) is a FastAPI application that exposes a REST API for the SPA. It shares the same Postgres and Redis connections as the api and worker.

### Auth

Session-based authentication with secure cookies. On first access, users are prompted to set a password. Routes under `/admin/*` return 401 if the session cookie is missing or expired.

### API surface

| Group | Endpoints | Purpose |
|---|---|---|
| Auth | `POST /admin/auth/setup`, `/login`, `/logout`, `GET /admin/auth/status` | Session management |
| Settings | `GET/PUT /admin/settings/llm`, `POST /admin/settings/llm/test` | LLM config + test |
| Repos | `GET/POST /admin/settings/repos`, `PUT/DELETE /admin/settings/repos/{id}` | Per-repo overrides |
| Deliveries | `GET /admin/deliveries` | Paginated webhook history |
| Jobs | `GET /admin/jobs` | Paginated pipeline job history |
| Replay | `POST /admin/replay/{delivery_id}` | Re-enqueue any delivery |
| Stats | `GET /admin/stats` | Dashboard metrics (24h / 7d) |

### Stats

`GET /admin/stats` returns:

```json
{
  "prs_reviewed_24h": 12,
  "prs_reviewed_7d": 83,
  "latency_p50_ms": 3200,
  "latency_p95_ms": 8100,
  "failure_rate_pct": 1.2,
  "llm_provider": "ollama",
  "llm_model": "llama3.1:8b-instruct-q4_K_M",
  "recent_deliveries": [...]
}
```

Latency is measured from `webhook_deliveries.received_at` to `pipeline_jobs.updated_at`.

---

## Scaling

### Stateless services

`api` and `admin` are stateless FastAPI services with no local state. Scale horizontally behind a load balancer.

### Worker

The worker is the compute-heavy service. Each worker process handles up to 10 concurrent jobs (`max_jobs = 10`). Scale by adding replicas:

- **Docker Compose:** `docker compose up --scale worker=N`
- **Kubernetes:** The HPA in `infra/k8s/worker/hpa.yaml` scales 1→10 replicas at 70% CPU.

Multiple worker replicas are safe: Arq uses Redis-based job locking so each job is executed exactly once regardless of replica count.

### Data stores

Postgres and Redis are single-instance in the reference compose setup. In production, use managed services:

- **Postgres:** Amazon RDS, Supabase, or any Postgres-compatible service.
- **Redis:** Amazon ElastiCache, Upstash, or a self-managed Redis cluster.

### Ollama

The bundled Ollama container is for local development. In production, deploy Ollama on a GPU-equipped instance and point `LLM_BASE_URL` at it (or switch to a cloud provider in the Admin UI).

---

## Extending Vellic

### Adding a new VCS platform

1. **Create an adapter** (`worker/app/adapters/<platform>.py`):

```python
from ..events import PREvent

def normalize_pr(delivery_id: str, payload: dict) -> PREvent:
    return PREvent(
        platform="<platform>",
        event_type="pull_request",
        delivery_id=delivery_id,
        repo=payload["project"]["path_with_namespace"],  # example: GitLab
        pr_number=int(payload["object_attributes"]["iid"]),
        action=payload["object_attributes"]["action"],
        diff_url=f"https://gitlab.com/api/v4/projects/.../merge_requests/{pr_number}/diffs",
        base_sha=payload["object_attributes"]["last_commit"]["id"],
        head_sha=payload["object_attributes"]["last_commit"]["id"],
        base_branch=payload["object_attributes"]["target_branch"],
        title=payload["object_attributes"].get("title") or "",
        description=payload["object_attributes"].get("description") or "",
    )
```

2. **Add a webhook route** (`api/app/webhook.py`):
   Validate the platform-specific signature scheme, then call your `normalize_pr()` and enqueue the job.

3. **Add a feedback poster** (`worker/app/pipeline/feedback_poster.py`):
   Implement the VCS Reviews API for your platform (e.g., GitLab Merge Request Discussions API).

No changes are required to the pipeline stages, the LLM layer, or the database schema.

### Adding a new LLM provider

1. **Create a provider** (`worker/app/llm/providers/<name>.py`):

```python
from ..registry import register

@register("<name>")
class MyProvider:
    def __init__(self, base_url: str, model: str, api_key: str = "", **kwargs):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key

    async def complete(self, prompt: str, *, max_tokens: int) -> str:
        # call your LLM API and return the response text
        ...

    async def health(self) -> bool:
        # return True if the provider is reachable
        ...
```

2. **Register it** — the `@register("<name>")` decorator is all that is needed. The admin settings router must also add the name to its `VALID_PROVIDERS` list so the UI dropdown includes it.

See [`docs/llm-providers.md`](llm-providers.md) for detailed provider setup, including authentication and privacy notes.
