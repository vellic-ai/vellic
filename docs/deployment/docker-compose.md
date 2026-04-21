# Docker Compose — single-host deployment

Use this recipe for a single VM or bare-metal host where you want full
Vellic running as Docker containers managed by Compose. Suitable for
staging, self-hosted teams, and small production installs (< 10 active
repositories).

## Prerequisites

| Requirement | Minimum version |
|---|---|
| Docker Engine | 24.x |
| Docker Compose plugin | v2.20 |
| CPU | 2 cores |
| RAM | 4 GB (8 GB recommended when using local Ollama) |
| Disk | 20 GB free |

The host must be able to reach `ghcr.io` to pull images, or you must push
them to a private registry first.

## Environment config

Copy the sample env file and fill in required values:

```bash
cp .env.example .env
```

Edit `.env` — **never commit this file**:

```dotenv
# Required
POSTGRES_PASSWORD=<strong-random-password>
GITHUB_WEBHOOK_SECRET=<output-of: openssl rand -hex 32>

# Optional overrides
POSTGRES_USER=vellic
POSTGRES_DB=vellic

# LLM backend (defaults to local Ollama)
LLM_PROVIDER=ollama
LLM_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b-instruct-q4_K_M

# Use an external provider instead of Ollama:
# LLM_PROVIDER=openai
# LLM_BASE_URL=https://api.openai.com/v1
# LLM_API_KEY=sk-...
# LLM_MODEL=gpt-4o-mini
```

Generate secrets:

```bash
openssl rand -hex 32   # webhook secret
openssl rand -base64 24  # postgres password
```

## First run

```bash
# Build all service images and start in the background
docker compose up --build -d

# Watch logs until everything is healthy (Ctrl-C to stop tailing)
docker compose logs -f

# Verify all services are healthy
bash scripts/health-check.sh
```

Expected output from health check:

```
[ok] api     http://localhost:8000/health
[ok] worker  http://localhost:8002/health
[ok] admin   http://localhost:8001/health
```

The Admin UI is available at `http://<host>:8001`. Open it to configure
LLM providers, connect repositories, and verify the installation.

## Expose to the internet (webhook endpoint)

The API service must be reachable from GitHub/GitLab for webhooks.
Recommended approach: put a reverse proxy (nginx / Caddy) in front:

```nginx
server {
    listen 443 ssl;
    server_name vellic.example.com;

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Then register `https://vellic.example.com/webhooks/github` (or `/webhooks/gitlab`)
as your webhook URL in the Admin UI.

## Upgrade

```bash
# Pull latest images (CI pushes on every merge to main)
docker compose pull

# Recreate containers that changed; keep volumes intact
docker compose up -d

# Confirm new containers are healthy
docker compose ps
bash scripts/health-check.sh
```

Pin a specific release by editing `docker-compose.yml` image tags to a
`<sha>` instead of `latest`:

```yaml
image: ghcr.io/vellic-ai/vellic-api:abc1234
```

## Backup

### Database

```bash
# Dump to a timestamped file
docker compose exec postgres \
  pg_dump -U vellic vellic \
  | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

### Restore

```bash
gunzip -c backup-20260101-120000.sql.gz \
  | docker compose exec -T postgres \
    psql -U vellic -d vellic
```

### Volumes

Docker named volumes (`postgres_data`, `ollama_data`) can be backed up
with any volume-snapshot tool (e.g. `docker run --rm -v postgres_data:/data
alpine tar czf - /data > postgres_data.tar.gz`).

Schedule nightly dumps with cron:

```cron
0 3 * * * cd /opt/vellic && docker compose exec -T postgres pg_dump -U vellic vellic | gzip > /backups/vellic-$(date +\%Y\%m\%d).sql.gz
```
