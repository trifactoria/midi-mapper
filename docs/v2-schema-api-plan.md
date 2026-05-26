# midi-mapper v2 schema and API migration plan

This is a planning document only. It defines how to move the current repository from its context/binding model toward the v2 model:

```text
Device -> Profile -> Layer -> Trigger -> Action -> Run
```

No schema or production code changes are made by this document.

## Current backend baseline

The current backend has already been modularized for Phase 1:

- App creation and router registration: `backend/main.py`
- Existing API routes: `backend/api/*.py`
- Current request models: `backend/schemas.py`
- Current DB helpers: `backend/db.py`
- Current migrations/schema helpers: `backend/migrations.py`
- Current MIDI state/normalization/matching: `backend/midi/state.py`, `backend/midi/normalize.py`, `backend/midi/matcher.py`, `backend/midi/listener.py`
- Current command execution and notification helpers: `backend/actions/executor.py`, `backend/actions/notifications.py`
- Compatibility ASGI/import shim: `app.py`
- Current base schema: `schema.sql`

The current frontend still uses context-oriented APIs through `src/components/useMidiApi.ts`, `src/components/MidiContextBar.tsx`, `src/components/BindingEditor.tsx`, `src/app/page.tsx`, and related screens. Phase 2 should not require frontend changes until compatibility adapters are in place.

## 1. Current tables

### `ports`

Current use:

- Defined in `schema.sql`.
- Used by `backend/api/ports.py`, `backend/api/midi.py`, `backend/api/contexts.py`, and `backend/services.py`.
- Stores registered MIDI input port names with `id` and unique `name`.
- Online state is computed at request time from `mido.get_input_names()`.

V2 handling:

- Migrate or mirror into `devices`.
- Keep temporarily for old APIs such as `/api/ports`, `/api/contexts/*`, and old context imports.
- Long term, replace direct port ownership in current APIs with device lookup adapters.

### `contexts`

Current use:

- Defined in `schema.sql`.
- Stores a unique context made from `daw_slot`, `preset_slot`, `port_id`, `channel`, `bank_msb`, `bank_lsb`, and `program`.
- Drives active selection and current matching through `backend/api/contexts.py`, `backend/services.py`, and `backend/midi/matcher.py`.

V2 handling:

- Do not delete initially.
- Treat as a legacy mapping container.
- Convert each context into either a v2 layer with advanced filters or into legacy compatibility metadata attached to migrated bindings.
- Keep old context APIs until the frontend moves to v2 profile/layer APIs.

### `bindings`

Current use:

- Defined in `schema.sql`.
- Combines trigger fields, command action, debounce, armed requirement, notes, notification text, and emoji.
- Used by `backend/api/bindings.py`, `backend/api/contexts.py`, and `backend/midi/matcher.py`.

V2 handling:

- Split into v2 trigger/binding and action records.
- Keep as legacy storage during adapter rollout.
- Backfill v2 `triggers`/`bindings` and `actions` from old rows.

### `settings`

Current use:

- Defined in `schema.sql`.
- Stores key/value app state such as keygrab, defaults, mouse mode, active context, preferred output port, and other runtime settings.
- Accessed through `backend/services.py` and `backend/api/settings.py`.

V2 handling:

- Keep as the app-wide settings store initially.
- Add v2 keys for active profile/layer, shell/execution settings, allowed script directories, and migration status.
- Consider a typed settings table later only if key/value validation becomes hard to maintain.

### `context_labels`

Current use:

- Created by inline migration logic in `backend/migrations.py`, not in the original `schema.sql`.
- Maps `context_id` to a friendly label.
- Used by `backend/api/contexts.py`.

V2 handling:

- Use as the best available source for v2 profile/layer names.
- Keep until legacy context APIs are retired.
- Backfill migrated profiles/layers with these labels where possible.

## 2. Proposed v2 tables

The first implementation should add v2 tables alongside legacy tables. Do not drop or rewrite legacy tables in the first v2 migration.

### `devices`

Purpose:

- Persistent representation of MIDI input sources.

Proposed fields:

