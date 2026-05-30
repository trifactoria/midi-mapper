# Linux Desktop Packaging

This document covers all ways to run MIDI Mapper on Linux, the current
packaging status, and what remains before a fully self-contained release is
possible.

## Launch Modes

| Mode | Command | Next.js | Tauri | Backend | Use for |
|---|---|---|---|---|---|
| Browser dev | `bash scripts/dev-stack.sh` | dev server (3000) | no | uvicorn | daily development |
| Desktop dev | `bash scripts/dev-desktop.sh` | dev server (3000) | yes | uvicorn | Tauri shell development |
| Desktop app | `bash scripts/run-app.sh` | prod server (3001) | yes | uvicorn | demo, recording, day use |
| Desktop preview | `bash scripts/preview-desktop.sh` | prod server (3001) | yes | uvicorn | one-off preview |
| Package build | `bash scripts/build-package.sh` | static export | yes (build only) | **not bundled** | AppImage / .deb artifact |

### Browser dev

```bash
bash scripts/dev-stack.sh
# Backend:  http://127.0.0.1:8765/api/health
# Frontend: http://localhost:3000/v2
```

No Rust or Tauri required. Uses the Next.js dev server with hot reload. Open
the URL in any browser.

### Desktop app (primary demo/use mode)

```bash
bash scripts/run-app.sh
```

The primary command for running MIDI Mapper as a desktop application:

- Verifies all dependencies (Python venv, Rust, pnpm).
- Checks both ports (8765, 3001) are free before starting.
- Builds the Next.js frontend if no production build exists (`src/.next`).
  Skips the rebuild on subsequent runs (delete `src/.next` to force a rebuild).
- Starts the FastAPI backend and the production Next.js server.
- Waits for both to be healthy before opening the Tauri window.
- Cleans up all child processes when the window closes or Ctrl-C is pressed.

First run compiles the Tauri Rust shell (~30-60 seconds). Subsequent runs use
cargo's incremental cache and start in seconds.

Custom port:

```bash
MIDI_MAPPER_APP_PORT=3002 bash scripts/run-app.sh
```

### Desktop preview

```bash
bash scripts/preview-desktop.sh
```

Equivalent to `run-app.sh` but always runs `pnpm build` first. Useful for a
clean preview from scratch.

### Desktop dev

```bash
bash scripts/dev-desktop.sh
```

Starts the Next.js dev server and opens a Tauri window. For Tauri shell
development. Hot reload is active — the browser dev indicator appears in the
Tauri window, which is expected.

## Building the Package (AppImage / .deb)

```bash
bash scripts/build-package.sh
# or specific targets:
bash scripts/build-package.sh --bundles appimage
bash scripts/build-package.sh --bundles deb
```

Output: `src-tauri/target/release/bundle/`

This script:
1. Builds the Next.js frontend as a static export into
   `src-tauri/frontend-dist/` (no Node.js server required at runtime).
2. Runs `cargo tauri build` which downloads `linuxdeploy` on first run
   (~30MB, cached in `~/.cache/tauri/`) and compiles the Rust shell.
3. Produces an AppImage and/or `.deb` containing the Tauri shell + bundled
   frontend.

**The Python backend is NOT bundled.** The packaged app opens
`http://127.0.0.1:8765` at startup. You must start the backend separately:

```bash
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765
# then launch the AppImage
```

For a self-contained demo that manages backend + frontend automatically, use
`bash scripts/run-app.sh` instead.

### What the package contains

| Component | In package? | Notes |
|---|---|---|
| Tauri shell (Rust binary) | yes | compiled via `cargo tauri build` |
| Frontend (Next.js) | yes | static HTML/JS/CSS, bundled via WebKit |
| Python backend | **no** | must run separately (uvicorn) |
| Python deps (.venv) | **no** | must be installed in host |
| Runtime database | **no** | lives at `./midi_map.db` by default |

### First-run requirements on the target machine

System packages required to run the AppImage:

```bash
sudo apt install -y libwebkit2gtk-4.1-0 libgtk-3-0
```

