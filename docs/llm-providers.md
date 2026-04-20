# LLM Providers

Vellic is LLM-agnostic. You pick and configure the LLM provider through the **Admin UI** at `http://localhost:8001` — no env var editing, no restarts.

## Configuring via Admin UI

1. Open the Admin panel at `http://localhost:8001`
2. Go to **Settings → LLM Provider**
3. Select your provider, enter the model name and any required credentials
4. Save — the worker picks up the new config on the next job run

Changes take effect without restarting any service.

## Supported providers

| Provider | Self-hosted | Sends data externally |
|---|---|---|
| Ollama (default) | ✅ | No |
| vLLM | ✅ | No |
| OpenAI | No | ⚠️ Yes |
| Anthropic | No | ⚠️ Yes |
| Claude Code CLI | No | ⚠️ Yes |
| Custom OpenAI-compatible endpoint | ✅ | Depends |

> **Privacy:** Providers marked ⚠️ send PR diff content to an external service. The Admin UI displays a warning when one of these is selected.

---

## Ollama (default)

Best for local development and on-prem deployments. Ships pre-configured in the Docker Compose stack — just boot the stack and select Ollama in the Admin UI.

To pull a different model into the running Ollama container:

```bash
docker compose exec ollama ollama pull mistral:7b-instruct
```

Then update the model name in the Admin UI.

---

## vLLM

For production self-hosted deployments. Exposes an OpenAI-compatible API.

In the Admin UI: set provider to **vLLM**, enter your vLLM base URL and model ID.

---

## OpenAI

In the Admin UI: set provider to **OpenAI**, enter your model (e.g. `gpt-4o`) and API key.

---

## Anthropic

In the Admin UI: set provider to **Anthropic**, enter your model (e.g. `claude-sonnet-4-6`) and API key.

---

## Claude Code CLI

Uses the local `claude` binary. In the Admin UI: set provider to **Claude Code**, optionally specify a model override.

The `claude` binary must be installed and authenticated inside the worker container.

---

## Custom / OpenAI-compatible endpoint

Any endpoint that implements the OpenAI Chat Completions API works.

In the Admin UI: set provider to **vLLM**, enter your custom base URL, model ID, and API key (if required).

---

## Adding a new provider

1. Create `worker/app/llm/providers/<name>.py` implementing the `LLMProvider` protocol:

```python
from ..protocol import LLMProvider, AnalysisResult

class MyProvider(LLMProvider):
    async def analyze(self, context, chunks) -> AnalysisResult:
        ...
```

2. Register it in `worker/app/llm/registry.py`.
3. Mark it as external in `config.py` if it sends data off-prem (triggers the privacy warning in the Admin UI).
4. Add it to the Admin UI provider selector.
5. Document it in this file and open a PR.
