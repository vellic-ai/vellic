# Rules Engine Reference

Vellic controls which pull requests it reviews, which LLM processes them, and how the analysis runs through three complementary rule layers: **repo routing rules**, **pipeline feature flags**, and **LLM review instructions**. This reference covers each layer and how they interact.

---

## Overview

```
Webhook arrives
    │
    ▼
[1] Repo routing rules  ──► repo not in allow-list? → skip
    │
    ▼
[2] Pipeline feature flags  ──► stage disabled? → skip stage
    │
    ▼
[3] LLM review instructions  ──► controls what the model looks for
    │
    ▼
Review posted to VCS
```

---

## Layer 1: Repo Routing Rules

Repo routing rules determine which repositories Vellic analyses. If a repository has no matching entry in the allow-list, Vellic silently ignores its webhooks.

### Adding a repository

Via the Admin UI: **Settings → Repositories → Add**.

Via the Admin API:

```http
POST /admin/settings/repos
Content-Type: application/json

{
  "platform": "github",
  "slug": "acme-org/backend",
  "provider": "ollama",
  "model": "qwen2.5-coder:14b"
}
```

| Field | Required | Description |
|---|---|---|
| `platform` | yes | `github` or `gitlab` |
| `slug` | yes* | `org/repo` or `org/*` for a wildcard rule |
| `org` + `repo` | yes* | Alternative to `slug` |
| `provider` | no | LLM provider for this repo. Inherits global default if omitted. |
| `model` | no | Model name for this repo. Inherits global default if omitted. |
| `enabled` | no | `true` (default). Set `false` to pause reviews without removing the rule. |

\* Provide either `slug` or both `org` + `repo`.

### Wildcard rules

A slug ending in `/*` matches any repo in that organisation:

```json
{ "platform": "github", "slug": "acme-org/*", "provider": "ollama", "model": "qwen2.5-coder:14b" }
```

When both a wildcard rule and a specific-repo rule exist, the **specific repo rule wins**.

### Disabling a repository

Toggle off via the Admin UI, or call:

```http
POST /admin/settings/repos/{repo_id}/toggle
```

Disabled repos are in the allow-list but skipped at processing time. Their webhook deliveries are marked `processed` without running the pipeline.

### Deleting a repository

```http
DELETE /admin/settings/repos/{repo_id}
```

Once deleted, webhooks from that repository are ignored again.

---

## Layer 2: Pipeline Feature Flags

Feature flags enable or disable individual pipeline stages and platform capabilities without redeploying. They are global (not per-repo).

### Reading the flag state

```http
GET /admin/features
```

Response:

```json
{
  "flags": {
    "pipeline.diff": true,
    "pipeline.llm_analysis": true,
    "pipeline.security_scan": false,
    ...
  },
  "catalog": [ ... ],
  "snapshot_at": "2026-04-21T09:00:00Z"
}
```

### Changing a flag

```http
PUT /admin/features/{flag_key}
Content-Type: application/json

{ "enabled": true }
```

Changes take effect immediately for new jobs. In-flight jobs use the flag state captured at dispatch time.

### Flag override precedence

```
In-memory override (API / Admin UI)
    ▼ wins over
Environment variable  VELLIC_FEATURE_<UPPER_KEY_WITH_DOTS_AS_UNDERSCORES>
    ▼ wins over
Built-in default
```

Environment variable example — enable Bitbucket at container start:

```bash
VELLIC_FEATURE_VCS_BITBUCKET=true
```

In-memory overrides reset on service restart. For persistent overrides, use the Admin UI or set the environment variable in your deployment manifest.

### Full flag catalog

#### VCS adapters

| Key | Default | Description |
|---|---|---|
| `vcs.github` | `true` | GitHub PR webhooks and review comments |
| `vcs.gitlab` | `true` | GitLab MR webhooks and review comments |
| `vcs.bitbucket` | `false` | Bitbucket Cloud PR webhooks (alpha) |
| `vcs.gitea` | `false` | Gitea PR webhooks (alpha) |

#### LLM providers

| Key | Default | Description |
|---|---|---|
| `llm.openai` | `true` | OpenAI-compatible API |
| `llm.anthropic` | `true` | Anthropic Claude |
| `llm.ollama` | `true` | Self-hosted Ollama |
| `llm.vllm` | `false` | Self-hosted vLLM inference server (🚧 coming soon) |

#### Pipeline stages

| Key | Default | Description |
|---|---|---|
| `pipeline.diff` | `true` | Fetch PR diff for analysis |
| `pipeline.context` | `true` | AST + vector semantic context (in development — see AST Providers note below) |
| `pipeline.llm_analysis` | `true` | Core code-review LLM pass |
| `pipeline.security_scan` | `false` | SAST and secret detection pass |
| `pipeline.coverage_hints` | `false` | Test coverage gap suggestions |
| `pipeline.issue_triage` | `false` | Auto-label and prioritise issues |
| `pipeline.commit_summary` | `false` | One-line commit message generator |
| `pipeline.changelog` | `false` | Auto-generate CHANGELOG entries |
| `pipeline.notifier_slack` | `false` | Post review summaries to Slack |
| `pipeline.notifier_teams` | `false` | Post review summaries to MS Teams |

