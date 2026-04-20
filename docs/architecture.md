# Architecture

Vellic is a three-service system built around an async job queue. Each service has a single responsibility and communicates through well-defined interfaces.

## Services

| Service | Port | Responsibility |
|---|---|---|
| `api` | 8000 | Receive webhooks, validate signatures, enqueue jobs |
| `worker` | 8002 | Execute the 4-stage analysis pipeline |
| `admin` | 8001 | Replay events, inspect job state, edit configuration |
| `postgres` | 5432 | Persistent storage for events, jobs, and review results |
| `redis` | 6379 | Arq job queue and result cache |

## Data flow

```
1. VCS emits a webhook (PR opened / synchronised / reopened)
2. api validates the HMAC signature
3. api normalises the platform-specific payload → PREvent (platform-agnostic)
4. api enqueues the job to Redis via Arq
5. worker picks up the job and runs the pipeline:
   a. diff_fetcher   — fetches changed files from the VCS API
   b. context_gatherer — builds review context (repo, PR metadata, commit SHA)
   c. llm_analyzer   — sends diff chunks to the configured LLM; receives structured feedback
   d. feedback_poster — posts inline review comments back to the VCS Reviews API
6. Results are persisted to PostgreSQL
7. Job status is visible in the admin panel
```

## Platform abstraction

Vellic is VCS-agnostic by design. The internal representation is `PREvent` (see `worker/app/events.py`), a dataclass that carries only what the pipeline needs:

```python
@dataclass
class PREvent:
    platform: str       # "github" | "gitlab" | "bitbucket" | …
    event_type: str
    delivery_id: str
    repo: str
    pr_number: int
    action: str
    diff_url: str       # Platform files API URL — fetched by diff_fetcher
    base_sha: str
    head_sha: str
    base_branch: str
    title: str
    description: str
```

Each VCS adapter (`worker/app/adapters/<platform>.py`) converts a raw webhook payload into a `PREvent`. The rest of the pipeline never touches platform-specific data.

## LLM abstraction

LLM providers implement the `LLMProvider` protocol (`worker/app/llm/protocol.py`). The pipeline calls `provider.analyze(context, chunks)` — it does not care whether the response comes from Ollama, OpenAI, or a local binary.

The registry (`worker/app/llm/registry.py`) loads the active provider based on the configuration stored by the Admin UI.

## Scaling

- `api` and `admin` are stateless FastAPI services — scale horizontally behind a load balancer.
- `worker` is the compute-heavy service — scale via Kubernetes HPA (configured at 1→10 replicas, 70% CPU threshold).
- Redis and PostgreSQL are single-instance in the reference setup; use managed services (RDS, ElastiCache) in production.

## Adding a new VCS platform

1. Create `worker/app/adapters/<platform>.py` with a `normalize_pr(delivery_id, payload) -> PREvent` function.
2. Add a webhook route in `api/app/webhook.py` that validates the platform's signature scheme and calls your normaliser.
3. Add a `feedback_poster` path for posting reviews back to the new platform's API.

See [`docs/vcs-integrations.md`](vcs-integrations.md) for a worked example.
