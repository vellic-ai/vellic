# Claude Code CLI Adapter

The Claude Code adapter lets Vellic use the `claude` CLI binary as its LLM backend. Instead
of making direct API calls, the worker spawns a `claude --print` subprocess and pipes the
prompt through it.

> ⚠️ **Closed-loop disclaimer:** This adapter is **not** a self-hosted option. The `claude`
> CLI routes requests to the Anthropic API. PR diff content leaves your infrastructure via
> Anthropic's network. Ollama remains the only fully closed-loop provider. Enable this only
> if your organization permits sending code to Anthropic's API.

---

## When to use this adapter

- You already have a Claude Code subscription and want to avoid managing a separate API key.
- You want to use Claude models (Sonnet, Opus, Haiku) without calling the Anthropic API
  directly.
- Development / evaluation only — for production on-prem deployments, use Ollama or vLLM.

---

## Prerequisites

1. **Claude Code CLI installed and authenticated** inside the worker container.

   The worker calls `claude --print` as a subprocess. The binary must be on the `PATH`
   (or at the path configured in `CLAUDE_CODE_BIN`) and already authenticated:

   ```bash
   # Inside the worker container
   claude --version        # confirm binary is present
   claude auth status      # confirm authenticated session
   ```

2. **Network access** from the worker container to `api.anthropic.com` (or your Claude
   Code endpoint).

---

## Installing Claude Code in the worker container

Add the installation to your `worker/Dockerfile` or a custom override:

```dockerfile
# Install Node.js (required for Claude Code)
RUN apt-get update && apt-get install -y nodejs npm && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Claude Code reads auth from this path at runtime
ENV CLAUDE_CONFIG_DIR=/home/worker/.claude
```

Authenticate by mounting a pre-authenticated `.claude` config directory as a Docker volume,
or by running `claude auth login` inside the container during initial setup.

---

## Admin UI configuration

Navigate to **Admin UI → Settings → LLM Provider**:

| Field | Value |
|---|---|
| Provider | `claude_code` |
| Base URL | *(not used — leave blank)* |
| Model | *(optional)* `claude-sonnet-4-6`, `claude-opus-4-7`, etc. — leave blank for default |
| API Key | *(not used — authentication is handled by the CLI session)* |

<!-- screenshot: admin-llm-claude-code.png -->
> **[Admin UI — LLM Provider screen with Claude Code selected; model field optional]**

Click **Save**. The Admin UI will display a data-exfiltration warning — confirm to proceed.

### Model override

If **Model** is left blank, the `claude` binary uses its own default model (typically the
latest Sonnet). To pin a specific model, enter the model ID:

```
claude-sonnet-4-6
claude-opus-4-7
claude-haiku-4-5-20251001
```

---

## How it works

The worker's `ClaudeCodeProvider` runs:

```
claude --print [--model <model>]
```

with the prompt piped to stdin. stdout is the completion text. Non-zero exit codes are treated
as errors and the job retries with exponential back-off.

The worker logs a warning on startup when this provider is active:

```
⚠️  External LLM provider enabled (Claude Code).
    PR diff content will leave your infrastructure via the Anthropic API.
    Ollama remains the only fully closed-loop option.
```

---

## Environment variable fallback

If no DB config row exists, the worker falls back to environment variables:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | Set to `claude_code` to enable |
| `CLAUDE_CODE_BIN` | `claude` | Path to the `claude` binary |
| `CLAUDE_CODE_MODEL` | *(empty)* | Optional model override |

```bash
# .env override (dev only)
LLM_PROVIDER=claude_code
CLAUDE_CODE_BIN=/usr/local/bin/claude
CLAUDE_CODE_MODEL=claude-sonnet-4-6
```

> The Admin UI DB config takes precedence over environment variables when a row exists.

---

## Troubleshooting

**`claude: command not found`** — The binary is not on the PATH inside the worker container.
Set `CLAUDE_CODE_BIN` to the absolute path, or reinstall Claude Code.

**Authentication errors** — Run `claude auth login` inside the container, or mount a valid
`.claude` config directory. Check `claude auth status` to verify the session.

**Rate limit / quota errors** — The `claude` CLI surfaces Anthropic API rate limits as
non-zero exit codes. The worker retries automatically. If you see persistent failures, check
your Claude Code plan limits or switch to a direct Anthropic API key via the
[BYOK guide](byok.md).

**Slow responses** — The subprocess startup adds ~50–200 ms overhead per request compared
to a direct API call. For high-volume deployments, consider using the Anthropic BYOK adapter
directly (`anthropic` provider) instead.
