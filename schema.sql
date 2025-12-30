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

  UNIQUE(context_id, trig_type, note, cc)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

INSERT OR IGNORE INTO settings(key, value) VALUES ('armed', '0');