#### AST providers

| Key | Default | Description |
|---|---|---|
| `ast.python` | `true` | Python tree-sitter AST context |
| `ast.typescript` | `true` | TypeScript/JavaScript AST context |
| `ast.go` | `false` | Go AST context |
| `ast.rust` | `false` | Rust AST context |

> **Status: in development** — AST and vector context enrichment is not available in the
> current release. The `pipeline.context`, `ast.*`, and `vector.*` flags are reserved for v0.2.
> Setting them has no effect today; this section will be updated when the feature ships.

#### Vector stores

| Key | Default | Description |
|---|---|---|
| `vector.qdrant` | `false` | Qdrant vector store |
| `vector.weaviate` | `false` | Weaviate vector store |
| `vector.pgvector` | `false` | PostgreSQL pgvector extension |
| `vector.chroma` | `false` | Chroma vector store |

#### Platform

| Key | Default | Description |
|---|---|---|
| `platform.multi_tenant` | `false` | Multi-organisation isolation |
| `platform.metrics_export` | `false` | Prometheus / OpenTelemetry metrics |
| `platform.tracing_export` | `false` | OpenTelemetry distributed tracing |
| `platform.prompt_dsl` | `false` | Custom prompt rules DSL (planned — see below) |

---

## Layer 3: LLM Review Instructions

The LLM analysis stage sends the PR diff and a set of review instructions to the configured language model. These instructions are the "rules" that determine what the model looks for and how it structures its output.

### Built-in instructions

The default instructions enforce the following predicates on every review:

| Predicate | Behaviour |
|---|---|
| **Specificity** | Comments must be anchored to an exact `file` + `line`. Generic observations are excluded. |
| **Actionability** | Every comment must contain concrete, actionable feedback — not style opinions. |
| **Confidence** | Each comment carries a `confidence` score (0.0–1.0). Low-confidence findings can be filtered downstream. |
| **Rationale** | Each comment explains *why* the finding matters, not just what it is. |
| **Generic ratio** | The model self-reports `generic_ratio`: the fraction of its comments it considers vague or low-value. |

### Review output schema

The LLM returns a JSON object matching this schema:

```json
{
  "comments": [
    {
      "file": "src/auth/session.py",
      "line": 42,
      "body": "Session secret is derived from a low-entropy source; use secrets.token_hex(32) instead.",
      "confidence": 0.95,
      "rationale": "Low-entropy session secrets are exploitable via brute force."
    }
  ],
  "summary": "One to three sentence overall PR assessment.",
  "generic_ratio": 0.05
}
```

### Per-repo LLM override

Per-repo routing rules (Layer 1) can specify a different `provider` and `model`. When a matching repo rule exists, that provider/model supersedes the global LLM settings for that job.

Example: run a lightweight model on a high-volume repo while using a larger model for security-sensitive repos:

```json
{ "platform": "github", "slug": "acme-org/frontend",  "provider": "ollama", "model": "qwen2.5-coder:7b" }
{ "platform": "github", "slug": "acme-org/payments",   "provider": "anthropic", "model": "claude-3-5-sonnet-20241022" }
```

### Custom Prompt DSL (planned)

> **Status: planned** — tracked in VEL-91. Feature flag `platform.prompt_dsl` (default `false`).

The upcoming Prompt DSL will let you author custom review rules alongside or in place of the built-in instructions. The DSL syntax, built-in predicate library, and authoring guide will be published here when the feature ships.

---

## Rule evaluation order

When processing a webhook:

1. **Repo allow-list check** — if no matching rule exists, the delivery is skipped immediately.
2. **`enabled` flag check** — if the matching rule has `enabled: false`, the delivery is skipped.
3. **Per-repo LLM override** — if the rule specifies a provider/model, it overrides the global LLM config.
4. **Pipeline stages** — each stage runs only if its feature flag is `true`.
5. **LLM review instructions** — applied inside the `pipeline.llm_analysis` stage.

---

## Examples

### Reviewing all repos in an org with a self-hosted model

```http
POST /admin/settings/repos
{ "platform": "github", "slug": "acme-org/*", "provider": "ollama", "model": "qwen2.5-coder:14b" }
```

### Enabling security scanning for a specific repo

1. Add the repo to the allow-list.
2. Enable the security scan stage globally (or wait for the per-rule override in VEL-91):

```http
PUT /admin/features/pipeline.security_scan
{ "enabled": true }
```

### Pausing reviews during a deployment freeze

```http
POST /admin/settings/repos/{repo_id}/toggle
```

Re-toggle to resume. Deliveries received during the pause are **not** replayed — use the Admin UI **Deliveries** tab to replay individual events if needed.
