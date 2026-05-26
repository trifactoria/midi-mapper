import asyncio
import importlib
import sqlite3
import sys

import pytest


LEGACY_SCHEMA_SQL = """
PRAGMA foreign_keys=ON;

CREATE TABLE ports (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE NOT NULL
);

CREATE TABLE contexts (
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

CREATE TABLE bindings (
  id INTEGER PRIMARY KEY,
  context_id INTEGER NOT NULL REFERENCES contexts(id) ON DELETE CASCADE,
  enabled INTEGER NOT NULL DEFAULT 1,
  trig_type INTEGER NOT NULL,
  note INTEGER,
  cc INTEGER,
  value_min INTEGER,
  value_max INTEGER,
  pitch_min INTEGER,
  pitch_max INTEGER,
  command TEXT NOT NULL,
  debounce_ms INTEGER NOT NULL DEFAULT 200,
  require_armed INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""

LEGACY_TABLES = {"ports", "contexts", "bindings", "settings", "context_labels"}
V2_TABLES = {
    "devices",
    "profiles",
    "layers",
    "triggers",
    "actions",
    "bindings_v2",
    "runs",
    "legacy_context_migrations",
    "legacy_binding_migrations",
}


def table_names(db_path):
    with sqlite3.connect(db_path) as con:
        return {
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }


def reset_backend_modules():
    for module_name in ("app", "backend.main", "backend.migrations", "backend.db", "backend.config"):
        sys.modules.pop(module_name, None)
    backend_pkg = sys.modules.get("backend")
    if backend_pkg is not None:
        for attr in ("main", "migrations", "db", "config"):
            if hasattr(backend_pkg, attr):
                delattr(backend_pkg, attr)


async def run_migrations(db_path, monkeypatch):
    monkeypatch.setenv("MIDI_MAPPER_DB_PATH", str(db_path))
    reset_backend_modules()
    migrations = importlib.import_module("backend.migrations")
    await migrations.apply_migrations()


def test_empty_db_initializes_legacy_and_v2_tables(tmp_path, monkeypatch):
    pytest.importorskip("aiosqlite")
    from backend.migrations import init_schema

    db_path = tmp_path / "fresh.db"
    init_schema(db_path)
    asyncio.run(run_migrations(db_path, monkeypatch))

    tables = table_names(db_path)
    assert LEGACY_TABLES <= tables
    assert V2_TABLES <= tables


def test_existing_legacy_db_gains_v2_tables_without_losing_legacy_data(tmp_path, monkeypatch):
    pytest.importorskip("aiosqlite")

    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as con:
        con.executescript(LEGACY_SCHEMA_SQL)
        con.execute("INSERT INTO ports(id, name) VALUES (1, 'Legacy MIDI')")
        con.execute(
            """
            INSERT INTO contexts(id, daw_slot, preset_slot, port_id, channel, bank_msb, bank_lsb, program)
            VALUES (10, 0, 0, 1, 2, 3, 4, 5)
            """
        )
        con.execute(
            """
            INSERT INTO bindings(id, context_id, enabled, trig_type, note, command)
            VALUES (20, 10, 1, 1, 60, 'echo legacy')
            """
        )
        con.execute("INSERT INTO settings(key, value) VALUES ('armed', '0')")
        con.commit()

    asyncio.run(run_migrations(db_path, monkeypatch))

    tables = table_names(db_path)
    assert LEGACY_TABLES <= tables
    assert V2_TABLES <= tables

    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT name FROM ports WHERE id=1").fetchone()[0] == "Legacy MIDI"
        assert con.execute("SELECT command FROM bindings WHERE id=20").fetchone()[0] == "echo legacy"
        binding_cols = {row[1] for row in con.execute("PRAGMA table_info(bindings)")}
        assert {"notes", "notify_text", "notify_emoji"} <= binding_cols


def test_apply_migrations_is_idempotent(tmp_path, monkeypatch):
    pytest.importorskip("aiosqlite")

    db_path = tmp_path / "idempotent.db"
    with sqlite3.connect(db_path) as con:
        con.executescript(LEGACY_SCHEMA_SQL)
        con.execute("INSERT INTO ports(id, name) VALUES (1, 'Legacy MIDI')")
        con.execute(
            """
            INSERT INTO contexts(id, daw_slot, preset_slot, port_id, channel, bank_msb, bank_lsb, program)
            VALUES (10, 0, 0, 1, 2, 3, 4, 5)
            """
        )
        con.execute(
            """
            INSERT INTO bindings(id, context_id, enabled, trig_type, note, command)
            VALUES (20, 10, 1, 1, 60, 'echo legacy')
            """
        )
        con.commit()

    asyncio.run(run_migrations(db_path, monkeypatch))
    before = table_names(db_path)
    asyncio.run(run_migrations(db_path, monkeypatch))
    after = table_names(db_path)

    assert before == after
    assert LEGACY_TABLES <= after
    assert V2_TABLES <= after

    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT COUNT(*) FROM bindings").fetchone()[0] == 1
