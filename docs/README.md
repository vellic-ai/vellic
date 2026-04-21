# Vellic Documentation

Your navigation index for everything vellic. Pick a section and follow the links.

---

## Start here

| | |
|---|---|
| [What is vellic?](../README.md) | Product overview, highlights, quick-start, supported platforms |
| [Quickstart](quickstart.md) | Full install walkthrough — first config, first PR reviewed end-to-end |
| [Architecture](architecture.md) | How the 4-stage pipeline works, service map, async job runner |

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
| [LLM providers](llm-providers/index.md) | Switch between Ollama, vLLM, OpenAI, Anthropic, Claude Code — plus DB-backed config |
| [VCS integrations](vcs-integrations.md) | Connect GitHub, GitLab, Bitbucket, or a custom webhook adapter |
| [Feature flags](feature-flags.md) | Enable/disable pipeline stages, VCS adapters, LLM providers — via Admin UI or ENV |
| [Security & secrets](security/index.md) | Encrypted secrets, BYOK, threat model, least-privilege guide |

---

## Use

| | |
|---|---|
| [Rules engine](rules-engine.md) | Repo routing rules, pipeline feature flags, LLM review instructions |
| [Prompt DSL](prompt-dsl.md) | Ship `.vellic/prompts/` alongside your code to customise review behaviour |
| [API reference](api-reference.md) | Webhook API (port 8000) and Admin API (port 8001) — endpoints, auth, examples |

---

## Extend

| | |
|---|---|
| [Plugins & MCP](plugins-mcp.md) | Upload plugin ZIPs, register per-repo tools, integrate MCP tool hosts |
| [VCS integrations](vcs-integrations.md) | Custom adapter guide — one file to add a new platform |
| [Contributing](contributing.md) | Dev setup, code style, PR checklist, how to add a VCS adapter or LLM provider |

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

- Changing **LLM provider**? See [LLM providers](llm-providers/index.md) → [Configuration](configuration.md) → [Feature flags](feature-flags.md) (`llm.*` flags).
- Connecting a **new VCS platform**? See [VCS integrations](vcs-integrations.md) → [Rules engine](rules-engine.md) → [Feature flags](feature-flags.md) (`vcs.*` flags).
- Customising **review behaviour**? See [Prompt DSL](prompt-dsl.md) → [Rules engine](rules-engine.md).
- Running in **production**? See [Deployment](deployment/index.md) → [Security](security/index.md) → [Configuration](configuration.md).
