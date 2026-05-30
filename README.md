# MIDI Mapper

A local MIDI-to-action automation tool for Linux. Map notes and CC events from a
MIDI controller to shell commands, desktop notifications, URLs, apps, or keyboard
shortcuts — anything you can trigger from your desktop.

A FastAPI backend listens for MIDI input, stores profiles, layers, and bindings
in SQLite, and streams events over WebSocket. A Next.js frontend provides a live
note grid, capture-based binding editor, run history, and device selection. A
Tauri desktop shell is available for a self-contained window experience.

**Linux-first, local-first.** All data stays on your machine. No cloud, no
accounts, no network calls. Built and tested on Ubuntu/Debian. Cross-platform
support is not planned.

**Personal tool, actively used and maintained.** Core workflows are stable.
Some rough edges remain.

## Current State

- **MIDI runtime:** Live note/CC events stream to the frontend via WebSocket.
  Device selection persists across restarts.
- **v2 binding model:** Profiles → layers → bindings hierarchy. Create, rename,
  activate, and delete profiles and layers. Bindings support enable/disable,
  cooldown, armed mode, and per-binding notes.
- **Native action types:** Four first-class action types beyond shell commands —
  desktop notification (`notify-send`), open URL (`xdg-open`), open app
  (detached), and hotkey (`xdotool`). All dispatch correctly from the UI and
  runtime.
- **Action sequencing:** Bindings support multi-step action sequences with
  ordering, per-step enable/disable, and configurable delays between steps.
- **Import/export:** Profiles export to JSON and import cleanly, including native
  action types and multi-step sequences.
- **Desktop app:** `scripts/run-app.sh` starts backend + frontend and opens a
  Tauri window — the primary demo command. Requires Rust + cargo-tauri + Python
  venv.
- **Package build:** `scripts/build-package.sh` produces an AppImage and .deb
  that bundle the Tauri shell and Next.js frontend as static files. The Python
  backend is not bundled and must be started separately. A fully self-contained
  package (backend frozen into the AppImage) requires PyInstaller bundling and
  Tauri sidecar wiring — see `docs/packaging-linux.md`.
- **Legacy runtime:** The original context/binding model (`app.py`) still runs
  internally. It is not exposed in the v2 UI and is not the product direction.

## Prerequisites

**System (Linux / Ubuntu/Debian)**

```bash
sudo apt install -y \
  build-essential pkg-config python3-dev \
  libasound2-dev libjack-jackd2-dev \
  libnotify-bin \
  xdotool
```

`libasound2-dev` and `libjack-jackd2-dev` are required for `python-rtmidi`.
`libnotify-bin` and `xdotool` are optional but required for the notification and
hotkey action types respectively. Both fail gracefully with a readable error if
missing.

- **Python:** 3.11 or newer
- **Node.js:** 20 or newer
- **pnpm:** install via Corepack if missing

```bash
corepack enable
corepack prepare pnpm@latest --activate
```

**Optional external tools** (for additional action presets):

| Preset | Tool | Install |
|---|---|---|
| Desktop notification | `notify-send` | `sudo apt install libnotify-bin` |
| Open URL / app | `xdg-open` | included in `xdg-utils` (usually pre-installed) |
| Hotkey / shortcut | `xdotool` | `sudo apt install xdotool` |
| Media controls | `playerctl` | `sudo apt install playerctl` |
| OBS scene/recording | `obs-cmd` | `pip install obs-cmd` |

## Setup

**Backend**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
cp .env.example .env
```

**Frontend**

```bash
cd src
pnpm install
```

## Development

Start backend and frontend together:

```bash
bash scripts/dev-stack.sh
```

Or separately:

```bash
bash scripts/dev-backend.sh    # http://127.0.0.1:8765/api/health
bash scripts/dev-frontend.sh   # http://localhost:3000/v2
```

Run all checks (pytest + tsc + build):

```bash
bash scripts/check.sh
```

The v2 interface is at **`http://localhost:3000/v2`**.

## Running as a Desktop App

To run MIDI Mapper as a desktop application (Tauri window, no browser):

```bash
bash scripts/run-app.sh
```

This script:
- Verifies all dependencies
- Builds the frontend if needed (skips rebuild on subsequent runs)
- Starts backend + production frontend
- Waits for both to be healthy, then opens the Tauri window
- Cleans up all child processes when the window closes

First run compiles the Tauri Rust shell (~30-60 seconds). Subsequent runs use
the cargo cache and start in seconds.

