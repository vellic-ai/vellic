<div align="center">

<br/>

```
 ██╗   ██╗███████╗██╗     ██╗     ██╗ ██████╗
 ██║   ██║██╔════╝██║     ██║     ██║██╔════╝
 ██║   ██║█████╗  ██║     ██║     ██║██║
 ╚██╗ ██╔╝██╔══╝  ██║     ██║     ██║██║
  ╚████╔╝ ███████╗███████╗███████╗██║╚██████╗
   ╚═══╝  ╚══════╝╚══════╝╚══════╝╚═╝ ╚═════╝
```

### Bring AI into every step of your development workflow.
### Any VCS. Any LLM. No lock-in.

<br/>

[![CI](https://github.com/vellic-ai/vellic/actions/workflows/ci.yml/badge.svg)](https://github.com/vellic-ai/vellic/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Docker](https://img.shields.io/badge/docker-compose-2496ED?logo=docker&logoColor=white)](docker-compose.yml)
[![Kubernetes](https://img.shields.io/badge/kubernetes-ready-326CE5?logo=kubernetes&logoColor=white)](infra/k8s/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](docs/contributing.md)

<br/>

---

</div>

Vellic is an **open-source AI integration platform for developer workflows**. Point it at your Git platform and an LLM of your choice, and it starts augmenting your team — automated code review, PR analysis, and more — delivered directly inside the tools your engineers already use.

It is designed to be:

- **VCS agnostic** — GitHub, GitLab, Bitbucket, and any platform that emits webhooks
- **LLM agnostic** — Ollama, vLLM, OpenAI, Anthropic, Claude Code, or your own endpoint
- **Self-hostable** — runs on Docker Compose locally or Kubernetes in production
- **Extensible** — clean adapter interfaces; adding a new VCS or LLM is a single file

---

## What it does today

| Capability | Description |
|---|---|
| **AI Code Review** | Analyses every PR diff and posts inline review comments via the VCS Reviews API |
| **Multi-platform webhooks** | Receives, validates (HMAC), and normalises events from any VCS into a unified internal model |
| **Async job pipeline** | 4-stage pipeline: diff fetch → context gathering → LLM analysis → feedback posting |
| **Admin panel** | Replay events, inspect jobs, tune configuration — no redeploy needed |

> **Roadmap**: issue triage, commit summarisation, automated changelog, security scanning, and more. See [`docs/roadmap.md`](docs/roadmap.md).

---

## Supported platforms

<table>
<tr>
<td align="center"><strong>VCS</strong></td>
<td>

| Platform | Status |
|---|---|
| GitHub | ✅ Supported |
| GitLab | 🚧 In progress |
| Bitbucket | 📋 Planned |
| Gitea / Forgejo | 📋 Planned |
| Any webhook | ✅ Via custom adapter |

</td>
<td align="center"><strong>LLM</strong></td>
<td>

| Provider | `LLM_PROVIDER` |
|---|---|
| Ollama (default) | `ollama` |
| vLLM | `vllm` |
| OpenAI | `openai` |
| Anthropic | `anthropic` |
| Claude Code CLI | `claude_code` |
| Custom endpoint | `vllm` (OpenAI-compatible) |

</td>
</tr>
</table>

See [`docs/vcs-integrations.md`](docs/vcs-integrations.md) and [`docs/llm-providers.md`](docs/llm-providers.md) for detailed setup.

---

## Architecture

```
 Webhook event (any VCS)
        │
        ▼
 ┌──────────────────────────────────────────────────────────┐
 │                        api  :8000                        │
 │  Validate signature → Normalise → Enqueue (Arq / Redis)  │
 └─────────────────────────┬────────────────────────────────┘
                           │  Redis queue
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │                      worker  :8002                       │
 │                                                          │
 │  ┌────────────┐  ┌─────────────────┐  ┌───────────────┐ │
 │  │ diff fetch │→ │ context gather  │→ │  LLM analyze  │ │
 │  └────────────┘  └─────────────────┘  └───────┬───────┘ │
 │                                               │         │
 │  ┌────────────────────────────────────────────▼───────┐ │
 │  │               feedback poster                      │ │
 │  │   VCS Reviews API  (GitHub / GitLab / …)           │ │
 │  └────────────────────────────────────────────────────┘ │
 └──────────────────────────────────────────────────────────┘
        │                           │
        ▼                           ▼
   PostgreSQL :5432             Redis :6379

 ┌──────────────────────────────────────────────────────────┐
 │                      admin  :8001                        │
 │         Event replay · Job inspector · Config            │
 └──────────────────────────────────────────────────────────┘
```

Deep dive: [`docs/architecture.md`](docs/architecture.md)

---

## Quick start

### Prerequisites

- Docker ≥ 24 + Docker Compose v2
- A webhook endpoint reachable from your VCS (or use [ngrok](https://ngrok.com) for local dev)

### 1. Clone and configure

```bash
git clone https://github.com/vellic-ai/vellic.git
cd vellic
cp .env.example .env
```

Edit `.env` — two required fields:

```dotenv
POSTGRES_PASSWORD=changeme
GITHUB_WEBHOOK_SECRET=your-hmac-secret
```

### 2. Boot the stack

```bash
make up
# shorthand for: docker compose up --build -d
```

### 3. Verify health

```bash
bash scripts/health-check.sh
```

All three services respond `{"status": "ok"}` when ready.

```bash
curl http://localhost:8000/health   # api
curl http://localhost:8001/health   # admin
curl http://localhost:8002/health   # worker
```

### 4. Connect your VCS

Point your platform's webhook at `https://<your-host>/webhook/github` (or the matching adapter path) and configure the HMAC secret. Detailed per-platform setup: [`docs/vcs-integrations.md`](docs/vcs-integrations.md).

---

## Configuration

Full reference: [`docs/configuration.md`](docs/configuration.md)

| Variable | Required | Default | Description |
|---|---|---|---|
| `POSTGRES_PASSWORD` | ✅ | — | Postgres password |
| `GITHUB_WEBHOOK_SECRET` | ✅ | — | HMAC secret for webhook validation |
| `LLM_PROVIDER` | | `ollama` | LLM backend |
| `LLM_BASE_URL` | | `http://ollama:11434` | Base URL for self-hosted LLM |
| `LLM_MODEL` | | `llama3.1:8b-instruct-q4_K_M` | Model name/ID |
| `LLM_API_KEY` | | — | API key for cloud LLM providers |
| `DATABASE_URL` | | derived | Full Postgres DSN |
| `REDIS_URL` | | `redis://redis:6379` | Redis DSN |

> **Privacy:** `openai`, `anthropic`, and `claude_code` providers send PR diff content to external services. A warning is logged at startup. Self-hosted providers (`ollama`, `vllm`) keep everything on-prem.

---

## Repository layout

```
vellic/
├── api/              Webhook ingestion service (FastAPI)
├── worker/           Async analysis pipeline (Arq)
│   └── app/
│       ├── pipeline/ 4-stage pipeline (diff → context → llm → feedback)
│       ├── llm/      LLM provider registry + adapters
│       └── adapters/ VCS platform adapters
├── admin/            Admin panel (FastAPI)
├── infra/
│   └── k8s/          Kubernetes manifests + HPA
├── scripts/          Dev tooling
├── docs/             ← Detailed documentation lives here
│   ├── architecture.md
│   ├── vcs-integrations.md
│   ├── llm-providers.md
│   ├── configuration.md
│   ├── deployment.md
│   └── roadmap.md
└── docker-compose.yml
```

---

## CI/CD

Pipeline runs on every PR and push to `main`:

```
Lint (ruff) → Test (pytest) → Build → Push to ghcr.io
```

Images tagged as `ghcr.io/vellic-ai/vellic-{service}:{sha}` and `:latest` (main only).

Deployment guide: [`docs/deployment.md`](docs/deployment.md)

---

## Documentation

| Doc | Description |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | System design, service boundaries, data flow |
| [`docs/vcs-integrations.md`](docs/vcs-integrations.md) | Connecting GitHub, GitLab, Bitbucket, custom platforms |
| [`docs/llm-providers.md`](docs/llm-providers.md) | Configuring and swapping LLM backends |
| [`docs/configuration.md`](docs/configuration.md) | Full environment variable reference |
| [`docs/deployment.md`](docs/deployment.md) | Docker Compose, Kubernetes, rollback |
| [`docs/roadmap.md`](docs/roadmap.md) | What's coming next |

---

## Contributing

We welcome contributions — new VCS adapters, LLM providers, pipeline stages, bug fixes, and docs improvements.

1. Read [`docs/contributing.md`](docs/contributing.md) before opening a PR
2. Fork and create a branch: `git checkout -b feat/your-feature`
3. Run `ruff check` and `pytest` locally
4. Open a PR against `main`

---

## License

[MIT](LICENSE) © 2026 vellic-ai
