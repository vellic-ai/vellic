# vellic

AI-powered code review platform — MVP v0.1.

## Services

| Service | Port | Description |
|---------|------|-------------|
| api | 8000 | FastAPI webhook ingestion (GitHub → Arq) |
| admin | 8001 | FastAPI admin panel (replay, config) |
| worker | 8002 | Arq task worker (analysis pipeline) |
| postgres | 5432 | PostgreSQL 16 |
| redis | 6379 | Redis 7 (Arq queue + cache) |

## Local dev quickstart

```bash
# One-time setup: build images and boot the stack
bash scripts/dev-setup.sh

# Or manually:
docker compose up --build

# Verify all services healthy
bash scripts/health-check.sh
```

### Health endpoints

```bash
curl http://localhost:8000/health  # api
curl http://localhost:8001/health  # admin
curl http://localhost:8002/health  # worker
```

## Environment variables

All services read these from `docker-compose.yml` in local dev. For production, inject via K8s Secret / external-secrets.

| Variable | Default (local) | Description |
|----------|-----------------|-------------|
| `DATABASE_URL` | `postgresql://vellic:vellic@postgres:5432/vellic` | Postgres DSN |
| `REDIS_URL` | `redis://redis:6379` | Redis URL for Arq |
| `GITHUB_WEBHOOK_SECRET` | — | HMAC secret for `X-Hub-Signature-256` validation |
| `LLM_PROVIDER` | `ollama` | LLM backend: `ollama`, `vllm`, `openai`, `anthropic` |
| `LLM_BASE_URL` | `http://localhost:11434` | Base URL for self-hosted LLM |
| `HEALTH_PORT` | `8002` | Worker health server port |

> **Warning:** Setting `LLM_PROVIDER=openai` or `LLM_PROVIDER=anthropic` sends PR diff content to an external provider. A warning is logged at startup.

## Repository layout

```
vellic/
├── api/          FastAPI webhook ingestion service
├── worker/       Arq async task worker
├── admin/        FastAPI admin panel
├── infra/
│   └── k8s/      Kubernetes manifests (namespace, deployments, HPA)
├── scripts/      Dev tooling (setup, health-check)
└── .github/
    └── workflows/
        └── ci.yml  Lint → Test → Build → Push pipeline
```

## CI/CD

GitHub Actions workflow (`.github/workflows/ci.yml`):

1. **Lint** — `ruff check` per service (runs on every PR and push to main)
2. **Test** — `pytest` per service
3. **Build & Push** — Docker images built for all three services; pushed to `ghcr.io` on merge to `main` only

Images are tagged with the short commit SHA and `latest` (main only).

## Kubernetes

Skeleton manifests live under `infra/k8s/`. Apply:

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/api/
kubectl apply -f infra/k8s/worker/
kubectl apply -f infra/k8s/admin/
```

Secrets in `infra/k8s/*/secret.yaml` are stubs — replace `CHANGE_ME` values with real secrets or use external-secrets before deploying to any real cluster.

Worker HPA scales 1→10 replicas at 70% CPU utilization.

## Rollback

```bash
# Roll back a service to the previous revision
kubectl rollout undo deployment/api -n vellic
kubectl rollout undo deployment/worker -n vellic
kubectl rollout undo deployment/admin -n vellic

# Verify
kubectl rollout status deployment/api -n vellic
```
