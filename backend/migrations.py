import sqlite3
from pathlib import Path

from .db import db_connect
from .paths import SCHEMA_PATH


V2_SCHEMA_SQL = """
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
  args_json TEXT,
  working_directory TEXT,
  environment_json TEXT,
  execution_mode TEXT NOT NULL DEFAULT 'argv',
  timeout_ms INTEGER,
  cooldown_ms INTEGER,
  allow_concurrent INTEGER NOT NULL DEFAULT 0,
  notify_text TEXT NOT NULL DEFAULT '',
  notify_emoji TEXT NOT NULL DEFAULT '',
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
  legacy_binding_id INTEGER REFERENCES bindings(id),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
"""


def init_schema(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='bindings'"
        ).fetchone()
        if row is None:
            raise RuntimeError(f"DB schema initialization failed: {db_path} has no bindings table")
        con.commit()
    finally:
        con.close()


async def apply_migrations() -> None:
    """Apply database migrations if needed."""
    async with db_connect() as db:
        # Check if new columns exist
        cursor = await db.execute("PRAGMA table_info(bindings)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Apply migration 002 if needed
        if "notes" not in column_names:
            await db.execute("ALTER TABLE bindings ADD COLUMN notes TEXT DEFAULT ''")
            await db.execute("ALTER TABLE bindings ADD COLUMN notify_text TEXT DEFAULT ''")
            await db.execute("ALTER TABLE bindings ADD COLUMN notify_emoji TEXT DEFAULT ''")
            await db.commit()

        # Apply migration 003: Add context_labels table
        cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='context_labels'")
        if not await cursor.fetchone():
            await db.execute(
                """
                CREATE TABLE context_labels (
                    context_id INTEGER PRIMARY KEY REFERENCES contexts(id) ON DELETE CASCADE,
                    label TEXT NOT NULL
                )
                """
            )
            await db.commit()

        await db.executescript(V2_SCHEMA_SQL)
        await db.commit()
