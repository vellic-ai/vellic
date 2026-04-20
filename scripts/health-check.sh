#!/usr/bin/env bash
# Polls /health on all three services until they respond 200 or timeout.
set -euo pipefail

TIMEOUT=60
INTERVAL=3
ELAPSED=0

SERVICES=(
  "api|http://localhost:8000/health"
  "admin|http://localhost:8001/health"
  "worker|http://localhost:8002/health"
)

declare -A HEALTHY
for entry in "${SERVICES[@]}"; do
  name="${entry%%|*}"
  HEALTHY[$name]=false
done

while true; do
  ALL_HEALTHY=true
  for entry in "${SERVICES[@]}"; do
    name="${entry%%|*}"
    url="${entry##*|}"
    if [[ "${HEALTHY[$name]}" == "false" ]]; then
      STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 "$url" 2>/dev/null || echo "000")
      if [[ "$STATUS" == "200" ]]; then
        HEALTHY[$name]=true
        echo "  [OK] $name"
      else
        ALL_HEALTHY=false
      fi
    fi
  done

  if $ALL_HEALTHY; then
    echo "All services healthy."
    exit 0
  fi

  if (( ELAPSED >= TIMEOUT )); then
    echo "ERROR: Timeout waiting for services after ${TIMEOUT}s"
    for entry in "${SERVICES[@]}"; do
      name="${entry%%|*}"
      url="${entry##*|}"
      [[ "${HEALTHY[$name]}" == "false" ]] && echo "  [FAIL] $name ($url)"
    done
    exit 1
  fi

  sleep "$INTERVAL"
  ELAPSED=$((ELAPSED + INTERVAL))
done
