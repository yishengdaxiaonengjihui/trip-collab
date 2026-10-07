#!/usr/bin/env bash
# 单容器启动：先起 uvicorn，健康检查通过后灌演示数据，最后 wait 保持前台。
set -euo pipefail

PORT="${PORT:-7860}"
TRIP_DB="${TRIP_DB:-/data/trip.db}"
export PORT TRIP_DB
mkdir -p "$(dirname "$TRIP_DB")"

# 容器重启后磁盘可能保留，避免重复播种
fresh=0
[ -f "$TRIP_DB" ] || fresh=1

uvicorn backend.app.main:app --host 0.0.0.0 --port "$PORT" &
app_pid=$!

trap 'kill -TERM "$app_pid" 2>/dev/null || true' TERM INT

echo "[entrypoint] waiting for app on :$PORT ..."
python - "$PORT" <<'PY'
import sys
import time
import urllib.request

port = sys.argv[1]
for _ in range(90):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1).read()
        sys.exit(0)
    except Exception:
        time.sleep(1)
sys.exit(1)
PY

if [ "$fresh" = "1" ] && [ "${SEED_DEMO:-1}" = "1" ]; then
  echo "[entrypoint] seeding demo data ..."
  TRIP_API_BASE="http://127.0.0.1:$PORT" python frontend/seed_demo.py \
    || echo "[entrypoint] seed failed, continuing without demo data"
fi

echo "[entrypoint] ready."
wait "$app_pid"
