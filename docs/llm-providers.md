# LLM Providers

Vellic is LLM-agnostic. The worker loads a provider at startup based on `LLM_PROVIDER` and the rest of the pipeline never sees provider-specific code.

## Provider summary

| Provider | `LLM_PROVIDER` | Self-hosted | Sends data externally |
|---|---|---|---|
| Ollama | `ollama` | ✅ | No |
| vLLM | `vllm` | ✅ | No |
| OpenAI | `openai` | No | ⚠️ Yes |
| Anthropic | `anthropic` | No | ⚠️ Yes |
| Claude Code CLI | `claude_code` | Depends | ⚠️ Yes |
| Custom (OpenAI-compatible) | `vllm` | ✅ | Depends |

> **Privacy note:** Providers marked ⚠️ send PR diff content to an external API. Vellic logs a warning at startup when these are selected.

---

## Ollama (default)

Best for local development. Runs entirely on your machine.

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.1:8b-instruct-q4_K_M
```

The `docker-compose.yml` includes an Ollama service that pulls the default model automatically on first boot.

To use a different model:

```dotenv
LLM_MODEL=mistral:7b-instruct
```

Ollama pulls the model on first use. Pre-pull to avoid cold-start latency:

```bash
docker compose exec ollama ollama pull mistral:7b-instruct
```

---

## vLLM

Use for production self-hosted deployments. Exposes an OpenAI-compatible API.

```dotenv
LLM_PROVIDER=vllm
LLM_BASE_URL=http://<your-vllm-host>:8000
LLM_MODEL=mistralai/Mistral-7B-Instruct-v0.3
LLM_API_KEY=optional-if-your-endpoint-requires-it
```

---

## OpenAI

```dotenv
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
LLM_API_KEY=sk-...
```

`LLM_BASE_URL` is ignored for the OpenAI provider — it always hits the official API.

---

## Anthropic

```dotenv
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
LLM_API_KEY=sk-ant-...
```

---

## Claude Code CLI

Uses the local `claude` binary. Useful when you want to leverage Claude Code's agentic capabilities.

```dotenv
LLM_PROVIDER=claude_code
CLAUDE_CODE_BIN=/usr/local/bin/claude
CLAUDE_CODE_MODEL=claude-sonnet-4-6   # optional; uses CLI default if empty
```

The `claude` binary must be installed and authenticated in the worker container.

---

## Custom / OpenAI-compatible endpoint

Any endpoint that implements the OpenAI Chat Completions API works via the `vllm` provider:

```dotenv
LLM_PROVIDER=vllm
LLM_BASE_URL=https://your-custom-endpoint.example.com
LLM_MODEL=your-model-id
LLM_API_KEY=your-key-if-needed
```

---

## Adding a new provider

1. Create `worker/app/llm/providers/<name>.py` implementing the `LLMProvider` protocol:

```python
from ..protocol import LLMProvider, AnalysisResult
from ..config import LLM_MODEL

class MyProvider(LLMProvider):
    async def analyze(self, context, chunks) -> AnalysisResult:
        ...
```

2. Register it in `worker/app/llm/registry.py`.
3. Add `<name>` to the `_EXTERNAL_PROVIDERS` set in `config.py` if it sends data externally.
4. Document it in this file and open a PR.

---

## Switching providers at runtime

No rebuild needed — just restart the worker with the new env var:

```bash
LLM_PROVIDER=openai LLM_MODEL=gpt-4o docker compose up -d worker
```
