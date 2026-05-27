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

if ! command -v pnpm >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing pnpm.

Install it with Corepack:
  corepack enable
  corepack prepare pnpm@latest --activate
EOF
  exit 1
fi

backend_pid=""
frontend_pid=""
preview_port="${MIDI_MAPPER_PREVIEW_PORT:-3001}"
preview_url="http://localhost:${preview_port}/v2"

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

is_port_open() {
  local port="$1"

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$port" <<'PY'
import socket
import sys

port = int(sys.argv[1])
try:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        sys.exit(0 if sock.connect_ex(("127.0.0.1", port)) == 0 else 1)
except OSError:
    sys.exit(1)
PY
    return
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -ltn "sport = :${port}" 2>/dev/null | grep -q ":${port}"
    return
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"${port}" -sTCP:LISTEN -n -P >/dev/null 2>&1
    return
  fi

  return 1
}

if is_port_open 3000; then
  cat >&2 <<'EOF'
Warning: port 3000 is already occupied.

Desktop dev mode uses port 3000. Preview mode uses port 3001 by default so it
does not silently connect Tauri to an existing Next dev server.
EOF
fi

if is_port_open "$preview_port"; then
  cat >&2 <<EOF
Preview port ${preview_port} is already occupied.

Stop the process using that port, or choose another one:
  MIDI_MAPPER_PREVIEW_PORT=3002 bash scripts/preview-desktop.sh
EOF
  exit 1
fi

echo "Building frontend for desktop preview..."
(
  cd src
  if [[ ! -d "node_modules" ]]; then
    pnpm install
  fi
  pnpm build
)

echo "Starting MIDI Mapper desktop preview stack..."
echo "Backend:  http://127.0.0.1:8765/api/health"
echo "Frontend: ${preview_url}"
echo "Desktop:  Tauri shell"

"$ROOT_DIR/scripts/dev-backend.sh" &
backend_pid=$!

(
  cd "$ROOT_DIR/src"
  exec pnpm exec next start --hostname localhost --port "$preview_port"
) &
frontend_pid=$!

wait_for_url "Backend" "http://127.0.0.1:8765/api/health" "$backend_pid" 30 "$frontend_pid"
wait_for_url "Frontend" "$preview_url" "$frontend_pid" 45 "$backend_pid"

cargo tauri dev --config "{\"build\":{\"devUrl\":\"${preview_url}\"}}"
exit_code=$?
cleanup
exit "$exit_code"
