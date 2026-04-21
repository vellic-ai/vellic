# Prompt DSL Reference

Vellic lets you ship AI-review prompts alongside your code. Drop `.md` files into `.vellic/prompts/` and Vellic will load, validate, and render them whenever it analyses a pull request.

## File layout

```
your-repo/
└── .vellic/
    └── prompts/
        ├── base.md          # shared base (extend with `inherits`)
        ├── api-security.md  # scoped to api/**
        └── frontend.md      # scoped to frontend/**
```

Files are loaded in alphabetical order. Each file must start with a YAML front-matter block delimited by `---`.

## Front-matter fields

```yaml
---
scope: api/**          # which files / labels / events this prompt targets
triggers:              # which pipeline events activate this prompt
  - pr.opened
  - pr.synchronize
priority: 10           # higher wins when multiple prompts match
inherits: base         # extend another prompt file (without .md)
variables:             # extra values injected into the template
  tone: strict
---
```

### `scope`

Type: `string | string[]` — Default: `[]` (matches everything)

Controls which PRs this prompt is applied to. Three pattern kinds are supported:

| Kind | Example | When it matches |
|------|---------|-----------------|
| Path glob | `api/**` | At least one changed file matches the glob |
| PR label | `security` | The PR carries this label |
| Event type | `pr.opened` | The triggering event matches (same syntax as `triggers`) |

A prompt with an empty `scope` matches every PR. A prompt with multiple scope entries matches when **any** entry matches.

**Examples:**

```yaml
scope: api/**                      # single glob
scope: [api/**, worker/**]         # multiple globs
scope: [security, breaking-change] # PR label names
scope: []                          # match everything (default)
```

### `triggers`

Type: `string | string[]` — Default: `[]` (all events)

Limits which pipeline events activate this prompt. Must start with one of three prefixes:

| Prefix | Example values |
|--------|---------------|
| `pr.` | `pr.opened`, `pr.synchronize`, `pr.reopened` |
| `push.` | `push.main`, `push.dev` |
| `schedule.` | `schedule.daily`, `schedule.weekly` |

An empty `triggers` list means the prompt is active for all events.

```yaml
triggers: pr.opened               # single value
triggers: [pr.opened, pr.synchronize]  # list
```

### `priority`

Type: `integer` — Default: `0`

When multiple prompts match the same PR, higher priority prompts win. Prompts are merged in priority order (lowest first, highest last), so a high-priority prompt can override the output of a lower-priority one.

Negative values are allowed and useful for "catch-all" base prompts you want applied before everything else.

### `inherits`

Type: `string` — Default: `null`

The filename (without `.md`) of another prompt this one extends. The inherited prompt's body is included before this prompt's own body.

```yaml
inherits: base   # loads base.md and prepends its rendered body
```

The referenced file must exist in the same `.vellic/prompts/` directory. Circular inheritance is not allowed.

### `variables`

Type: `mapping` — Default: `{}`

Extra key/value pairs injected into the template context. These **override** the pipeline-provided context variables of the same name, so you can use them to set per-prompt defaults.

```yaml
variables:
  tone: strict
  max_findings: "5"
  team: backend
```

All values are coerced to strings. Unknown variable names in the template body are silently replaced with an empty string.

---

## Template variables

Inside the prompt body, use `{{ variable_name }}` placeholders. Vellic performs simple string substitution — no loops, conditionals, or filters.

### Pipeline context

These variables are automatically populated from the current PR and pipeline run:

| Variable | Type | Description |
|----------|------|-------------|
| `diff` | string | Full unified diff of the PR |
| `symbols` | string | Extracted code symbols and AST context |
| `coverage` | string | Test coverage data for changed files |
| `prev_reviews` | string | Previous review comments, joined with newlines |
| `pr_title` | string | PR title |
| `pr_body` | string | PR description body |
| `repo` | string | Repository name in `owner/repo` format |
| `base_branch` | string | Target branch the PR is merging into |
| `changed_files` | string | Newline-separated list of changed file paths |
| `labels` | string | Comma-separated list of PR labels |

### Custom variables

Variables declared in `variables` front-matter are merged on top of the pipeline context before rendering. If a custom variable shares a name with a pipeline variable, the custom value wins.

### Substitution rules

- Syntax: `{{ variable_name }}` (spaces around the name are optional)
- Variable names must match `[a-zA-Z_][a-zA-Z0-9_]*`
- Unknown variables are replaced with an empty string — no error is raised
- Only simple substitution is supported; no filters, conditionals, or loops

**Example prompt body:**

