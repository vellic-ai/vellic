# VCS Integrations

Vellic uses a webhook-based adapter model. Each platform adapter converts platform-specific
webhook payloads into the internal `PREvent` format, which drives the unified AI review
pipeline.

## Supported platforms

| Platform | Status | Guide |
|---|---|---|
| GitHub | ✅ Live | [docs/integrations/github.md](integrations/github.md) |
| GitLab | ✅ Live | [docs/integrations/gitlab.md](integrations/gitlab.md) |
| Bitbucket | 🚧 Alpha | [Enable flag](#bitbucket) |
| Gitea / Forgejo | 🚧 Alpha | [Enable flag](#gitea--forgejo) |
| Custom / self-hosted | ✅ Extensible | [Custom adapter guide](#custom--self-hosted-platforms) |

---

## GitHub

Full setup guide: **[docs/integrations/github.md](integrations/github.md)**

Quick reference:

- Webhook URL: `https://<your-host>/webhook/github`
- Signature header: `X-Hub-Signature-256` (HMAC-SHA256)
- Env var: `GITHUB_WEBHOOK_SECRET`
- Triggers: `pull_request` (opened / synchronize / reopened)

---

## GitLab

Full setup guide: **[docs/integrations/gitlab.md](integrations/gitlab.md)**

Quick reference:

- Webhook URL: `https://<your-host>/webhook/gitlab`
- Token header: `X-Gitlab-Token` (plain shared secret)
- Env vars: `GITLAB_WEBHOOK_SECRET`, `GITLAB_BASE_URL` (self-managed only)
- Triggers: `Merge Request Hook` (open / reopen / update)

---

## Bitbucket

> 🚧 **Status: alpha — available behind the `vcs.bitbucket` feature flag.**

Enable via Admin UI (Settings → Feature flags → "Bitbucket") or:

```bash
VELLIC_FEATURE_VCS_BITBUCKET=true
```

Quick reference:

- Webhook URL: `https://<your-host>/webhook/bitbucket`
- Signature header: `X-Hub-Signature` (HMAC-SHA256)
- Env var: `BITBUCKET_WEBHOOK_SECRET`
- Adapter: `worker/app/adapters/bitbucket.py`

---

## Gitea / Forgejo

> 🚧 **Status: alpha — available behind the `vcs.gitea` feature flag.**

Enable via Admin UI (Settings → Feature flags → "Gitea") or:

```bash
VELLIC_FEATURE_VCS_GITEA=true
```

Quick reference:

- Webhook URL: `https://<your-host>/webhook/gitea`
- Signature header: `X-Gitea-Signature` (HMAC-SHA256)
- Env var: `GITEA_WEBHOOK_SECRET`
- Adapter: `worker/app/adapters/gitea.py`

---

## Custom / self-hosted platforms

Any platform that can send a JSON webhook can be integrated.

### Steps

1. Create `worker/app/adapters/<platform>.py`:

```python
from ..events import PREvent

def normalize_pr(delivery_id: str, payload: dict) -> PREvent:
    return PREvent(
        platform="<platform>",
        event_type="pull_request",
        delivery_id=delivery_id,
        repo=payload["..."],
        pr_number=int(payload["..."]),
        action=payload["..."],
        diff_url=payload["..."],
        base_sha=payload["..."],
        head_sha=payload["..."],
        base_branch=payload["..."],
        title=payload.get("...") or "",
        description=payload.get("...") or "",
    )
```

2. Add a route in `api/app/webhook.py`:

```python
@router.post("/webhook/<platform>")
async def receive_<platform>(request: Request, ...):
    # 1. Validate your platform's signature
    # 2. Parse JSON payload
    # 3. Call normalize_pr(delivery_id, payload)
    # 4. Enqueue the job
```

3. Add a feedback poster in `worker/app/pipeline/feedback_poster.py` that calls your
   platform's review/comment API.

4. Open a PR — contributions welcome.
