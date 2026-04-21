# GitLab Integration

Vellic integrates with GitLab via webhooks. When a merge request is opened, updated, or
reopened, GitLab sends a signed delivery to Vellic, which queues it for AI review and posts
the feedback back as a merge request note.

> **Status:** The GitLab adapter and webhook route are live on the `dev` branch.
> Self-managed GitLab and GitLab.com are both supported.

---

## Prerequisites

- A running Vellic instance reachable from your GitLab instance (or the internet for GitLab.com).
- **Maintainer** or **Owner** access on the GitLab project (to manage webhooks).
- `GITLAB_WEBHOOK_SECRET` set in your Vellic `.env`.
- `GITLAB_BASE_URL` set if you run a self-managed GitLab instance (defaults to `https://gitlab.com`).

---

## Setup

### 1. Generate a webhook token

GitLab uses a plain shared secret (not HMAC). Generate a strong random value:

```bash
openssl rand -hex 32
```

### 2. Add the token to Vellic

In your `.env`:

```dotenv
GITLAB_WEBHOOK_SECRET=<paste-token-here>

# Only needed for self-managed GitLab:
# GITLAB_BASE_URL=https://gitlab.example.com
```

Restart the API service so the new value is picked up.

### 3. Add the webhook on GitLab

#### GitLab.com / self-managed (project-level)

1. Open your GitLab project.
2. Go to **Settings** → **Webhooks**.
3. Fill in the form:

   | Field | Value |
   |---|---|
   | URL | `https://<your-vellic-host>/webhook/gitlab` |
   | Secret token | `<token from step 1>` |
   | Trigger | ✅ Merge request events |
   | SSL verification | Enabled (recommended) |

4. Click **Add webhook**.

GitLab fires a test push immediately. Vellic returns `200 {"status":"ignored"}` because the
test event is not a merge request hook — that is the expected response.

#### Group-level webhooks (GitLab Premium / Ultimate)

Group webhooks cover all projects in a group (including subgroups). Setup is identical to
project-level but done under **Group → Settings → Webhooks**.

### 4. Verify delivery

In **Settings → Webhooks**, click **Test** next to the webhook, then choose
**Merge request events**. Vellic should return `202 {"status":"accepted", ...}` (or `200`
for a duplicate delivery).

---

## GitLab OAuth (personal access token for feedback posting)

Vellic posts review feedback as MR notes using a GitLab personal access token (PAT) or a
project access token.

### Create a personal access token

1. Go to **User settings** → **Access tokens** → **Add new token**.
2. Give it a name (`vellic-bot`) and select an expiry.
3. Grant these scopes:

   | Scope | Why |
   |---|---|
   | `api` | Post MR notes and read diff data |

4. Click **Create personal access token** and copy the value.

### Create a project access token (recommended for production)

Project access tokens are scoped to a single project and do not expire with a user account.

1. Go to **Project → Settings → Access tokens → Add new token**.
2. Role: **Developer** (minimum for posting notes).
3. Scopes: `api`.
4. Copy the token.

### Add the token to Vellic

```dotenv
GITLAB_TOKEN=<your-token>
```

---

## Permissions reference

| Requirement | Minimum level |
|---|---|
| Add project webhook | Maintainer |
| Add group webhook | Owner |
| PAT scope for posting notes | `api` |
| Project access token role | Developer |
| Self-managed: network policy | Vellic host must be reachable from GitLab (check Admin → Network → Outbound requests) |

### Self-managed: allow outbound requests to Vellic

If your self-managed GitLab blocks outbound webhook requests (common in air-gapped setups):

1. Go to **Admin → Settings → Network → Outbound requests**.
2. Add your Vellic host to the allowlist:
   ```
   https://vellic.example.com
   ```

---

## Events handled

| GitLab event header (`X-Gitlab-Event`) | Action | Vellic behaviour |
|---|---|---|
| `Merge Request Hook` | `open` | Full AI review triggered |
| `Merge Request Hook` | `reopen` | Full AI review triggered |
| `Merge Request Hook` | `update` | Full AI review triggered (new commits) |
| `Merge Request Hook` | `close`, `merge`, etc. | Returns `200 {"status":"ignored"}` |
| `Note Hook` | any | Acknowledged; not queued (future: threaded replies) |
| Any other event | any | Returns `200 {"status":"ignored"}` |

GitLab does not send a stable delivery UUID header. Vellic derives an idempotency key from the
MR object ID and a received timestamp. Duplicate deliveries within the same second for the same
MR may be processed twice; this is expected to be rare in practice.

---

## Troubleshooting

### Webhook returns 401

**Cause:** The `X-Gitlab-Token` header does not match `GITLAB_WEBHOOK_SECRET`.

**Fix:**
1. Re-generate the token (`openssl rand -hex 32`).
2. Update both the GitLab webhook **Secret token** field and your Vellic `.env`.

Note: GitLab sends the token as a plain string, not as an HMAC. Vellic compares it with
`hmac.compare_digest` to prevent timing attacks, but no hashing is involved.

### Webhook returns 200 with `"status": "ignored"` for all events

Check the `X-Gitlab-Event` header in GitLab's delivery log. Vellic only processes
`Merge Request Hook` and `Note Hook`. Ensure the **Merge request events** trigger is enabled
on the webhook.

### Reviews are not posted after delivery is accepted

1. Check worker logs:
   ```bash
   docker compose logs -f worker
   ```
2. Confirm `GITLAB_TOKEN` is set and valid:
   ```bash
   curl -s --header "PRIVATE-TOKEN: $GITLAB_TOKEN" \
     https://gitlab.com/api/v4/user | jq .username
   ```
3. For self-managed instances, confirm `GITLAB_BASE_URL` points to your instance
   (default is `https://gitlab.com`).
4. Ensure the token has the `api` scope and Developer or higher access on the project.

### Self-managed GitLab: "SSL certificate problem" in webhook test

If GitLab cannot verify Vellic's TLS certificate, enable **Disable SSL verification** on the
webhook **only if** Vellic is on a private network with a self-signed cert. For public
deployments, use a valid certificate from Let's Encrypt or your CA.

### Diff endpoint returns 404

Vellic fetches diffs from:
```
GET <GITLAB_BASE_URL>/api/v4/projects/<encoded-path>/merge_requests/<iid>/changes
```

If `GITLAB_BASE_URL` is wrong or the token lacks `api` scope, you will see 401/404 in the
worker logs on the diff-fetcher step.

---

## Next steps

- [GitHub integration](./github.md)
- [Configuration reference](../configuration.md)
- [Architecture overview](../architecture.md)
