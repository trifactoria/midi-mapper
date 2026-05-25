# midi-mapper v2 gap analysis

This document compares the current repository to the midi-mapper v2 design spec and outlines what would be required to migrate the project toward the v2 goal:

> a local MIDI-powered automation launcher that turns keyboards/controllers into programmable workflow hotkeys.

No implementation changes are included here.

## 1. Current repository summary

### Backend

The backend is a single-file FastAPI application in `app.py`.

- Framework: FastAPI with `uvicorn` startup, `pydantic` request models, and CORS middleware. See `app.py` and `requirements.txt`.
- Database access: SQLite through `aiosqlite`, with helper functions `db_connect`, `db_exec`, `db_fetchall`, and `db_fetchone` in `app.py`.
- Schema: `schema.sql` defines `ports`, `contexts`, `bindings`, and `settings`. `app.py` also applies inline migrations for `bindings.notes`, `bindings.notify_text`, `bindings.notify_emoji`, and `context_labels`.
- Runtime state: in-memory dictionaries in `app.py` track per-channel state, per-port state, output port cache, last note channel, active UI selection, and debounce timestamps.
- MIDI handling: `mido` and `python-rtmidi` are used directly from `app.py`. `midi_pump()` opens all input ports visible at startup, polls them with `iter_pending()`, derives bank/program state, matches events, executes matching bindings, and broadcasts WebSocket events.
- Command execution: `safe_execute_command()` in `app.py` executes binding commands using `asyncio.create_subprocess_exec`. Shell execution is controlled by `MIDI_MAPPER_EXEC_USE_SHELL`, defaults to false, and uses `bash -lc` when enabled. In argv mode, commands are parsed with `shlex.split` and resolved with `shutil.which` against `MIDI_MAPPER_EXEC_PATH`.
- Notifications: `send_notification()` in `app.py` optionally invokes `notify-send`.
- WebSocket flow: `/ws/events` is implemented in `app.py` through `WSManager`; frontend clients send keepalive pings while the backend broadcasts MIDI payloads.
- Import/export: context-level import/export exists through `/api/contexts/{context_id}/export` and `/api/contexts/import`.
- Helper workflow script: `vdj-midi-mapper.py` is a separate CLI for video/cue/mpv workflows that calls the midi-mapper API and manages mpv IPC. It is useful as an integration example, but it is not part of the core backend service.

### Frontend

The frontend is a Next.js app in `src/`.

- Framework: Next.js 16, React 19, TypeScript, Tailwind CSS. See `src/package.json`, `src/app/layout.tsx`, and `src/app/globals.css`.
- API client: `src/components/useMidiApi.ts` wraps `fetch` calls against `NEXT_PUBLIC_API_BASE`, defaulting to `http://127.0.0.1:8765`.
- App shell: `src/app/layout.tsx` provides metadata, header, constrained main content, and footer. `src/components/Header.tsx` includes a logo menu, help/about links, and repo/sponsor links.
- Main screen: `src/app/page.tsx` combines a status strip, keygrab/mouse/live-console toggles, `MidiContextBar`, `BindingEditor`, `NoteGrid`, and an optional embedded live MIDI console.
- Binding page: `src/app/bind/page.tsx` provides a simpler context + grid + binding editor layout.
- Console page: `src/app/console/page.tsx` provides a dedicated live MIDI event console.
- Context UI: `src/components/MidiContextBar.tsx` exposes DAW slot, preset slot, port, channel, bank MSB, bank LSB, and program. It also supports saved context labels, defaults, MIDI output context send, and context import/export.
- Binding UI: `src/components/BindingEditor.tsx` edits note bindings only in the current UI path. It stores a command string, debounce, require-keygrab, enabled state, notes, notify text, and emoji marker.
- Grid UI: `src/components/NoteGrid.tsx` renders a 0-127 note grid, shows bound markers, selected note, and last pressed note.
- Shared types: `src/components/types.ts` defines `Port`, `ContextHeader`, and `Binding` shapes.

