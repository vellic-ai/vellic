# Vellic Documentation

Your navigation index for everything vellic. Pick a section and follow the links.

Vellic is a **self-hosted platform for AI-powered developer automations**. Every automation is a *pipeline*: trigger → stages → outputs. Code review is the flagship built-in pipeline; PR summaries, issue triage, CI-failure explainers, and doc-drift detection are on the near-term roadmap. You can also author your own pipelines in `.vellic/pipelines/*.yaml`.

---

## Start here

| | |
|---|---|
| [What is vellic?](../README.md) | Product overview, highlights, built-in pipelines, quick-start |
| [Quickstart](quickstart.md) | Full install walkthrough — first config, first pipeline run end-to-end |
| [Architecture](architecture.md) | Pipeline runtime, webhook flow, stage primitives, LLM abstraction, async job runner |
| [Roadmap](roadmap.md) | What is built and what is coming — organised around "pipelines as a platform" |

---

## Install

| | |
|---|---|
| [Docker Compose](deployment/docker-compose.md) | Single host or staging — one command brings up the full stack |
| [Kubernetes](deployment/kubernetes.md) | Plain manifests, HPA auto-scaling, recommended for production |
| [Helm](deployment/helm.md) | Values-driven multi-environment installs |
| [Bare-metal / systemd](deployment/bare-metal.md) | Air-gapped hosts, no container runtime |

---

## Configure

| | |
|---|---|
| [Configuration reference](configuration.md) | All environment variables, ports, secret generation |
| [LLM providers](llm-providers/index.md) | Switch between Ollama, OpenAI, Anthropic, Claude Code — plus DB-backed config (vLLM: 🚧 coming soon) |
| [VCS integrations](vcs-integrations.md) | Connect GitHub, GitLab, Bitbucket, or a custom webhook adapter |
| [Feature flags](feature-flags.md) | Enable/disable pipelines, stages, VCS adapters, LLM providers — via Admin UI or ENV |
| [Security & secrets](security/index.md) | Encrypted secrets, BYOK, threat model, least-privilege guide |

---

## Use

| | |
|---|---|
| [Prompt DSL](prompt-dsl.md) | Ship `.vellic/prompts/` and `.vellic/pipelines/` alongside your code |
| [Rules engine](rules-engine.md) | Repo routing rules, pipeline feature flags, LLM instructions |
| [API reference](api-reference.md) | Webhook API (port 8000) and Admin API (port 8001) — endpoints, auth, examples |

---

## Extend

| | |
|---|---|
| [Plugins & MCP](plugins-mcp.md) | Attach MCP tool hosts or Python plugins as pipeline stages |
| [VCS integrations](vcs-integrations.md) | Custom adapter guide — one file to add a new platform |
| [LLM providers](llm-providers/index.md) | Add a new LLM backend — register + implement the two-method protocol |
| [Contributing](contributing.md) | Dev setup, code style, PR checklist, how to add stages / pipelines / adapters |

---

## Deploy

| | |
|---|---|
| [Deployment recipes](deployment/index.md) | Choose the right recipe for your infrastructure |
| [Kubernetes](deployment/kubernetes.md) | Manifest reference, HPA config, secrets injection |
| [Helm](deployment/helm.md) | Chart values reference, multi-environment patterns |

---

## Troubleshoot

| | |
|---|---|
| [Quickstart — troubleshooting](quickstart.md#troubleshooting) | Most common first-run issues |
| [Roadmap](roadmap.md) | What is built and what is coming next |

---

### Cross-links

- Authoring a **new pipeline**? See [Prompt DSL](prompt-dsl.md) → [Rules engine](rules-engine.md) → [Plugins & MCP](plugins-mcp.md) for custom stages.
- Changing **LLM provider**? See [LLM providers](llm-providers/index.md) → [Configuration](configuration.md) → [Feature flags](feature-flags.md) (`llm.*` flags).
- Connecting a **new VCS platform**? See [VCS integrations](vcs-integrations.md) → [Rules engine](rules-engine.md) → [Feature flags](feature-flags.md) (`vcs.*` flags).
- Running in **production**? See [Deployment](deployment/index.md) → [Security](security/index.md) → [Configuration](configuration.md).