```markdown
You are reviewing changes to **{{ repo }}** targeting `{{ base_branch }}`.

## Changed files
{{ changed_files }}

## Diff
{{ diff }}

## Symbols
{{ symbols }}

## Instructions
Apply a {{ tone }} review. Flag at most {{ max_findings }} issues. Focus on correctness and security.
```

---

## Inheritance

Use `inherits` to build a hierarchy of prompts. A child prompt's body is appended after its parent's rendered body, separated by a blank line.

```
.vellic/prompts/
├── base.md           (priority: 0)
├── api-security.md   (priority: 10, inherits: base)
└── api-perf.md       (priority: 5, inherits: base)
```

`api-security.md`:

```yaml
---
scope: api/**
priority: 10
inherits: base
variables:
  focus: security
---

### Security checklist
- Check all input validation at API boundaries
- Look for injection vectors in {{ diff }}
```

Resolution order when `api/**` files change:

1. `base.md` rendered → included first
2. `api-security.md` rendered → appended after base

---

## Preset catalogue

Vellic ships built-in presets you can import and customise. Presets are read-only templates you **fork** into your own `.vellic/prompts/` directory, then modify freely.

| Preset name | Focus |
|-------------|-------|
| `secure-review` | OWASP-aligned security checks — injection, auth, cryptography |
| `performance-review` | Algorithmic bottlenecks, O(n²) loops, database call batching |
| `test-review` | Test quality, coverage gaps, assertion patterns |
| `doc-review` | Docstring completeness, changelog entries, API documentation |
| `style-review` | Naming conventions, import order, commented-out code |

To use a preset as a starting point:

1. Open the **Prompt Editor** in the Vellic admin UI.
2. Select a preset from the library panel.
3. Click **Fork** — Vellic creates a copy in your repo's `.vellic/prompts/`.
4. Edit and commit the forked file.

> **Note:** Presets are managed through the UI. Direct import via API is planned for a future release.

---

## Dry-run

Dry-run lets you test a prompt against a real PR without posting review comments.

### Via the UI

1. Open **Prompts** → select a prompt → **Dry Run** tab.
2. Pick a PR from the dropdown (uses the most recent open PR by default).
3. Click **Run** — Vellic renders the prompt against the selected PR and shows the LLM output inline.
4. Use the **Diff** toggle to compare output against the current production prompt.

### Via the API

```http
POST /api/v1/repos/{owner}/{repo}/prompts/dry-run
Content-Type: application/json

{
  "prompt_name": "api-security",
  "pr_number": 42
}
```

Response:

```json
{
  "rendered_prompt": "...",
  "llm_output": "...",
  "sources": ["base", "api-security"],
  "pr": {
    "number": 42,
    "title": "...",
    "changed_files": [...]
  }
}
```

No comments are posted to the PR. The run is logged in the audit trail for the prompt.

> **Feature flag:** The dry-run endpoint requires `platform.prompt_dsl` to be enabled. See [configuration](configuration.md) for flag management.

---

## Validation

Vellic validates every prompt file when it loads the `.vellic/prompts/` directory. Invalid files abort the load with a descriptive error — no silent failures.

**Common errors and fixes:**

| Error | Cause | Fix |
|-------|-------|-----|
| `Prompt file must start with '---'` | Missing front-matter opening delimiter | Add `---` as the very first line |
| `No closing '---' for front-matter` | Missing closing delimiter | Add `---` on its own line after the YAML block |
| `Unknown front-matter keys: ['foo']` | Typo in a key name | Use only: `scope`, `triggers`, `priority`, `inherits`, `variables` |
| `Invalid trigger 'push'` | Trigger missing event suffix | Use `push.main` not `push` |
| `'priority' must be an integer` | Priority is a string or float | Use `priority: 10`, not `priority: "10"` |
| `YAML parse error` | Malformed YAML | Validate with `python -c "import yaml; yaml.safe_load(open('file').read())"` |

---

## Complete example

```markdown
---
scope:
  - api/**
  - "*.py"
triggers:
  - pr.opened
  - pr.synchronize
priority: 20
inherits: base
variables:
  tone: strict
  focus: security and correctness
---

## Review: {{ repo }} — `{{ base_branch }}`

**PR:** {{ pr_title }}

**Changed files:**
{{ changed_files }}

---

### Diff
{{ diff }}

---

### Code symbols
{{ symbols }}

---

### Previous review comments
{{ prev_reviews }}

---

### Instructions
Perform a {{ focus }} review with a {{ tone }} standard.
Flag issues as `[CRITICAL]`, `[WARNING]`, or `[INFO]`.
Do not repeat findings already covered in previous reviews above.
```
