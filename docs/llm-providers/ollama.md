# Ollama — Local Setup Guide

Ollama runs entirely within your infrastructure — PR diff content never leaves your network.
Vellic does not bundle Ollama in the default compose stack; you either bring up the opt-in
overlay described below or point Vellic at an Ollama server you already run.

**Suggested starter model:** `llama3.1:8b-instruct-q4_K_M` (quantized 4-bit, ~5 GB VRAM / ~8 GB RAM)

---

## Option 1 — Docker Compose overlay (recommended for dev / small on-prem)

The repo ships `docker-compose.ollama.yml` as an opt-in overlay:

```bash
# Start the full stack alongside the Ollama overlay
docker compose -f docker-compose.yml -f docker-compose.ollama.yml up -d

# Confirm Ollama is healthy
docker compose exec ollama ollama list
```

The `ollama` service pulls `$OLLAMA_MODEL` on first boot (default
`nomic-embed-text`; set the env var in `.env` to pull a larger generation
model instead) and serves it on `http://ollama:11434` on the internal
Docker network.

### Admin UI — first-time setup

Open **Settings → LLM Provider** in the Admin panel and save:

| Field | Value |
|---|---|
| Provider | `ollama` |
| Base URL | `http://ollama:11434` |
| Model | whichever tag you pulled (e.g. `llama3.1:8b-instruct-q4_K_M`) |
| API Key | *(not required)* |

Click **Save**, then **Test** to verify the worker can reach Ollama.

---

## Option 2 — External Ollama instance (recommended for production)

Run Ollama on a dedicated host (bare-metal, a GPU-equipped VM, or another
container outside this stack) and point the worker at it:

1. Install Ollama on the target host and pull your model: `ollama pull <tag>`.
2. In **Admin UI → Settings → LLM Provider**, set:
   - **Provider:** `ollama`
   - **Base URL:** `http://<your-ollama-host>:11434`
   - **Model:** the model tag pulled on that host
3. Ensure the Ollama host is reachable from the worker container on port `11434`.

There are no `LLM_*` environment variables — all LLM configuration is
UI-driven and stored in the `llm_settings` table.

---

## Changing the model

### With the overlay

```bash
# Pull Mistral 7B (example)
docker compose exec ollama ollama pull mistral:7b-instruct

# List available local models
docker compose exec ollama ollama list
```

Then update the **Model** field in **Admin UI → Settings → LLM Provider** and save.

### On an external Ollama host

```bash
# On the Ollama host
ollama pull mistral:7b-instruct
ollama list
```

Then update the **Model** field in the Admin UI.

### Recommended models by hardware

| Model | VRAM required | Notes |
|---|---|---|
| `llama3.1:8b-instruct-q4_K_M` | ~5 GB | Good balance of speed and quality |
| `llama3.1:8b-instruct` (fp16) | ~16 GB | Higher accuracy, needs GPU |
| `mistral:7b-instruct` | ~5 GB | Fast, strong on code review tasks |
| `codellama:13b-instruct` | ~10 GB | Code-focused, better for large diffs |
| `llama3.1:70b-instruct-q4_K_M` | ~40 GB | Best quality, requires high-VRAM GPU |

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
# Manual health check (overlay)
curl http://localhost:11434/api/tags

# Manual health check (external host)
curl http://<your-ollama-host>:11434/api/tags
```

---

## Troubleshooting

**`model not found` error** — The model tag in the Admin UI doesn't match what's pulled
on the Ollama host. Run `ollama list` (or `docker compose exec ollama ollama list` for
the overlay) and update the Admin UI to match.

**Slow first response** — Ollama loads the model into memory on first request. Subsequent
requests are faster. Consider pre-warming with a test prompt after pulling a model.

**Out of memory** — Switch to a smaller quantized model (e.g. `q4_K_M`) or add a GPU.

**Worker logs `No LLM config found`** — You haven't saved an Admin UI config yet. Open
**Settings → LLM Provider**, fill it in, and click Save.
