# Linux Desktop Packaging

This is the first Linux-first desktop path for MIDI Mapper v2. It keeps the
existing FastAPI and Next.js development workflow intact and adds a thin Tauri
v2 shell.

## What Works Now

- `bash scripts/dev-desktop.sh` starts the FastAPI backend, the Next.js
  frontend, and a Tauri desktop window.
- The Tauri dev window opens the real v2 UI at `http://localhost:3000/v2`.
- `bash scripts/preview-desktop.sh` builds the frontend, starts `next start`,
  starts the backend, and opens the same Tauri shell against the production
  Next server.
- Browser usage remains unchanged at `http://localhost:3000/v2`.
- `cargo tauri build` can build the Rust shell, but the produced package is not
  yet a complete offline MIDI Mapper app.

## What Is Still Manual

The backend and frontend are not bundled into the release package yet. The
current release shell uses `src-tauri/frontend-dist/index.html`, which documents
that the local services still need to be running.

The next packaging step is to choose and implement process supervision for:

- FastAPI/uvicorn backend startup and shutdown.
- Next.js production server or exported static frontend strategy.
- Runtime database path under the user's application data directory.
- Python dependency bundling, including `python-rtmidi` native libraries.

## Dependencies

Install the Linux desktop and MIDI build dependencies before using this path.

Ubuntu/Debian packages:

```bash
sudo apt install -y \
  build-essential \
  curl \
  file \
  libasound2-dev \
  libayatana-appindicator3-dev \
  libgtk-3-dev \
  libjack-jackd2-dev \
  librsvg2-dev \
  libsoup-3.0-dev \
  libwebkit2gtk-4.1-dev \
  pkg-config \
  python3-dev
```

Toolchains:

```bash
# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Tauri CLI
cargo install tauri-cli --version '^2'

# Node/pnpm
corepack enable
corepack prepare pnpm@latest --activate

# Python dependencies
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r requirements-dev.txt
```

MIDI runtime note:

- `/dev/snd/seq` must be available for ALSA sequencer access.
- `python-rtmidi` may require ALSA/JACK headers at install time.

## Desktop Dev

```bash
bash scripts/dev-desktop.sh
```

This runs:

- Backend: `http://127.0.0.1:8765/api/health`
- Frontend: `http://localhost:3000/v2` via `next dev`
- Tauri shell: opens `http://localhost:3000/v2`

This mode is intentionally a development mode. It uses the Next.js dev server,
so development indicators may appear in the Tauri window. That confirms the
desktop shell is loading the local dev UI; it is not the final packaged
production app.

## Desktop Preview

```bash
bash scripts/preview-desktop.sh
```

This runs:

- `pnpm build` in `src/`
- Backend: `http://127.0.0.1:8765/api/health`
- Frontend: `http://localhost:3001/v2` via `next start`
- Tauri shell: opens `http://localhost:3001/v2`

Preview mode is closer to the intended production visual experience because it
does not use the Next.js dev server. It still is not self-contained packaging:
the backend and frontend are local child processes started by the script.

Preview mode intentionally uses port 3001 so it does not silently attach to a
dev server already running on port 3000. If the Next.js dev indicator appears
in the Tauri window during preview, you are probably connected to a dev server
instead of the preview server. Confirm the script output says:

```text
Frontend: http://localhost:3001/v2
```

To use another preview port:

```bash
MIDI_MAPPER_PREVIEW_PORT=3002 bash scripts/preview-desktop.sh
```

The existing scripts still work independently:

```bash
bash scripts/dev-backend.sh
bash scripts/dev-frontend.sh
bash scripts/dev-stack.sh
bash scripts/check.sh
```

## Linux Build Attempt

```bash
cargo tauri build --bundles deb
```

or:

```bash
cargo tauri build --bundles appimage
```

Current limitation: this builds the shell package only. It does not yet bundle
the FastAPI backend, the Next.js server, the Python virtual environment, or the
runtime SQLite database lifecycle.

Before a real self-contained package, the desktop path still needs:

- Tauri-side process supervision for backend/frontend startup and shutdown.
- A production frontend strategy, either bundled static assets where feasible or
  a bundled local Next server.
- A user data directory for the runtime SQLite database.
- Python dependency bundling, including `python-rtmidi` and native ALSA/JACK
  libraries.
