#!/usr/bin/env bash
# Run E2E smoke tests locally using docker for infra + local frontend dev server.
# Mirrors the CI e2e.yml workflow.
#
# Usage:
#   ./scripts/e2e-local.sh           # full run (starts services, seeds, runs tests, tears down)
#   ./scripts/e2e-local.sh --no-down # keep services running after tests (faster re-runs)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
FRONTEND="$ROOT/frontend"

KEEP_UP=false
for arg in "$@"; do
  [[ "$arg" == "--no-down" ]] && KEEP_UP=true
done

E2E_ADMIN_PASSWORD="${E2E_ADMIN_PASSWORD:-vellic_dev}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-vellic_dev}"
ADMIN_PORT="${ADMIN_PORT:-8001}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

echo "==> Starting postgres + redis..."
POSTGRES_PASSWORD="$POSTGRES_PASSWORD" docker compose -f "$ROOT/docker-compose.yml" up -d postgres redis

echo "==> Waiting for postgres..."
for i in $(seq 1 30); do
  docker compose -f "$ROOT/docker-compose.yml" exec -T postgres \
    pg_isready -U vellic >/dev/null 2>&1 && break
  sleep 2
done

echo "==> Running DB migrations..."
(cd "$ROOT/api" && DATABASE_URL="postgresql://vellic:${POSTGRES_PASSWORD}@localhost:5432/vellic" alembic upgrade head)

echo "==> Seeding E2E test data..."
PGPASSWORD="$POSTGRES_PASSWORD" psql -h localhost -U vellic -d vellic -f "$SCRIPT_DIR/e2e-seed.sql"

echo "==> Starting admin service (VELLIC_ADMIN_V2=1)..."
(cd "$ROOT/admin" && \
  DATABASE_URL="postgresql://vellic:${POSTGRES_PASSWORD}@localhost:5432/vellic" \
  REDIS_URL="redis://localhost:6379" \
  VELLIC_ADMIN_V2=1 \
  PORT="$ADMIN_PORT" \
  uvicorn app.main:app --host 0.0.0.0 --port "$ADMIN_PORT" &)

for i in $(seq 1 20); do
  curl -sf "http://localhost:${ADMIN_PORT}/health" >/dev/null 2>&1 && break
  sleep 2
done
echo "Admin service ready at http://localhost:${ADMIN_PORT}"

echo "==> Building frontend..."
(cd "$FRONTEND" && VITE_API_BASE="http://localhost:${ADMIN_PORT}" npm run build)

echo "==> Starting frontend preview..."
(cd "$FRONTEND" && npm run preview -- --host --port "$FRONTEND_PORT" &)

for i in $(seq 1 15); do
  curl -sf "http://localhost:${FRONTEND_PORT}" >/dev/null 2>&1 && break
  sleep 2
done
echo "Frontend preview ready at http://localhost:${FRONTEND_PORT}"

echo "==> Running Playwright smoke tests..."
(cd "$FRONTEND" && \
  E2E_BASE_URL="http://localhost:${FRONTEND_PORT}" \
  E2E_API_BASE="http://localhost:${ADMIN_PORT}" \
  E2E_ADMIN_PASSWORD="$E2E_ADMIN_PASSWORD" \
  npm run test:e2e)

echo ""
echo "E2E tests finished."

if [[ "$KEEP_UP" == false ]]; then
  echo "==> Stopping docker services..."
  POSTGRES_PASSWORD="$POSTGRES_PASSWORD" docker compose -f "$ROOT/docker-compose.yml" down
fi
