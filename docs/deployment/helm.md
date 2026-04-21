# Helm — chart-based deployment

The Vellic Helm chart packages the same manifests from `infra/k8s/` into a
single, values-driven release. Use this recipe when you want repeatable
installs across multiple environments (dev / staging / prod) with minimal
manifest duplication.

> **Chart availability:** The chart is located at `infra/helm/vellic/`.
> It is also published to the OCI registry at
> `ghcr.io/vellic-ai/charts/vellic` on each release tag.

## Prerequisites

| Requirement | Detail |
|---|---|
| Kubernetes | 1.27+ |
| Helm | 3.12+ |
| `kubectl` | configured with cluster access |
| Container registry access | `ghcr.io/vellic-ai/` |

## Environment config

Helm uses a `values.yaml` file. The chart ships `values.yaml` with safe
defaults; override only what you need.

Create a `values.override.yaml` file (keep it out of version control if it
contains secrets):

```yaml
# values.override.yaml

image:
  tag: "abc1234"   # pin to a specific SHA in production

api:
  replicaCount: 2
  env:
    GITHUB_WEBHOOK_SECRET: ""   # set via --set or external secrets

worker:
  replicaCount: 1
  autoscaling:
    enabled: true
    minReplicas: 1
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70

postgresql:
  enabled: true          # deploy in-cluster Postgres (dev/staging)
  auth:
    password: ""         # set via --set postgresql.auth.password=<value>

redis:
  enabled: true          # deploy in-cluster Redis

ingress:
  enabled: false
  # enabled: true
  # host: vellic.example.com
  # tls: true
```

For production, set secrets via `--set` flags or inject them through an
external-secrets operator rather than writing them into any file:

```bash
--set api.env.GITHUB_WEBHOOK_SECRET="$(cat /run/secrets/webhook-secret)"
--set postgresql.auth.password="$(cat /run/secrets/pg-password)"
```

## First run

**Install from local chart:**

```bash
helm install vellic infra/helm/vellic \
  --namespace vellic \
  --create-namespace \
  -f values.override.yaml \
  --set api.env.GITHUB_WEBHOOK_SECRET="<your-secret>" \
  --set postgresql.auth.password="<your-pg-password>"
```

**Install from OCI registry:**

```bash
helm install vellic oci://ghcr.io/vellic-ai/charts/vellic \
  --version 0.1.0 \
  --namespace vellic \
  --create-namespace \
  -f values.override.yaml
```

Watch the rollout:

```bash
kubectl rollout status deployment/vellic-api    -n vellic
kubectl rollout status deployment/vellic-worker -n vellic
kubectl rollout status deployment/vellic-admin  -n vellic
```

Verify the release:

```bash
helm list -n vellic
helm status vellic -n vellic
```

## Upgrade

```bash
helm upgrade vellic infra/helm/vellic \
  --namespace vellic \
  -f values.override.yaml \
  --set image.tag="<new-sha>"
```

Or from the registry:

```bash
helm upgrade vellic oci://ghcr.io/vellic-ai/charts/vellic \
  --version <new-chart-version> \
  --namespace vellic \
  -f values.override.yaml
```

Helm keeps a release history. Confirm the revision number after upgrade:

```bash
helm history vellic -n vellic
```

## Rollback

```bash
# Roll back to the previous release
helm rollback vellic -n vellic

# Roll back to a specific revision
helm rollback vellic 2 -n vellic
```

## Backup

If you use the bundled in-cluster PostgreSQL (the `postgresql.enabled: true`
subchart), back up with:

```bash
# Get the postgres pod name
PG_POD=$(kubectl get pod -n vellic -l app.kubernetes.io/component=postgresql -o jsonpath='{.items[0].metadata.name}')

# Dump and save locally
kubectl exec -n vellic "$PG_POD" -- \
  pg_dump -U vellic vellic \
  | gzip > vellic-backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

For an external managed database (RDS, Cloud SQL, etc.) use your cloud
provider's native snapshot / backup mechanism instead.

## Uninstall

```bash
helm uninstall vellic -n vellic

# Optionally remove the namespace (deletes all remaining resources)
kubectl delete namespace vellic
```

> Persistent volume claims are **not** deleted automatically on uninstall.
> Remove them explicitly if you want to free the storage.