### Storage and domain model

The current persistent model is centered on contexts and bindings:

- `ports`: registered MIDI input port names.
- `contexts`: a unique combination of `daw_slot`, `preset_slot`, `port_id`, `channel`, `bank_msb`, `bank_lsb`, and `program`.
- `bindings`: command mappings scoped to a context, with trigger columns for note, CC, pitchwheel, and program change.
- `settings`: generic key/value state for active context, keygrab, defaults, mouse mode, preferred output port, and similar runtime configuration.
- `context_labels`: added by inline migration in `app.py`, not present in `schema.sql`.

This model works for DAW/preset/bank/program aware mappings, but it does not yet model v2 profiles, layers, actions, runs, normalized triggers, or device lifecycle explicitly.

### Current API surface

The current API is functional but not grouped into the v2 resource shape:

- Ports and diagnostics: `/api/ports`, `/api/ports/refresh`, `/api/health`, `/api/diag/db_stats`, `/api/capabilities`.
- MIDI outputs: `/api/midi/outputs`, `/api/midi/output/select`, `/api/midi/send_context`.
- Active state: `/api/active_context/set`, `/api/active_selection/set`.
- Contexts: `/api/contexts/get_or_create`, `/api/contexts/with_bindings`, context labels, context delete, context export/import.
- Bindings: `/api/contexts/{context_id}/bindings`, `/api/bindings/set`, `/api/bindings/remove`, `/api/bindings/run`.
- Settings: `/api/settings`, `/api/settings/set`, `/api/keygrab`, `/api/keygrab/set`, `/api/defaults`, `/api/defaults/save`, `/api/mouse_mode`, `/api/mouse_mode/set`.
- WebSocket: `/ws/events`.

There are no automated tests currently found in the repository.

## 2. Current architecture compared to v2 target architecture

### Already aligns

- Local-first FastAPI plus browser UI matches the v2 local automation launcher direction.
- MIDI input is already captured through `mido` and streamed to the frontend over `/ws/events`.
- SQLite is a reasonable local storage approach for profiles, bindings, actions, and run history.
- Shell mode is already disabled by default through `MIDI_MAPPER_EXEC_USE_SHELL=false` behavior in `app.py`.
- The command executor already supports argv-style execution by default, PATH control, and explicit shell opt-in.
- The frontend already has useful primitives for v2: live MIDI stream, note grid, binding editor, status strip, and import/export modal.
- Context export/import provides a starting point for profile import/export.
- Debounce exists on bindings and can evolve into v2 cooldown.
- Manual test execution exists through `/api/bindings/run` and the Binding Editor's "Run Now" control.

### Partially aligns

- Current `ports` are close to v2 `Device`, but they only store `id` and `name`. Online status is computed at read time; connected status and last seen timestamp are not persisted.
- Current `contexts` are loosely similar to advanced trigger filters or a layer selector, but they are not v2 profiles or layers.
- Current `bindings` combine trigger, action, safety, notification, and metadata into one row. V2 wants separate trigger/action concepts and run history.
- Current WebSocket payloads contain raw message fields, derived bank/program state, context match, binding match, and command execution result. V2 wants a clearer event stream with raw message, normalized trigger, matched binding, and ignored reason.
- Current import/export is context-level, not profile-level. It can be adapted but should not remain the primary portable unit.
- Current UI has the building blocks for Dashboard, Live MIDI Monitor, Layer Grid, and Binding Editor, but the information architecture is still context-first rather than profile/layer/action-first.
- Current settings exist as key/value rows and environment variables, but there is no dedicated Settings screen for local-only warnings, command execution mode, allowed script directories, CORS/origin settings, database path, and MIDI backend diagnostics.

### Conflicts with target design

