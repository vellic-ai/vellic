# GitHub Integration

Vellic integrates with GitHub via webhooks. When a pull request is opened, pushed to, or
reopened, GitHub sends a signed delivery to Vellic, which queues it for AI review and posts
the feedback back as a PR comment.

---

## Prerequisites

- A running Vellic instance reachable from the internet (or GitHub's IP ranges).
- A GitHub repository (personal or organization) where you have **Admin** access.

---

## Option A — Repo-level webhook (simplest)

### 1. Get a webhook secret from the Admin UI

Open the Admin UI → **Settings → Webhook** and click **Rotate**. Vellic generates a fresh HMAC secret, stores it encrypted in the database, and displays it once so you can copy it.

### 2. Add the webhook on GitHub

1. Go to your repository on GitHub.
2. Click **Settings** → **Webhooks** → **Add webhook**.
3. Fill in the form:

   | Field | Value |
   |---|---|
   | Payload URL | `https://<your-vellic-host>/webhook/github` |
   | Content type | `application/json` |
   | Secret | `<secret from step 1>` |
   | Which events? | **Let me select individual events** |

4. Under "Let me select individual events", enable:
   - **Pull requests**
   - **Pull request reviews** *(optional — lets Vellic react to human review comments)*

5. Click **Add webhook**.

GitHub sends a `ping` event immediately. Vellic returns `200` and logs `ignored event=ping`.

### 4. Verify delivery

Back on the **Webhooks** page, click into the new webhook and scroll to **Recent Deliveries**.
The ping delivery should show a green tick and a `200` response.

---

## Option B — GitHub App (recommended for organizations)

A GitHub App lets you install Vellic once at the organization level and automatically cover
all current and future repositories without editing webhook settings per-repo.

### 1. Create the GitHub App

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App**
   (or your org: **Org Settings → Developer settings → GitHub Apps**).
2. Fill in the registration form:

   | Field | Value |
   |---|---|
   | GitHub App name | `Vellic Review` (or any name) |
   | Homepage URL | Your Vellic host URL |
   | Webhook URL | `https://<your-vellic-host>/webhook/github` |
   | Webhook secret | Copy from Admin UI → Settings → Webhook (click **Rotate** first if empty) |

3. Under **Repository permissions**, grant:

   | Permission | Level |
   |---|---|
   | Pull requests | Read & write |
   | Contents | Read-only |
   | Metadata | Read-only (mandatory) |

4. Under **Subscribe to events**, check:
   - **Pull request**
   - **Pull request review**

5. Set **Where can this GitHub App be installed?** to **Any account** (or **Only on this account**
   for private use).

6. Click **Create GitHub App**.

### 2. Note the App ID and generate a private key

After creation, GitHub shows the **App ID** on the app settings page.
Scroll to **Private keys** → **Generate a private key** and save the `.pem` file.

> Vellic does not currently use the private key for API calls — it only needs the webhook
> secret for inbound delivery validation. Keep the key safe for future use.

### 3. Install the App

1. On the App settings page click **Install App**.
2. Choose the account (user or org) and select **All repositories** or specific repos.
3. Click **Install**.

GitHub now delivers webhooks for every matching event on installed repos.

### 4. Set the webhook secret in Vellic

```dotenv
GITHUB_WEBHOOK_SECRET=<webhook-secret-from-step-1>
```

Restart the API service.

---

## Permissions reference

| Permission | Why Vellic needs it |
|---|---|
| Pull requests — read & write | Post review comments and inline suggestions |
| Contents — read | Fetch file diffs for the AI review |
| Metadata — read | Resolve repo/owner info from webhook payload |

No other permissions are required for the core review flow.

---

## Events handled

| GitHub event | Action | Vellic behaviour |
|---|---|---|
| `pull_request` | `opened` | Full AI review triggered |
| `pull_request` | `synchronize` | Full AI review triggered (new commits) |
| `pull_request` | `reopened` | Full AI review triggered |
| `pull_request_review` | any | Acknowledged; not queued (future: threaded replies) |
| Any other event | any | Returns `200 {"status":"ignored"}` |

Duplicate deliveries (same `X-GitHub-Delivery` UUID) are deduplicated by the database layer.

---

## Troubleshooting

### Webhook returns 401

**Cause:** The `X-Hub-Signature-256` header does not match.

Possible reasons:
- The secret in GitHub does not match the one stored in Admin UI → Settings → Webhook.
- The secret field was left blank in GitHub (GitHub omits the header entirely).
- Vellic is behind a reverse proxy that buffers the body before forwarding it, changing
  the bytes used for HMAC computation.

**Fix:**
1. In the Admin UI, open **Settings → Webhook** and click **Rotate** to get a fresh secret.
2. Paste the new value into the GitHub webhook settings.
3. If behind nginx/Caddy, ensure the proxy does not modify the request body
   (no `gzip` decompression on the proxy side for this path).

### Webhook returns 400 — "missing X-GitHub-Delivery header"

GitHub always sends this header. If it is missing, your request did not come from GitHub or
was rewritten by a proxy. Check your reverse-proxy configuration.

### Events appear in GitHub "Recent Deliveries" but no review is posted

1. Check the Vellic worker logs for the `process_webhook` job:
   ```bash
   docker compose logs -f worker
   ```
2. Confirm the GitHub token (Admin UI → Settings → GitHub Personal Access Token) has
   `repo` scope, or — if using the GitHub App path — that the App is installed on the
   target repo with Pull requests: read & write. For a quick check of a PAT:
   ```bash
   curl -s -H "Authorization: Bearer <paste PAT>" https://api.github.com/user | jq .login
   ```
3. Verify the pull request is against a branch in a repo the credential has access to.

### Rate limit errors from GitHub API

If you run Vellic against many repos, the feedback poster may hit GitHub's secondary rate
limits when posting review comments in parallel. Reduce parallelism or upgrade to a GitHub
App installation token (which has higher per-installation limits).

---

## Next steps

- [GitLab integration](./gitlab.md)
- [Configuration reference](../configuration.md)
- [Architecture overview](../architecture.md)
