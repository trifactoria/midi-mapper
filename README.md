# MIDI Mapper

MIDI Mapper is a local utility for turning MIDI controller events into configurable
command actions. A FastAPI backend listens for MIDI input, stores contexts and
bindings in SQLite, streams events over WebSockets, and a Next.js UI provides a
note grid and binding editor for mapping notes, controls, and program state to
local workflows.

This project is intended for trusted local use. It can execute commands on the
host machine when matching MIDI events are received.

## Status

This is an experimental local automation tool, not a hosted service. Run it on a
machine you control, with MIDI devices and command bindings you trust.

## Screenshots and Demo

TODO - add screenshots or a short GIF of the note grid, binding editor, and live
MIDI console. Suggested paths:

- `docs/screenshots/note-grid.png`
- `docs/screenshots/binding-editor.png`
- `docs/screenshots/live-console.png`

## Prerequisites

- Python 3.11 or newer
- Node.js 20 or newer and npm
- A MIDI input device visible to `mido`
- Optional: `notify-send` for desktop notifications
- Optional: `mpv` for workflows that use `vdj-midi-mapper.py`

## Backend Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

The backend reads configuration from `.env`. By default it stores runtime data in
`midi_map.db` next to `app.py`; that file is runtime state and should not be
committed.

Start the backend:

```bash
uvicorn app:app --host 127.0.0.1 --port 8765
```

Health check:

```bash
curl http://127.0.0.1:8765/api/health
```

## Frontend Setup

```bash
cd src
npm ci
npm run dev
```

The frontend expects the API at `NEXT_PUBLIC_API_BASE`, which defaults to
`http://127.0.0.1:8765` in `.env.example`.

Build and lint:

```bash
cd src
npm run lint
npm run build
```

## Local Development

For repeatable local startup and verification commands, see
[docs/dev.md](docs/dev.md). The short path is:

```bash
bash scripts/dev-stack.sh
bash scripts/check.sh
```

## Security and Local-Only Notes

- MIDI bindings can execute local commands. Treat every binding as code that can
  affect your machine.
- Shell mode is disabled by default with `MIDI_MAPPER_EXEC_USE_SHELL=false`.
  Leave it disabled unless you specifically need shell features such as pipes,
  redirects, or shell expansion.
- When shell mode is enabled, commands run through `bash -lc`, so quote and
  review bindings carefully.
- `MIDI_MAPPER_EXEC_PATH` controls command lookup. Prefer a narrow PATH for
  automation commands instead of exposing every user/system binary.
- `.env.example` uses `MIDI_MAPPER_CORS_ORIGINS=*` for local development. For any
  non-local or shared network use, restrict it to the exact frontend origin.
- Run the backend on `127.0.0.1` unless you have reviewed the command execution
  risk and trust every client that can reach it.
- Do not commit `.env`, runtime databases, exports containing private paths, or
  local command bindings you do not want public.

## Supported Binding Inputs

The backend supports bindings for implemented MIDI trigger types:

- `note_on`
- control change (`cc`)
- `pitchwheel`
- `program_change`

Bindings are scoped by context fields such as port, channel, bank MSB/LSB, and
program. The UI also exposes keygrab/arming controls and a live MIDI console.

## Repository Layout

```text
.
├── app.py                 # FastAPI backend and MIDI event bridge
├── schema.sql             # SQLite schema used for runtime DB initialization
├── vdj-midi-mapper.py     # Helper CLI for mpv/cue workflows
├── requirements.txt       # Backend Python dependencies
├── .env.example           # Local configuration template
└── src/                   # Next.js frontend
```