- `app.py` is a monolith containing config, database helpers, migrations, API routes, MIDI listener, matcher, command executor, notification logic, and WebSocket manager. The v2 spec calls for backend modules such as `config.py`, `db.py`, `midi/normalize.py`, `midi/matcher.py`, `actions/executor.py`, and resource-specific API routers.
- The primary domain is `context`, built around `daw_slot`, `preset_slot`, bank MSB/LSB, and program. V2's primary domain should be Device -> Profile -> Layer -> Trigger -> Action -> Run.
- The frontend exposes DAW and preset controls as first-class UI in `MidiContextBar.tsx`. The v2 spec says these should not be primary workflow concepts.
- Binding execution currently fires detached subprocesses and discards stdout/stderr. V2 requires run history with status, duration, exit code, stdout/stderr preview, and error message.
- There is no action abstraction. A binding stores a single command string; v2 wants command, script, open_url, http_request, sequence, toggle, and noop/test extensibility.
- Current matching is tied to active context and active selection. V2 needs profile/layer selection and normalized trigger matching, with bank/program and raw message filters hidden as advanced options.
- The MIDI listener opens inputs only at startup. V2 devices need connected status and last seen behavior, which implies refresh/reopen behavior or a device manager.
- `schema.sql` is no longer authoritative because `context_labels` and some binding columns are created by inline migrations in `app.py`.

### Missing

- Profiles table/API/UI.
- Layers table/API/UI and active layer selection.
- Normalized trigger model.
- Action table/API/model separate from binding.
- Run history table/API/UI.
- Settings screen.
- Safety policy layer for allowed script directories, timeout, confirmation/destructive warnings, concurrency, and shell toggle persistence.
- Command timeout and output capture.
- Structured API routers under `/api/devices`, `/api/profiles`, `/api/layers`, `/api/bindings`, `/api/actions`, `/api/runs`, and `/api/settings`.
- WebSocket ignored reasons and normalized event envelope.
- Profile-level import/export.
- Automated backend and frontend tests.
- Packaging story beyond `start`, README setup commands, and direct `uvicorn`/`next dev`.
- Demo/media assets referenced by README.

## 3. Hardware-specific, DAW-specific, or overcomplicated current concepts

| Current concept | Where | Assessment | Recommendation |
| --- | --- | --- | --- |
| `daw_slot` | `schema.sql`, `ContextIn`, `MidiContextBar.tsx` | DAW-specific and primary in current UI. It conflicts with generic workflow-hotkey positioning. | Hide as advanced during migration, then either remove from the primary model or convert to optional advanced metadata/filter. |
| `preset_slot` | `schema.sql`, `ContextIn`, `MidiContextBar.tsx` | Similar to DAW slot; useful for some controllers but not a v2 core concept. | Hide as advanced; migrate useful behavior into layers or optional trigger filters. |
| Bank MSB/LSB and program as primary context | `schema.sql`, `app.py`, `MidiContextBar.tsx` | Valid MIDI concepts, but too prominent for a generic launcher. | Keep as advanced trigger filters. Do not remove until existing mappings can migrate. |
| Context labels and saved contexts | `context_labels` migration, `MidiContextBar.tsx` | Useful, but the name "context" encodes the old model. | Keep temporarily; migrate labeled contexts into profiles/layers or imported legacy mappings. |
| Active selection gating | `ACTIVE_SELECTION`, `/api/active_selection/set`, `selection_matches_event()` | Works for current note grid behavior but ties matching to the UI header. | Simplify into active profile/layer plus optional advanced filters. Keep only as compatibility during migration. |
| Per-port sticky bank/program state | `PORT_STATE`, `update_state()` | Useful for controllers that emit bank/program on a different channel. It is hardware-behavior aware but not necessarily wrong. | Keep in MIDI normalization as advanced derived state, with tests. Do not expose as a primary v2 concept. |
| `effective_channel()` using last note channel | `app.py` | Explicitly Oxygen-style behavior. Helpful but hardware-specific. | Keep as an optional compatibility normalization mode; document and test it. Default v2 matching should use the actual event channel unless configured. |
| MIDI output "send context" | `/api/midi/send_context`, `apiSendContext()` | Hardware-editor flavored. Not central to a local automation launcher. | Hide as advanced or diagnostics; keep only if it remains useful for controller synchronization. |
| Keygrab | settings and UI toggles | Conceptually similar to an arm/safety switch. | Rename/reframe as "armed" or "automation enabled"; keep as a safety feature. |
| Mouse Mode | `/api/mouse_mode`, `page.tsx` | Useful for demos and testing without hardware. | Keep as demo/test mode, but avoid making it central to v2 UI. |
| Emoji markers and notify text | `BindingEditor.tsx`, `bindings` metadata | Helpful for visual grid and notifications, but currently mixed into binding execution. | Keep visual label/color/notification as action metadata or UI metadata. Avoid using emoji as the main action identity. |
| `vdj-midi-mapper.py` | root script | Workflow-specific mpv/cue helper, not generic core. | Keep as an example/integration script or move later under examples. Do not let it shape the core v2 model. |
| Inline styling and one large screen | most frontend components | Fast for prototype, but makes v2 UX harder to maintain. | Replace during frontend redesign with a small component system and route-level screens. |

