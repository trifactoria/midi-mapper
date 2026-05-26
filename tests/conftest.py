import importlib
import sys
from pathlib import Path

import pytest


def init_test_db(path: Path) -> None:
    from backend.migrations import init_schema

    init_schema(path)


class FakeMidiInput:
    name = "Test MIDI In"

    def iter_pending(self):
        return []

    def close(self):
        pass


@pytest.fixture
def app_module(tmp_path, monkeypatch):
    pytest.importorskip("aiosqlite")
    pytest.importorskip("dotenv")
    pytest.importorskip("fastapi")
    pytest.importorskip("mido")

    db_path = tmp_path / "midi_mapper_test.db"
    init_test_db(db_path)

    monkeypatch.setenv("MIDI_MAPPER_DB_PATH", str(db_path))
    monkeypatch.setenv("MIDI_MAPPER_EXEC_USE_SHELL", "false")
    monkeypatch.setenv("MIDI_MAPPER_EXEC_PATH", "$PATH")
    monkeypatch.setenv("MIDI_MAPPER_WS_POLL_INTERVAL", "0.01")

    for module_name in (
        "app",
        "backend.main",
        "backend.api.websocket",
        "backend.api.settings",
        "backend.api.ports",
        "backend.api.midi",
        "backend.api.health",
        "backend.api.contexts",
        "backend.api.bindings",
        "backend.services",
        "backend.schemas",
        "backend.runtime",
        "backend.ws",
        "backend.midi.matcher",
        "backend.midi.normalize",
        "backend.midi.state",
        "backend.actions.notifications",
        "backend.actions.executor",
        "backend.migrations",
        "backend.db",
        "backend.config",
    ):
        sys.modules.pop(module_name, None)
    backend_pkg = sys.modules.get("backend")
    if backend_pkg is not None:
        for attr in ("main", "migrations", "db", "config", "midi", "api", "services", "schemas", "runtime", "ws"):
            if hasattr(backend_pkg, attr):
                delattr(backend_pkg, attr)
    api_pkg = sys.modules.get("backend.api")
    if api_pkg is not None:
        for attr in ("bindings", "contexts", "health", "midi", "ports", "settings", "websocket"):
            if hasattr(api_pkg, attr):
                delattr(api_pkg, attr)
    midi_pkg = sys.modules.get("backend.midi")
    if midi_pkg is not None:
        for attr in ("matcher", "normalize", "state"):
            if hasattr(midi_pkg, attr):
                delattr(midi_pkg, attr)
    actions_pkg = sys.modules.get("backend.actions")
    if actions_pkg is not None:
        for attr in ("executor", "notifications"):
            if hasattr(actions_pkg, attr):
                delattr(actions_pkg, attr)
    module = importlib.import_module("app")

    monkeypatch.setattr(module.mido, "get_input_names", lambda: ["Test MIDI In"])
    monkeypatch.setattr(module.mido, "get_output_names", lambda: ["Test MIDI Out"])
    monkeypatch.setattr(module.mido, "open_input", lambda name: FakeMidiInput())

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
