#!/usr/bin/env bash
# Sends a sample pull_request.opened payload to the local API with a valid
# HMAC-SHA256 signature, matching GitHub's X-Hub-Signature-256 format.
#
# Reads the webhook HMAC secret directly from Postgres (webhook_config.hmac), the
# same place the api service reads it from. Requires `docker compose` to be running.
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
SECRET="${GITHUB_WEBHOOK_SECRET:-}"

if [[ -z "$SECRET" ]]; then
  # Fetch the encrypted HMAC from Postgres and decrypt it via the admin container.
  if ! docker compose ps admin --format '{{.Name}}' | grep -q .; then
    echo "ERROR: admin container is not running; start the stack with 'make up' first." >&2
    exit 1
  fi
  SECRET=$(docker compose exec -T admin python -c "
import asyncio, sys; sys.path.insert(0, '/app')
from app.db import init_pool, close_pool, get_pool
from app.crypto import decrypt
async def run():
    await init_pool()
    row = await get_pool().fetchrow('SELECT hmac FROM webhook_config WHERE id = 1')
    await close_pool()
    print(decrypt(row['hmac']) if row and row['hmac'] else '')
asyncio.run(run())
" | tr -d '\r\n')
fi

if [[ -z "$SECRET" ]]; then
  echo "ERROR: could not fetch webhook HMAC from webhook_config." >&2
  echo "       Open Admin UI → Settings → Webhook and click 'Rotate' first." >&2
  exit 1
fi

DELIVERY_ID="test-$(date +%s)"

PAYLOAD='{"action":"opened","number":1,"pull_request":{"title":"Test PR","head":{"sha":"abc1234"},"base":{"ref":"main"}},"repository":{"full_name":"vellic-ai/vellic"}}'

SIGNATURE="sha256=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')"

echo "==> POST $API_URL/webhook/github"
echo "    X-GitHub-Delivery: $DELIVERY_ID"
echo "    X-Hub-Signature-256: $SIGNATURE"

HTTP_STATUS=$(curl -s -o /tmp/webhook-response.json -w "%{http_code}" \
  -X POST "$API_URL/webhook/github" \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: $DELIVERY_ID" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -d "$PAYLOAD")

echo "    Response: $HTTP_STATUS $(cat /tmp/webhook-response.json 2>/dev/null)"

if [[ "$HTTP_STATUS" == "202" ]]; then
  echo "==> OK: got 202 Accepted"
else
  echo "ERROR: expected 202, got $HTTP_STATUS" >&2
  exit 1
fi