```sql
id INTEGER PRIMARY KEY
name TEXT NOT NULL
port_name TEXT NOT NULL
port_index INTEGER
connected INTEGER NOT NULL DEFAULT 0
last_seen_at TEXT
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
UNIQUE(port_name)
```

Migration source:

- Backfill from `ports.name`.
- `devices.port_name` should initially equal `ports.name`.

Compatibility:

- `/api/ports` can read from `ports` until adapters are ready.
- `/api/devices` should read from `devices` and compute connection state from `mido.get_input_names()`.

### `profiles`

Purpose:

- Named mapping collection for a workflow.

Proposed fields:

```sql
id INTEGER PRIMARY KEY
name TEXT NOT NULL
description TEXT NOT NULL DEFAULT ''
active INTEGER NOT NULL DEFAULT 0
legacy_context_id INTEGER REFERENCES contexts(id)
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Migration source:

- Minimum initial migration can create one profile named `Imported Legacy Contexts`.
- Better migration can create one profile per labeled context group only if grouping rules are explicit.

Recommended first pass:

- Create one default profile for existing data.
- Convert each legacy context into a layer under that profile.
- Preserve `contexts.id` in `layers.legacy_context_id` rather than overloading `profiles`.

### `layers`

Purpose:

- Logical bank of bindings inside a profile.

Proposed fields:

```sql
id INTEGER PRIMARY KEY
profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE
name TEXT NOT NULL
sort_order INTEGER NOT NULL DEFAULT 0
color TEXT
active INTEGER NOT NULL DEFAULT 0
activation_trigger_id INTEGER REFERENCES triggers(id)
legacy_context_id INTEGER REFERENCES contexts(id)
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Migration source:

- Each legacy `contexts` row becomes a layer.
- `context_labels.label` becomes `layers.name`.
- If no label exists, generate a stable name from the legacy context fields, for example `Context 12 - ch 1 msb 0 lsb 0 program 0`.

Advanced filters:

- Store legacy context filters on migrated triggers, not only on layers, so matching remains exact.

### `triggers` and `bindings`

The v2 design can use either one table named `bindings` containing trigger matching fields plus `action_id`, or separate `triggers` and `bindings`. To preserve clarity and future action reuse, use both:

```sql
triggers:
id INTEGER PRIMARY KEY
event_type TEXT NOT NULL
channel INTEGER
note INTEGER
controller INTEGER
program INTEGER
pitch_min INTEGER
pitch_max INTEGER
value_min INTEGER
value_max INTEGER
velocity_min INTEGER
velocity_max INTEGER
device_id INTEGER REFERENCES devices(id)
port_name TEXT
bank_msb INTEGER
bank_lsb INTEGER
program_filter INTEGER
raw_match_json TEXT
legacy_context_id INTEGER REFERENCES contexts(id)
legacy_binding_id INTEGER REFERENCES bindings(id)
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

bindings_v2:
id INTEGER PRIMARY KEY
profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE
layer_id INTEGER NOT NULL REFERENCES layers(id) ON DELETE CASCADE
trigger_id INTEGER NOT NULL REFERENCES triggers(id) ON DELETE CASCADE
action_id INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE
enabled INTEGER NOT NULL DEFAULT 1
require_armed INTEGER NOT NULL DEFAULT 1
cooldown_ms INTEGER NOT NULL DEFAULT 200
notes TEXT NOT NULL DEFAULT ''
display_label TEXT NOT NULL DEFAULT ''
display_color TEXT
display_emoji TEXT NOT NULL DEFAULT ''
legacy_binding_id INTEGER REFERENCES bindings(id)
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Migration source:

- Existing `bindings.trig_type` maps to `triggers.event_type`:
  - `1` -> `note_on`
  - `2` -> `control_change`
  - `3` -> `pitch_bend`
  - `4` -> `program_change`
- Existing `bindings.note` maps to `triggers.note`.
- Existing `bindings.cc` maps to `triggers.controller`.
- Existing value/pitch min/max fields map directly.
- Existing `contexts.channel`, `contexts.bank_msb`, `contexts.bank_lsb`, and `contexts.program` become advanced trigger filters.
- Existing `contexts.port_id` resolves to `ports.name`, then `devices.id` and/or `triggers.port_name`.

Naming note:

- If keeping a v2 table named `bindings`, avoid collision with the current `bindings` table. Either rename the old table later after migration or use `bindings_v2` during the compatibility period.
- Recommended first implementation uses `bindings_v2` to avoid breaking current routes.

### `actions`

Purpose:

- Configured operation executed when a binding matches.

Proposed fields:

```sql
id INTEGER PRIMARY KEY
type TEXT NOT NULL DEFAULT 'command'
label TEXT NOT NULL DEFAULT ''
command TEXT
args_json TEXT
working_directory TEXT
environment_json TEXT
execution_mode TEXT NOT NULL DEFAULT 'argv'
timeout_ms INTEGER
cooldown_ms INTEGER
allow_concurrent INTEGER NOT NULL DEFAULT 0
notify_text TEXT NOT NULL DEFAULT ''
notify_emoji TEXT NOT NULL DEFAULT ''
legacy_binding_id INTEGER REFERENCES bindings(id)
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Migration source:

- Existing `bindings.command` becomes `actions.command`.
- Initial migrated `actions.type` should be `command`.
- Existing notification fields move from old `bindings` into `actions.notify_text` and `actions.notify_emoji`.
- Existing `bindings.notes` can remain on `bindings_v2.notes`, with action label generated from command or note metadata.

Future action types:

- `script`
- `open_url`
- `http_request`
- `sequence`
- `toggle`
- `noop/test`

Do not implement these in the schema migration beyond allowing `type`.

### `runs`

Purpose:

- Execution history for action runs.

Proposed fields:

```sql
id INTEGER PRIMARY KEY
action_id INTEGER REFERENCES actions(id)
binding_id INTEGER REFERENCES bindings_v2(id)
profile_id INTEGER REFERENCES profiles(id)
layer_id INTEGER REFERENCES layers(id)
trigger_snapshot_json TEXT NOT NULL DEFAULT '{}'
action_summary TEXT NOT NULL DEFAULT ''
started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
finished_at TEXT
duration_ms INTEGER
status TEXT NOT NULL DEFAULT 'started'
exit_code INTEGER
stdout_preview TEXT NOT NULL DEFAULT ''
stderr_preview TEXT NOT NULL DEFAULT ''
error_message TEXT NOT NULL DEFAULT ''
created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

Migration source:

- No backfill from current data because current command execution is detached and does not persist run history.

### Optional legacy mapping tables/views

Recommended compatibility mapping:

```sql
legacy_context_migrations:
legacy_context_id INTEGER PRIMARY KEY REFERENCES contexts(id)
profile_id INTEGER NOT NULL REFERENCES profiles(id)
layer_id INTEGER NOT NULL REFERENCES layers(id)
migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP

