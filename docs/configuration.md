# Configuration

Infrastructure configuration (database, Redis, ports) is done through environment variables. In local dev they are read from `docker-compose.yml`. In production, inject via Kubernetes Secrets or an external secrets manager.

**LLM provider selection, model, API keys, and per-repository settings are configured through the Admin UI** (`http://localhost:8001`), not through environment variables.

## Required variables

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Postgres password. Must match across services. |
| `GITHUB_WEBHOOK_SECRET` | HMAC secret for `X-Hub-Signature-256` validation. Generate with `openssl rand -hex 32`. |

## Database

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://vellic:<POSTGRES_PASSWORD>@postgres:5432/vellic` | Full Postgres DSN. Set this directly to override the derived value. |
| `POSTGRES_USER` | `vellic` | Postgres username (used when constructing the DSN). |
| `POSTGRES_DB` | `vellic` | Postgres database name. |

## Redis / Queue

| Variable | Default | Description |
|---|---|---|
| `REDIS_URL` | `redis://redis:6379` | Redis DSN for Arq queue and cache. |

## Worker

| Variable | Default | Description |
|---|---|---|
| `HEALTH_PORT` | `8002` | Port for the worker's health HTTP server. |

## Ports (docker-compose defaults)

| Service | Port | Configurable via |
|---|---|---|
| api | `8000` | `PORT` env var |
| admin | `8001` | `PORT` env var |
| worker (health) | `8002` | `HEALTH_PORT` |
| PostgreSQL | `5432` | Compose port mapping |
| Redis | `6379` | Compose port mapping |
| Ollama | `11434` | Compose port mapping |

## Generating secrets

```bash
# Webhook secret
openssl rand -hex 32

# Postgres password
openssl rand -base64 24
```
