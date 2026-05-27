"""Tests for native action types: notification, open_url, open_app, hotkey."""
import asyncio
import os
import shutil


def create_profile_layer_binding(client, action_type="command", **action_fields):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    action = {"type": action_type, "label": "Test", **action_fields}
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={"trigger": {"event_type": "note_on", "note": 60}, "action": action},
    ).json()
    return profile, layer, binding


# ── Schema / CRUD ────────────────────────────────────────────────────────────

def test_create_notification_action(client):
    response = client.post(
        "/api/layers/1/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 61},
            "action": {
                "type": "notification",
                "label": "Scene Start",
                "title": "Recording starting",
                "message": "Scene is live",
                "urgency": "normal",
            },
        },
    )
    assert response.status_code in (200, 404)  # 404 if layer 1 not pre-created


def test_create_notification_via_layer(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 62},
            "action": {
                "type": "notification",
                "label": "Notify step",
                "title": "Hello",
                "message": "World",
                "urgency": "low",
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"]["type"] == "notification"
    assert body["action"]["title"] == "Hello"
    assert body["action"]["message"] == "World"
    assert body["action"]["urgency"] == "low"


def test_create_notification_title_required(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 63},
            "action": {"type": "notification", "label": "No title", "title": "  "},
        },
    )
    assert response.status_code == 400


def test_create_open_url_action(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 64},
            "action": {"type": "open_url", "label": "Open site", "command": "https://example.com"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"]["type"] == "open_url"
    assert body["action"]["command"] == "https://example.com"


def test_create_open_app_action(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 65},
            "action": {"type": "open_app", "label": "Open Firefox", "command": "firefox"},
        },
    )
    assert response.status_code == 200
    assert response.json()["action"]["type"] == "open_app"


def test_create_hotkey_action(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 66},
            "action": {"type": "hotkey", "label": "Terminal", "command": "ctrl+alt+t"},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["action"]["type"] == "hotkey"
    assert body["action"]["command"] == "ctrl+alt+t"


def test_create_open_url_command_required(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 67},
            "action": {"type": "open_url", "label": "No URL", "command": ""},
        },
    )
    assert response.status_code == 400


def test_invalid_urgency_rejected(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 68},
            "action": {"type": "notification", "label": "N", "title": "Hi", "urgency": "extreme"},
        },
    )
    assert response.status_code == 400


# ── Binding action steps (POST /api/bindings/{id}/actions) ───────────────────

def test_add_notification_step_to_binding(client):
    _, _, binding = create_profile_layer_binding(client, command="echo base")
    response = client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={"type": "notification", "title": "Step notify", "message": "hello", "label": "Notify step"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "notification"
    assert body["title"] == "Step notify"


def test_add_hotkey_step_to_binding(client):
    _, _, binding = create_profile_layer_binding(client, command="echo base")
    response = client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={"type": "hotkey", "command": "ctrl+alt+t", "label": "Hotkey"},
    )
    assert response.status_code == 200
    assert response.json()["type"] == "hotkey"


# ── Executor: notification ───────────────────────────────────────────────────

def test_execute_notification_missing_dependency(monkeypatch):
    """If notify-send is not in PATH, returns ok=False with a helpful error."""
    import asyncio
    from backend.actions.executor import execute_notification

    monkeypatch.setenv("PATH", "/tmp/nonexistent_path_xyz")
    import backend.actions.executor as exc_mod
    monkeypatch.setattr(exc_mod, "EXEC_PATH", "/tmp/nonexistent_path_xyz")

    result = asyncio.run(execute_notification("Test", "Body"))
    assert result["ok"] is False
    assert "notify-send" in result["error"]


# ── Executor: hotkey ─────────────────────────────────────────────────────────

def test_execute_hotkey_missing_dependency(monkeypatch):
    """If xdotool is not in PATH, returns ok=False with a helpful error."""
    import asyncio
    from backend.actions.executor import execute_hotkey

    import backend.actions.executor as exc_mod
    monkeypatch.setattr(exc_mod, "EXEC_PATH", "/tmp/nonexistent_path_xyz")

    result = asyncio.run(execute_hotkey("ctrl+alt+t"))
    assert result["ok"] is False
    assert "xdotool" in result["error"]


def test_execute_hotkey_empty_shortcut(monkeypatch):
    """Empty shortcut returns ok=False immediately without calling xdotool."""
    import asyncio
    from backend.actions.executor import execute_hotkey

    result = asyncio.run(execute_hotkey("  "))
    assert result["ok"] is False
    assert "shortcut" in result["error"].lower()


# ── Hotkey normalization ─────────────────────────────────────────────────────

def test_hotkey_modifier_normalization():
    from backend.actions.executor import _normalize_hotkey

    assert _normalize_hotkey("Ctrl+Alt+T") == "ctrl+alt+T"
    assert _normalize_hotkey("Control+Shift+F5") == "ctrl+shift+F5"
    assert _normalize_hotkey("Super+D") == "super+D"
    assert _normalize_hotkey("Win+D") == "super+D"
    assert _normalize_hotkey("ctrl+alt+t") == "ctrl+alt+t"


# ── Test action endpoint ─────────────────────────────────────────────────────

def test_test_action_endpoint_notification(client, monkeypatch):
    """POST /api/actions/{id}/test for notification type returns a summary."""
    _, _, binding = create_profile_layer_binding(
        client,
        action_type="notification",
        title="Test Alert",
        message="test body",
        label="Test notify",
    )
    action_id = binding["action_id"]

    async def fake_notify(title, message="", urgency=None):
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "argv": []}

    import backend.actions.executor as exc_mod
    monkeypatch.setattr(exc_mod, "execute_notification", fake_notify)
    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "execute_notification", fake_notify)

    response = client.post(f"/api/actions/{action_id}/test")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Notify" in body.get("summary", "")