legacy_binding_migrations:
legacy_binding_id INTEGER PRIMARY KEY REFERENCES bindings(id)
trigger_id INTEGER NOT NULL REFERENCES triggers(id)
action_id INTEGER NOT NULL REFERENCES actions(id)
binding_v2_id INTEGER NOT NULL REFERENCES bindings_v2(id)
migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
```

These tables make rollback and repeated idempotent migrations easier. They also prevent guessing when a legacy binding has already been converted.

## 3. Migration strategy

### Step 1: Add v2 tables without modifying legacy tables

Add new tables in `backend/migrations.py` and `schema.sql` only after a migration PR is approved. For this planning phase, no changes are made.

Migration should be idempotent:

- Create `devices`, `profiles`, `layers`, `triggers`, `actions`, `bindings_v2`, `runs`, and optional legacy mapping tables if missing.
- Do not drop or rename `ports`, `contexts`, `bindings`, `settings`, or `context_labels`.

### Step 2: Backfill devices

For each `ports` row:

- Insert `devices.name = ports.name`.
- Insert `devices.port_name = ports.name`.
- Preserve connection state as computed state, not static truth.

### Step 3: Backfill profile and layers

Recommended first migration:

- Create one profile named `Legacy Mappings`.
- Set it active if no active v2 profile exists.
- For each `contexts` row, create one `layers` row.
- Layer name resolution:
  - use `context_labels.label` if present;
  - otherwise use deterministic generated text from context fields.

This keeps migration deterministic and avoids guessing user intent.

Alternative later:

- Group contexts into profiles using labels or shared `daw_slot`/`preset_slot`, but only after UX and import/export semantics are defined.

### Step 4: Backfill triggers/actions/bindings

For each legacy `bindings` row joined to its `contexts` row:

- Create one `actions` row:
  - `type = 'command'`
  - `command = bindings.command`
  - `execution_mode = 'argv'` unless future settings explicitly say shell
  - `cooldown_ms = bindings.debounce_ms`
  - `notify_text = bindings.notify_text`
  - `notify_emoji = bindings.notify_emoji`
  - `legacy_binding_id = bindings.id`
- Create one `triggers` row:
  - event type from `trig_type`
  - note/controller/pitch/value fields from `bindings`
  - channel/bank/program/port filters from `contexts`
  - `legacy_context_id` and `legacy_binding_id` set
- Create one `bindings_v2` row:
  - link profile/layer/trigger/action
  - copy `enabled`, `require_armed`, `debounce_ms` as `cooldown_ms`, `notes`, and `notify_emoji` as `display_emoji`

### Step 5: Preserve old import/export

Current routes:

- `GET /api/contexts/{context_id}/export`
- `POST /api/contexts/import`

These must remain in `backend/api/contexts.py` until the frontend and scripts no longer depend on them.

Compatibility policy:

- Old export should continue to export from legacy tables while the old UI exists.
- Old import should continue writing legacy `contexts` and `bindings`, then optionally trigger v2 backfill for the imported context.
- New v2 profile export/import should be added under `/api/profiles/{profile_id}/export` and `/api/profiles/import`.

### Step 6: Matching engine migration

Current matching:

- `backend/midi/listener.py` calls `binding_matches_message()` from `backend/midi/matcher.py`.
- `binding_matches_message()` queries legacy `bindings` by active context.
- `selection_matches_event()` gates by `ACTIVE_SELECTION`.

V2 matching should be introduced behind a compatibility switch:

1. Keep current legacy matcher as default.
2. Add `binding_matches_message_v2()` that:
   - reads active profile/layer from settings;
   - normalizes the MIDI message;
   - evaluates trigger fields and advanced filters;
   - returns binding/action data in a shape the listener can execute.
3. Add tests proving old and migrated v2 rows match the same events.
4. Only switch default matching after compatibility tests pass.

## 4. API plan

Existing routes remain temporarily. New v2 routes should be added alongside them.

### `/api/devices`

Module:

- `backend/api/devices.py`

Routes:

- `GET /api/devices`
- `POST /api/devices/refresh`
- `GET /api/devices/{device_id}`

Behavior:

- Backed by `devices`.
- Compute `connected` from current `mido.get_input_names()`.
- Eventually replace `/api/ports`, but do not remove `/api/ports` during Phase 2.

### `/api/profiles`

Module:

- `backend/api/profiles.py`

Routes:

- `GET /api/profiles`
- `POST /api/profiles`
- `GET /api/profiles/{profile_id}`
- `PATCH /api/profiles/{profile_id}`
- `POST /api/profiles/{profile_id}/activate`
- `POST /api/profiles/{profile_id}/duplicate`
- `DELETE /api/profiles/{profile_id}`
- `GET /api/profiles/{profile_id}/export`
- `POST /api/profiles/import`

Behavior:

- Manage v2 profiles.
- Activation should update a settings key such as `active_profile_id`.

### `/api/layers`

Module:

- `backend/api/layers.py`

Routes:

- `GET /api/profiles/{profile_id}/layers`
- `POST /api/profiles/{profile_id}/layers`
- `PATCH /api/layers/{layer_id}`
- `POST /api/layers/{layer_id}/activate`
- `DELETE /api/layers/{layer_id}`

Behavior:

- Manage layers for a profile.
- Activation should update `active_layer_id`.

### `/api/bindings`

Current module:

- `backend/api/bindings.py`

V2 expansion:

- Keep current `/api/bindings/set`, `/api/bindings/remove`, and `/api/bindings/run`.
- Add v2 routes without changing old route behavior:
  - `GET /api/layers/{layer_id}/bindings`
  - `POST /api/layers/{layer_id}/bindings`
  - `GET /api/bindings/{binding_id}`
  - `PATCH /api/bindings/{binding_id}`
  - `DELETE /api/bindings/{binding_id}`

Important:

- Avoid ambiguity with current `bindings` table by using `bindings_v2` internally until legacy routes are retired.

### `/api/actions`

Module:

- `backend/api/actions.py`

Routes:

- `GET /api/actions/{action_id}`
- `PATCH /api/actions/{action_id}`
- `POST /api/actions/{action_id}/test`
- `POST /api/actions/{action_id}/dry_run`

Behavior:

- Initially support command actions only.
- Use existing `backend/actions/executor.py`.
- Do not add run-history behavior until `runs` table is ready.

### `/api/runs`

Module:

- `backend/api/runs.py`

Routes:

- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `DELETE /api/runs/{run_id}`

Behavior:

- Read from `runs`.
- Write path should be integrated later into `backend/actions/executor.py` or a wrapper around it.

### `/api/settings`

Current module:

- `backend/api/settings.py`

V2 expansion:

- Keep current key/value routes.
- Add typed convenience endpoints later:
  - `GET /api/settings/execution`
  - `PATCH /api/settings/execution`
  - `GET /api/settings/midi`
  - `GET /api/settings/database`

### Temporary compatibility routes

Keep until frontend migration is complete:

- `/api/ports`
- `/api/ports/refresh`
- `/api/contexts/get_or_create`
- `/api/contexts/with_bindings`
- `/api/contexts/{context_id}/bindings`
- `/api/contexts/{context_id}/label`
- `/api/contexts/{context_id}/export`
- `/api/contexts/import`
- `/api/active_context/set`
- `/api/active_selection/set`
- `/api/bindings/set`
- `/api/bindings/remove`
- `/api/bindings/run`
- `/api/midi/send_context`

Do not remove these until `src/components/MidiContextBar.tsx`, `src/components/BindingEditor.tsx`, `src/app/page.tsx`, and helper scripts such as `vdj-midi-mapper.py` are migrated.

## 5. Rollout phases

### Phase 2.1: Add v2 tables without changing old UI

Goal:

- Add v2 tables and idempotent migrations.
- No frontend change.
- Legacy APIs still read/write legacy tables.

Files likely affected:

- `schema.sql`
- `backend/migrations.py`
- `tests/`

Done when:

- Existing 12 tests pass.
- New migration tests prove v2 tables are created against empty and legacy DBs.

### Phase 2.2: Add compatibility adapters

Goal:

- Backfill v2 rows from legacy rows.
- Track mappings between old and new ids.
- Keep old import/export compatible.

Files likely affected:

- `backend/migrations.py`
- `backend/services.py`
- new `backend/legacy.py` or `backend/legacy/adapters.py`
- `backend/api/contexts.py`
- `backend/api/bindings.py`

Done when:

- Migrated rows preserve old matching semantics.
- Old context import can populate v2 mappings without duplicate backfills.

### Phase 2.3: Expose v2 APIs

Goal:

- Add `/api/devices`, `/api/profiles`, `/api/layers`, `/api/actions`, and `/api/runs`.
- Existing old APIs remain.

Files likely affected:

- new `backend/api/devices.py`
- new `backend/api/profiles.py`
- new `backend/api/layers.py`
- new `backend/api/actions.py`
- new `backend/api/runs.py`
- `backend/main.py` router inclusion
- `backend/schemas.py`

Done when:

- API tests cover basic CRUD without frontend changes.

### Phase 2.4: Migrate matching engine

Goal:

- Add v2 matching path while preserving old matching as fallback.

Files likely affected:

- `backend/midi/matcher.py`
- `backend/midi/listener.py`
- `backend/actions/executor.py`
- `tests/test_midi_matching.py`

Done when:

- Legacy row and migrated v2 row match the same synthetic MIDI events.
- Debounce, keygrab/armed behavior, effective-channel behavior, and bank/program filters remain identical.

### Automation armed setting

The v2 API introduces `automation_armed` in the existing `settings` table as the future global pause/unpause switch for MIDI-triggered automation. It is exposed through:

- `GET /api/settings/automation`
- `PATCH /api/settings/automation`

This setting is intentionally separate from legacy `keygrab_enabled`. The old `/api/keygrab` and `/api/keygrab/set` routes remain compatibility APIs for the current frontend and current matcher behavior. Future v2 matching should read `automation_armed` as the global safety switch while preserving `bindings_v2.require_armed` as the per-binding requirement.

### Phase 2.5: Later frontend update

Goal:

- Move UI from context-first to profile/layer/action-first.

Files likely affected later:

- `src/components/MidiContextBar.tsx`
- `src/components/BindingEditor.tsx`
- `src/components/NoteGrid.tsx`
- `src/components/types.ts`
- `src/components/useMidiApi.ts`
- `src/app/page.tsx`
- new profile/layer/run/settings screens

Not part of the first schema/API migration.

## 6. Tests required before implementation

Before implementing schema changes:

- Migration test: empty DB -> all legacy and v2 tables exist.
- Migration test: current legacy DB -> v2 tables exist and old tables/data unchanged.
- Migration test: `context_labels` migration still works.
- Backfill test: one port/context/binding creates one device/profile/layer/trigger/action/bindings_v2 mapping.
- Backfill idempotency test: running migration twice does not duplicate v2 rows.
- Trigger mapping tests for `note_on`, `control_change`, `pitch_bend`, and `program_change`.
- Advanced filter tests for device/port/channel/bank MSB/bank LSB/program.
- Old API regression tests for context CRUD, binding CRUD, context import/export, and manual run.
- V2 API CRUD tests for devices, profiles, layers, bindings, actions, and runs.
- Matching parity test: old matcher and v2 matcher return equivalent binding/action for migrated data.
- Shell disabled by default test remains in `tests/test_command_execution.py`.
- WebSocket payload regression test remains in `tests/test_websocket_shape.py`; no v2 event shape change until explicitly planned.
- Rollback test: disabling v2 matcher still permits old context/binding matching.

## 7. Risks and rollback plan

### Risks

- Data duplication: legacy imports may create duplicate v2 mappings unless migration tables enforce idempotency.
- Semantic drift: contexts include DAW/preset/bank/program filters that do not map cleanly to a generic profile/layer model.
- Matching regressions: current matching depends on `ACTIVE_SELECTION`, `LAST_NOTE_CHANNEL`, port-level bank/program state, and debounce state in `backend/midi/state.py`.
- UI mismatch: old frontend still expects context IDs and legacy binding IDs.
- Action split risk: existing `bindings.command`, notify fields, and debounce fields are currently one row; splitting into action/trigger/binding can accidentally change execution behavior.
- Import/export ambiguity: old context exports are not profile exports.
- Rollout complexity: maintaining old and new route sets temporarily increases test burden.

### Rollback plan

- Keep all legacy tables intact in Phase 2.
- Keep old APIs intact and default frontend traffic to old APIs.
- Add v2 matcher behind a setting such as `matching_mode=legacy|v2|dual`, with default `legacy` until parity tests pass.
- Use mapping tables to identify and delete v2 rows generated from legacy rows if a migration must be rolled back.
- Do not mutate or delete old `contexts` or `bindings` during v2 backfill.
- If v2 API rollout fails, remove router inclusion from `backend/main.py` while leaving v2 tables unused.
- If v2 matching fails, switch the setting back to `legacy` and keep current `backend/midi/matcher.py` path active.

## 8. Implementation guardrails

- No frontend migration in the first v2 schema PR.
- No table drops or renames in the first v2 schema PR.
- No change to `/ws/events` payload shape in the first v2 schema PR.
- No change to command execution behavior in `backend/actions/executor.py`.
- No change to old import/export payload version in `backend/api/contexts.py`.
- Every migration must be idempotent and safe against an existing `midi_map.db`.
