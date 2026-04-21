# LLM Providers

Vellic is LLM-agnostic. You configure the provider through the **Admin UI** at
`http://localhost:8001` — no env-var editing, no restarts required.

> **Privacy baseline:** Vellic defaults to **Ollama** — fully local, no data leaves your
> infrastructure. Cloud providers (OpenAI, Anthropic, Claude Code) are opt-in and display an
> explicit warning in the Admin UI before you save.

## Provider overview

| Provider | Guide | Self-hosted | Data leaves infra |
|---|---|:---:|:---:|
| Ollama (default) | [ollama.md](ollama.md) | ✅ | No |
| vLLM | (see below) | ✅ | No |
| OpenAI / OpenAI-compatible BYOK | [byok.md](byok.md) | No | ⚠️ Yes |
| Anthropic BYOK | [byok.md](byok.md) | No | ⚠️ Yes |
| Claude Code CLI | [claude-code.md](claude-code.md) | Partial | ⚠️ Yes |
| Custom OpenAI-compatible endpoint | [byok.md](byok.md) | Depends | Depends |

---

## Configuring via Admin UI

1. Open the Admin panel: `http://localhost:8001`
2. Go to **Settings → LLM Provider**
3. Choose your provider from the dropdown
4. Fill in the required fields (model name, base URL, API key where applicable)
5. Click **Save** — the worker picks up the new config on the next job run

No service restart needed.

---

## Quick-start: Ollama (default)

Ollama ships pre-configured in the Docker Compose stack. To start analyzing PRs with the
default model (`llama3.1:8b-instruct-q4_K_M`), just boot the stack:

```bash
docker compose up -d
```

See the [full Ollama guide](ollama.md) to change the model or run Ollama outside Docker.

---

## vLLM

vLLM exposes an OpenAI-compatible API endpoint. In the Admin UI, set provider to **vLLM**,
enter your vLLM base URL (e.g. `http://vllm-host:8000`) and the model ID served by that
instance. No API key required for self-hosted deployments unless you add one to vLLM.

---

## DB-backed per-repo LLM config

Vellic supports storing LLM provider config per repository in the database — so different repos can use different models or providers without changing global settings.

This feature is gated behind the `platform.llm_config_ui` feature flag (off by default):

```bash
# Enable via ENV
VELLIC_FEATURE_PLATFORM_LLM_CONFIG_UI=true

# Or via Admin UI: Settings → Feature flags → "LLM config UI" → toggle on
```

Once enabled:

1. Go to **Admin UI → Repositories → select repo → LLM config**.
2. Override the provider, model, API key, and base URL for that repo.
3. The worker resolves config in order: **repo override → global config → environment default**.

The per-repo config is stored encrypted in PostgreSQL (same encryption used for all secrets). See [security](../security/index.md) for details.

---

## Adding a new provider

1. Create `worker/app/llm/providers/<name>.py` implementing the `LLMProvider` protocol:

   ```python
   from ..registry import register

   @register("my_provider")
   class MyProvider:
       def __init__(self, **kwargs): ...
       async def complete(self, prompt: str, *, max_tokens: int) -> str: ...
       async def health(self) -> bool: ...
   ```

2. Register it in `worker/app/llm/registry.py` (the `@register` decorator handles this).
3. If the provider sends data off-prem, add it to `_EXTERNAL_PROVIDERS` in
   `worker/app/llm/config.py` so the privacy warning fires in the Admin UI.
4. Add the provider name to `VALID_PROVIDERS` in `admin/app/settings_router.py`.
5. Add it to the Admin UI provider selector.
6. Document it in this directory and open a PR.