def test_test_action_endpoint_hotkey(client, monkeypatch):
    """POST /api/actions/{id}/test for hotkey type returns a summary."""
    _, _, binding = create_profile_layer_binding(
        client,
        action_type="hotkey",
        command="ctrl+alt+t",
        label="Terminal",
    )
    action_id = binding["action_id"]

    async def fake_hotkey(shortcut):
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "argv": []}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "execute_hotkey", fake_hotkey)

    response = client.post(f"/api/actions/{action_id}/test")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Hotkey" in body.get("summary", "")


# ── Preview endpoint regressions ────────────────────────────────────────────

def test_preview_hotkey_never_executes_as_shell_command(client, monkeypatch):
    """Hotkey preview must call xdotool, not execute ctrl+alt+t as a shell command."""
    shell_calls: list[str] = []

    async def fake_safe_execute(command, timeout_ms=None, execution_mode="argv", working_directory=None):
        shell_calls.append(command)
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "argv": []}

    async def fake_hotkey(shortcut):
        return {"ok": True, "exit_code": 0, "stdout": "ok", "stderr": "", "argv": ["xdotool", "key", shortcut]}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_safe_execute)
    monkeypatch.setattr(actions_mod, "execute_hotkey", fake_hotkey)

    response = client.post(
        "/api/actions/preview/test",
        json={"type": "hotkey", "label": "Terminal", "command": "ctrl+alt+t"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Hotkey" in body.get("summary", "")
    # Must NOT have tried to execute ctrl+alt+t as a shell command
    assert not any("ctrl" in c for c in shell_calls), f"Shell was called with hotkey: {shell_calls}"


def test_preview_notification_never_executes_as_shell_command(client, monkeypatch):
    """Notification preview must call notify-send executor, not run title as a shell command."""
    shell_calls: list[str] = []

    async def fake_safe_execute(command, timeout_ms=None, execution_mode="argv", working_directory=None):
        shell_calls.append(command)
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "argv": []}

    async def fake_notify(title, message="", urgency=None):
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "argv": ["notify-send", title]}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_safe_execute)
    monkeypatch.setattr(actions_mod, "execute_notification", fake_notify)

    response = client.post(
        "/api/actions/preview/test",
        json={"type": "notification", "label": "N", "title": "Recording started", "message": "Scene is live"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Notify" in body.get("summary", "")
    # Must NOT have tried to execute the title as a shell command
    assert not any("Recording" in c for c in shell_calls), f"Shell was called with title: {shell_calls}"


def test_preview_open_url_calls_xdg_open(client, monkeypatch):
    """Open URL preview calls xdg-open via safe_execute_command, not raw shell."""
    xdg_calls: list[str] = []

    async def fake_safe_execute(command, timeout_ms=None, execution_mode="argv", working_directory=None):
        xdg_calls.append(command)
        return {"ok": True, "launched": True, "exit_code": None, "stdout": "", "stderr": "", "argv": []}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_safe_execute)

    response = client.post(
        "/api/actions/preview/test",
        json={"type": "open_url", "label": "Site", "command": "https://example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Open URL" in body.get("summary", "")
    assert any("xdg-open" in c for c in xdg_calls), f"xdg-open not called: {xdg_calls}"


def test_preview_command_type_still_works(client, monkeypatch):
    """Preview endpoint still dispatches plain command type correctly."""
    async def fake_safe_execute(command, timeout_ms=None, execution_mode="argv", working_directory=None):
        return {"ok": True, "exit_code": 0, "stdout": "hi", "stderr": "", "argv": ["echo", "hi"]}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_safe_execute)

    response = client.post(
        "/api/actions/preview/test",
        json={"type": "command", "label": "Echo", "command": "echo hi"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body.get("command") == "echo hi"


def test_preview_hotkey_safe_default_shortcut(client, monkeypatch):
    """ctrl+a (the safe default shortcut) dispatches via hotkey executor, not shell."""
    shell_calls: list[str] = []

    async def fake_safe_execute(command, timeout_ms=None, execution_mode="argv", working_directory=None):
        shell_calls.append(command)
        return {"ok": True, "exit_code": 0, "stdout": "", "stderr": "", "argv": []}

    async def fake_hotkey(shortcut):
        return {"ok": True, "exit_code": 0, "stdout": "ok", "stderr": "", "argv": ["xdotool", "key", shortcut]}

    import backend.api.actions as actions_mod
    monkeypatch.setattr(actions_mod, "safe_execute_command", fake_safe_execute)
    monkeypatch.setattr(actions_mod, "execute_hotkey", fake_hotkey)

    response = client.post(
        "/api/actions/preview/test",
        json={"type": "hotkey", "label": "Hotkey / Shortcut", "command": "ctrl+a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "Hotkey" in body.get("summary", "")
    assert not shell_calls, f"Shell executor was called instead of hotkey executor: {shell_calls}"


def test_dry_run_native_types(client):
    """dry_run for native types returns summary without executing."""
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()

    for action in [
        {"type": "notification", "label": "N", "title": "Hi", "message": "Body"},
        {"type": "open_url", "label": "U", "command": "https://example.com"},
        {"type": "open_app", "label": "A", "command": "firefox"},
        {"type": "hotkey", "label": "K", "command": "ctrl+t"},
    ]:
        note = 70 + list(["notification", "open_url", "open_app", "hotkey"]).index(action["type"])
        binding = client.post(
            f"/api/layers/{layer['id']}/bindings",
            json={"trigger": {"event_type": "note_on", "note": note}, "action": action},
        ).json()
        action_id = binding["action_id"]
        resp = client.post(f"/api/actions/{action_id}/dry_run")
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["would_execute"] is False
        assert body["type"] == action["type"]
