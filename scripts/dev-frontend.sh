#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v pnpm >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Missing pnpm.

Install it with Corepack:
  corepack enable
  corepack prepare pnpm@latest --activate

Or install pnpm another way, then rerun this script.
EOF
  exit 1
fi

cd src

if [[ ! -d "node_modules" ]]; then
  echo "node_modules missing; running pnpm install..."
  pnpm install
fi

echo "Starting frontend: http://localhost:3000/v2"
exec pnpm dev --hostname localhost --port 3000
