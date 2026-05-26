#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  cat >&2 <<'EOF'
Missing Python virtual environment: .venv

Create it and install test dependencies:
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements-dev.txt
EOF
  exit 1
fi

if ! command -v pnpm >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing pnpm.

Install it with:
  corepack enable
  corepack prepare pnpm@latest --activate
EOF
  exit 1
fi

echo "Running backend tests..."
.venv/bin/python -m pytest

echo "Running frontend typecheck..."
(
  cd src
  pnpm exec tsc --noEmit --pretty false
)

echo "Running frontend build..."
(
  cd src
  pnpm build
)
