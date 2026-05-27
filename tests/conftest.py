import importlib
import asyncio
import sys
from pathlib import Path

import httpx
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
        "backend.api.v2_bindings",
        "backend.api.settings",
        "backend.api.runs",
        "backend.api.profiles",
        "backend.api.ports",
        "backend.api.midi",
        "backend.api.layers",
        "backend.api.health",
        "backend.api.devices",
        "backend.api.contexts",
        "backend.api.bindings",
        "backend.api.actions",
        "backend.services",
        "backend.schemas",
        "backend.runtime",
        "backend.ws",
        "backend.midi.matcher",
        "backend.midi.normalize",
        "backend.midi.state",
        "backend.midi.status",
        "backend.midi.listener",
        "backend.actions.history",
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
        for attr in (
            "actions",
            "bindings",
            "contexts",
            "devices",
            "health",
            "layers",
            "midi",
            "ports",
            "profiles",
            "runs",
            "settings",
            "v2_bindings",
            "websocket",
        ):
            if hasattr(api_pkg, attr):
                delattr(api_pkg, attr)
    midi_pkg = sys.modules.get("backend.midi")
    if midi_pkg is not None:
        for attr in ("listener", "matcher", "normalize", "state", "status"):
            if hasattr(midi_pkg, attr):
                delattr(midi_pkg, attr)
    actions_pkg = sys.modules.get("backend.actions")
    if actions_pkg is not None:
        for attr in ("executor", "history", "notifications"):
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


class LocalASGIClient:
    def __init__(self, app):
        self.app = app

    def request(self, method: str, url: str, **kwargs):
        async def run_request():
            transport = httpx.ASGITransport(app=self.app)
            async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
                response = await async_client.request(method, url, **kwargs)
                await response.aread()
                return response

        return asyncio.run(run_request())

    def get(self, url: str, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self.request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self.request("PATCH", url, **kwargs)

    def put(self, url: str, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self.request("DELETE", url, **kwargs)


@pytest.fixture
def client(app_module, monkeypatch):
    async def idle_midi_pump():
        await asyncio.Event().wait()

    monkeypatch.setattr(app_module, "midi_pump", idle_midi_pump)

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(app_module._startup())
        yield LocalASGIClient(app_module.app)
    finally:
        loop.run_until_complete(app_module._shutdown())
        loop.close()
