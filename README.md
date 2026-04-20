<div align="center">

# vellic

**AI-powered code review, straight into your GitHub PRs.**

[![CI](https://github.com/vellic-ai/vellic/actions/workflows/ci.yml/badge.svg)](https://github.com/vellic-ai/vellic/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

</div>

---

Vellic listens for GitHub pull-request events, runs your diff through an LLM analysis pipeline, and posts structured code review comments back as a GitHub Review — all without leaving your workflow.

## Features

- **GitHub Webhook ingestion** — validates `X-Hub-Signature-256`, deduplicates events, enqueues jobs via Arq
- **Pluggable LLM backends** — Ollama (default, self-hosted), vLLM, OpenAI, Anthropic, or Claude Code CLI
- **Multi-stage analysis pipeline** — diff fetching → context gathering → LLM analysis → feedback posting
- **GitHub Reviews API** — posts inline comments at the exact changed line, grouped into a single review
- **Admin panel** — replay events, inspect jobs, tune config without redeploying
- **Kubernetes-ready** — Helm-free manifests with HPA (1→10 worker replicas at 70% CPU)
- **Full observability** — structured logging, health endpoints on every service

## Architecture

```
GitHub PR event
      │
      ▼
┌─────────────┐     Arq queue     ┌──────────────────────────────────────┐
│   api :8000 │──────────────────▶│           worker :8002               │
│  (FastAPI)  │                   │  diff_fetcher → context_gatherer     │
└─────────────┘                   │  → llm_analyzer → feedback_poster    │
                                  └───────────────────┬──────────────────┘
┌─────────────┐                                       │
│ admin :8001 │◀── PostgreSQL :5432                   │
│  (FastAPI)  │◀── Redis :6379                        ▼
└─────────────┘                              GitHub Reviews API
```

## Quick start

### Prerequisites

- Docker ≥ 24 and Docker Compose v2
- A GitHub repo with a configured webhook (see [Webhook setup](#webhook-setup))

### 1. Clone and configure

```bash
git clone https://github.com/vellic-ai/vellic.git
cd vellic
cp .env.example .env   # edit POSTGRES_PASSWORD and GITHUB_WEBHOOK_SECRET
```

### 2. Boot the stack

```bash
make up
# or: docker compose up --build
```

### 3. Verify

```bash
bash scripts/health-check.sh
# or manually:
curl http://localhost:8000/health  # api
curl http://localhost:8001/health  # admin
curl http://localhost:8002/health  # worker
```

All three should return `{"status": "ok"}`.

### Webhook setup

1. In your GitHub repo → **Settings → Webhooks → Add webhook**
2. Payload URL: `https://<your-domain>/webhook/github`
3. Content type: `application/json`
4. Secret: same value as `GITHUB_WEBHOOK_SECRET` in `.env`
5. Events: **Pull requests**

## LLM providers

| Provider | `LLM_PROVIDER` value | Notes |
|---|---|---|
| Ollama (default) | `ollama` | Self-hosted; pulled automatically in dev |
| vLLM | `vllm` | OpenAI-compatible endpoint |
| OpenAI | `openai` | Sends PR diffs to OpenAI API |
| Anthropic | `anthropic` | Sends PR diffs to Anthropic API |
| Claude Code CLI | `claude_code` | Uses local `claude` binary |

> **Privacy:** Providers marked with ⚠️ (`openai`, `anthropic`, `claude_code`) send your PR diff content to an external service. A warning is logged at startup when these are selected.

Switch providers at runtime via environment variable — no rebuild needed:

```bash
# Switch to OpenAI
LLM_PROVIDER=openai LLM_MODEL=gpt-4o docker compose up worker
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | — | **Required.** Postgres password |
| `GITHUB_WEBHOOK_SECRET` | — | **Required.** HMAC secret for webhook validation |
| `DATABASE_URL` | `postgresql://vellic:…@postgres:5432/vellic` | Full Postgres DSN |
| `REDIS_URL` | `redis://redis:6379` | Redis URL (Arq queue + cache) |
| `LLM_PROVIDER` | `ollama` | LLM backend (see table above) |
| `LLM_BASE_URL` | `http://ollama:11434` | Base URL for self-hosted LLM |
| `LLM_MODEL` | `llama3.1:8b-instruct-q4_K_M` | Model name/ID |
| `LLM_API_KEY` | — | API key for cloud providers |
| `CLAUDE_CODE_BIN` | `claude` | Path to the `claude` binary |
| `HEALTH_PORT` | `8002` | Worker health server port |

## Repository layout

```
vellic/
├── api/              FastAPI webhook ingestion service
│   └── app/
│       ├── main.py   App entrypoint, route registration
│       └── webhook.py GitHub event handler + Arq enqueue
├── worker/           Arq async task worker
│   └── app/
│       ├── pipeline/ Analysis stages (diff → context → llm → feedback)
│       ├── llm/      Provider registry + adapters
│       └── adapters/ Platform adapters (GitHub)
├── admin/            FastAPI admin panel (replay, config)
├── infra/
│   └── k8s/          Kubernetes manifests (namespace, deployments, HPA)
├── scripts/          Dev tooling (setup, health-check, test-webhook)
├── docker-compose.yml
└── .github/
    └── workflows/ci.yml
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every PR and push to `main`:

| Stage | What it does |
|---|---|
| **Lint** | `ruff check` across all three services |
| **Test** | `pytest` per service |
| **Build & Push** | Docker images built for `api`, `worker`, `admin`; pushed to `ghcr.io` on `main` merges only |

Images are tagged with the short commit SHA and `latest` (main only):

```
ghcr.io/vellic-ai/vellic-api:<sha>
ghcr.io/vellic-ai/vellic-worker:<sha>
ghcr.io/vellic-ai/vellic-admin:<sha>
```

## Kubernetes

Skeleton manifests live under `infra/k8s/`. Replace `CHANGE_ME` placeholders in `*/secret.yaml` before applying.

```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/api/
kubectl apply -f infra/k8s/worker/
kubectl apply -f infra/k8s/admin/
```

Worker HPA scales from 1 to 10 replicas at 70% CPU utilization.

### Rollback

```bash
kubectl rollout undo deployment/api    -n vellic
kubectl rollout undo deployment/worker -n vellic
kubectl rollout undo deployment/admin  -n vellic

# Verify
kubectl rollout status deployment/api -n vellic
```

## Development

```bash
# Run linter
cd api && ruff check .
cd worker && ruff check .
cd admin && ruff check .

# Run tests
cd api && pytest
cd worker && pytest
cd admin && pytest

# Fire a test webhook
make test-webhook
```

## Contributing

Pull requests are welcome. For significant changes, open an issue first to discuss what you'd like to change.

1. Fork the repo and create a feature branch: `git checkout -b feat/my-feature`
2. Make your changes and add tests
3. Run `ruff check` and `pytest` locally
4. Open a PR against `main`

## License

[MIT](LICENSE) © 2026 vellic-ai
