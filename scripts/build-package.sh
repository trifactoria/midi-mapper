#!/usr/bin/env bash
# Build MIDI Mapper Linux packages (AppImage and .deb).
#
# What this produces
# ------------------
# A Tauri AppImage and .deb that bundle the Tauri shell and the Next.js
# frontend as static files. The Python backend is NOT included.
#
# The packaged app opens http://127.0.0.1:8765 at startup. You must run the
# backend separately before launching the package:
#
#   .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765
#   # then launch the AppImage
#
# For a fully scripted demo (backend + frontend + Tauri window in one command),
# use scripts/run-app.sh instead.
#
# Requirements
# ------------
#   Rust + cargo-tauri:  cargo install tauri-cli --version '^2'
#   pnpm:                corepack enable && corepack prepare pnpm@latest --activate
#   System libs:         see docs/packaging-linux.md
#
# Usage
#   bash scripts/build-package.sh
#   bash scripts/build-package.sh --bundles appimage   # AppImage only
#   bash scripts/build-package.sh --bundles deb        # .deb only
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

BUNDLES="${*:---bundles appimage deb}"

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

# ── Frontend static build ─────────────────────────────────────────────────────

echo "[midi-mapper] Building Next.js frontend as static export..."
echo "  Output: src-tauri/frontend-dist/"
echo ""

(
  cd src
  if [[ ! -d node_modules ]]; then
    echo "[midi-mapper] Installing frontend dependencies..."
    pnpm install
  fi
  MIDI_MAPPER_PACKAGE_BUILD=true pnpm build
)

echo ""
echo "[midi-mapper] Frontend static build complete."

# ── Tauri package build ───────────────────────────────────────────────────────

echo ""
echo "[midi-mapper] Building Tauri packages..."
echo "  Bundles: ${BUNDLES}"
echo "  Output:  src-tauri/target/release/bundle/"
echo ""
echo "  Note: first run downloads linuxdeploy (~30MB) and compiles Rust (~5 min)."
echo "  Subsequent runs use the cargo cache and are much faster."
echo ""

# shellcheck disable=SC2086
cargo tauri build $BUNDLES

# ── Output summary ────────────────────────────────────────────────────────────

echo ""
echo "[midi-mapper] ─────────────────────────────────────────────────────────"
echo "[midi-mapper]  Package build complete."
echo ""

BUNDLE_DIR="$ROOT_DIR/src-tauri/target/release/bundle"
if [[ -d "$BUNDLE_DIR/appimage" ]]; then
  echo "  AppImage:"
  find "$BUNDLE_DIR/appimage" -name "*.AppImage" | while read -r f; do
    echo "    $f"
  done
fi
if [[ -d "$BUNDLE_DIR/deb" ]]; then
  echo "  .deb:"
  find "$BUNDLE_DIR/deb" -name "*.deb" | while read -r f; do
    echo "    $f"
  done
fi

cat <<'EOF'

  ─────────────────────────────────────────────────────────────────
  IMPORTANT: The backend is NOT bundled in this package.
  ─────────────────────────────────────────────────────────────────
  Start the backend before launching the AppImage or installing the .deb:

    .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765

  For a self-contained demo that manages all processes automatically:

    bash scripts/run-app.sh

  See docs/packaging-linux.md for the full packaging roadmap.
  ─────────────────────────────────────────────────────────────────
EOF
