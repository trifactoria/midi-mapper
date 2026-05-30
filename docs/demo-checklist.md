# Demo Checklist

Steps to verify and record a clean demo of midi-mapper v2.

## 1. Install dependencies

```bash
# System (Ubuntu/Debian)
sudo apt install -y \
  build-essential pkg-config python3-dev \
  libasound2-dev libjack-jackd2-dev \
  libnotify-bin \
  xdotool

# Python venv
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt

# Frontend
cd src && pnpm install && cd ..
```

## 2. Run checks

```bash
bash scripts/check.sh
```

All tests should pass. TypeScript build should succeed.

## 3. Start the app

**Desktop app mode (recommended for demo/recording):**

```bash
bash scripts/run-app.sh
# Builds frontend if needed, starts backend + production server, opens Tauri window
```

Requires Rust and cargo-tauri:
- `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- `cargo install tauri-cli --version '^2'`

First run compiles the Tauri shell (~30-60 seconds). Subsequent runs use cargo's
incremental cache and start quickly.

**Browser mode (no Rust required):**

```bash
bash scripts/dev-stack.sh
# Backend:  http://127.0.0.1:8765/api/health
# Frontend: http://localhost:3000/v2
```

## 4. Connect a MIDI device

- Plug in your MIDI controller before starting the backend.
- In the top bar, select your device from the port dropdown.
- The status indicator turns green when a device is active.

Without a physical controller:
- Import `examples/demo-profile.json` or `examples/demo-workflows.json` (see step 5).
- Use the note grid in Mouse Mode to trigger actions by click.

## 5. Import the demo profile

1. Open the Tauri window (from `run-app.sh`) or `http://localhost:3000/v2`.
2. In the sidebar, click the import icon next to Profiles.
3. Select `examples/demo-workflows.json`.
4. The "Demo Workflows" profile appears and activates.
5. The "Live Workflows" layer is selected automatically.

The four demo bindings map to notes C3, E3, G3, B3 (MIDI notes 48, 52, 55, 59)
visible in the note grid at "Octaves 1 to 6".

## 6. Walk through demo bindings

| Key | Note | Action | Requires |
|-----|------|--------|----------|
| C3 | 48 | Desktop notification: "Recording started" | `notify-send` (libnotify-bin) |
| E3 | 52 | Open GitHub in browser | `xdg-open` (standard) |
| G3 | 55 | Launch Firefox | `firefox` in PATH |
| B3 | 59 | Wait 500ms → echo "Scene ready" | nothing |

For each binding:
- Click "Test Action" in Quick Bind to test without a MIDI device.
- Or press the physical key to trigger live.
- Watch Run History update in real time.

## 7. Record demo video

Suggested flow (≈ 90 seconds):

1. Show the note grid with bindings lit up (C3, E3, G3, B3).
2. Press C3 → notification pops up on desktop.
3. Press E3 → browser opens to GitHub.
4. Press G3 → Firefox launches.
5. Press B3 → Run History shows two steps (delay → echo).
6. Open a binding in the Actions tab to show the step sequence editor.
7. Show the Quick Bind panel: switch to "Hotkey / Shortcut" preset, enter a
   shortcut, click Test Action.

## Known limitations

- **Linux only.** `python-rtmidi` requires ALSA/JACK headers. macOS and Windows
  are untested and unsupported.
- **xdotool required for hotkeys.** Hotkey actions fail gracefully with a
  readable error if xdotool is not installed.
- **notify-send required for notifications.** Install `libnotify-bin` or the
  notification action returns `ok: false` with an install hint.
- **No self-contained package.** There is no installer, Flatpak, or systemd
  unit. Run from the working directory.
- **Armed mode.** Bindings with "Require Armed" only fire when the arm toggle
  is active. This is on by default in the demo profile.
- **Tauri build requires Rust.** The desktop preview (`scripts/preview-desktop.sh`)
  needs Rust and `cargo-tauri`. The browser mode (`scripts/dev-stack.sh`) has no
  Rust dependency.
