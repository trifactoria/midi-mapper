#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -x ".venv/bin/python" ]]; then
  cat >&2 <<'EOF'
Missing Python virtual environment: .venv

Create it and install backend dependencies:
  python3 -m venv .venv
  .venv/bin/python -m pip install -r requirements.txt
EOF
  exit 1
fi

if ! .venv/bin/python - <<'PY'
import importlib.util
import sys

modules = {
    "aiosqlite": "aiosqlite",
    "dotenv": "python-dotenv",
    "fastapi": "fastapi",
    "mido": "mido",
    "pydantic": "pydantic",
    "rtmidi": "python-rtmidi",
    "uvicorn": "uvicorn",
}

missing = [package for module, package in modules.items() if importlib.util.find_spec(module) is None]
if missing:
    print(", ".join(missing))
    sys.exit(1)
PY
then
  cat >&2 <<'EOF'
Missing Python backend dependencies.

Install them with:
  .venv/bin/python -m pip install -r requirements.txt

On Ubuntu, python-rtmidi may also need native MIDI headers:
  sudo apt install -y build-essential pkg-config python3-dev libasound2-dev libjack-jackd2-dev
EOF
  exit 1
fi

if [[ ! -e "/dev/snd/seq" ]]; then
  cat >&2 <<'EOF'
Warning: /dev/snd/seq is not available.

The backend may fail during MIDI startup if ALSA sequencer support is missing.
On Ubuntu, install the native headers and make sure the snd-seq device is
available:
  sudo apt install -y build-essential pkg-config python3-dev libasound2-dev libjack-jackd2-dev
EOF
fi

echo "Starting backend: http://127.0.0.1:8765/api/health"
exec .venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765
