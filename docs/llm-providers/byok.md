# Cloud BYOK — Bring Your Own Key

Vellic supports OpenAI, Anthropic, and any OpenAI-compatible endpoint as LLM providers.
These are collectively referred to as **BYOK (Bring Your Own Key)** providers because they
require an API key issued by an external service.

> ⚠️ **Data leaves your infrastructure.** When a BYOK provider is selected, PR diff content
> is sent to the provider's API servers for inference. The Admin UI displays this warning
> every time you save a BYOK configuration. Review your organization's data handling policies
> before enabling.

---

## OpenAI

### Prerequisites

- An [OpenAI API key](https://platform.openai.com/api-keys) with access to the model you want
  to use.
- Network access from the worker container to `api.openai.com`.

### Admin UI configuration

Navigate to **Admin UI → Settings → LLM Provider**:

| Field | Value |
|---|---|
| Provider | `openai` |
| Base URL | *(leave blank — uses OpenAI default)* |
| Model | `gpt-4o` (or `gpt-4o-mini`, `gpt-4-turbo`, etc.) |
| API Key | Your OpenAI secret key (`sk-...`) |

<!-- screenshot: admin-llm-openai.png -->
> **[Admin UI — LLM Provider screen with OpenAI selected, model gpt-4o, and masked API key]**

Click **Save**. The Admin UI will display a data-exfiltration warning — confirm to proceed.

The API key is encrypted at rest in the database using AES-256 (Fernet). It is never
returned in plaintext through the API; the UI shows only a masked version (`sk-...****`).

### Recommended models

| Model | Notes |
|---|---|
| `gpt-4o` | Best quality, recommended for production |
| `gpt-4o-mini` | Faster and cheaper, good for high volume |
| `gpt-4-turbo` | Large context window (128k tokens) |

---

## Anthropic

### Prerequisites

- An [Anthropic API key](https://console.anthropic.com/settings/keys).
- Network access from the worker container to `api.anthropic.com`.

### Admin UI configuration

| Field | Value |
|---|---|
| Provider | `anthropic` |
| Base URL | *(leave blank)* |
| Model | `claude-sonnet-4-6` (or `claude-haiku-4-5-20251001`, etc.) |
| API Key | Your Anthropic key (`sk-ant-...`) |

<!-- screenshot: admin-llm-anthropic.png -->
> **[Admin UI — LLM Provider screen with Anthropic selected and masked API key]**

Same data-exfiltration warning applies on save.

---

## Custom / OpenAI-compatible endpoint

Any server that implements the OpenAI Chat Completions API (`POST /v1/chat/completions`)
works as a BYOK provider. Common examples: Azure OpenAI, Together AI, Fireworks AI,
Groq, or a self-hosted vLLM instance exposed publicly.

### Admin UI configuration

| Field | Value |
|---|---|
| Provider | `vllm` |
| Base URL | Your endpoint URL, e.g. `https://my-vllm.example.com` |
| Model | The model ID as expected by your endpoint |
| API Key | Bearer token / API key (optional depending on endpoint) |

<!-- screenshot: admin-llm-custom.png -->
> **[Admin UI — LLM Provider screen with vLLM selected and custom base URL]**

If your endpoint does not require authentication, leave the API Key field blank.

> **Note on data privacy:** Whether data leaves your infrastructure depends entirely on where
> the endpoint runs. A self-hosted vLLM instance on your own servers is as private as Ollama.
> An endpoint hosted by a third party is subject to their data policies.

---

## Security notes

- API keys are encrypted in the database using a Fernet key stored in `LLM_ENCRYPTION_KEY`.
  Rotate this env var and re-enter API keys if the secret is compromised.
- Do not share the `LLM_ENCRYPTION_KEY` value. It is required to decrypt stored keys.
- The worker logs a warning (`⚠️ External LLM provider enabled`) on every startup when a
  cloud provider is active. Monitor your logs to detect unexpected provider switches.

---

## Switching back to Ollama

To restore a fully closed-loop setup:

1. Make sure Ollama is reachable — either bring up the opt-in overlay
   (`docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d`)
   or run your own instance.
2. **Admin UI → Settings → LLM Provider**
3. Set **Provider** to `ollama`, **Base URL** to `http://ollama:11434`
   (or wherever your instance lives), and **Model** to the tag you pulled
4. Clear the API Key field
5. Save — no restart needed
