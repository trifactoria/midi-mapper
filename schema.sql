PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS ports (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS contexts (
  id INTEGER PRIMARY KEY,

  daw_slot INTEGER NOT NULL DEFAULT 0,
  preset_slot INTEGER NOT NULL DEFAULT 0,

  port_id INTEGER NOT NULL REFERENCES ports(id),
  channel INTEGER NOT NULL DEFAULT 0,
  bank_msb INTEGER NOT NULL DEFAULT 0,
  bank_lsb INTEGER NOT NULL DEFAULT 0,
  program INTEGER NOT NULL DEFAULT 0,

  UNIQUE(daw_slot, preset_slot, port_id, channel, bank_msb, bank_lsb, program)
);

CREATE TABLE IF NOT EXISTS bindings (
  id INTEGER PRIMARY KEY,
  context_id INTEGER NOT NULL REFERENCES contexts(id) ON DELETE CASCADE,
  enabled INTEGER NOT NULL DEFAULT 1,

  trig_type INTEGER NOT NULL, -- 1=note_on, 2=cc, 3=pitchwheel, 4=program_change
  note INTEGER,
  cc INTEGER,
  value_min INTEGER,
  value_max INTEGER,
  pitch_min INTEGER,
  pitch_max INTEGER,

  command TEXT NOT NULL,
  debounce_ms INTEGER NOT NULL DEFAULT 200,
  require_armed INTEGER NOT NULL DEFAULT 1,

  -- Binding metadata (from migration 002)
  notes TEXT NOT NULL DEFAULT '',
  notify_text TEXT NOT NULL DEFAULT '',
  notify_emoji TEXT NOT NULL DEFAULT '',

  UNIQUE(context_id, trig_type, note, cc)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- v2 schema, currently additive/unused by legacy APIs.
CREATE TABLE IF NOT EXISTS devices (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  port_name TEXT NOT NULL,
  port_index INTEGER,
  connected INTEGER NOT NULL DEFAULT 0,
  last_seen_at TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(port_name)
);

CREATE TABLE IF NOT EXISTS profiles (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  active INTEGER NOT NULL DEFAULT 0,
  legacy_context_id INTEGER REFERENCES contexts(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS layers (
  id INTEGER PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  sort_order INTEGER NOT NULL DEFAULT 0,
  color TEXT,
  active INTEGER NOT NULL DEFAULT 0,
  activation_trigger_id INTEGER REFERENCES triggers(id),
  legacy_context_id INTEGER REFERENCES contexts(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS triggers (
  id INTEGER PRIMARY KEY,
  event_type TEXT NOT NULL,
  channel INTEGER,
  note INTEGER,
  controller INTEGER,
  program INTEGER,
  pitch_min INTEGER,
  pitch_max INTEGER,
  value_min INTEGER,
  value_max INTEGER,
  velocity_min INTEGER,
  velocity_max INTEGER,
  device_id INTEGER REFERENCES devices(id),
  port_name TEXT,
  bank_msb INTEGER,
  bank_lsb INTEGER,
  program_filter INTEGER,
  raw_match_json TEXT,
  legacy_context_id INTEGER REFERENCES contexts(id),
  legacy_binding_id INTEGER REFERENCES bindings(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS actions (
  id INTEGER PRIMARY KEY,
  type TEXT NOT NULL DEFAULT 'command',
  label TEXT NOT NULL DEFAULT '',
  command TEXT,
  duration_ms INTEGER,
  args_json TEXT,
  working_directory TEXT,
  environment_json TEXT,
  execution_mode TEXT NOT NULL DEFAULT 'argv',
  timeout_ms INTEGER,
  cooldown_ms INTEGER,
  allow_concurrent INTEGER NOT NULL DEFAULT 0,
  notify_text TEXT NOT NULL DEFAULT '',
  notify_emoji TEXT NOT NULL DEFAULT '',
  title TEXT,
  message TEXT,
  urgency TEXT,
  legacy_binding_id INTEGER REFERENCES bindings(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bindings_v2 (
  id INTEGER PRIMARY KEY,
  profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
  layer_id INTEGER NOT NULL REFERENCES layers(id) ON DELETE CASCADE,
  trigger_id INTEGER NOT NULL REFERENCES triggers(id) ON DELETE CASCADE,
  action_id INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  enabled INTEGER NOT NULL DEFAULT 1,
  require_armed INTEGER NOT NULL DEFAULT 1,
  cooldown_ms INTEGER NOT NULL DEFAULT 200,
  notes TEXT NOT NULL DEFAULT '',
  display_label TEXT NOT NULL DEFAULT '',
  display_color TEXT,
  display_emoji TEXT NOT NULL DEFAULT '',
  display_icon TEXT NOT NULL DEFAULT '',
  legacy_binding_id INTEGER REFERENCES bindings(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS binding_actions (
  id INTEGER PRIMARY KEY,
  binding_id INTEGER NOT NULL REFERENCES bindings_v2(id) ON DELETE CASCADE,
  action_id INTEGER NOT NULL REFERENCES actions(id) ON DELETE CASCADE,
  execution_order INTEGER NOT NULL DEFAULT 0,
  enabled INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(binding_id, action_id)
);

CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY,
  action_id INTEGER REFERENCES actions(id),
  binding_id INTEGER REFERENCES bindings_v2(id),
  profile_id INTEGER REFERENCES profiles(id),
  layer_id INTEGER REFERENCES layers(id),
  trigger_snapshot_json TEXT NOT NULL DEFAULT '{}',
  action_summary TEXT NOT NULL DEFAULT '',
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  duration_ms INTEGER,
  status TEXT NOT NULL DEFAULT 'started',
  exit_code INTEGER,
  stdout_preview TEXT NOT NULL DEFAULT '',
  stderr_preview TEXT NOT NULL DEFAULT '',
  error_message TEXT NOT NULL DEFAULT '',
  session_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS legacy_context_migrations (
  legacy_context_id INTEGER PRIMARY KEY REFERENCES contexts(id),
  profile_id INTEGER NOT NULL REFERENCES profiles(id),
  layer_id INTEGER NOT NULL REFERENCES layers(id),
  migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS legacy_binding_migrations (
  legacy_binding_id INTEGER PRIMARY KEY REFERENCES bindings(id),
  trigger_id INTEGER NOT NULL REFERENCES triggers(id),
  action_id INTEGER NOT NULL REFERENCES actions(id),
  binding_v2_id INTEGER NOT NULL REFERENCES bindings_v2(id),
  migrated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Defaults
INSERT OR IGNORE INTO settings(key, value) VALUES ('armed', '0');
