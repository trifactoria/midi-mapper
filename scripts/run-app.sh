#!/usr/bin/env bash
# Launch MIDI Mapper as a desktop app.
#
# Starts backend, builds/starts production frontend, opens Tauri window.
# All child processes are cleaned up when the window closes or Ctrl-C is pressed.
#
# Usage:
#   bash scripts/run-app.sh
#   MIDI_MAPPER_APP_PORT=3002 bash scripts/run-app.sh  # custom port
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_PORT="${MIDI_MAPPER_APP_PORT:-3001}"
BACKEND_PORT="8765"
BACKEND_HEALTH_URL="http://127.0.0.1:${BACKEND_PORT}/api/health"
APP_URL="http://localhost:${APP_PORT}/v2"

backend_pid=""
frontend_pid=""

# ── Cleanup ───────────────────────────────────────────────────────────────────

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

# ── Dependency checks ─────────────────────────────────────────────────────────

if ! command -v cargo >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing cargo.

Install Rust via rustup:
  https://rustup.rs/
EOF
  exit 1
fi

if ! cargo tauri --version >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing cargo-tauri.

Install it with:
  cargo install tauri-cli --version '^2'
EOF
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing pnpm.

Install via Corepack:
  corepack enable
  corepack prepare pnpm@latest --activate
EOF
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  cat >&2 <<'EOF'
Missing Python virtual environment (.venv).

Set it up with:
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
EOF
  exit 1
fi

# ── Port availability ─────────────────────────────────────────────────────────

is_port_open() {
  local port="$1"
  python3 - "$port" <<'PY' 2>/dev/null
import socket, sys
port = int(sys.argv[1])
try:
    with socket.socket() as s:
        s.settimeout(0.2)
        sys.exit(0 if s.connect_ex(("127.0.0.1", port)) == 0 else 1)
except OSError:
    sys.exit(1)
PY
}

if is_port_open "$BACKEND_PORT"; then
  cat >&2 <<EOF
Port ${BACKEND_PORT} is already in use — the backend cannot start.

Stop the existing process and retry.
EOF
  exit 1
fi

if is_port_open "$APP_PORT"; then
  cat >&2 <<EOF
App port ${APP_PORT} is already in use.

Choose another port:
  MIDI_MAPPER_APP_PORT=3002 bash scripts/run-app.sh
EOF
  exit 1
fi

# ── Frontend build ────────────────────────────────────────────────────────────

(
  cd src
  if [[ ! -d node_modules ]]; then
    echo "[midi-mapper] Installing frontend dependencies..."
    pnpm install
  fi
)

if [[ ! -f src/.next/BUILD_ID ]]; then
  echo "[midi-mapper] Building frontend (first run or rebuild required)..."
  (cd src && pnpm build)
  echo "[midi-mapper] Frontend build complete."
else
  echo "[midi-mapper] Using existing frontend build. (Delete src/.next to force rebuild.)"
fi

# ── Start services ────────────────────────────────────────────────────────────

echo ""
echo "[midi-mapper] Starting backend on port ${BACKEND_PORT}..."
"$ROOT_DIR/scripts/dev-backend.sh" &
backend_pid=$!

echo "[midi-mapper] Starting frontend on port ${APP_PORT}..."
(cd "$ROOT_DIR/src" && exec pnpm exec next start --hostname localhost --port "$APP_PORT") &
frontend_pid=$!

# ── Readiness ─────────────────────────────────────────────────────────────────

wait_for_url() {
  local label="$1"
  local url="$2"
  local pid="$3"
  local max_attempts="${4:-30}"
  local companion_pid="${5:-}"

  if ! command -v curl >/dev/null 2>&1; then
    sleep 3
    return 0
  fi

  local i=0
  while [[ $i -lt $max_attempts ]]; do
    if curl --silent --fail --output /dev/null --max-time 1 "$url" 2>/dev/null; then
      echo "[midi-mapper] $label ready."
      return 0
    fi
    if ! kill -0 "$pid" >/dev/null 2>&1; then
      echo "" >&2
      echo "[midi-mapper] ERROR: $label process exited unexpectedly. Check output above." >&2
      return 1
    fi
    if [[ -n "$companion_pid" ]] && ! kill -0 "$companion_pid" >/dev/null 2>&1; then
      echo "" >&2
      echo "[midi-mapper] ERROR: companion process died while waiting for $label." >&2
      return 1
    fi
    sleep 1
    i=$((i + 1))
  done

  echo "" >&2
  echo "[midi-mapper] ERROR: $label did not respond at $url after ${max_attempts}s." >&2
  if [[ "$label" == "Backend" ]]; then
    echo "  Check: port ${BACKEND_PORT} free, .venv set up, MIDI headers installed." >&2
  else
    echo "  Check: frontend build succeeded, port ${APP_PORT} free." >&2
  fi
  return 1
}

wait_for_url "Backend"  "$BACKEND_HEALTH_URL" "$backend_pid"  30 "$frontend_pid" || exit 1
wait_for_url "Frontend" "$APP_URL"             "$frontend_pid" 60 "$backend_pid"  || exit 1

# ── Open desktop window ───────────────────────────────────────────────────────

echo ""
echo "[midi-mapper] ─────────────────────────────────────────"
echo "[midi-mapper]  MIDI Mapper"
echo "[midi-mapper]  Backend:  ${BACKEND_HEALTH_URL}"
echo "[midi-mapper]  App:      ${APP_URL}"
echo "[midi-mapper] ─────────────────────────────────────────"
echo "[midi-mapper]  Opening desktop window..."
echo ""
echo "  (First run compiles the Tauri shell — this takes ~30-60s."
echo "   Subsequent runs use the cargo cache and start in seconds.)"
echo ""

cargo tauri dev --config "{\"build\":{\"devUrl\":\"${APP_URL}\"}}"
exit_code=$?
cleanup
exit "$exit_code"
