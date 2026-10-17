#!/usr/bin/env bash
# Starts the worker (owns the models) and the API in one container. FORTE_API_KEY must be set.
set -euo pipefail
: "${FORTE_API_KEY:?set FORTE_API_KEY}"
mkdir -p /data/uploads /data/cache
python -m server.worker --poll 1.0 &
WORKER=$!
uvicorn server.app:app --host 0.0.0.0 --port "${PORT:-8000}" --log-level info &
API=$!
trap 'kill $WORKER $API 2>/dev/null || true' TERM INT
wait -n $WORKER $API
kill $WORKER $API 2>/dev/null || true
