# Current behavior

This document captures the behavior covered by the pre-refactor tests.

## Command execution

- Binding commands are executed by `safe_execute_command()` in `app.py`.
- Shell execution is disabled by default. `MIDI_MAPPER_EXEC_USE_SHELL` must be set to `true`, `1`, or `yes` to route commands through `bash -lc`.
- In the default argv mode, command strings are parsed with `shlex.split`, the executable is resolved with `shutil.which` against `MIDI_MAPPER_EXEC_PATH`, and the resolved executable is passed directly to `asyncio.create_subprocess_exec`.
- Empty commands and commands whose executable cannot be resolved are rejected before subprocess launch.
- Subprocess stdout and stderr are discarded in current behavior; run history is not persisted yet.

## MIDI state and matching

- `midi_pump()` opens all MIDI input ports visible at backend startup.
- Incoming messages update per-channel and per-port bank/program state via `update_state()`.
- CC 0 updates bank MSB, CC 32 updates bank LSB, and `program_change` updates program.
- The flattened `derived` state currently uses the per-port sticky state, while `derived_ch` and `derived_port` are included for debugging.
- `effective_channel()` returns the message channel for note messages and the last observed note channel for non-note messages when available.
- `selection_matches_event()` gates matching by active port, effective channel, bank MSB, bank LSB, and program.

## Contexts and bindings

- Contexts are keyed by `daw_slot`, `preset_slot`, `port_id`, `channel`, `bank_msb`, `bank_lsb`, and `program`.
- Bindings are scoped to a context and store trigger columns, command text, debounce, require-keygrab, enabled state, notes, notify text, and notify emoji.
- The current UI primarily edits note bindings, but the backend schema and matching path include CC, pitchwheel, and program change trigger types.
- Removing the final binding from a context deletes the now-empty context.

## Import/export

- Export is context-level at `/api/contexts/{context_id}/export`.
- The export payload uses `version: 1`, includes `port_name` for portability, includes an optional context label, and excludes binding ids.
- Import is context-level at `/api/contexts/import`.
- Import resolves `port_name` to a local port row, creating the port row if needed.
- Import supports `merge` and `replace`; unsupported versions are rejected.

## WebSocket event shape

- `/ws/events` broadcasts JSON text payloads from `midi_pump()`.
- Current event fields include raw MIDI fields, `effective_channel`, `derived`, `derived_ch`, `derived_port`, `context_match`, `observed_note_channel`, `keygrab_enabled`, `max_note`, `active_context_id`, and `binding_match`.
- When command execution happens during MIDI handling, `command_execution` may be included in the event payload.
