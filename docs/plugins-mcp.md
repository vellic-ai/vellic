# Plugins & MCP

Vellic can attach external tool servers to the analysis pipeline via the **Model Context Protocol (MCP)**. Each MCP server runs as a supervised subprocess alongside the worker during a PR run, giving the LLM access to repo-specific tools — test runners, linters, build systems, custom scripts — without modifying the vellic core.

---

## Overview

```
Worker (PR run)
    │
    ├─► MCP server 1  (e.g. repo-level linter)
    ├─► MCP server 2  (e.g. custom build tool)
    └─► LLM analysis  ← tool results injected into context
```

MCP servers are attached **per repository** through the Admin UI. During a PR run the worker spawns each enabled server as an isolated subprocess, calls `tools/list`, and exposes the returned tools to the LLM.

---

## Enabling the plugin loader

The MCP / plugin system is gated by the `plugins.enabled` feature flag (off by default):

```bash
# Via ENV (applies globally)
VELLIC_FEATURE_PLUGINS_ENABLED=true

# Via Admin UI: Settings → Feature flags → "Plugin Loader" → toggle on
```

See [Feature flags](feature-flags.md) for scope and override details.

---

## Attaching an MCP server to a repository

1. Open **Admin UI** → **Repositories** → select your repo.
2. Click **MCP servers** → **Attach server**.
3. Fill in:
   - **Name** — display label (must be unique per repo).
   - **URL** — `stdio://` or `http://` endpoint the worker will connect to.
   - **Credentials** — optional JSON object; encrypted at rest with AES-256-GCM before storage.
   - **Enabled** — toggle to activate/deactivate without removing the server.

Alternatively, use the Admin REST API directly:

```bash
curl -X POST http://localhost:8001/admin/repos/<repo-id>/mcp \
  -H "Content-Type: application/json" \
  -H "Cookie: session=<your-session>" \
  -d '{
    "name": "my-linter",
    "url": "stdio:///usr/local/bin/my-linter-mcp",
    "credentials": {"token": "secret"},
    "enabled": true
  }'
```

---

## Admin API — MCP endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/admin/repos/{repo_id}/mcp` | List all attached MCP servers |
| `POST` | `/admin/repos/{repo_id}/mcp` | Attach a new server |
| `PATCH` | `/admin/repos/{repo_id}/mcp/{server_id}` | Update `enabled`, `url`, or `credentials` |
| `DELETE` | `/admin/repos/{repo_id}/mcp/{server_id}` | Remove a server |

Interactive docs: **http://localhost:8001/docs** → `mcp` tag.

---

## Process isolation

Each MCP server runs as a subprocess of the worker with:

- `cwd` set to the sandboxed workspace directory for the PR run.
- Only explicit environment variables passed — no parent env inheritance.
- Process group isolation so `kill()` reaches all child processes.
- Up to **3 automatic restarts** before the server is marked failed and the run continues without it.
- A configurable **timeout** (default 300 s) after which the process is killed.

---

## Writing an MCP server

Any process that speaks the [MCP protocol](https://modelcontextprotocol.io) over stdio or HTTP can be attached. The worker calls:

1. `tools/list` — discover available tools.
2. `tools/call` — invoke a tool with arguments during LLM analysis.

Minimal example (Python, stdio transport):

```python
# my_linter_mcp.py
import sys, json

def handle(msg):
    if msg["method"] == "tools/list":
        return {"tools": [{"name": "lint", "description": "Run linter on file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}}]}
    if msg["method"] == "tools/call" and msg["params"]["name"] == "lint":
        path = msg["params"]["arguments"]["path"]
        # ... run linter ...
        return {"content": [{"type": "text", "text": "No issues found."}]}

for line in sys.stdin:
    msg = json.loads(line)
    result = handle(msg)
    print(json.dumps({"id": msg["id"], "result": result}))
    sys.stdout.flush()
```

Attach it with `url: "stdio:///path/to/my_linter_mcp.py"`.

---

## Security notes

- Credentials are encrypted with AES-256-GCM before being written to the database. The encryption key is derived from `SECRET_KEY` in the admin service environment.
- MCP server processes do **not** inherit the worker's environment variables. Pass only what the server needs via `credentials`.
- Network access from MCP subprocesses is not restricted at the OS level in the default Docker Compose setup. For stricter isolation, run the worker in a Kubernetes pod with a network policy.

---

## Related

- [Feature flags](feature-flags.md) — `plugins.enabled` flag
- [Security & secrets](security/index.md) — credential encryption
- [Architecture](architecture.md) — where MCP fits in the pipeline
