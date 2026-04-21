# Bare-metal / VM — systemd deployment

Use this recipe to run Vellic directly on a Linux host without Docker or
Kubernetes. Suitable for air-gapped environments, hosts with constrained
resources, or operators who prefer native process supervision.

Each Vellic service (`api`, `worker`, `admin`) runs as a systemd unit under
a dedicated `vellic` user. PostgreSQL and Redis are installed from the
distribution package manager.

## Prerequisites

| Requirement | Detail |
|---|---|
| OS | Ubuntu 22.04 / Debian 12 / RHEL 9 (or equivalent) |
| Python | 3.11+ |
| PostgreSQL | 15 or 16 |
| Redis | 7.x |
| CPU | 2 cores (4 recommended) |
| RAM | 4 GB |
| Disk | 20 GB free |

## System setup

```bash
# Create a dedicated system user (no shell, no home directory by default)
sudo useradd --system --no-create-home --shell /usr/sbin/nologin vellic

# Create working directories
sudo mkdir -p /opt/vellic /etc/vellic /var/log/vellic
sudo chown vellic:vellic /opt/vellic /var/log/vellic
sudo chmod 750 /etc/vellic   # restrict env file access
```

Install system dependencies (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip \
    postgresql-16 redis-server
```

## Install Vellic

```bash
# Clone the repository (or unpack a release tarball)
sudo git clone https://github.com/vellic-ai/vellic.git /opt/vellic/src
sudo chown -R vellic:vellic /opt/vellic/src

# Create per-service virtual environments
sudo -u vellic python3.11 -m venv /opt/vellic/venv/api
sudo -u vellic python3.11 -m venv /opt/vellic/venv/worker
sudo -u vellic python3.11 -m venv /opt/vellic/venv/admin

sudo -u vellic /opt/vellic/venv/api/bin/pip install -r /opt/vellic/src/api/requirements.txt
sudo -u vellic /opt/vellic/venv/worker/bin/pip install -r /opt/vellic/src/worker/requirements.txt
sudo -u vellic /opt/vellic/venv/admin/bin/pip install -r /opt/vellic/src/admin/requirements.txt
```

## Environment config

Create `/etc/vellic/env` (mode 640, owned root:vellic) — systemd units
will `EnvironmentFile` this path:

```bash
sudo tee /etc/vellic/env > /dev/null <<'EOF'
# Database
DATABASE_URL=postgresql://vellic:<POSTGRES_PASSWORD>@127.0.0.1:5432/vellic

# Redis
REDIS_URL=redis://127.0.0.1:6379

# API
PORT=8000
GITHUB_WEBHOOK_SECRET=<output-of: openssl rand -hex 32>

# Admin
# PORT is overridden per unit; share the file via EnvironmentFile

# Worker
HEALTH_PORT=8002
LLM_PROVIDER=ollama
LLM_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=llama3.1:8b-instruct-q4_K_M
EOF

sudo chown root:vellic /etc/vellic/env
sudo chmod 640 /etc/vellic/env
```

## Database setup

```bash
# Start PostgreSQL
sudo systemctl enable --now postgresql

# Create the vellic database role and database
sudo -u postgres psql <<'SQL'
CREATE ROLE vellic WITH LOGIN PASSWORD '<POSTGRES_PASSWORD>';
CREATE DATABASE vellic OWNER vellic;
SQL

# Run migrations
sudo -u vellic /opt/vellic/venv/api/bin/python -m alembic \
    --config /opt/vellic/src/api/alembic.ini upgrade head
```

## systemd units

Create one unit file per service.

### `/etc/systemd/system/vellic-api.service`

```ini
[Unit]
Description=Vellic API
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=vellic
Group=vellic
WorkingDirectory=/opt/vellic/src/api
EnvironmentFile=/etc/vellic/env
Environment=PORT=8000
ExecStart=/opt/vellic/venv/api/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vellic-api

[Install]
WantedBy=multi-user.target
```

### `/etc/systemd/system/vellic-worker.service`

```ini
[Unit]
Description=Vellic Worker
After=network.target postgresql.service redis.service vellic-api.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=vellic
Group=vellic
WorkingDirectory=/opt/vellic/src/worker
EnvironmentFile=/etc/vellic/env
ExecStart=/opt/vellic/venv/worker/bin/python -m app.main
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vellic-worker

[Install]
WantedBy=multi-user.target
```

### `/etc/systemd/system/vellic-admin.service`

```ini
[Unit]
Description=Vellic Admin
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=vellic
Group=vellic
WorkingDirectory=/opt/vellic/src/admin
EnvironmentFile=/etc/vellic/env
Environment=PORT=8001
ExecStart=/opt/vellic/venv/admin/bin/uvicorn app.main:app --host 127.0.0.1 --port 8001
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=vellic-admin

[Install]
WantedBy=multi-user.target
```

## First run

```bash
sudo systemctl daemon-reload

sudo systemctl enable --now vellic-api
sudo systemctl enable --now vellic-worker
sudo systemctl enable --now vellic-admin

# Check status
sudo systemctl status vellic-api vellic-worker vellic-admin

# Tail logs
sudo journalctl -u vellic-api -u vellic-worker -u vellic-admin -f
```

Verify health endpoints:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8002/health
```

Each should return `{"status":"ok"}`.

## Reverse proxy (nginx)

Services bind to `127.0.0.1` by default. Use nginx to expose them:

```nginx
server {
    listen 443 ssl;
    server_name vellic.example.com;

    # API (webhook endpoint)
    location /webhooks/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin UI
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Upgrade

```bash
# Pull latest source
cd /opt/vellic/src && sudo -u vellic git pull origin main

# Update dependencies
sudo -u vellic /opt/vellic/venv/api/bin/pip install -r api/requirements.txt
sudo -u vellic /opt/vellic/venv/worker/bin/pip install -r worker/requirements.txt
sudo -u vellic /opt/vellic/venv/admin/bin/pip install -r admin/requirements.txt

# Run database migrations
sudo -u vellic /opt/vellic/venv/api/bin/python -m alembic \
    --config /opt/vellic/src/api/alembic.ini upgrade head

# Restart services
sudo systemctl restart vellic-api vellic-worker vellic-admin

# Confirm they came back healthy
sudo systemctl status vellic-api vellic-worker vellic-admin
```

To roll back, check out the previous tag and re-run the steps above:

```bash
cd /opt/vellic/src && sudo -u vellic git checkout <previous-tag>
```

## Backup

```bash
# Dump the database
sudo -u postgres pg_dump vellic \
  | gzip > /var/backups/vellic-$(date +%Y%m%d-%H%M%S).sql.gz
```

Schedule with cron (`/etc/cron.d/vellic-backup`):

```cron
0 3 * * * postgres pg_dump vellic | gzip > /var/backups/vellic-$(date +\%Y\%m\%d).sql.gz
```

Keep at least 7 days of backups and ship them offsite (S3, rsync to another
host, etc.).

### Restore

```bash
gunzip -c /var/backups/vellic-20260101.sql.gz \
  | sudo -u postgres psql -d vellic
```

Stop services before restoring to avoid write conflicts:

```bash
sudo systemctl stop vellic-api vellic-worker vellic-admin
# … restore …
sudo systemctl start vellic-api vellic-worker vellic-admin
```
