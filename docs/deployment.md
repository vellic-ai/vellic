# Deployment

## Local development (Docker Compose)

```bash
# First boot — build images and start all services
docker compose up --build -d

# Tail logs
docker compose logs -f

# Stop everything (preserves volumes)
docker compose down

# Fire a test webhook
bash scripts/test-webhook.sh
```

Health check all services:

```bash
bash scripts/health-check.sh
```

## Production (Kubernetes)

### Prerequisites

- A Kubernetes cluster (EKS, GKE, AKE, or self-managed)
- `kubectl` configured with cluster access
- Container images pushed to `ghcr.io` (done automatically by CI on merge to `main`)

### Deploy

Replace all `CHANGE_ME` placeholders in `infra/k8s/*/secret.yaml` with real values before applying. Use sealed secrets or an external secrets operator — never commit real secrets.

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/api/
kubectl apply -f infra/k8s/worker/
kubectl apply -f infra/k8s/admin/
```

Verify rollout:

```bash
kubectl rollout status deployment/api    -n vellic
kubectl rollout status deployment/worker -n vellic
kubectl rollout status deployment/admin  -n vellic
```

### Auto-scaling

Worker HPA is configured in `infra/k8s/worker/hpa.yaml`:

- Min replicas: 1
- Max replicas: 10
- Scale-up trigger: 70% CPU utilisation

### Rollback

```bash
kubectl rollout undo deployment/api    -n vellic
kubectl rollout undo deployment/worker -n vellic
kubectl rollout undo deployment/admin  -n vellic
```

### Image tags

CI pushes two tags on merge to `main`:

```
ghcr.io/vellic-ai/vellic-api:<short-sha>
ghcr.io/vellic-ai/vellic-api:latest
```

Pin deployments to `<short-sha>` in production — never use `:latest` in a live cluster.

## CI/CD pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every PR and push to `main`:

| Stage | Runs when | What |
|---|---|---|
| Lint | PR + push | `ruff check` on `api/`, `worker/`, `admin/` |
| Test | PR + push | `pytest` per service |
| Build | PR + push | Docker multi-stage build |
| Push | Push to `main` only | Push images to `ghcr.io` |

## Secrets management

In production, never put secrets in `docker-compose.yml` or committed YAML. Recommended approaches:

- **Kubernetes**: use [external-secrets](https://external-secrets.io/) to pull from AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault
- **Docker Compose (staging)**: use a `.env` file that is gitignored, or Docker secrets