(The AppImage includes most of its own libraries but depends on the system
WebKit and GTK.)

### Build requirements (developer machine)

```bash
sudo apt install -y \
  build-essential curl file pkg-config \
  libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev \
  libayatana-appindicator3-dev libsoup-3.0-dev \
  libasound2-dev libjack-jackd2-dev python3-dev \
  libnotify-bin xdotool

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Tauri CLI
cargo install tauri-cli --version '^2'

# Node/pnpm
corepack enable && corepack prepare pnpm@latest --activate
```

## Desktop Launcher (`.desktop` file)

To add MIDI Mapper to your application menu, use the template at
`examples/midi-mapper.desktop`:

```bash
cp examples/midi-mapper.desktop ~/Desktop/midi-mapper.desktop
sed -i "s|REPLACE_WITH_ABSOLUTE_PATH|$(pwd)|g" ~/Desktop/midi-mapper.desktop

# Install to the application menu
cp ~/Desktop/midi-mapper.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

The launcher uses `Terminal=true` so startup messages are visible while
launching. This is intentional until the app is fully self-contained.

## User Data Path

The runtime database lives at `./midi_map.db` relative to wherever the
script is run. This works for development and demo use.

To keep data outside the source tree:

```bash
mkdir -p "$HOME/.local/share/midi-mapper"
MIDI_MAPPER_DB_PATH="$HOME/.local/share/midi-mapper/midi_map.db" bash scripts/run-app.sh
```

For a packaged `.deb` or AppImage, the database should live at
`~/.local/share/midi-mapper/midi_map.db`. This requires:

1. `backend/config.py` defaulting to the XDG path and creating the directory
   on first run.
2. The Tauri sidecar (when implemented) setting `MIDI_MAPPER_DB_PATH` before
   starting the backend.

## Current State vs. Fully Self-Contained Target

| Concern | `run-app.sh` (current demo) | Package build (current) | Self-contained target |
|---|---|---|---|
| Frontend | `next start` child process | Static HTML in AppImage | Static HTML in AppImage ✓ done |
| Backend | uvicorn child process | **not bundled** | PyInstaller sidecar in AppImage |
| Database | `./midi_map.db` (CWD) | `./midi_map.db` (CWD) | `~/.local/share/midi-mapper/` |
| Python deps | `.venv/` in repo | **not bundled** | bundled via PyInstaller |
| Startup | bash script | bash (backend) + AppImage | Tauri manages all processes |
| Port conflicts | script checks and fails | user must manage | not applicable |

## Blockers for True Self-Contained AppImage

These are the remaining steps to a fully standalone release artifact:

### 1. Bundle the Python backend (hard — multi-week)

The backend (FastAPI + uvicorn + python-rtmidi) must be frozen into a single
binary using PyInstaller or Nuitka, then configured as a Tauri sidecar. The
`src-tauri/src/lib.rs` shell must launch and supervise it.

PyInstaller with python-rtmidi (a C extension) requires careful dependency
handling and is the most complex step.

### 2. XDG-compliant database path (medium — hours)

`backend/config.py` should default to `~/.local/share/midi-mapper/midi_map.db`
and create the directory on first run. The Tauri sidecar must set
`MIDI_MAPPER_DB_PATH` from the XDG path.

### 3. Tauri sidecar process management (medium — days)

`src-tauri/src/lib.rs` needs to:
- Start the frozen backend binary before the window opens.
- Wait for the backend health endpoint to respond.
- Shut down the backend when the window closes.

Once this is done, `run-app.sh` becomes unnecessary.

### What is already done

- Frontend static export — the `MIDI_MAPPER_PACKAGE_BUILD=true pnpm build`
  path produces clean static files in `src-tauri/frontend-dist/` that Tauri
  bundles correctly.
- Tauri window opens at `/v2/` directly from the bundled frontend.
- `cargo tauri build --bundles appimage deb` produces a working AppImage with
  the frontend embedded (backend must be run separately).
