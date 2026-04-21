# Security

Vellic is designed to run in your infrastructure. This section covers the security model, credential handling, and hardening guidance.

---

## Guides

| | |
|---|---|
| [Threat model](threat-model.md) | STRIDE analysis — components, trust boundaries, mitigations |
| [Encrypted secrets & BYOK](../llm-providers/byok.md) | How API keys are stored and how to bring your own key |
| [Contributor checklist](contributor-checklist.md) | Security requirements for PRs — for contributors and reviewers |

---

## Core principles

### Encrypted credentials at rest

All LLM API keys and MCP server credentials are encrypted with **AES-256-GCM** before being written to PostgreSQL. The encryption key is derived from `SECRET_KEY` in the admin service environment. Losing `SECRET_KEY` means losing access to stored credentials — back it up alongside your database.

```bash
# Generate a strong SECRET_KEY
openssl rand -base64 32
```

Set it as an environment variable on the `admin` service:

```yaml
# docker-compose.yml
admin:
  environment:
    SECRET_KEY: "${SECRET_KEY}"
```

### BYOK (Bring Your Own Key)

Vellic never proxies or caches your LLM API keys through external servers. You configure them directly in the Admin UI — they are stored encrypted in your own database and sent directly from the `worker` service to the LLM provider. See [LLM providers → BYOK](../llm-providers/byok.md) for step-by-step setup.

### Webhook signature validation

All inbound webhooks are validated with **HMAC-SHA256** (`X-Hub-Signature-256` for GitHub). Requests with missing or invalid signatures return `400 Bad Request` immediately — no processing occurs.

Generate a strong secret:

```bash
openssl rand -hex 32
```

Set `GITHUB_WEBHOOK_SECRET` (or the equivalent for your VCS platform) in `.env`.

### Privacy-first default

The default compose stack ships **Ollama** as the LLM provider. Your code never leaves your infrastructure. If you switch to a cloud LLM provider (OpenAI, Anthropic), the Admin UI shows a **privacy warning** to make the data flow explicit.

---

## Attack surface summary

| Exposed surface | Protection |
|---|---|
| Webhook endpoint (port 8000) | HMAC signature validation, deduplication |
| Admin UI / API (port 8001) | Session authentication, admin password required on first launch |
| Postgres | Not exposed outside Docker network by default |
| Redis | Not exposed outside Docker network by default |
| Ollama | Not exposed outside Docker network by default |
| MCP subprocesses | Sandboxed cwd, no env inheritance, process group isolation |

For a full threat analysis see [threat-model.md](threat-model.md).

---

## Hardening checklist (production)

- [ ] Set a strong `SECRET_KEY`, `POSTGRES_PASSWORD`, and `GITHUB_WEBHOOK_SECRET`.
- [ ] Expose only the `api` service (port 8000) and `frontend` (port 80) to the internet. Keep `admin`, `postgres`, `redis`, and `ollama` internal.
- [ ] Use TLS termination (nginx / ingress controller) in front of `api` and `frontend`.
- [ ] Rotate `GITHUB_WEBHOOK_SECRET` and update it in your VCS platform settings on a schedule.
- [ ] If using a cloud LLM, ensure your provider has a DPA in place.
- [ ] In Kubernetes, apply a `NetworkPolicy` that restricts worker egress to only the LLM endpoint and VCS API.

---

## Related

- [Configuration](../configuration.md) — environment variables, secret generation
- [Deployment](../deployment/index.md) — production setup
- [LLM providers](../llm-providers/index.md) — BYOK setup per provider
