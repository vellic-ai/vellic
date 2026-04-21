# Quickstart Guide

This guide walks you through installing Vellic, wiring it to a GitHub repository, and seeing your first automated PR review — in under 15 minutes.

**Prerequisites:** Docker ≥ 24 and Docker Compose v2. No other runtime dependencies.

---

## 1. Install

```bash
git clone https://github.com/vellic-ai/vellic.git
cd vellic
```

## 2. Configure

Copy the example environment file and fill in two required values:

```bash
cp .env.example .env
```

Open `.env` and set:

```dotenv
POSTGRES_PASSWORD=<a strong password>
GITHUB_WEBHOOK_SECRET=<output of: openssl rand -hex 32>
```

Everything else — LLM provider, model, API keys, per-repo settings — is configured in the Admin UI after the stack is running. You do not need to edit `.env` further.

> **Generate secrets quickly:**
> ```bash
> echo "POSTGRES_PASSWORD=$(openssl rand -base64 24)"
> echo "GITHUB_WEBHOOK_SECRET=$(openssl rand -hex 32)"
> ```

## 3. Start the stack

```bash
docker compose up --build -d
```

This builds and starts five containers:

| Container | Port | Role |
|---|---|---|
| `postgres` | 5432 | Persistent storage |
| `redis` | 6379 | Arq job queue |
| `ollama` | 11434 | Local LLM inference (default) |
| `api` | 8000 | Webhook ingestion |
| `worker` | 8002 | Async pipeline |
| `admin` | 8001 | REST API for the SPA |
| `frontend` | 80 | Admin SPA (nginx) |

The `api` container runs Alembic migrations on startup, so the database schema is created automatically.

## 4. Verify health

```bash
bash scripts/health-check.sh
```

Or check each endpoint manually:

```
http://localhost:8000/health   → {"status": "ok", "service": "api"}
http://localhost:8001/health   → {"status": "ok", "service": "admin"}
http://localhost:8002/health   → {"status": "ok", "service": "worker"}
http://localhost/health        → 200 OK (nginx)
```

All four must be healthy before proceeding. If a service is not ready, check its logs with `docker compose logs <service>`.

## 5. Set up the Admin UI

Open **http://localhost** in your browser. You will be prompted to create an admin password — this is the only credential for the UI.

Once logged in, you can leave the default LLM configuration (Ollama with `llama3.1:8b-instruct-q4_K_M`) as-is for a local, privacy-first setup. If you want to use a cloud provider, see [LLM Providers](llm-providers.md).

## 6. Connect a GitHub repository

### Create a webhook in GitHub

1. Go to your repository → **Settings → Webhooks → Add webhook**.
2. Set **Payload URL** to `https://<your-public-host>/webhook/github`.
3. Set **Content type** to `application/json`.
4. Set **Secret** to the same value you put in `GITHUB_WEBHOOK_SECRET`.
5. Under "Which events", select **Let me select individual events**, then check:
   - **Pull requests**
   - **Pull request reviews**
6. Click **Add webhook**.

> **Local development:** GitHub cannot reach `localhost`. Use [ngrok](https://ngrok.com/) or a similar tunnelling tool:
> ```bash
> ngrok http 8000
> # Use the https://xxx.ngrok.io URL as your Payload URL
> ```

### Verify the connection

GitHub sends a `ping` event when a webhook is created. Check **http://localhost/deliveries** — you should see a delivery with event type `ping` and status `done`.

## 7. Trigger your first PR review

Open or re-open a pull request in the connected repository. Vellic listens for `pull_request` events with action `opened`, `synchronize`, or `reopened`.

Within a few seconds:

1. The webhook appears in **http://localhost/deliveries** with status `done`.
2. A pipeline job appears in **http://localhost/jobs** with status `done`.
3. A code review is posted to the pull request in GitHub — inline comments at the changed lines, plus a summary.

If the job shows `failed`, click it to see the error. Common causes are shown in [Troubleshooting](#troubleshooting) below.

## 8. Tune the configuration

### Change the LLM provider

Go to **http://localhost/settings**. The provider dropdown lists all supported backends:

| Provider | When to use |
|---|---|
| `ollama` (default) | On-prem, no data leaves your host |
| `vllm` | 🚧 Coming soon — self-hosted OpenAI-compatible endpoint |
| `openai` | OpenAI API (requires API key; data sent to OpenAI) |
| `anthropic` | Anthropic API (requires API key; data sent to Anthropic) |
| `claude_code` | Local Claude Code CLI (data sent to Anthropic API) |

Cloud providers show a privacy warning. After saving, click **Test** to verify the connection.

### Per-repo overrides

Go to **http://localhost/repos** to enable or disable Vellic for specific repositories, or to override the LLM provider and model for a single repo or an entire org (`org/*`).

---

## Troubleshooting

**No deliveries appear after opening a PR**

- Confirm the webhook is enabled in GitHub (green checkmark).
- Confirm `GITHUB_WEBHOOK_SECRET` in `.env` matches the secret you set in GitHub.
- Check the api logs: `docker compose logs api`.

**Job status is `failed`**

- Check `docker compose logs worker` for the Python traceback.
- If the LLM is unreachable, the Ollama container may still be pulling the model. Watch progress with `docker compose logs ollama`.
- If the model is not found, update the model name in the Admin UI settings.

**Inline comments are missing from the GitHub review**

The feedback poster falls back to a summary-only review when GitHub returns a 422 for inline comments (this happens when line numbers in the diff do not match the PR's current state). The summary review is always posted.

**Stack does not start**

- Ensure Docker Compose v2 is installed: `docker compose version`.
- Ensure no other process is using ports 80, 8000, 8001, 8002, 5432, 6379, or 11434.
- Run `docker compose ps` to see which container failed, then `docker compose logs <name>`.

---

## What's next

| | |
|---|---|
| [Architecture](architecture.md) | Understand the pipeline, webhook flow, LLM abstraction, and async job runner |
| [VCS Integrations](vcs-integrations.md) | Connect GitLab, Bitbucket, or a custom webhook |
| [LLM Providers](llm-providers.md) | All supported backends, env vars, privacy notes |
| [Configuration](configuration.md) | Full environment variable reference |
| [Deployment](deployment.md) | Kubernetes manifests, production secrets, scaling |
| [Contributing](contributing.md) | Dev setup, code style, how to add a VCS adapter or LLM provider |
