#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

backend_pid=""
frontend_pid=""

cleanup() {
  trap - INT TERM EXIT
  if [[ -n "$frontend_pid" ]] && kill -0 "$frontend_pid" >/dev/null 2>&1; then
    kill "$frontend_pid" >/dev/null 2>&1 || true
  fi
  if [[ -n "$backend_pid" ]] && kill -0 "$backend_pid" >/dev/null 2>&1; then
    kill "$backend_pid" >/dev/null 2>&1 || true
  fi
  wait "$frontend_pid" "$backend_pid" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "Starting MIDI Mapper dev stack..."
echo "Backend:  http://127.0.0.1:8765/api/health"
echo "Frontend: http://localhost:3000/v2"

"$ROOT_DIR/scripts/dev-backend.sh" &
backend_pid=$!

"$ROOT_DIR/scripts/dev-frontend.sh" &
frontend_pid=$!

wait -n "$backend_pid" "$frontend_pid"
exit_code=$?
cleanup
exit "$exit_code"
