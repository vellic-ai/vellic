# Kubernetes — manifest-based deployment

Use this recipe to deploy Vellic to an existing Kubernetes cluster using
the plain YAML manifests in `infra/k8s/`. Suitable for teams that already
manage a cluster and want full control over resource definitions.

For a packaged, values-driven install see [Helm](./helm.md).

## Prerequisites

| Requirement | Detail |
|---|---|
| Kubernetes | 1.27+ |
| `kubectl` | matching minor version |
| Container registry access | images at `ghcr.io/vellic-ai/` |
| PostgreSQL | external managed instance **or** in-cluster (see below) |
| Redis | external managed instance **or** in-cluster |

CI pushes images to `ghcr.io/vellic-ai/vellic-{api,worker,admin}` on every
merge to `main`. No registry credentials are needed if your cluster nodes
can pull from `ghcr.io` anonymously (public images).

## Environment config

All secrets live in `infra/k8s/{service}/secret.yaml`. Each file ships
with `CHANGE_ME` stubs — **replace them before applying**.

**Option A — edit in place (dev/staging only):**

```bash
# Replace stubs in all secret files
sed -i 's/CHANGE_ME/<real-value>/g' infra/k8s/api/secret.yaml
sed -i 's/CHANGE_ME/<real-value>/g' infra/k8s/worker/secret.yaml
sed -i 's/CHANGE_ME/<real-value>/g' infra/k8s/admin/secret.yaml
```

**Option B — external-secrets (production recommended):**

Install [external-secrets operator](https://external-secrets.io/) and
replace the `Secret` manifests with `ExternalSecret` objects pointing to
AWS Secrets Manager, GCP Secret Manager, or Vault. Never commit real
credentials to the manifests.

Key values required per service:

| Service | Key | Description |
|---|---|---|
| api | `DATABASE_URL` | Full Postgres DSN |
| api | `REDIS_URL` | Redis DSN |
| api | `GITHUB_WEBHOOK_SECRET` | HMAC secret |
| worker | `DATABASE_URL` | Full Postgres DSN |
| worker | `REDIS_URL` | Redis DSN |
| admin | `DATABASE_URL` | Full Postgres DSN |
| admin | `REDIS_URL` | Redis DSN |

## First run

```bash
# 1. Create the namespace
kubectl apply -f infra/k8s/namespace.yaml

# 2. Apply all service resources
kubectl apply -f infra/k8s/api/
kubectl apply -f infra/k8s/worker/
kubectl apply -f infra/k8s/admin/

# 3. Wait for rollouts
kubectl rollout status deployment/api    -n vellic
kubectl rollout status deployment/worker -n vellic
kubectl rollout status deployment/admin  -n vellic
```

Verify pods are running:

```bash
kubectl get pods -n vellic
```

Expected:

```
NAME                      READY   STATUS    RESTARTS   AGE
api-xxxxxxxxx-xxxxx       1/1     Running   0          1m
worker-xxxxxxxxx-xxxxx    1/1     Running   0          1m
admin-xxxxxxxxx-xxxxx     1/1     Running   0          1m
```

## Auto-scaling

Worker HPA is configured in `infra/k8s/worker/hpa.yaml`:

- Min replicas: 1
- Max replicas: 10
- Scale trigger: 70% average CPU utilisation

Metrics server must be installed in the cluster for HPA to function:

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

Check HPA status:

```bash
kubectl get hpa -n vellic
```

## Accessing services

The `admin` and `api` services are exposed as `ClusterIP` by default.
To reach them from outside the cluster, add an Ingress or use port-forward
for quick access:

```bash
kubectl port-forward svc/admin 8001:8001 -n vellic
kubectl port-forward svc/api   8000:8000 -n vellic
```

For production, add an Ingress resource pointing to each service.

## Upgrade

CI tags images as both `<short-sha>` and `latest` on each `main` merge.
Pin deployments to a specific SHA in production:

```bash
# Update api to a new image
kubectl set image deployment/api \
  api=ghcr.io/vellic-ai/vellic-api:<new-sha> \
  -n vellic

kubectl set image deployment/worker \
  worker=ghcr.io/vellic-ai/vellic-worker:<new-sha> \
  -n vellic

kubectl set image deployment/admin \
  admin=ghcr.io/vellic-ai/vellic-admin:<new-sha> \
  -n vellic

# Watch rollout
kubectl rollout status deployment/api    -n vellic
kubectl rollout status deployment/worker -n vellic
kubectl rollout status deployment/admin  -n vellic
```

## Rollback

```bash
kubectl rollout undo deployment/api    -n vellic
kubectl rollout undo deployment/worker -n vellic
kubectl rollout undo deployment/admin  -n vellic
```

View rollout history:

```bash
kubectl rollout history deployment/api -n vellic
```

Roll back to a specific revision:

```bash
kubectl rollout undo deployment/api --to-revision=2 -n vellic
```

## Backup

Vellic stores all state in PostgreSQL. Back up the database on the schedule
appropriate for your cluster:

**Kubernetes CronJob example:**

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: vellic-db-backup
  namespace: vellic
spec:
  schedule: "0 3 * * *"
  jobTemplate:
    spec:
      template:
        spec:
          containers:
            - name: pg-dump
              image: postgres:16-alpine
              env:
                - name: DATABASE_URL
                  valueFrom:
                    secretKeyRef:
                      name: api-secrets
                      key: DATABASE_URL
              command:
                - /bin/sh
                - -c
                - pg_dump "$DATABASE_URL" | gzip > /backup/vellic-$(date +%Y%m%d).sql.gz
              volumeMounts:
                - name: backup-storage
                  mountPath: /backup
          restartPolicy: OnFailure
          volumes:
            - name: backup-storage
              persistentVolumeClaim:
                claimName: vellic-backup-pvc
```

Adjust the `persistentVolumeClaim` to match your cluster's storage class,
or replace the volume with an `emptyDir` and add a sidecar that ships the
dump to S3 / GCS.
