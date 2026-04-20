<p align="center">
  <img src="docs/assets/vellic-banner.svg" alt="vellic" width="600" />
</p>

<p align="center">
  <strong>AI integration for your entire development workflow.</strong><br/>
  Any VCS. Any LLM. No lock-in.
</p>

<p align="center">
  <a href="https://github.com/vellic-ai/vellic/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/vellic-ai/vellic/ci.yml?branch=main&style=for-the-badge" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/vellic-ai/vellic/releases"><img src="https://img.shields.io/github/v/release/vellic-ai/vellic?include_prereleases&style=for-the-badge" alt="Release"></a>
  <a href="https://github.com/vellic-ai/vellic/stargazers"><img src="https://img.shields.io/github/stars/vellic-ai/vellic?style=for-the-badge" alt="Stars"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="docs/quickstart.md">Quickstart Guide</a> ·
  <a href="docs/architecture.md">Architecture</a> ·
  <a href="docs/vcs-integrations.md">VCS Integrations</a> ·
  <a href="docs/llm-providers.md">LLM Providers</a> ·
  <a href="docs/deployment.md">Deployment</a> ·
  <a href="docs/roadmap.md">Roadmap</a> ·
  <a href="docs/contributing.md">Contributing</a>
</p>

---

**vellic** connects your Git platform to an AI analysis pipeline. Every pull request gets reviewed, every diff gets analysed, and structured feedback lands directly inside your existing VCS workflow — with no code changes and no new tools to learn.

It is self-hosted, swap the LLM with a single env var, and adding a new VCS platform is a single file.

> GitHub, GitLab, Bitbucket, and any platform that emits webhooks. Ollama, vLLM, OpenAI, Anthropic, Claude Code — or bring your own endpoint.

## Highlights

- **[VCS-agnostic webhook adapter](docs/vcs-integrations.md)** — normalises GitHub, GitLab, Bitbucket, and custom webhooks into one platform-agnostic `PREvent` model. Adding a new platform is one file.
- **[LLM-agnostic provider registry](docs/llm-providers.md)** — Ollama (default, on-prem), vLLM, OpenAI, Anthropic, Claude Code. Swap with one env var, no rebuild.
- **[4-stage async pipeline](docs/architecture.md)** — diff fetch → context gather → LLM analysis → VCS feedback posting, all via Redis/Arq with full job tracking.
- **[VCS Reviews API integration](docs/vcs-integrations.md)** — posts structured inline comments at the exact changed lines, grouped into a single review.
- **[Admin SPA](http://localhost:80)** — replay events, inspect jobs, tune LLM config. React SPA served by nginx; admin FastAPI serves the REST API on port 8001.
- **[Kubernetes-ready](docs/deployment.md)** — manifest-first, no Helm required. Worker HPA scales 1→10 replicas at 70% CPU.
- **Privacy-first by default** — self-hosted Ollama ships in the compose stack. Cloud LLM providers show a privacy warning in the Admin UI when selected.

## Quick start

Runtime: **Docker ≥ 24 + Docker Compose v2**.

```bash
git clone https://github.com/vellic-ai/vellic.git
cd vellic
cp .env.example .env                    # set POSTGRES_PASSWORD + GITHUB_WEBHOOK_SECRET
docker compose up --build -d            # build images and boot the stack
bash scripts/health-check.sh            # verify all three services are healthy
```

All services respond `{"status": "ok"}` when ready:

```
http://localhost:8000/health   api
http://localhost:8001/health   admin
http://localhost:8002/health   worker
```

Point your VCS webhook at `https://<your-host>/webhook/<platform>`. Full setup: [VCS Integrations](docs/vcs-integrations.md).

## Supported platforms

<table>
<tr>
<td valign="top">

**VCS**

| Platform | Status |
|---|---|
| GitHub | ✅ Supported |
| GitLab | 🚧 In progress |
| Bitbucket | 📋 Planned |
| Gitea / Forgejo | 📋 Planned |
| Custom webhook | ✅ One-file adapter |

</td>
<td valign="top">

**LLM**

| Provider | `LLM_PROVIDER` | On-prem |
|---|---|---|
| Ollama | `ollama` | ✅ |
| vLLM | `vllm` | ✅ |
| OpenAI | `openai` | — |
| Anthropic | `anthropic` | — |
| Claude Code CLI | `claude_code` | — |
| Custom OpenAI-compatible | `vllm` | ✅ |

</td>
</tr>
</table>

## Configuration

Two variables are required. Everything else has a sensible default or is configured through the **Admin UI** at `http://localhost:8001`.

```dotenv
POSTGRES_PASSWORD=changeme
GITHUB_WEBHOOK_SECRET=<openssl rand -hex 32>
```

LLM provider, model, API keys, and per-repo settings are configured in the Admin SPA — not in `.env`.

Set `VELLIC_ADMIN_V2=1` on the `admin` service (default in `docker-compose.yml`) to enable nginx-served SPA mode. Without it, the admin falls back to serving legacy static files from `admin/static/`.

Full infrastructure reference: [docs/configuration.md](docs/configuration.md)

## Repository layout

```
vellic/
├── api/          Webhook ingestion (FastAPI, port 8000)
├── worker/       Async pipeline (Arq, port 8002)
│   └── app/
│       ├── pipeline/   4 stages: diff → context → llm → feedback
│       ├── llm/        Provider registry + adapters
│       └── adapters/   VCS platform adapters
├── admin/        Admin API (FastAPI, port 8001) — auth, stats, settings, delivery replay
├── frontend/     Admin SPA (Vite + React + TypeScript) — served by nginx on port 80
├── infra/k8s/    Kubernetes manifests + HPA
├── scripts/      Dev tooling (setup, health-check, test-webhook, e2e-local)
└── docs/         Detailed documentation
```

## Documentation

| | |
|---|---|
| [Quickstart](docs/quickstart.md) | Full install walkthrough — first config, first PR review, troubleshooting |
| [Architecture](docs/architecture.md) | Pipeline internals, webhook flow, LLM abstraction, async job runner |
| [VCS Integrations](docs/vcs-integrations.md) | GitHub, GitLab, Bitbucket, custom adapter guide |
| [LLM Providers](docs/llm-providers.md) | All backends, env vars, privacy notes, adding a new provider |
| [Configuration](docs/configuration.md) | Full environment variable reference |
| [Deployment](docs/deployment.md) | Docker Compose, Kubernetes, rollback, secrets |
| [Roadmap](docs/roadmap.md) | What is built and what is coming |
| [Contributing](docs/contributing.md) | Dev setup, code style, PR checklist |

## Contributing

Pull requests are welcome. The highest-impact contributions right now are new VCS adapters (GitLab, Bitbucket) and LLM providers.

See [docs/contributing.md](docs/contributing.md) to get started.

## License

[MIT](LICENSE) © 2026 vellic-ai
