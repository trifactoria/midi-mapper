# Frontend startup

The current frontend is the existing context-based Next.js UI under `src/`. It has not been migrated to the v2 profile/layer APIs yet.

## Package manager

Use npm. The frontend has a tracked `src/package-lock.json`, and the verified install command is:

```bash
cd src
npm ci
```

## Backend

Run the backend from the repository root:

```bash
uvicorn app:app --host 127.0.0.1 --port 8765
```

The frontend API base defaults to `http://127.0.0.1:8765` in `src/components/useMidiApi.ts`. You can override it for the browser build with:

```bash
NEXT_PUBLIC_API_BASE=http://127.0.0.1:8765 npm run dev
```

## Frontend

Run the development server from `src/`:

```bash
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Then open:

```text
http://127.0.0.1:3000
```

No real MIDI hardware is required for the page to open. Without backend MIDI ports, some selectors and live event data may be empty.

## Checks

```bash
cd src
npm run lint
npm run build
```

