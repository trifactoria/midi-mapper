#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v cargo >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing cargo.

Install Rust with rustup, then rerun this script:
  https://rustup.rs/
EOF
  exit 1
fi

if ! cargo tauri --version >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing cargo-tauri.

Install the Tauri CLI:
  cargo install tauri-cli --version '^2'
EOF
  exit 1
fi

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

wait_for_url() {
  local label="$1"
  local url="$2"
  local pid="$3"
  local attempts="${4:-30}"
  local companion_pid="${5:-}"

  if ! command -v curl >/dev/null 2>&1; then
    sleep 2
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      wait "$pid"
      return 1
    fi
    return 0
  fi

  for _ in $(seq 1 "$attempts"); do
    if curl --silent --fail --output /dev/null "$url"; then
      return 0
    fi
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      wait "$pid"
      return 1
    fi
    if [[ -n "$companion_pid" ]] && ! kill -0 "$companion_pid" >/dev/null 2>&1; then
      wait "$companion_pid"
      return 1
    fi
    sleep 1
  done

  echo "$label did not become ready at $url" >&2
  return 1
}

echo "Starting MIDI Mapper desktop dev stack..."
echo "Backend:  http://127.0.0.1:8765/api/health"
echo "Frontend: http://localhost:3000/v2"
echo "Desktop:  Tauri shell"

"$ROOT_DIR/scripts/dev-backend.sh" &
backend_pid=$!

"$ROOT_DIR/scripts/dev-frontend.sh" &
frontend_pid=$!

wait_for_url "Backend" "http://127.0.0.1:8765/api/health" "$backend_pid" 30 "$frontend_pid"
wait_for_url "Frontend" "http://localhost:3000/v2" "$frontend_pid" 45 "$backend_pid"

cargo tauri dev
exit_code=$?
cleanup
exit "$exit_code"
