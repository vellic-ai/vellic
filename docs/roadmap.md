# Roadmap

Vellic's mission: every repeated, context-heavy task in the software lifecycle should be a pipeline — one that *your* team can read, fork, and own. AI code review is where we started; it is one pipeline among many.

The plan is split into four horizons. Everything in "Now" ships in `main` today. "Near-term" is the work-in-progress platform refactor. Medium- and long-term items are committed directions but not yet scoped.

---

## Now: MVP v0.1 (shipped)

- [x] GitHub webhook ingestion with HMAC validation
- [x] GitLab MR integration
- [x] Platform-agnostic `PREvent` model + VCS adapter layer
- [x] Async pipeline runtime — Arq on Redis, retry / DLQ, per-job tracking
- [x] 4-stage code-review pipeline (diff → context → LLM → feedback), hard-coded
- [x] VCS Reviews API integration (inline PR comments, grouped review)
- [x] 4 LLM provider adapters — Ollama (default), OpenAI, Anthropic, Claude Code
- [x] Prompt DSL — `.vellic/prompts/` loaded per repo
- [x] Feature flags — per-repo, per-tenant control over stages, adapters, providers
- [x] DB-backed LLM config — per-repo provider overrides via Admin UI
- [x] Admin panel — event replay, job inspection, LLM settings, per-repo overrides
- [x] Kubernetes manifests with HPA (1→10 replicas @ 70% CPU)
- [x] Encrypted secrets at rest (Fernet via `LLM_ENCRYPTION_KEY`)

---

## Near-term: "Pipelines as a platform"

The thesis of v0.2: **stop hard-coding the code-review pipeline** and turn the runtime into a generic stage-graph executor driven by YAML in your repo. Once that exists, everything else is additional stage primitives, triggers, and YAML files.

### Runtime & schema

- [ ] **Config-driven pipeline engine** — replace the hard-coded 4-stage runner in `worker/app/pipeline/` with a generic stage-graph executor.
- [ ] **`.vellic/pipelines/*.yaml` loader** — parse + validate + resolve prompt and plugin references; cache per repo/SHA.
- [ ] **Stage-primitive registry** — `gather_context`, `fetch_diff`, `fetch_issue`, `fetch_ci_logs`, `llm_call`, `post_review`, `post_comment`, `open_issue`, `open_pr`.
- [ ] **Re-express code review as `code-review.yaml`** — dogfood the engine on the flagship pipeline. Behaviour-preserving, no user-visible change.
- [ ] **Pipeline run model** — promote `pipeline_jobs` into a per-pipeline-run record with stage-level status, so the UI can show "stage 3 of 5 failed".

### New built-in pipelines

- [ ] **PR-summary pipeline** — structured description on PR open, updated on push. Second built-in; proves the engine.
- [ ] **Issue-triage pipeline** — labels, severity, assignee suggestions on `issues.opened`. First non-PR trigger.

### New triggers

- [ ] **Issue webhooks** (`issues.opened`, `issues.edited`, `issues.labeled`).
- [ ] **CI webhooks** (`workflow_run` with `conclusion=failure`).
- [ ] **Cron triggers** — `@daily`, `@weekly`, explicit cron expressions; persisted in a `scheduled_pipelines` table, dispatched by a lightweight scheduler in the worker.
- [ ] **Manual-run button** — Admin UI + CLI command to trigger any pipeline against a repo / PR / issue.

### Admin UI

- [ ] **Pipelines page** — catalog across all repos, per-repo enable/disable, YAML viewer, run history per pipeline.
- [ ] **Run detail view** — stage-by-stage status, per-stage inputs/outputs, LLM token usage, re-run from any stage.

### Platform

- [ ] **vLLM provider adapter** — self-hosted OpenAI-compatible inference (stub exists).
- [ ] **Bitbucket PR integration** — alpha → stable.
- [ ] **Webhook retry / DLQ polish** — exponential back-off, visible DLQ page, requeue-from-UI.

---

## Medium-term

### More built-in pipelines

- [ ] **CI-failure explainer** — reads failing logs, posts an explainer comment with a suggested fix. Requires the `fetch_ci_logs` primitive + CI webhook trigger.
- [ ] **Doc-drift detector** — flags PRs that change code referenced by docs without updating the docs.
- [ ] **Stale-issue sweeper** — cron pipeline; summarises activity, nudges or closes per policy.
- [ ] **Automated changelog** — on merge, append a structured entry to `CHANGELOG.md` using the PR summary as source.
- [ ] **Release-notes drafter** — on tag push, aggregate PR summaries between tags into a release draft.

### Extensibility

- [ ] **MCP/plugin-backed stages** — invoke registered MCP tool hosts or Python plugins as `use: mcp.<tool>` / `use: plugin.<name>` in pipeline YAML.
- [ ] **Pipeline chaining** — one pipeline's output is an input/trigger for another (e.g. `code-review` hands its summary to `changelog` on merge).
- [ ] **Slack / Teams notifier primitive** — `use: slack_notify` stage, configured once per org, callable from any pipeline.

### Ops & scale

- [ ] **Multi-tenant mode** — per-organisation API keys, isolated pipelines and LLM configs, shared runtime.
- [ ] **LLM cost accounting** — per-pipeline, per-repo token / $ tracking; visible in the dashboard and exportable.
- [ ] **Observability hooks** — OpenTelemetry traces per pipeline run, exportable to Grafana / Honeycomb / Datadog.

---

## Long-term

- [ ] **IDE bridge** — run any pipeline against an open PR or branch from VS Code / JetBrains *before* opening the PR. Same pipeline definitions, same stage primitives, local runtime that talks to your Vellic instance.
- [ ] **Slack slash-command trigger** — `/vellic review <PR>`, `/vellic triage <issue>` — any pipeline invokable from Slack.
- [ ] **Pipeline marketplace** — shareable YAML pipelines between teams (opt-in, public repo or internal catalog).
- [ ] **Metrics dashboard** — pipeline quality trends (e.g. review accept-rate), LLM cost tracking, team velocity.
- [ ] **Custom trigger plugins** — teams register their own trigger sources (e.g. PagerDuty alert → postmortem-draft pipeline).

---

Want to contribute to any of these? See [`docs/contributing.md`](contributing.md) or open an issue.
