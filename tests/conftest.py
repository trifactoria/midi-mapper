import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_SQL = ROOT / "schema.sql"


def init_test_db(path: Path) -> None:
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
        con.commit()
    finally:
        con.close()


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    db_path = tmp_path / "midi_mapper_test.db"
    init_test_db(db_path)

    monkeypatch.setenv("MIDI_MAPPER_DB_PATH", str(db_path))
    monkeypatch.setenv("MIDI_MAPPER_EXEC_USE_SHELL", "false")
    monkeypatch.setenv("MIDI_MAPPER_EXEC_PATH", "$PATH")
    monkeypatch.setenv("MIDI_MAPPER_WS_POLL_INTERVAL", "0.01")

    sys.modules.pop("app", None)
    module = importlib.import_module("app")

    monkeypatch.setattr(module.mido, "get_input_names", lambda: ["Test MIDI In"])
    monkeypatch.setattr(module.mido, "get_output_names", lambda: ["Test MIDI Out"])

    module.CHAN_STATE.clear()
    module.PORT_STATE.clear()
    module.OUTPUT_PORT_CACHE.clear()
    module.LAST_NOTE_CHANNEL.clear()
    module.LAST_FIRED.clear()
    module.ACTIVE_SELECTION.update(
        {
            "port_id": None,
            "port_name": None,
            "channel": 0,
            "bank_msb": 0,
            "bank_lsb": 0,
            "program": 0,
        }
    )

    return module


@pytest.fixture
def client(app_module):
    from fastapi.testclient import TestClient

    with TestClient(app_module.app) as test_client:
        yield test_client
