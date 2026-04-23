# Feature Flags

Vellic ships a typed flag catalog (`vellic_flags`) that controls which pipeline stages, VCS adapters, LLM providers, and platform features are active. Flags are defined in code; values are resolved at runtime from ENV overrides or Admin UI database overrides.

---

## How flags are resolved

```
ENV override (highest priority)
    │
    ▼
DB override — most-specific scope wins: user > repo > tenant > global
    │
    ▼
Catalog default (lowest priority)
```

The `vellic_flags` package provides `FlagResolver` which runs this chain for every flag, every request.

---

## Toggling flags in the Admin UI

1. Open **http://localhost:80** → **Settings** → **Feature flags**.
2. Each flag shows its key, description, current value, cost impact, and finest scope at which it can be overridden.
3. Toggle the switch. Changes take effect on the next pipeline run.

---

## Toggling flags via ENV

Set `VELLIC_FEATURE_<KEY_UPPER_UNDERSCORED>=true|false` on the relevant service(s).

```bash
# Disable GitHub adapter
VELLIC_FEATURE_VCS_GITHUB=false

# Enable vLLM provider
VELLIC_FEATURE_LLM_VLLM=true

# Turn on security scan pipeline stage
VELLIC_FEATURE_PIPELINE_SECURITY_SCAN=true
```

ENV overrides apply globally (they bypass all DB overrides).

---

## Flag catalog

### VCS adapters

| Key | Default | Scope | Description |
|---|---|---|---|
| `vcs.github` | ✅ on | repo | GitHub PR webhooks and review comments |
| `vcs.gitlab` | ✅ on | repo | GitLab MR webhooks and review comments |
| `vcs.bitbucket` | ⚠️ off | repo | Bitbucket Cloud PR webhooks (alpha) |
| `vcs.gitea` | ⚠️ off | repo | Gitea PR webhooks (alpha) |

### LLM providers

| Key | Default | Scope | Cost impact | Description |
|---|---|---|---|---|
| `llm.openai` | ✅ on | tenant | High | OpenAI-compatible API (GPT-4, etc.) |
| `llm.anthropic` | ✅ on | tenant | High | Anthropic Claude via API key |
| `llm.ollama` | ✅ on | tenant | Low | Self-hosted Ollama (opt-in overlay or your own host) |
| `llm.vllm` | ⚠️ off | tenant | Low | Self-hosted vLLM inference server (🚧 adapter not yet implemented) |

### Pipeline stages

| Key | Default | Scope | Cost impact | Description |
|---|---|---|---|---|
| `pipeline.diff` | ✅ on | repo | None | Fetch PR diff for analysis |
| `pipeline.context` | ✅ on | repo | Low | AST + vector semantic context enrichment |
| `pipeline.llm_analysis` | ✅ on | repo | High | Core code-review LLM pass |
| `pipeline.security_scan` | ⚠️ off | repo | Medium | SAST and secret detection pass |
| `pipeline.coverage_hints` | ⚠️ off | repo | Medium | Test coverage gap suggestions |
| `pipeline.issue_triage` | ⚠️ off | repo | Low | Auto-label and prioritise linked issues |
| `pipeline.commit_summary` | ⚠️ off | repo | Low | One-line commit message generator |
| `pipeline.changelog` | ⚠️ off | repo | Low | Auto-generate CHANGELOG entries |
| `pipeline.notifier_slack` | ⚠️ off | tenant | None | Post review summaries to Slack |
| `pipeline.notifier_teams` | ⚠️ off | tenant | None | Post review summaries to MS Teams |

### AST context (requires `pipeline.context`)

| Key | Default | Scope | Description |
|---|---|---|---|
| `ast.python` | ✅ on | repo | Python tree-sitter AST context |
| `ast.typescript` | ✅ on | repo | TypeScript/JavaScript AST context |
| `ast.go` | ⚠️ off | repo | Go tree-sitter AST context |
| `ast.rust` | ⚠️ off | repo | Rust tree-sitter AST context |

### Vector stores (requires `pipeline.context`)

| Key | Default | Scope | Description |
|---|---|---|---|
| `vector.qdrant` | ⚠️ off | tenant | Qdrant vector store for semantic search |
| `vector.weaviate` | ⚠️ off | tenant | Weaviate vector store |
| `vector.pgvector` | ⚠️ off | tenant | PostgreSQL pgvector extension |
| `vector.chroma` | ⚠️ off | tenant | Chroma vector store |

### Platform

| Key | Default | Scope | Description |
|---|---|---|---|
| `platform.prompt_dsl` | ✅ on | repo | Custom prompt rules DSL (see [Prompt DSL](prompt-dsl.md)) |
| `platform.vcs_settings` | ✅ on | global | GitHub App + GitLab token config tab in Admin UI |
| `platform.llm_config_ui` | ⚠️ off | repo | DB-backed LLM provider config per repo with UI form |
| `plugins.enabled` | ⚠️ off | repo | Plugin loader — upload ZIPs, register per-repo tools |
| `platform.multi_tenant` | ⚠️ off | global | Multi-organisation isolation mode |
| `platform.metrics_export` | ⚠️ off | global | Prometheus / OpenTelemetry metrics export |
| `platform.tracing_export` | ⚠️ off | global | OpenTelemetry distributed tracing export |

---

## Scope levels

| Scope | Override applies to |
|---|---|
| `global` | All tenants, repos, users |
| `tenant` | One organisation |
| `repo` | One repository |
| `user` | One user |

Most-specific scope wins. A `repo`-scoped flag can be overridden per-repo even when the tenant default differs.

---

## Adding a new flag

Edit `packages/vellic_flags/__init__.py` and append a `FlagDef` to `CATALOG`. Run tests with `pytest packages/vellic_flags`. The Admin UI auto-discovers new catalog entries on restart.

---

## Related

- [Rules engine](rules-engine.md) — how pipeline feature flags interact with repo routing rules
- [LLM providers](llm-providers/index.md) — enabling/disabling specific providers
- [Plugins & MCP](plugins-mcp.md) — `plugins.enabled` flag
