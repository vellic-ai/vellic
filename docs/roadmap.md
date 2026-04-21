# Roadmap

Vellic's mission is to integrate AI deeply into the software development lifecycle — not just code review, but every repeated, context-heavy task that slows teams down.

## Current: MVP v0.1

- [x] GitHub webhook ingestion with HMAC validation
- [x] Platform-agnostic `PREvent` model
- [x] 4-stage async analysis pipeline (diff → context → LLM → feedback)
- [x] GitHub Reviews API integration (inline PR comments)
- [x] 4 LLM provider adapters (Ollama, OpenAI, Anthropic, Claude Code)
- [x] Admin panel (event replay, job inspection)
- [x] Kubernetes manifests with HPA

## Near-term

- [ ] **vLLM provider adapter** — self-hosted OpenAI-compatible inference server (stub in place, full implementation pending)
- [ ] **GitLab MR integration** — adapter + webhook route + MR discussions API
- [ ] **Bitbucket PR integration**
- [ ] **Issue triage** — classify new issues by type/severity using LLM; suggest labels and assignees
- [ ] **Commit summarisation** — auto-generate commit/PR summaries for changelogs
- [ ] **Configurable review rules** — per-repo rules engine (what to flag, what to ignore)
- [ ] **Webhook retry / dead-letter queue** — resilient delivery with exponential back-off

## Medium-term

- [ ] **Security scanning** — flag common vulnerability patterns in diffs
- [ ] **Test coverage hints** — identify untested code paths introduced in a PR
- [ ] **Automated changelog** — generate structured changelogs from merged PRs
- [ ] **Slack / Teams notifications** — deliver review summaries to team channels
- [ ] **Multi-tenant SaaS mode** — per-organisation API keys, isolated pipelines

## Long-term

- [ ] **IDE integration** — surface AI feedback before the PR is even opened
- [ ] **Custom pipeline stages** — plugin architecture for team-specific analysis steps
- [ ] **Metrics dashboard** — review quality trends, LLM cost tracking, team velocity

---

Want to contribute to any of these? See [`docs/contributing.md`](contributing.md) or open an issue.