## 4. Recommended migration plan

### Phase 0: documentation and tests only

Goal:
Establish the target behavior and protect the current behavior before moving code.

Files likely affected:

- `docs/midi-mapper-v2-gap-analysis.md`
- New backend test files, likely under `tests/`
- New frontend test setup if selected
- Possibly test fixtures under `tests/fixtures/`
- No production code changes except tiny testability hooks if absolutely necessary, but prefer none in this phase

Risks:

- Current behavior is monolithic and hardware-dependent, so tests may need mocks for `mido`, SQLite, subprocesses, and WebSocket clients.
- Tests that depend on real MIDI ports would be fragile.
- Existing runtime DB migrations are in `app.py`, so tests need isolated temporary DB paths.

Tests needed:

- Unit tests around command parsing/execution safety using mocked subprocesses.
- Unit tests for MIDI state derivation and matching using synthetic `mido.Message` objects.
- API tests for context creation, binding CRUD, import/export, keygrab, and health.
- WebSocket event tests with mocked MIDI input or factored event handling.

Definition of done:

- Gap analysis is committed.
- Test strategy is documented.
- Initial automated tests cover the current matching and execution behavior without requiring real MIDI hardware.
- No user-facing behavior changes.

### Phase 1: backend modularization without behavior changes

Goal:
Split `app.py` into modules while preserving current API, schema, and runtime behavior.

Files likely affected:

- `app.py`
- New `backend/main.py`
- New `backend/config.py`
- New `backend/db.py`
- New `backend/models.py`
- New `backend/midi/listener.py`
- New `backend/midi/normalize.py`
- New `backend/midi/matcher.py`
- New `backend/actions/executor.py`
- New `backend/api/*.py`
- `requirements.txt` only if test dependencies are added
- `start` if the ASGI app import path changes

Risks:

- Startup lifecycle changes can break MIDI listener startup or output port cleanup.
- Global state movement can change debounce, active selection, or WebSocket behavior.
- API route paths must remain stable for the current frontend.
- Import path changes can break local run commands.

Tests needed:

- Regression tests for existing API endpoints.
- Matching tests confirming note, CC, pitchwheel, and program_change behavior remains unchanged.
- WebSocket broadcast tests.
- Command execution tests for argv and shell modes.
- Smoke test for application startup with mocked MIDI ports.

Definition of done:

- Current frontend works unchanged against the modular backend.
- Existing API paths still respond with compatible payloads.
- `schema.sql` and migrations are reconciled or at least centralized.
- Tests pass with no real MIDI hardware.

### Phase 2: domain model cleanup

Goal:
Introduce v2 concepts while preserving a migration path from existing contexts and bindings.

Files likely affected:

