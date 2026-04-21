# API Reference

Vellic exposes two HTTP services: the **Webhook API** (`api`, port 8000) and the **Admin API** (`admin`, port 8001). Both services are FastAPI applications and auto-generate interactive documentation.

---

## Interactive docs

| Service | Swagger UI | Redoc |
|---|---|---|
| Webhook API | `http://localhost:8000/docs` | `http://localhost:8000/redoc` |
| Admin API | `http://localhost:8001/docs` | `http://localhost:8001/redoc` |

The raw OpenAPI schema is available at `/openapi.json` on each service (e.g. `http://localhost:8000/openapi.json`).

---

## Authentication

### Webhook API

No authentication for inbound webhooks — callers must instead provide a valid **HMAC signature**.

- GitHub: `X-Hub-Signature-256: sha256=<hex>` using your `GITHUB_WEBHOOK_SECRET`.

Requests with a missing or invalid signature return `400 Bad Request`.

### Admin API

All `/admin/*` endpoints (except those listed under [Auth endpoints](#auth-endpoints)) require an authenticated session.

Two authentication methods are supported:

| Method | How |
|---|---|
| Session cookie | Log in via `POST /admin/auth/login`; the response sets a `vellic_session` cookie valid for 24 hours. |
| HTTP Basic | `Authorization: Basic base64(:<password>)` on each request. |

Unauthenticated requests to protected endpoints return `401 Unauthorized`.

---

## Webhook API

Base URL: `http://localhost:8000` (configurable via `PORT` env var)

### Health

```
GET /health
```

Returns `200 OK` with `{ "status": "ok", "service": "api" }`. No auth required.

### GitHub webhook

```
POST /webhook/github
```

Receives GitHub webhook events. Requires a valid `X-Hub-Signature-256` header.

**Handled events:**

| Event | Actions handled |
|---|---|
| `pull_request` | `opened`, `synchronize`, `reopened` |
| `pull_request_review` | all actions |

Other events receive `200 OK` with `{ "status": "ignored" }`.

**Required headers:**

| Header | Description |
|---|---|
| `X-GitHub-Event` | Event name |
| `X-GitHub-Delivery` | Unique delivery UUID |
| `X-Hub-Signature-256` | HMAC-SHA256 of the raw body |

**Responses:**

| Code | Meaning |
|---|---|
| `202 Accepted` | Event accepted and queued for processing |
| `200 OK` | Event ignored (unsupported type or action) |
| `400 Bad Request` | Invalid signature or missing delivery ID |

---

## Admin API

Base URL: `http://localhost:8001` (configurable via `PORT` env var)

All endpoints are prefixed with `/admin/` and require auth unless noted otherwise.

### Health

```
GET /health
```

Returns `{ "status": "ok", "service": "admin" }`. No auth required.

---

### Auth endpoints

These endpoints do **not** require an existing session.

#### Get auth status

```
GET /admin/auth/status
```

Returns whether initial setup is required and whether the current request is authenticated.

```json
{ "setup_required": false, "authenticated": true }
```

#### First-time setup

```
PUT /admin/auth/setup
```

Sets the admin password. Returns `409 Conflict` if a password is already set.

```json
{ "password": "your-password" }
```

Returns `204 No Content` and sets a session cookie on success.

#### Login

```
POST /admin/auth/login
```

```json
{ "password": "your-password" }
```

Returns `{ "authenticated": true }` and sets a session cookie. Returns `401` on wrong password (with a 1-second delay to mitigate brute force).

#### Logout

```
POST /admin/auth/logout
```

Clears the session cookie. Returns `204 No Content`.

#### Change password

```
POST /admin/auth/change-password
```

```json
{ "current_password": "old", "new_password": "new" }
```

Returns `204 No Content`. Returns `401` if `current_password` is wrong.

---

### Stats

#### Dashboard stats

```
GET /admin/stats
```

Returns pipeline metrics and recent deliveries.

```json
{
  "prs_reviewed_24h": 12,
  "prs_reviewed_7d": 84,
  "latency_p50_ms": 4200,
  "latency_p95_ms": 11800,
  "failure_rate_pct": 1.23,
  "llm_provider": "ollama",
  "llm_model": "qwen2.5-coder:14b",
  "recent_deliveries": [
    {
      "delivery_id": "abc-123",
      "event_type": "pull_request",
      "repo": "acme-org/backend",
      "received_at": "2026-04-21T09:00:00Z",
      "status": "done"
    }
  ]
}
```

---

### Deliveries

#### List webhook deliveries

```
GET /admin/deliveries?limit=50&offset=0
```

Returns paginated webhook delivery records with their processing status.

#### Replay a delivery

```
POST /admin/replay/{delivery_id}
```

Re-enqueues a delivery for pipeline processing. Useful after fixing a misconfiguration. Returns `202 Accepted`.

---

### LLM settings

#### Get LLM settings

```
GET /admin/settings/llm
```

Returns the active global LLM configuration. API keys are masked (`sk-...••••`).

```json
{
  "provider": "ollama",
  "base_url": "http://ollama:11434",
  "model": "qwen2.5-coder:14b",
  "api_key": null,
  "extra": {},
  "updated_at": "2026-04-20T10:00:00Z"
}
```

#### Update LLM settings

```
PUT /admin/settings/llm
```

```json
{
  "provider": "anthropic",
  "model": "claude-3-5-sonnet-20241022",
  "api_key": "sk-ant-..."
}
```

Valid providers: `ollama`, `vllm`, `openai`, `anthropic`, `claude_code`.

Changes take effect on the next job run — no restart required.

---

### Webhook / VCS settings

#### Get webhook config

```
GET /admin/settings/webhook
```

```json
{
  "url": "https://vellic.example.com",
  "hmac": "whsec_...",
  "github_app_id": "12345",
  "github_installation_id": "67890",
  "github_key_set": true,
  "gitlab_token_set": false
}
```

#### Set webhook URL

```
PUT /admin/settings/webhook
```

```json
{ "url": "https://vellic.example.com" }
```

URL must use `http` or `https` scheme.

#### Rotate HMAC secret

```
POST /admin/settings/webhook/rotate
```

Generates a new `whsec_...` HMAC secret. Returns the new plaintext secret — copy it immediately and update your VCS webhook configuration.

```json
{ "hmac": "whsec_<new-secret>" }
```

#### Configure GitHub App

```
PUT /admin/settings/github
```

```json
{
  "app_id": "12345",
  "installation_id": "67890",
  "private_key": "-----BEGIN RSA PRIVATE KEY-----\n..."
}
```

`private_key` is optional on subsequent updates — omit it to leave the existing key in place.

#### Test GitHub connection

```
POST /admin/settings/github/test
```

Mints a short-lived JWT from the stored GitHub App private key and calls the GitHub API to verify the credentials. Returns `{ "ok": true }` or `502 Bad Gateway` with an error detail.

#### Configure GitLab token

```
PUT /admin/settings/gitlab
```

```json
{ "token": "glpat-..." }
```

#### Test GitLab connection

```
POST /admin/settings/gitlab/test
```

Calls `GET /api/v4/user` on the configured GitLab instance to verify the token. Returns `{ "ok": true }` or `502`.

---

### Repository rules

See also [Rules Engine Reference](rules-engine.md) for the full routing-rule semantics.

#### List repositories

```
GET /admin/settings/repos
```

```json
{
  "items": [
    {
      "id": "uuid",
      "platform": "github",
      "org": "acme-org",
      "repo": "backend",
      "slug": "acme-org/backend",
      "enabled": true,
      "provider": "ollama",
      "model": "qwen2.5-coder:14b",
      "created_at": "2026-04-01T00:00:00Z"
    }
  ]
}
```

#### Add a repository

```
POST /admin/settings/repos
```

```json
{
  "platform": "github",
  "slug": "acme-org/backend",
  "provider": "ollama",
  "model": "qwen2.5-coder:14b"
}
```

Returns `201 Created` with the created item. Returns `409 Conflict` if the slug is already configured.

Valid platforms: `github`, `gitlab`.
Valid providers: `ollama`, `vllm`, `openai`, `anthropic`, `claude_code`.

Use `slug: "acme-org/*"` for a wildcard rule that matches all repos in an org.

#### Update a repository

```
PATCH /admin/settings/repos/{repo_id}
```

Accepts the same body as the create endpoint. All fields are replaced.

#### Toggle enabled/disabled

```
POST /admin/settings/repos/{repo_id}/toggle
```

Flips the `enabled` flag. Returns the updated item.

#### Delete a repository

```
DELETE /admin/settings/repos/{repo_id}
```

Returns `204 No Content`. Webhooks from this repo will be ignored again until re-added.

---

### Feature flags

See [Rules Engine Reference — Pipeline Feature Flags](rules-engine.md#layer-2-pipeline-feature-flags) for the full flag catalog.

#### Get all flags

```
GET /admin/features
```

```json
{
  "flags": { "vcs.github": true, "pipeline.security_scan": false, ... },
  "catalog": [
    {
      "key": "vcs.github",
      "name": "GitHub",
      "category": "vcs",
      "description": "GitHub PR webhooks and review comments",
      "enabled": true,
      "default": true
    }
  ],
  "snapshot_at": "2026-04-21T09:00:00Z"
}
```

#### Set a flag

```
PUT /admin/features/{flag_key}
```

```json
{ "enabled": true }
```

Returns `200 OK` with `{ "key": "...", "enabled": true }`. Returns `404` for unknown keys.

---

## Error responses

All error responses follow the standard FastAPI format:

```json
{ "detail": "Human-readable error message" }
```

Common status codes:

| Code | Meaning |
|---|---|
| `400` | Bad request (e.g. invalid HMAC signature) |
| `401` | Not authenticated |
| `404` | Resource not found |
| `409` | Conflict (e.g. duplicate repo slug) |
| `422` | Validation error (missing or invalid fields) |
| `502` | Upstream error (e.g. GitHub/GitLab API unreachable) |
