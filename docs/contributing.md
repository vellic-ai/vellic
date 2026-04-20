# Contributing

Contributions are welcome — whether it's a new VCS adapter, an LLM provider, a pipeline stage improvement, a bug fix, or documentation.

## What we need most

- **VCS adapters** — GitLab, Bitbucket, Gitea (see [`docs/vcs-integrations.md`](vcs-integrations.md))
- **LLM providers** — anything with a clean API (see [`docs/llm-providers.md`](llm-providers.md))
- **Pipeline improvements** — better diff chunking, smarter context gathering, more structured LLM output
- **Bug reports** — especially edge cases in webhook parsing or feedback posting
- **Docs** — if something is unclear, a PR improving the docs is just as valuable as code

## Development setup

```bash
git clone https://github.com/vellic-ai/vellic.git
cd vellic
cp .env.example .env   # set POSTGRES_PASSWORD and GITHUB_WEBHOOK_SECRET
make up
```

## Code style

We use [ruff](https://github.com/astral-sh/ruff) for linting and formatting.

```bash
cd api    && ruff check .
cd worker && ruff check .
cd admin  && ruff check .
```

CI will fail if ruff reports any errors.

## Tests

```bash
cd api    && pytest
cd worker && pytest
cd admin  && pytest
```

Add tests for any new behaviour. Bug fixes should include a regression test.

## Pull request checklist

- [ ] `ruff check` passes for all affected services
- [ ] `pytest` passes for all affected services
- [ ] New behaviour is covered by tests
- [ ] Docs updated if you changed a public interface or added configuration
- [ ] PR description explains the **why**, not just the **what**

## Commit style

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(worker): add GitLab MR adapter
fix(api): reject duplicate delivery IDs
docs: add vLLM setup guide
```

## Architecture decisions

For significant changes (new service, new abstraction, breaking change), open an issue first and discuss the approach. A short write-up of the problem, proposed solution, and trade-offs is enough — we don't need ADR docs for small changes.
