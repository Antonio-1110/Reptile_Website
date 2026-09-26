#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEV_DIR="$ROOT_DIR/.dev"
PID_FILE="$DEV_DIR/pids"
LOG_DIR="$DEV_DIR/logs"

mkdir -p "$LOG_DIR"

if [[ -f "$PID_FILE" ]]; then
  echo "Development processes may already be running. Run ./stop-dev.sh first."
  exit 1
fi

if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/.venv/bin/python"
elif [[ -x "$ROOT_DIR/backend/.venv/bin/python" ]]; then
  PYTHON="$ROOT_DIR/backend/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  echo "python3 is required to start the backend."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "npm is required to start the frontend."
  exit 1
fi

(
  cd "$ROOT_DIR/backend"
  # The compiled translations (.mo) aren't committed; build them from the .po files.
  "$PYTHON" manage.py compilemessages -v0 --ignore=".venv/*" --ignore=".e2e/*" \
    || echo "Warning: couldn't compile translations; install GNU gettext for Chinese API messages." >&2
  exec "$PYTHON" manage.py runserver 127.0.0.1:8000 >"$LOG_DIR/backend.log" 2>&1
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/Frontend"
  exec npm run dev -- --host 127.0.0.1 >"$LOG_DIR/frontend.log" 2>&1
) &
FRONTEND_PID=$!

printf 'backend=%s\nfrontend=%s\n' "$BACKEND_PID" "$FRONTEND_PID" >"$PID_FILE"

cleanup() {
  rm -f "$PID_FILE"
}
trap cleanup EXIT

# Give both servers a moment to fail fast (missing packages, port in use) before reporting success.
sleep 3

if ! kill -0 "$BACKEND_PID" 2>/dev/null; then
  echo "Backend failed to start. See $LOG_DIR/backend.log"
  exit 1
fi

if ! kill -0 "$FRONTEND_PID" 2>/dev/null; then
  echo "Frontend failed to start. See $LOG_DIR/frontend.log"
  exit 1
fi

trap - EXIT
echo "Backend: http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:5173"
echo "Logs: $LOG_DIR"
echo "Stop both with: ./stop-dev.sh"
