# Linux Desktop Packaging

This document covers the four ways to run MIDI Mapper on Linux and what must
change before a fully self-contained release package is ready.

## Launch Modes

| Mode | Command | Next.js | Tauri | Use for |
|---|---|---|---|---|
| Browser dev | `bash scripts/dev-stack.sh` | dev server (3000) | no | daily development |
| Desktop dev | `bash scripts/dev-desktop.sh` | dev server (3000) | yes | Tauri shell development |
| Desktop app | `bash scripts/run-app.sh` | prod server (3001) | yes | demo, recording, day use |
| Desktop preview | `bash scripts/preview-desktop.sh` | prod server (3001) | yes | one-off preview |

### Browser dev

```bash
bash scripts/dev-stack.sh
# Backend:  http://127.0.0.1:8765/api/health
# Frontend: http://localhost:3000/v2
```

No Rust or Tauri required. Uses the Next.js dev server with hot reload. Open the
URL in any browser.

### Desktop dev

```bash
bash scripts/dev-desktop.sh
```

Starts the Next.js dev server and opens a Tauri window. Useful when working on
the Tauri shell itself (Rust side). Hot reload is active — the browser dev
indicator appears in the Tauri window, which is expected.

### Desktop app (primary demo/use mode)

```bash
bash scripts/run-app.sh
```

This is the primary command for running MIDI Mapper as a desktop application:

- Activates the Python venv, verifies dependencies.
- Checks both ports (8765, 3001) are free before starting.
- Builds the Next.js frontend if no production build exists (`src/.next`).
  Skips the build on subsequent runs (delete `src/.next` to force a rebuild).
- Starts the FastAPI backend and the production Next.js server.
- Waits for both to be healthy before opening the Tauri window.
- Cleans up all child processes when the window closes or Ctrl-C is pressed.
- Does not open a browser tab.

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
clean preview from scratch. `run-app.sh` is preferred for regular use because it
skips the build when one already exists.

## Desktop Launcher (`.desktop` file)

To add MIDI Mapper to your application menu, use the template at
`examples/midi-mapper.desktop`:

```bash
# 1. Copy and edit the template
cp examples/midi-mapper.desktop ~/Desktop/midi-mapper.desktop
# Replace REPLACE_WITH_ABSOLUTE_PATH with the actual repo path, e.g.:
sed -i "s|REPLACE_WITH_ABSOLUTE_PATH|$(pwd)|g" ~/Desktop/midi-mapper.desktop

# 2. Install to the application menu
cp ~/Desktop/midi-mapper.desktop ~/.local/share/applications/
update-desktop-database ~/.local/share/applications/
```

The launcher uses `Terminal=true` so startup messages are visible in a terminal
window. This is intentional until the app is fully self-contained.

## Dependencies

**System packages (Ubuntu/Debian):**

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
  libnotify-bin \
  pkg-config \
  python3-dev \
  xdotool
```

**Toolchains:**

```bash
# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Tauri CLI
cargo install tauri-cli --version '^2'

# Node/pnpm
corepack enable
corepack prepare pnpm@latest --activate

# Python venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

## User Data Path

### Current behavior

The runtime database lives at `./midi_map.db` relative to wherever the script is
run. This works for development and demo use but is not suitable for a packaged
application.

```
./midi_map.db           — runtime database (current)
./midi_map.db-shm       — SQLite shared memory (auto-created)
./midi_map.db-wal       — SQLite WAL journal (auto-created)
```

To keep data separate from the source tree today, set `MIDI_MAPPER_DB_PATH`:

```bash
export MIDI_MAPPER_DB_PATH="$HOME/.local/share/midi-mapper/midi_map.db"
mkdir -p "$HOME/.local/share/midi-mapper"
MIDI_MAPPER_DB_PATH="$HOME/.local/share/midi-mapper/midi_map.db" bash scripts/run-app.sh
```

### What must change before release packaging

For a packaged `.deb` or AppImage, the database must live in the user's XDG data
directory:

```
$XDG_DATA_HOME/midi-mapper/midi_map.db
# typically: ~/.local/share/midi-mapper/midi_map.db
```

Steps needed before packaging works correctly:

1. **Backend startup defaults to XDG path.** `backend/config.py` should default
   `MIDI_MAPPER_DB_PATH` to `$XDG_DATA_HOME/midi-mapper/midi_map.db` and create
   the directory on first run.

2. **Tauri sets the env var.** The Tauri shell (`src-tauri/src/`) needs to
   resolve the XDG path and pass it to the backend subprocess via environment
   variable before starting the backend.

3. **Migration on first packaged run.** If `./midi_map.db` exists but the XDG
   path does not, a first-run migration can offer to copy the data.

4. **Profile export before switching.** Until migration is implemented, export
   all profiles before moving to a packaged version.

## What Works Now vs. Packaged Target

| Concern | Current (`run-app.sh`) | Packaged target |
|---|---|---|
| Frontend | `next start` child process | Static assets bundled in Tauri shell |
| Backend | `uvicorn` child process | Supervised subprocess or sidecar |
| Database | `./midi_map.db` (CWD) | `~/.local/share/midi-mapper/` |
| Python deps | `.venv/` in repo | Bundled with PyInstaller or similar |
| Startup | bash script | Tauri app entry point |
| Port conflicts | Script checks and fails | Not applicable (bundled) |

## Building the Shell Package

The Tauri shell itself can be packaged, but the result is not yet a complete
offline app (see the table above):

```bash
cargo tauri build --bundles deb
cargo tauri build --bundles appimage
```

Output goes to `src-tauri/target/release/bundle/`.

Before these packages work as a standalone app, the backend and frontend process
lifecycle must be managed by the Tauri shell rather than a shell script.
