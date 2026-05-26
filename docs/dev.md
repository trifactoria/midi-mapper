# Local Development

This project has a FastAPI backend at `127.0.0.1:8765` and a Next.js frontend at
`localhost:3000`. Use the scripts in `scripts/` so Python and Node commands run
from the expected directories.

## Fresh Setup

Install system prerequisites:

```bash
sudo apt install -y build-essential pkg-config python3-dev libasound2-dev libjack-jackd2-dev
```

The Ubuntu packages above are needed by `python-rtmidi` when building against
ALSA/JACK.

Create the Python environment and install backend plus test dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
```

Install frontend dependencies:

```bash
cd src
pnpm install
```

If `pnpm` is missing, enable it with Corepack:

```bash
corepack enable
corepack prepare pnpm@latest --activate
```

## Backend Setup

Start the backend from the repo root:

```bash
bash scripts/dev-backend.sh
```

The backend health URL is:

```text
http://127.0.0.1:8765/api/health
```

The script verifies `.venv` and the required runtime Python imports before
starting:

```bash
.venv/bin/python -m uvicorn app:app --host 127.0.0.1 --port 8765
```

## Frontend Setup

Start the frontend from the repo root:

```bash
bash scripts/dev-frontend.sh
```

The frontend URL is:

```text
http://localhost:3000/v2
```

The script verifies `pnpm`, installs dependencies if `src/node_modules` is
missing, then runs:

```bash
cd src
pnpm dev --hostname localhost --port 3000
```

## One-Command Dev Stack

Start backend and frontend together:

```bash
bash scripts/dev-stack.sh
```

The script prints both URLs and stops both processes when you press Ctrl-C:

```text
Backend:  http://127.0.0.1:8765/api/health
Frontend: http://localhost:3000/v2
```

## V2 Demo Seed

Use the demo seed to prove `/v2` is reading and mutating real backend data
instead of mock fallback data.

In one terminal, start the backend:

```bash
bash scripts/dev-backend.sh
```

In another terminal, seed the v2 demo data:

```bash
.venv/bin/python scripts/seed-demo-v2.py
```

The seed is idempotent and safe to rerun. It creates or updates:

```text
Profile: Demo Workflow
Layer:   Default Layer
Binding: C3 -> echo "C3 triggered"
Binding: CC 21 value >= 100 -> echo "CC 21 high"
```

You can verify the backend directly:

```bash
curl http://127.0.0.1:8765/api/profiles
curl http://127.0.0.1:8765/api/profiles/1/layers
```

Use the profile and layer IDs printed by the seed command if your database
already had data.

Start the frontend:

```bash
bash scripts/dev-frontend.sh
```

Open:

```text
http://localhost:3000/v2
```

The `/v2` footer should show `Data Real backend data`, and the sidebar should
show `Demo Workflow` and `Default Layer`. The Active Bindings panel should show
the C3 and CC 21 demo bindings.

Manual verification flow:

1. Select a demo binding in Active Bindings and confirm the editor populates.
2. Click Dry Run and confirm a command summary appears.
3. Click Test Action and confirm Run History updates.
4. Create a new command binding from Quick Bind.
5. Confirm it appears in Active Bindings.

If the footer shows `Mock fallback` or `Backend unavailable`, creation and test
controls remain guarded and will explain that a real backend layer/action is
required.

## Checks

Run the full local verification from the repo root:

```bash
bash scripts/check.sh
```

This runs:

```bash
.venv/bin/python -m pytest
cd src && pnpm exec tsc --noEmit --pretty false
cd src && pnpm build
```

## Troubleshooting

### `python-rtmidi` fails to install or cannot find ALSA

Install the native MIDI build dependencies, then reinstall Python requirements:

```bash
sudo apt install -y build-essential pkg-config python3-dev libasound2-dev libjack-jackd2-dev
.venv/bin/python -m pip install -r requirements-dev.txt
```

### `ModuleNotFoundError: No module named 'dotenv'`

You are using the wrong Python interpreter or skipped the virtual environment.
Use the repo venv explicitly:

```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

Do not use bare `pytest`; it may use a global Python that does not have the
project dependencies.

### Frontend API base

The frontend defaults to:

```text
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8765
```

Set `NEXT_PUBLIC_API_BASE` before starting `pnpm dev` if your backend runs
somewhere else.

### Ports already in use

The default ports are:

```text
Backend:  127.0.0.1:8765
Frontend: localhost:3000
```

Find and stop the process using a port:

```bash
lsof -i :8765
lsof -i :3000
```
