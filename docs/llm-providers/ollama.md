# Ollama — Local Setup Guide

Ollama is the default LLM provider for Vellic. It runs entirely within your infrastructure —
PR diff content never leaves your network.

**Default model:** `llama3.1:8b-instruct-q4_K_M` (quantized 4-bit, ~5 GB VRAM / ~8 GB RAM)

---

## Docker Compose setup (recommended)

The default `docker-compose.yml` ships a pre-configured Ollama service. No changes needed for
a standard local or on-prem deployment.

```bash
# Start the full stack (Ollama included)
docker compose up -d

# Confirm Ollama is healthy
docker compose exec ollama ollama list
```

The `ollama` service pulls `llama3.1:8b-instruct-q4_K_M` on first boot and serves it on
`http://ollama:11434` (internal Docker network).

### Admin UI — default config

Navigate to **Settings → LLM Provider** in the Admin panel:

| Field | Default value |
|---|---|
| Provider | `ollama` |
| Base URL | `http://ollama:11434` |
| Model | `llama3.1:8b-instruct-q4_K_M` |
| API Key | *(not required)* |

<!-- screenshot: admin-llm-ollama-default.png -->
> **[Admin UI — LLM Provider screen with Ollama selected and default model]**

Click **Save** to persist. The worker reads this from the DB on the next job run.

---

## Changing the model

### Pull a different model at runtime

```bash
# Pull Mistral 7B (example)
docker compose exec ollama ollama pull mistral:7b-instruct

# List available local models
docker compose exec ollama ollama list
```

Then update the **Model** field in **Admin UI → Settings → LLM Provider** and save.

### Recommended models by hardware

| Model | VRAM required | Notes |
|---|---|---|
| `llama3.1:8b-instruct-q4_K_M` | ~5 GB | Default — good balance of speed and quality |
| `llama3.1:8b-instruct` (fp16) | ~16 GB | Higher accuracy, needs GPU |
| `mistral:7b-instruct` | ~5 GB | Fast, strong on code review tasks |
| `codellama:13b-instruct` | ~10 GB | Code-focused, better for large diffs |
| `llama3.1:70b-instruct-q4_K_M` | ~40 GB | Best quality, requires high-VRAM GPU |

---

## External Ollama instance

To use an Ollama server running outside Docker (e.g. on a dedicated GPU host):

1. In **Admin UI → Settings → LLM Provider**, set:
   - **Provider:** `ollama`
   - **Base URL:** `http://<your-ollama-host>:11434`
   - **Model:** the model tag pulled on that host

2. Ensure the Ollama host is reachable from the worker container on port `11434`.

Alternatively, override the environment variable before starting:

```bash
LLM_BASE_URL=http://192.168.1.50:11434 docker compose up -d worker
```

> The Admin UI setting takes precedence over environment variables when a DB row exists.

---

## Hardware requirements

| Setup | Minimum | Recommended |
|---|---|---|
| CPU-only (slow) | 16 GB RAM | 32 GB RAM |
| GPU | 6 GB VRAM (RTX 3060) | 16 GB+ VRAM (RTX 4090 / A10) |
| Production on-prem | — | NVIDIA A10 / A100 or equivalent |

Ollama falls back to CPU inference automatically if no compatible GPU is detected.

---

## Health check

The worker pings `GET /api/tags` on the Ollama base URL before each job. If Ollama is
unreachable, the job is retried with exponential back-off and eventually moved to the DLQ.

```bash
# Manual health check
curl http://localhost:11434/api/tags
```

---

## Troubleshooting

**`model not found` error** — The model tag in the Admin UI doesn't match what's pulled
locally. Run `docker compose exec ollama ollama list` to see available tags and update
the Admin UI to match.

**Slow first response** — Ollama loads the model into memory on first request. Subsequent
requests are faster. Consider pre-warming with a test prompt after pulling a model.

**Out of memory** — Switch to a smaller quantized model (e.g. `q4_K_M`) or add a GPU.
