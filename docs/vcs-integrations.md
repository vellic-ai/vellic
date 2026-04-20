# VCS Integrations

Vellic uses a webhook-based adapter model. Each platform adapter converts platform-specific webhook payloads into the internal `PREvent` format.

## GitHub

### Webhook setup

1. Go to your GitHub repo → **Settings → Webhooks → Add webhook**
2. **Payload URL**: `https://<your-host>/webhook/github`
3. **Content type**: `application/json`
4. **Secret**: same value as `GITHUB_WEBHOOK_SECRET` in your `.env`
5. **Events**: select **Pull requests** (or "Send me everything")

### Signature validation

Vellic validates the `X-Hub-Signature-256` header on every request. Requests with a missing or invalid signature are rejected with `403`.

### Events handled

| GitHub event | Action | Behaviour |
|---|---|---|
| `pull_request` | `opened` | Triggers full pipeline |
| `pull_request` | `synchronize` | Triggers full pipeline (new commits pushed) |
| `pull_request` | `reopened` | Triggers full pipeline |
| All others | any | Acknowledged (`200`) but not queued |

---

## GitLab

> 🚧 **Status: in progress.** The `PREvent` model and pipeline already support `platform: "gitlab"`. The adapter and webhook route are being built.

### Planned setup

1. Go to your GitLab project → **Settings → Webhooks**
2. **URL**: `https://<your-host>/webhook/gitlab`
3. **Secret token**: set `GITLAB_WEBHOOK_SECRET` in `.env`
4. **Trigger**: Merge request events

Adapter location: `worker/app/adapters/gitlab.py` (coming soon).

---

## Bitbucket

> 📋 **Status: planned.**

Adapter location: `worker/app/adapters/bitbucket.py` (planned).

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
        diff_url=payload["..."],       # URL to fetch file diffs
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

3. Add a feedback poster in `worker/app/pipeline/feedback_poster.py` that calls your platform's review/comment API.

4. Open a PR — contributions welcome.