- `schema.sql` or new migration files
- `backend/models.py`
- `backend/db.py`
- `backend/api/devices.py`
- `backend/api/profiles.py`
- `backend/api/layers.py`
- `backend/api/bindings.py`
- `backend/api/actions.py`
- `backend/api/runs.py`
- `backend/midi/normalize.py`
- `backend/midi/matcher.py`
- Legacy compatibility routes for current context APIs
- Import/export code

Risks:

- Existing user DBs could lose mappings if migration is not careful.
- Ambiguity mapping old contexts to new profile/layer concepts.
- Existing bindings store command strings directly; separating actions requires backfill.
- Over-modeling too early can slow the migration.

Tests needed:

- Migration tests from the current schema to v2 schema.
- Legacy context export/import tests.
- New profile import/export tests.
- Binding matching tests against normalized triggers.
- Layer/profile activation tests.
- Tests that old context-based mappings still execute during compatibility period.

Definition of done:

- V2 tables exist for devices, profiles, layers, triggers/bindings, actions, and runs.
- Existing context rows can be migrated or read through compatibility views/adapters.
- Primary matching path uses normalized triggers and active profile/layer.
- Advanced MIDI filters remain available but are not primary model fields.

### Phase 3: frontend redesign

Goal:
Move from one context-first control surface to v2 screens: Dashboard, Live MIDI Monitor, Layer Grid, Binding Editor, Profiles, Run Log, and Settings.

Files likely affected:

- `src/app/page.tsx`
- `src/app/bind/page.tsx`
- `src/app/console/page.tsx`
- New `src/app/profiles/page.tsx`
- New `src/app/runs/page.tsx`
- New `src/app/settings/page.tsx`
- New or revised frontend components under `src/components/`
- `src/components/MidiContextBar.tsx`
- `src/components/BindingEditor.tsx`
- `src/components/NoteGrid.tsx`
- `src/components/types.ts`
- `src/components/useMidiApi.ts`
- `src/app/globals.css`
- `src/components/Header.tsx`

Risks:

- A large UI rewrite could regress current mapping workflows.
- Hiding DAW/bank/program controls may make existing users think data disappeared.
- WebSocket event shape changes need compatibility or coordinated frontend/backend rollout.
- Current inline styles will be hard to evolve without introducing visual inconsistency.

Tests needed:

- Component tests for Binding Editor action types and validation.
- Integration tests for profile/layer selection and binding creation.
- WebSocket-driven Live MIDI Monitor tests.
- Profile import/export UI tests.
- Run Log rendering tests.
- Responsive layout checks for dashboard, grid, and settings.

Definition of done:

- Dashboard shows active profile/layer, devices, recent MIDI events, recent runs, and service status.
- Live MIDI Monitor shows raw message, normalized trigger, matched binding, and ignored reason.
- Layer Grid supports mapped/unmapped states and quick binding creation.
- Binding Editor configures trigger, action details, cooldown, enabled state, test run, and dry run.
- Profiles screen supports create, duplicate, activate, import/export, and delete.
- Run Log and Settings screens exist.
- Legacy context controls are hidden under advanced or compatibility UI.

### Phase 4: safety hardening and packaging

Goal:
Make local command execution explicit, inspectable, and safer by default; improve install/run ergonomics.

Files likely affected:

- `backend/actions/executor.py`
- `backend/actions/safety.py`
- `backend/api/settings.py`
- `backend/api/runs.py`
- `schema.sql` or migrations
- `src/app/settings/page.tsx`
- `src/components/BindingEditor.tsx`
- README later, but not in this task
- Packaging scripts or service files if added

Risks:

- Stricter safety defaults may break existing bindings.
- Capturing stdout/stderr can hang or consume memory without limits.
- Timeouts and concurrency controls can change command semantics.
- Network binding/CORS defaults need clear local development behavior.

Tests needed:

