#!/bin/sh
set -e

MAX_RETRIES=10
DELAY=2

i=1
while [ "$i" -le "$MAX_RETRIES" ]; do
    echo "alembic upgrade head (attempt $i/$MAX_RETRIES)..."
    if alembic upgrade head; then
        echo "migrations applied"
        break
    fi
    if [ "$i" -eq "$MAX_RETRIES" ]; then
        echo "migration failed after $MAX_RETRIES attempts" >&2
        exit 1
    fi
    echo "retrying in ${DELAY}s..."
    sleep "$DELAY"
    DELAY=$((DELAY * 2))
    i=$((i + 1))
done

exec "$@"
