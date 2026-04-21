<p align="center">
  <img src="docs/assets/vellic-banner.svg" alt="vellic" width="600" />
</p>

<p align="center">
  <strong>AI code review for every pull request. Any VCS. Any LLM. No lock-in.</strong>
</p>

<p align="center">
  <a href="https://github.com/vellic-ai/vellic/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/vellic-ai/vellic/ci.yml?branch=main&style=for-the-badge" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge" alt="MIT License"></a>
  <a href="https://github.com/vellic-ai/vellic/releases"><img src="https://img.shields.io/github/v/release/vellic-ai/vellic?include_prereleases&style=for-the-badge" alt="Release"></a>
  <a href="https://github.com/vellic-ai/vellic/stargazers"><img src="https://img.shields.io/github/stars/vellic-ai/vellic?style=for-the-badge" alt="Stars"></a>
  <img src="https://img.shields.io/badge/coverage-85%25%2B-brightgreen?style=for-the-badge" alt="Test Coverage ≥85%">
</p>

<p align="center">
  <a href="#-start-here">Start here</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="docs/README.md">All docs</a> ·
  <a href="docs/architecture.md">Architecture</a> ·
  <a href="docs/vcs-integrations.md">VCS</a> ·
  <a href="docs/llm-providers/index.md">LLM Providers</a> ·
  <a href="docs/deployment/index.md">Deployment</a> ·
  <a href="#roadmap">Roadmap</a>
</p>

---

## 🚀 Start here

**vellic is a self-hosted AI code review tool.** Connect it to your Git platform and every pull request automatically receives an AI-generated inline review — posted directly in your existing VCS workflow.

**Who it's for:**
- Engineering teams who want AI code review without sending code to a SaaS platform.
- Teams that need to control which LLM processes their code (on-prem or BYOK cloud).
- Organisations that want to extend review behaviour with custom rules and prompts.

**30-second quickstart:**

```bash
git clone https://github.com/vellic-ai/vellic.git && cd vellic
cp .env.example .env          # set POSTGRES_PASSWORD + GITHUB_WEBHOOK_SECRET
docker compose up --build -d  # boot the full stack (includes local Ollama)
bash scripts/health-check.sh  # confirm all services are healthy
```

Then point your GitHub webhook at `https://<your-host>/webhook/github` and open a PR.

**Where to go next:**
- Full install walkthrough → [docs/quickstart.md](docs/quickstart.md)
- Connect a different VCS → [docs/vcs-integrations.md](docs/vcs-integrations.md)
- Switch to a cloud LLM → [docs/llm-providers/byok.md](docs/llm-providers/byok.md)
- Browse all docs → [docs/README.md](docs/README.md)

---

## Highlights

