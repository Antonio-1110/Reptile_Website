#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT_DIR/.dev/pids"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No development process file found."
  exit 0
fi

kill_tree() {
  local pid="$1"
  local child

  if ! kill -0 "$pid" 2>/dev/null; then
    return
  fi

  while read -r child; do
    [[ -n "$child" ]] && kill_tree "$child"
  done < <(pgrep -P "$pid" 2>/dev/null || true)

  kill "$pid" 2>/dev/null || true
}

while IFS='=' read -r service pid; do
  [[ -n "$service" && -n "$pid" ]] || continue
  kill_tree "$pid"
  echo "Stopped $service (PID $pid)."
done <"$PID_FILE"

rm -f "$PID_FILE"
