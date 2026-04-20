#!/usr/bin/env bash
# Sets up local dev environment. Run once after cloning.
set -euo pipefail

echo "==> Checking dependencies..."
for cmd in docker python3 git; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "ERROR: $cmd not found"; exit 1; }
done

COMPOSE_VERSION=$(docker compose version --short 2>/dev/null || echo "0")
if [[ "$COMPOSE_VERSION" < "2" ]]; then
  echo "ERROR: docker compose v2+ required (got $COMPOSE_VERSION)"
  exit 1
fi

echo "==> Building images..."
docker compose build --parallel

echo "==> Starting stack..."
docker compose up -d

echo "==> Waiting for health checks (up to 60s)..."
bash "$(dirname "$0")/health-check.sh"

echo ""
echo "Stack is up:"
echo "  API:    http://localhost:8000/health"
echo "  Admin:  http://localhost:8001/health"
echo "  Worker: http://localhost:8002/health"
echo ""
echo "To tail logs:  docker compose logs -f"
echo "To stop:       docker compose down"