- **[VCS-agnostic webhook adapter](docs/vcs-integrations.md)** — normalises GitHub, GitLab, Bitbucket, and custom webhooks into one platform-agnostic `PREvent` model. Adding a new platform is one file.
- **[LLM-agnostic provider registry](docs/llm-providers/index.md)** — Ollama (default, on-prem), OpenAI, Anthropic, Claude Code. Swap provider in the Admin UI, no restart. (vLLM: 🚧 coming soon)
- **[4-stage async pipeline](docs/architecture.md)** — diff fetch → context gather → LLM analysis → VCS feedback posting, all via Redis/Arq with full job tracking.
- **[VCS Reviews API integration](docs/vcs-integrations.md)** — posts structured inline comments at the exact changed lines, grouped into a single review.
- **[Admin SPA](http://localhost:80)** — replay events, inspect jobs, tune LLM config, toggle feature flags. React SPA served by nginx.
- **[Kubernetes-ready](docs/deployment/kubernetes.md)** — manifest-first, no Helm required. Worker HPA scales 1→10 replicas at 70% CPU.
- **[Prompt DSL](docs/prompt-dsl.md)** — ship `.vellic/prompts/` alongside your code to customise exactly what the LLM looks for in each PR.
- **[Feature flags](docs/feature-flags.md)** — granular control over every pipeline stage, VCS adapter, and LLM provider.
- **Privacy-first by default** — self-hosted Ollama ships in the compose stack. Cloud LLM providers show an explicit privacy warning before you save.

---

## How it looks

**Inline review comment posted directly in the PR:**

> _Screenshots will be added once captured from a live deployment — see [VEL-141](/VEL/issues/VEL-141)._

**Admin dashboard** (PR metrics, job inspection, provider config):

> _Screenshots will be added once captured from a live deployment — see [VEL-141](/VEL/issues/VEL-141)._

**PR → vellic → review posted, end to end:**

> _Screenshots will be added once captured from a live deployment — see [VEL-141](/VEL/issues/VEL-141)._

---

## Quick start

Runtime: **Docker ≥ 24 + Docker Compose v2**.

```bash
git clone https://github.com/vellic-ai/vellic.git
cd vellic
cp .env.example .env                    # set POSTGRES_PASSWORD + GITHUB_WEBHOOK_SECRET
docker compose up --build -d            # build images and boot the stack
bash scripts/health-check.sh            # verify all services are healthy
```

All services respond `{"status": "ok"}` when ready:

```
http://localhost:8000/health   api       webhook ingestion
http://localhost:8001/health   admin     REST API for the SPA
http://localhost:8002/health   worker    async pipeline
http://localhost:80            frontend  admin SPA (nginx)
```

### Accessing the admin panel

Open **http://localhost:80** in your browser. On first launch you will be prompted to set an admin password.

| Page | URL | What it does |
|---|---|---|
| Dashboard | `/dashboard` | Live metrics — PRs reviewed, latency p50/p95, failure rate |
| Deliveries | `/deliveries` | Inbound webhooks, status, replay any delivery |
| Jobs | `/jobs` | Pipeline runs per PR — status, duration, error logs |
| Providers | `/settings` | Configure LLM provider, model, API key, base URL |
| Repositories | `/repos` | Per-repo model overrides and enable/disable toggles |
| Feature flags | `/settings` | Toggle pipeline stages, VCS adapters, LLM providers |

Point your VCS webhook at `https://<your-host>/webhook/<platform>`. Full setup: [VCS Integrations](docs/vcs-integrations.md).

---

## Supported platforms

<table>
<tr>
<td valign="top">

**VCS**

| Platform | Status |
|---|---|
| GitHub | ✅ Supported |
| GitLab | ✅ Supported |
| Bitbucket | 🚧 Alpha (feature flag) |
| Gitea / Forgejo | 🚧 Alpha (feature flag) |
| Custom webhook | ✅ One-file adapter |

</td>
<td valign="top">

**LLM**

| Provider | On-prem | BYOK |
|---|---|---|
| Ollama (default) | ✅ | — |
| vLLM | 🚧 Soon | — |
| OpenAI | — | ✅ |
| Anthropic | — | ✅ |
| Claude Code CLI | Partial | ✅ |
| Custom OpenAI-compatible | ✅ | ✅ |

</td>
</tr>
</table>

---

## vs the alternatives

| | vellic | CodeRabbit | Greptile | Qodo | GitHub Copilot Reviews |
|---|:---:|:---:|:---:|:---:|:---:|
| Precision-first (structured inline comments) | ✅ | ✅ | ⚠️ | ✅ | ⚠️ |
| Self-host (your infra, your data) | ✅ | ❌ | ❌ | ❌ | ❌ |
| VCS-agnostic (GitHub + GitLab + custom) | ✅ | ✅ | ⚠️ | ⚠️ | GitHub only |
| LLM-agnostic (swap provider freely) | ✅ | ❌ | ❌ | ❌ | ❌ |
| BYOK (bring your own API key) | ✅ | ⚠️ | ❌ | ⚠️ | ❌ |
| Plugin / MCP tool host | ✅ | ❌ | ❌ | ❌ | ❌ |
| On-prem LLM (Ollama; vLLM soon) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Open source | ✅ MIT | ❌ | ❌ | ❌ | ❌ |

---

## Configuration

Two variables are required. Everything else has a sensible default or is configured through the **Admin UI**.

```dotenv
POSTGRES_PASSWORD=changeme
GITHUB_WEBHOOK_SECRET=<openssl rand -hex 32>
```

LLM provider, model, API keys, and per-repo settings are configured in the Admin SPA — not in `.env`. Full reference: [docs/configuration.md](docs/configuration.md)

---

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
├── packages/     Shared packages (vellic_flags, vellic_plugins)
├── infra/k8s/    Kubernetes manifests + HPA
├── scripts/      Dev tooling (setup, health-check, test-webhook, e2e-local)
└── docs/         Detailed documentation (see docs/README.md)
```

---

## Documentation

| | |
|---|---|
| [Docs index](docs/README.md) | Full navigation — Start here → Install → Configure → Use → Extend → Deploy |
| [Quickstart](docs/quickstart.md) | Full install walkthrough — first config, first PR review |
| [Architecture](docs/architecture.md) | Pipeline internals, webhook flow, LLM abstraction, async job runner |
| [VCS Integrations](docs/vcs-integrations.md) | GitHub, GitLab, Bitbucket, custom adapter guide |
| [LLM Providers](docs/llm-providers/index.md) | All backends, BYOK, privacy notes, adding a new provider |
| [Feature flags](docs/feature-flags.md) | Full flag catalog, ENV overrides, Admin UI toggle |
| [Prompt DSL](docs/prompt-dsl.md) | Custom per-repo review prompts shipped with your code |
| [Rules engine](docs/rules-engine.md) | Repo routing rules, pipeline flags, LLM review instructions |
| [Plugins & MCP](docs/plugins-mcp.md) | MCP server attachment, per-repo tools, process isolation |
| [Configuration](docs/configuration.md) | Full environment variable reference |
| [Deployment](docs/deployment/index.md) | Docker Compose, Kubernetes, Helm, bare-metal |
| [Security](docs/security/index.md) | Encrypted secrets, BYOK, threat model, hardening checklist |
| [Roadmap](#roadmap) | What is built and what is coming |
| [Contributing](docs/contributing.md) | Dev setup, code style, PR checklist |

---

## Troubleshooting

**Stack won't start**

```bash
docker compose logs --tail=50   # check which service is failing
bash scripts/health-check.sh    # confirm which services are healthy
```

Common causes: `POSTGRES_PASSWORD` not set in `.env`, port conflicts (8000/8001/8002/80 already in use), Docker version < 24.

**Webhooks not arriving**

- Check `http://localhost:80/deliveries` — if the delivery appears there, the issue is downstream in the pipeline.
- Confirm your webhook URL matches `https://<host>/webhook/github` (or `/gitlab`, `/bitbucket`).
- Verify the webhook secret matches `GITHUB_WEBHOOK_SECRET` in `.env`.
- Ensure the VCS platform can reach your host (ngrok or similar for local dev).

**PR reviewed but no comments posted**

- Check `http://localhost:80/jobs` — look at the failed job's error log.
- Confirm the LLM provider is reachable: Admin UI → Settings → LLM Provider → test connection.
- If using Ollama, wait for the model to finish pulling: `docker compose logs ollama`.

**Admin UI not loading**

- Confirm `VELLIC_ADMIN_V2=1` is set on the `admin` service in `docker-compose.yml`.
- Check `docker compose ps` — both `admin` and `frontend` services must be running.
- Hard-refresh your browser (`Ctrl+Shift+R`) to clear stale assets.

**LLM returns empty or garbled reviews**

- Check model name in Admin UI → Settings → LLM Provider.
- For Ollama: run `docker compose exec ollama ollama list` to confirm the model is available.
- For cloud providers: verify your API key has sufficient quota.

**Worker crashes immediately**

- Check `DATABASE_URL` — it must match `POSTGRES_PASSWORD` and the postgres service name.
- Run `docker compose restart worker` after fixing env vars; no full rebuild needed.

**GitLab MRs not triggering reviews**

- Ensure `GITLAB_WEBHOOK_SECRET` matches the token set in GitLab webhook settings.
- Check `GITLAB_BASE_URL` is set if using a self-managed GitLab instance.

**Bitbucket / Gitea webhooks not processed**

- These platforms are in alpha. Enable the feature flag first:
  `VELLIC_FEATURE_VCS_BITBUCKET=true` or `VELLIC_FEATURE_VCS_GITEA=true`.
- See [Feature flags](docs/feature-flags.md) and [VCS Integrations](docs/vcs-integrations.md).

**High latency or timeouts on large PRs**

- Large diffs can exceed the LLM's context window. Use a model with a larger context limit.
- Enable `pipeline.context` flag selectively per repo via the Admin UI to reduce payload size.
- For Ollama, increase `OLLAMA_NUM_CTX` in `docker-compose.yml`.

---

## Roadmap

### Now (v0.1 — shipped)

- [x] GitHub webhook ingestion with HMAC validation
- [x] GitLab MR integration
- [x] 4-stage async pipeline (diff → context → LLM → feedback)
- [x] 4 LLM provider adapters (Ollama, OpenAI, Anthropic, Claude Code)
- [x] Prompt DSL — ship prompts alongside your code
- [x] Feature flags — per-repo, per-tenant control over pipeline stages
- [x] DB-backed LLM config — per-repo provider overrides via Admin UI
- [x] Admin panel (event replay, job inspection, provider settings)
- [x] Kubernetes manifests with HPA

### Near-term

- [ ] vLLM provider adapter — self-hosted OpenAI-compatible inference (stub in place, full implementation pending)
- [ ] Bitbucket PR integration (alpha → stable)
- [ ] Issue triage — classify new issues by type/severity; suggest labels and assignees
- [ ] Security scanning — flag vulnerability patterns in diffs
- [ ] Webhook retry / dead-letter queue — resilient delivery with exponential back-off

### Medium-term

- [ ] Test coverage hints — identify untested code paths in PRs
- [ ] Automated changelog — generate structured changelogs from merged PRs
- [ ] Slack / Teams notifications — deliver review summaries to team channels
- [ ] Multi-tenant SaaS mode — per-organisation API keys, isolated pipelines

### Long-term

- [ ] IDE integration — surface AI feedback before the PR is even opened
- [ ] Metrics dashboard — review quality trends, LLM cost tracking, team velocity

Full roadmap: [docs/roadmap.md](docs/roadmap.md)

---

## FAQ

**Does vellic work with private repositories?**
Yes. vellic is self-hosted — it runs in your infrastructure and connects to your VCS platform via webhooks. It never touches GitHub.com / GitLab.com / Bitbucket.org directly; the diff is fetched from your VCS platform's API using the credentials you configure.

**Can I self-host the LLM too?**
Yes. The default stack ships Ollama with a local model — no data leaves your infrastructure at all. Cloud providers (OpenAI, Anthropic) are available but opt-in, and the Admin UI shows an explicit privacy warning before you save. vLLM support (OpenAI-compatible self-hosted inference) is coming soon.

**What data leaves my infrastructure?**
With the default Ollama setup: nothing. The diff is fetched from your VCS, processed inside the worker container, and the review is posted back. If you switch to a cloud LLM provider, the diff is sent to that provider's API — the Admin UI makes this explicit with a warning.

**How do I set up BYOK (Bring Your Own Key)?**
In the Admin UI: Settings → LLM Provider → select OpenAI / Anthropic → paste your API key → Save. The key is encrypted at rest with AES-256-GCM. See [docs/llm-providers/byok.md](docs/llm-providers/byok.md) for full details.

**How does vellic compare in precision to Copilot code review or CodeRabbit?**
vellic posts structured inline comments anchored to the exact changed lines using the VCS Reviews API — the same mechanism used by human code reviewers. You control the model, the prompt, and the review rules. See [the comparison table](#vs-the-alternatives) above.

**Which VCS platforms are supported?**
GitHub and GitLab are fully supported. Bitbucket and Gitea are in alpha (enable via feature flag). Any platform that emits webhooks can be added with a single adapter file. See [docs/vcs-integrations.md](docs/vcs-integrations.md).

**Which LLM providers are supported?**
Ollama (default, local), OpenAI, Anthropic, and Claude Code CLI. vLLM (self-hosted OpenAI-compatible inference) is 🚧 coming soon. See [docs/llm-providers/index.md](docs/llm-providers/index.md).

**How much does it cost to run?**
The self-hosted stack with Ollama has zero LLM API cost — only your compute cost. With a cloud LLM, cost depends on diff size and model. A typical 200-line diff costs ~$0.01–0.05 with GPT-4o or Claude Haiku. Enable `pipeline.coverage_hints` and `pipeline.security_scan` only for repos where the cost-benefit is clear.

**Can I customise what the LLM looks for in each PR?**
Yes. Drop `.md` files in `.vellic/prompts/` in your repo and vellic loads them automatically. See [docs/prompt-dsl.md](docs/prompt-dsl.md).

**Is there a hosted / cloud version?**
Not yet. Vellic is currently open-source self-hosted only. Multi-tenant SaaS mode is on the roadmap.

---

## Contributing

Pull requests are welcome. The highest-impact contributions right now are new VCS adapters (Bitbucket stable, Forgejo) and LLM providers.

See [docs/contributing.md](docs/contributing.md) to get started.

---

## License

[MIT](LICENSE) © 2026 vellic-ai
