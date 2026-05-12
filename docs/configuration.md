# Configuration

Infrastructure configuration (database, Redis, ports) is done through environment variables. In local dev they are read from `docker-compose.yml`. In production, inject via Kubernetes Secrets or an external secrets manager.

**Everything else — LLM provider, GitHub webhook secret, GitHub App / personal access token, GitLab token, per-repository settings — is configured through the Admin UI** (`http://localhost:8001`), stored encrypted in Postgres, and survives container restarts.

## Required variables

| Variable | Description |
|---|---|
| `POSTGRES_PASSWORD` | Postgres password. Must match across services. |

## Optional variables

| Variable | Default | Description |
|---|---|---|
| `LLM_ENCRYPTION_KEY` | auto-generated | Fernet key used to encrypt secrets at rest (LLM API keys, VCS tokens, webhook HMACs). When unset, the admin container generates one on first boot and writes it to `/data/secrets/llm_encryption_key` inside the shared `vellic_secrets` Docker volume. Set this env var only if you want to manage the key externally (e.g. inject from Vault). **Losing the key locks you out of every encrypted setting — back up the `vellic_secrets` volume alongside `postgres_data`.** |
| `VELLIC_SECRETS_DIR` | `/data/secrets` | Where the auto-generated key file lives inside each container. Override in tests or bare-metal deploys. |

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
| Ollama (optional overlay) | `11434` | `docker-compose.ollama.yml` |

## Generating the Postgres password

```bash
openssl rand -base64 24
```

## Generating a Fernet key manually (optional)

Only needed if you want to manage `LLM_ENCRYPTION_KEY` externally. Otherwise the admin generates one on first boot.

```bash
python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'
```
