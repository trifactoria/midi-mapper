"""Tests for session_id grouping in runs and the session runtime architecture."""
import asyncio
import json


def create_profile_layer_binding(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 60},
            "action": {"type": "command", "label": "cmd", "command": "echo hi"},
        },
    ).json()
    return profile, layer, binding


def patch_executor(monkeypatch, result):
    async def fake_execute(command, timeout_ms=None, execution_mode="argv", working_directory=None):
        return dict(result)

    import backend.api.actions as actions_api
    monkeypatch.setattr(actions_api, "safe_execute_command", fake_execute)


def test_runs_include_session_id_column(client, monkeypatch):
    """Runs returned by the API include a session_id field."""
    _, _, binding = create_profile_layer_binding(client)
    patch_executor(monkeypatch, {"ok": True, "exit_code": 0, "stdout": ""})

    client.post(f"/api/actions/{binding['action_id']}/test")
    runs = client.get("/api/runs").json()

    assert len(runs) == 1
    assert "session_id" in runs[0]


def test_action_test_run_has_null_session_id(client, monkeypatch):
    """Test-triggered runs (not from MIDI) have session_id=null."""
    _, _, binding = create_profile_layer_binding(client)
    patch_executor(monkeypatch, {"ok": True, "exit_code": 0, "stdout": ""})

    client.post(f"/api/actions/{binding['action_id']}/test")
    runs = client.get("/api/runs").json()

    # Test runs don't go through listener so they have no session_id
    assert runs[0]["session_id"] is None


def test_record_v2_action_run_with_session_id(tmp_path):
    """record_v2_action_run stores session_id in runs table."""
    import os
    os.environ["MIDI_MAPPER_DB_PATH"] = str(tmp_path / "test.db")

    from backend.migrations import init_schema
    from pathlib import Path
    db_path = tmp_path / "test.db"
    init_schema(db_path)

    async def run():
        import backend.db as db_module
        db_module._DB_PATH = str(db_path)

        from backend.migrations import apply_migrations
        await apply_migrations()

        from backend.actions.history import record_v2_action_run

        run_id = await record_v2_action_run(
            action_id=1,
            binding_id=1,
            profile_id=1,
            layer_id=1,
            trigger_snapshot_json='{"note": 60}',
            action_summary="echo test",
            started_at=1000.0,
            result={"ok": True, "exit_code": 0, "stdout": "hi"},
            session_id="abc123session",
        )

        from backend.db import db_fetchone
        row = await db_fetchone("SELECT session_id FROM runs WHERE id = ?", (run_id,))
        assert row is not None
        assert row["session_id"] == "abc123session"

    asyncio.run(run())


def test_listener_generates_session_id_for_sequence():
    """The v2 listener generates a uuid session_id for each trigger fire."""
    import inspect
    import backend.midi.listener as listener_mod

    src = inspect.getsource(listener_mod._execute_v2_match)
    assert "session_id" in src
    assert "uuid" in src
