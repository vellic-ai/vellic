# Configuration

All configuration is through environment variables. In local dev they are read from `docker-compose.yml`. In production, inject via Kubernetes Secrets or an external secrets manager.

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

## LLM

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | Provider: `ollama`, `vllm`, `openai`, `anthropic`, `claude_code` |
| `LLM_BASE_URL` | `http://ollama:11434` | Base URL for self-hosted LLM endpoint. Ignored for OpenAI/Anthropic. |
| `LLM_MODEL` | `llama3.1:8b-instruct-q4_K_M` | Model identifier. |
| `LLM_API_KEY` | — | API key for cloud providers (OpenAI, Anthropic). |
| `CLAUDE_CODE_BIN` | `claude` | Path to the Claude Code CLI binary. Used only when `LLM_PROVIDER=claude_code`. |
| `CLAUDE_CODE_MODEL` | — | Model override for Claude Code CLI. Uses CLI default if empty. |

See [`docs/llm-providers.md`](llm-providers.md) for per-provider setup details.

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