- Shell disabled by default.
- Shell opt-in requires explicit setting.
- Argv execution does not invoke shell expansion.
- Allowed script directory checks.
- Timeout behavior.
- Cooldown/concurrency behavior.
- Run history status, exit code, output preview, and error capture.
- Settings persistence and validation.

Definition of done:

- Execution defaults to argv mode with shell disabled.
- Commands/actions support timeout, cooldown, working directory, environment overrides, and concurrency policy.
- Run history records started/finished timestamps, status, exit code, stdout/stderr preview, and errors.
- Settings screen exposes local-only warnings and safety controls.
- Backend defaults bind to localhost for normal startup documentation/scripts.

### Phase 5: demo/media polish

Goal:
Make the project understandable as a portfolio-quality local automation launcher.

Files likely affected:

- `README.md` later, but not in this task
- `docs/screenshots/*`
- `docs/demo/*` or similar
- Example profiles/imports under `examples/`
- Possibly `vdj-midi-mapper.py` if moved under examples later

Risks:

- Demo assets can drift from actual UI.
- Overemphasizing a specific workflow can undermine the generic positioning.
- Example commands can be unsafe if copied blindly.

Tests needed:

- Example profile import validation.
- Smoke test for demo profile commands using noop/test actions.
- Link/path checks for README media.

Definition of done:

- README and screenshots show midi-mapper as a generic MIDI automation launcher.
- Demo profile uses safe noop/test or harmless local commands.
- Live MIDI Monitor and Run Log are visible in demo media.
- Hardware-specific scripts are clearly examples, not core product positioning.

## 5. Proposed target file structure

### Backend

```text
backend/
  __init__.py
  main.py
  config.py
  db.py
  migrations.py
  models.py
  schemas.py
  api/
    __init__.py
    devices.py
    profiles.py
    layers.py
    bindings.py
    actions.py
    runs.py
    settings.py
    health.py
    websocket.py
  midi/
    __init__.py
    devices.py
    listener.py
    normalize.py
    matcher.py
    state.py
  actions/
    __init__.py
    executor.py
    safety.py
    history.py
  legacy/
    __init__.py
    contexts.py
    import_export.py
schema.sql
tests/
  backend/
    test_midi_normalize.py
    test_matcher.py
    test_profiles_layers.py
    test_executor_safety.py
    test_runs.py
    test_websocket_events.py
    test_import_export.py
```

### Frontend

```text
src/
  app/
    page.tsx
    monitor/page.tsx
    profiles/page.tsx
    runs/page.tsx
    settings/page.tsx
    layout.tsx
    globals.css
  components/
    app-shell/
      Header.tsx
      Nav.tsx
      StatusBar.tsx
    dashboard/
      DeviceSummary.tsx
      RecentEvents.tsx
      RecentRuns.tsx
      ServiceStatus.tsx
    midi/
      LiveMidiMonitor.tsx
      LayerGrid.tsx
      TriggerDisplay.tsx
      DevicePicker.tsx
    bindings/
      BindingEditor.tsx
      TriggerEditor.tsx
      ActionEditor.tsx
      SafetyControls.tsx
    profiles/
      ProfileList.tsx
      LayerList.tsx
      ImportExportDialog.tsx
    runs/
      RunLog.tsx
      RunDetail.tsx
    settings/
      ExecutionSettings.tsx
      MidiDiagnostics.tsx
      LocalOnlyWarning.tsx
  lib/
    api.ts
    ws.ts
    types.ts
```

## 6. Proposed test plan

### MIDI normalization

- Normalize `note_on`, `note_off`, `control_change`, `program_change`, and `pitchwheel` into one trigger shape.
- Verify velocity/value/range fields are preserved.
- Verify bank MSB/LSB and program are derived correctly from CC 0, CC 32, and program change.
- Verify per-port and per-channel derived state behavior.
- Verify any Oxygen-style effective-channel compatibility mode is opt-in or clearly covered.

### Binding matching