Requires Rust and the Tauri CLI:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
cargo install tauri-cli --version '^2'
```

The browser dev mode (`scripts/dev-stack.sh`) has no Rust dependency.

See `docs/packaging-linux.md` for all launch modes, the desktop launcher
(`.desktop` file) setup, and the packaging roadmap.

## Demo Profiles

Two ready-to-import profiles are included under `examples/`.

### demo-profile.json

Two-layer profile covering the main action types:

| Trigger | Layer | Action | What it does |
|---------|-------|--------|--------------|
| C4 (note 60) | Keys | Multi-step | `echo` → wait 3 s → desktop notification |
| D4 (note 62) | Keys | Hotkey | Sends `Ctrl+M` (mute in Zoom/Meet/Teams) |
| CC 7 (Volume) | Faders | Command | Logs CC 7 events to stdout |

**To import:**

1. Start the stack and open `http://localhost:3000/v2`.
2. In the sidebar, click the import icon (⬆) next to Profiles.
3. Select `examples/demo-profile.json`.
4. The "Demo Profile" activates with the "Keys" layer selected.

Activate the "Faders" layer in the sidebar to reach the CC 7 binding. Without a
MIDI device, use **Quick Bind → Test Action** or the note grid in **Mouse Mode**
to trigger each binding manually.

Dependencies for all steps to work:

```bash
sudo apt install libnotify-bin xdotool
```

### demo-workflows.json

Flat single-layer profile with four bindings on notes C3/E3/G3/B3 (48/52/55/59):

| Note | Action | What it does |
|------|--------|--------------|
| C3 | Notification | "Recording started" via notify-send |
| E3 | Open URL | Opens GitHub in your default browser |
| G3 | Open App | Launches Firefox (edit to your app) |
| B3 | Wait + Command | Waits 500ms, then echoes "Scene ready" |

Import the same way — select `examples/demo-workflows.json` in the import dialog.

See `docs/demo-checklist.md` for a full demo and recording guide.

## Quick Start (no MIDI device)

1. Start the stack: `bash scripts/dev-stack.sh`
2. Open `http://localhost:3000/v2`
3. Create a profile and layer in the sidebar, or import the demo profile.
4. In Quick Bind, choose a preset from the "Desktop" group (notification, URL,
   app, or hotkey).
5. Fill in the field and click **Test Action** to run it immediately.
6. Click **Create Binding** to save — assign a MIDI trigger later.

## Configuration

Key `.env` variables:

| Variable | Default | Notes |
|---|---|---|
| `MIDI_MAPPER_DB_PATH` | `./midi_map.db` | Runtime SQLite database |
| `MIDI_MAPPER_EXEC_USE_SHELL` | `false` | Set `true` for shell features (pipes, redirects) |
| `MIDI_MAPPER_EXEC_PATH` | `$PATH` | PATH used for command resolution |
| `MIDI_MAPPER_CORS_ORIGINS` | `*` | Restrict for any non-localhost use |
| `NEXT_PUBLIC_API_BASE` | `http://127.0.0.1:8765` | Frontend → backend URL |

Shell mode is disabled by default. When enabled, commands run through `bash -lc`.
Review every binding before enabling it.

## Security Notes

- Bindings execute local commands. Treat every binding as code that runs on your
  machine when a MIDI event fires.
- Run the backend on `127.0.0.1`. Do not expose it to a network without
  reviewing the execution risk.
- Do not commit `.env`, the runtime database, or binding exports that contain
  private paths or credentials.

## Repository Layout

```text
.
├── app.py                  # Shim — delegates to backend.main
├── backend/                # FastAPI application package
│   ├── main.py             # App factory, MIDI pump, lifecycle
│   ├── api/                # Route modules (profiles, layers, bindings, runs, …)
│   ├── actions/            # Command execution, run recording, executor
│   ├── midi/               # MIDI listener and state
│   └── migrations.py       # SQLite schema migrations
├── examples/               # Importable demo profiles
│   ├── demo-profile.json   # Two-layer demo: sequence, hotkey, CC
│   └── demo-workflows.json # Flat single-layer demo (notification, URL, app)
├── tests/                  # pytest test suite
├── scripts/                # Dev helpers (dev-stack.sh, check.sh, preview-desktop.sh, …)
├── docs/                   # Dev notes, demo checklist, packaging guide
│   └── archive/            # Archived planning docs
├── src/                    # Next.js frontend
│   └── components/
│       ├── layout/         # V2Shell — top-level app shell
│       ├── mapping/        # Note grid, CC faders, Quick Bind, Run History
│       ├── sidebar/        # Profile and layer selector
│       └── v2/             # API client, data hooks, types, adapters
├── src-tauri/              # Tauri desktop shell (Rust)
├── requirements.txt        # Backend runtime dependencies
├── requirements-dev.txt    # Backend + test dependencies
└── .env.example            # Configuration template
```

## Roadmap

Near-term:

- Action execution hardening (timeout enforcement, retry on failure)
- Per-device profiles (bind triggers to specific MIDI port names)
- Better preset integrations (tool version detection, install hints)
- Visual binding management improvements

Longer-term:

- Fully self-contained AppImage (Python backend bundled via PyInstaller sidecar)
- Multi-window / multi-profile session support

Not planned:

- Cloud sync or remote access
- macOS or Windows support
