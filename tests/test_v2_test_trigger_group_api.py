"""Regression tests for POST /api/bindings/{binding_id}/test-trigger-group.

The endpoint must execute all steps in a trigger group as one ordered sequence,
honoring delay steps so that later steps (e.g. open_url) do not fire immediately.
"""
import asyncio
import sqlite3
import time


def seed_trigger_group(db_path, *, delay_ms=50):
    """Seed a three-step trigger group: echo → delay → open_url on note 48 ch 1.

    Uses Default Profile (id=1) and Default Layer (id=1) created by startup bootstrap.
    """
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        # Default Profile (id=1) and Default Layer (id=1) already exist from bootstrap.
        con.execute(
            "INSERT INTO triggers(id, event_type, channel, note) VALUES (3, 'note_on', 1, 48)"
        )

        # Three separate actions
        con.execute("INSERT INTO actions(id, type, label, command, execution_mode) VALUES (10, 'command', 'Echo', 'echo hello', 'argv')")
        con.execute(f"INSERT INTO actions(id, type, label, duration_ms, execution_mode) VALUES (11, 'delay', 'Wait', {delay_ms}, 'argv')")
        con.execute("INSERT INTO actions(id, type, label, command, execution_mode) VALUES (12, 'open_url', 'Firefox', 'https://example.com', 'argv')")

        # Three bindings on the same trigger — one action each, in Default Profile/Layer
        con.execute("INSERT INTO bindings_v2(id, profile_id, layer_id, trigger_id, action_id, enabled, require_armed) VALUES (20, 1, 1, 3, 10, 1, 0)")
        con.execute("INSERT INTO bindings_v2(id, profile_id, layer_id, trigger_id, action_id, enabled, require_armed) VALUES (21, 1, 1, 3, 11, 1, 0)")
        con.execute("INSERT INTO bindings_v2(id, profile_id, layer_id, trigger_id, action_id, enabled, require_armed) VALUES (22, 1, 1, 3, 12, 1, 0)")

        # binding_actions: execution_order assigned group-wide (0, 1, 2)
        con.execute("INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled) VALUES (20, 10, 0, 1)")
        con.execute("INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled) VALUES (21, 11, 1, 1)")
        con.execute("INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled) VALUES (22, 12, 2, 1)")
        con.commit()


def test_trigger_group_executes_steps_in_order(client, app_module, monkeypatch):
    """All steps run once, in order: echo → delay → open_url."""
    seed_trigger_group(app_module.DB_PATH, delay_ms=50)

    call_log = []

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        call_log.append(command)
        return {"ok": True, "stdout": "", "stderr": "", "exit_code": 0}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_execute)

    resp = client.post("/api/bindings/20/test-trigger-group")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["steps"]) == 3
    # Step order: echo, delay (no execute call), open_url
    assert any("echo" in c for c in call_log), "echo step did not run"
    assert any("xdg-open" in c for c in call_log), "open_url step did not run"
    assert call_log.index(next(c for c in call_log if "echo" in c)) < call_log.index(
        next(c for c in call_log if "xdg-open" in c)
    ), "open_url ran before echo"


def test_trigger_group_open_url_fires_after_delay(client, app_module, monkeypatch):
    """open_url must not fire until after the delay step has elapsed."""
    delay_ms = 80
    seed_trigger_group(app_module.DB_PATH, delay_ms=delay_ms)

    timestamps: dict[str, float] = {}

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        if "xdg-open" in command:
            timestamps["url"] = time.monotonic()
        else:
            timestamps["echo"] = time.monotonic()
        return {"ok": True, "stdout": "", "stderr": "", "exit_code": 0}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_execute)

    resp = client.post("/api/bindings/20/test-trigger-group")
    assert resp.status_code == 200

    assert "echo" in timestamps and "url" in timestamps
    elapsed_ms = (timestamps["url"] - timestamps["echo"]) * 1000
    assert elapsed_ms >= delay_ms * 0.8, (
        f"open_url fired too early: {elapsed_ms:.1f}ms after echo, expected >= {delay_ms * 0.8:.0f}ms"
    )


def test_trigger_group_all_steps_share_session_id(client, app_module, monkeypatch):
    """All steps in one trigger group fire must share a single session_id in the run log."""
    seed_trigger_group(app_module.DB_PATH, delay_ms=0)

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        return {"ok": True, "stdout": "", "stderr": "", "exit_code": 0}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_execute)

    resp = client.post("/api/bindings/20/test-trigger-group")
    assert resp.status_code == 200
    data = resp.json()

    session_id = data.get("session_id")
    assert session_id, "Response must include a session_id"

    # Verify all runs recorded in the DB share that session_id
    with sqlite3.connect(app_module.DB_PATH) as con:
        rows = con.execute("SELECT session_id FROM runs ORDER BY id").fetchall()
    assert len(rows) == 3
    assert all(row[0] == session_id for row in rows), (
        f"Not all runs share session_id {session_id!r}: {[r[0] for r in rows]}"
    )


def test_trigger_group_returns_404_for_unknown_binding(client, app_module):
    """Requesting a non-existent binding returns 404."""
    resp = client.post("/api/bindings/9999/test-trigger-group")
    assert resp.status_code == 404