- Match note bindings by event type, channel, note, and optional velocity range.
- Match CC bindings by controller number and value range.
- Match pitch bend and program change triggers.
- Confirm disabled bindings do not match.
- Confirm advanced filters such as device, bank/program, port, and raw matcher work only when configured.
- Confirm ignored reasons are generated for no active profile, no active layer, disabled binding, filter mismatch, cooldown, and safety gating.

### Layer/profile selection

- Activate one profile at a time.
- Select active layer manually.
- Select active layer from a configured MIDI trigger.
- Confirm matching only considers active profile/layer unless explicitly configured otherwise.
- Confirm duplicate/imported profiles do not collide with existing IDs.

### Command execution safety

- Argv execution parses commands without shell expansion.
- PATH lookup uses configured execution PATH.
- Working directory and environment overrides are applied safely.
- Timeout terminates long-running actions.
- Concurrent run policy is enforced.
- Destructive warning/confirmation metadata can block test run or manual run where required.

### Shell disabled by default

- With default config, shell metacharacters are not interpreted.
- Shell mode cannot be enabled accidentally by binding content.
- Shell mode requires explicit setting/environment opt-in.
- Settings/API/UI report shell mode accurately.

### Run history

- Every manual and MIDI-triggered action records a run.
- Runs include action id, trigger snapshot, command/action summary, started at, finished at, status, exit code, stdout/stderr preview, and error message.
- Failed command resolution records a failed run.
- Timeout records a timeout status.
- Output previews are truncated predictably.

### WebSocket event flow

- Connect/disconnect client lifecycle works.
- Incoming MIDI event produces one event envelope with raw message and normalized trigger.
- Matched binding is included when applicable.
- Ignored reason is included when no action runs.
- Command execution/run updates are sent or can be fetched consistently.
- Multiple WebSocket clients receive the same event.

### Profile import/export

- Export includes profiles, layers, bindings, triggers, actions, settings needed for portability, and schema version.
- Import validates version and required fields.
- Import supports merge and replace modes.
- Import maps devices by name without requiring matching numeric IDs.
- Import rejects unsafe or unsupported action fields with clear errors.
- Export/import round trip preserves runnable mappings.

## 7. README repositioning plan

The README should eventually be repositioned around this statement:

> midi-mapper is a local MIDI-powered automation launcher that turns keyboards/controllers into programmable workflow hotkeys.

Recommended README changes later:

- Lead with the generic automation use case, not DAW/preset/controller editing.
- Describe the core flow: MIDI input -> normalized trigger -> profile/layer binding -> action execution -> run history.
- Show concrete workflow examples: run scripts, open tools, trigger local HTTP endpoints, control OBS/dev tasks, launch safe demo actions.
- Keep the local-only and command-execution warning near the top.
- Document shell-disabled-by-default behavior and argv mode before showing shell examples.
- Move DAW/bank/program/context details into an "Advanced MIDI filters" section.
- Move `vdj-midi-mapper.py` into an examples/integrations section.
- Add screenshots or GIFs for Dashboard, Live MIDI Monitor, Layer Grid, Binding Editor, Run Log, and Settings.
- Include a safe demo profile that uses noop/test or harmless commands.
- Keep setup concise: backend install/start, frontend install/start, API base configuration, and troubleshooting.

## 8. Summary

The current repository is a working local MIDI-to-command mapper with a FastAPI backend, SQLite storage, `mido` MIDI polling, WebSocket event streaming, and a Next.js UI for context-scoped note bindings. It already contains several strong foundations for v2: local-first architecture, command execution with shell disabled by default, MIDI event streaming, a note grid, a binding editor, and import/export.

The main gap is domain shape. The current implementation is centered on DAW/preset/bank/program contexts, while v2 should be centered on devices, profiles, layers, normalized triggers, actions, and run history. The safest path is to first add tests, then modularize without behavior changes, then introduce the v2 model behind compatibility adapters, and only then redesign the frontend around the new product positioning.
