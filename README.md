# MIDI Mapper

A local MIDI-to-command automation tool. Map notes and CC events from a MIDI
controller to shell commands — media controls, OBS scene switches, desktop
shortcuts, or anything you can run from a terminal.

A FastAPI backend listens for MIDI input, stores profiles, layers, and bindings
in SQLite, and streams events over WebSocket. A Next.js frontend provides a live
note grid, capture-based binding editor, run history, and device selection.

**This is an active personal tool, not a finished product.** Core plumbing works.
Rough edges exist. The UI and API are still evolving.

## Current State

- **Core MIDI runtime: operational.** Live note/CC events stream to the frontend
  via WebSocket. Device selection persists.
- **v2 binding model: operational.** Profiles → layers → bindings hierarchy.
  Create, rename, and activate profiles and layers. Create and delete bindings
  via the capture UI. Run history is recorded and clearable.
- **Action execution: working but minimal.** Commands run as direct `argv`
  (no shell by default). Shell mode is available via config. No retry, timeout
  enforcement, or output capture beyond preview.
- **Action presets: partial.** The UI offers one-click presets for `playerctl`,
  `obs-cmd`, and `notify-send`. These require the respective tools to be
  installed separately.
- **Frontend/backend integration: largely complete.** No mock data leak when
  backend is reachable. Empty states are handled.
- **Legacy runtime: still present internally.** The original context/binding
  model (`/api/contexts`, `app.py`) still runs behind the shim. It is not
  exposed in the v2 UI and is not the product direction.
- **Packaging/distribution: not started.** No systemd unit, no Flatpak, no
  installer. Intended to be run from a working directory.
- **Cross-platform: untested.** ALSA/JACK native headers are required for
  `python-rtmidi`. This is a Linux-first tool.

## Prerequisites

**System (Linux / Ubuntu)**

```bash
sudo apt install -y build-essential pkg-config python3-dev libasound2-dev libjack-jackd2-dev
```

These native headers are required for `python-rtmidi`. The dev script checks for
`/dev/snd/seq` and warns if it is missing.

**Python**: 3.11 or newer  
**Node.js**: 20 or newer  
**pnpm**: install via Corepack if missing

```bash
corepack enable
corepack prepare pnpm@latest --activate
```

**Optional external tools** (for action presets):

| Preset | Tool | Install |
|---|---|---|
| Media controls | `playerctl` | `sudo apt install playerctl` |
| OBS scene/recording | `obs-cmd` | `pip install obs-cmd` |
| Desktop notifications | `notify-send` | included in `libnotify-bin` |

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

## Quick Demo

1. Start the stack: `bash scripts/dev-stack.sh`
2. Open `http://localhost:3000/v2`
3. In the sidebar, click **+** next to Profiles to create a profile, then **+**
   next to Layers to create a layer.
4. In the topbar, select your MIDI input device.
5. In the Quick Bind panel, click **Capture Next** and press a note on your
   controller.
6. Fill in a command (e.g. `echo "hello"`) and click **Create Binding**.
7. The binding appears in Active Bindings. Click **Test Action** to trigger it
   manually.
8. Observe the result in the Run History panel.

To seed demo data without a MIDI device:

```bash
.venv/bin/python scripts/seed-demo-v2.py
```

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
Review every binding command before enabling it.

## Security Notes

- Bindings execute local commands. Treat every binding as code that runs on your
  machine when a MIDI event fires.
- Run the backend on `127.0.0.1`. Do not expose it to a network without reviewing
  the execution risk.
- Do not commit `.env`, the runtime database, or binding exports that contain
  private paths or credentials.

## Repository Layout

```text
.
├── app.py                  # Shim — delegates to backend.main
├── backend/                # FastAPI application package
│   ├── main.py             # App factory, MIDI pump, lifecycle
│   ├── api/                # Route modules (profiles, layers, bindings, runs, …)
│   ├── actions/            # Command execution, run recording, notifications
│   ├── midi/               # MIDI listener and state
│   └── migrations.py       # SQLite schema migrations
├── tests/                  # pytest test suite
├── scripts/                # Dev stack helpers (dev-stack.sh, check.sh, …)
├── docs/                   # Dev notes, architecture docs
├── src/                    # Next.js frontend
│   └── components/
│       ├── layout/         # V2Shell — top-level app shell
│       ├── mapping/        # Note grid, CC faders, Quick Bind, Run History
│       ├── sidebar/        # Profile and layer selector
│       └── v2/             # API client, data hooks, types, adapters
├── requirements.txt        # Backend runtime dependencies
├── requirements-dev.txt    # Backend + test dependencies
└── .env.example            # Configuration template
```

## Roadmap / Planned Work

Near-term:

- Profile and layer delete
- Better action feedback (stdout/stderr display in run detail)
- Binding enable/disable toggle in the UI
- Binding import/export

Longer-term:

- Action execution hardening (timeout enforcement, retry)
- Better preset integrations (more tools, version detection)
- Multi-device workflows (per-device profiles)
- Packaging/distribution (systemd unit or similar)
- Visual binding management improvements

Not planned:

- Cloud sync or remote access
- Non-Linux platform support (no near-term effort)
