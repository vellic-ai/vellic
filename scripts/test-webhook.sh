#!/usr/bin/env bash
# Sends a sample pull_request.opened payload to the local API with a valid
# HMAC-SHA256 signature, matching GitHub's X-Hub-Signature-256 format.
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
SECRET="${GITHUB_WEBHOOK_SECRET:-}"

if [[ -z "$SECRET" ]]; then
  # Try loading from .env in repo root
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  ENV_FILE="$SCRIPT_DIR/../.env"
  if [[ -f "$ENV_FILE" ]]; then
    # shellcheck disable=SC1090
    source <(grep -E '^GITHUB_WEBHOOK_SECRET=' "$ENV_FILE")
    SECRET="${GITHUB_WEBHOOK_SECRET:-}"
  fi
fi

if [[ -z "$SECRET" ]]; then
  echo "ERROR: GITHUB_WEBHOOK_SECRET is not set. Export it or define it in .env" >&2
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
