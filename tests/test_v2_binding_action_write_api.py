import sqlite3


def assert_dict_contains(actual, expected):
    assert expected.items() <= actual.items()


def create_profile_layer(client):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Layer"},
    ).json()
    return profile, layer


def create_note_binding(client, layer_id, **overrides):
    payload = {
        "trigger": {
            "event_type": "note_on",
            "channel": 1,
            "note": 60,
            "velocity_min": 64,
            "velocity_max": 127,
            "port_name": "MIDI Keyboard",
        },
        "action": {
            "type": "command",
            "label": "Open editor",
            "command": "echo editor",
            "execution_mode": "argv",
            "timeout_ms": 1000,
            "notify_text": "Opened",
            "notify_emoji": "*",
        },
        "enabled": 1,
        "require_armed": 1,
        "cooldown_ms": 250,
        "notes": "Middle C",
        "display_label": "Editor",
        "display_color": "#336699",
        "display_emoji": "*",
    }
    payload.update(overrides)
    return client.post(f"/api/layers/{layer_id}/bindings", json=payload)


def test_create_note_binding_with_command_action(client):
    _, layer = create_profile_layer(client)

    response = create_note_binding(client, layer["id"])
    assert response.status_code == 200
    binding = response.json()

    assert_dict_contains(binding, {
        "layer_id": layer["id"],
        "enabled": 1,
        "require_armed": 1,
        "cooldown_ms": 250,
        "notes": "Middle C",
        "display_label": "Editor",
        "display_color": "#336699",
        "display_emoji": "*",
    })
    assert_dict_contains(binding["trigger"], {
        "event_type": "note_on",
        "channel": 1,
        "note": 60,
        "velocity_min": 64,
        "velocity_max": 127,
        "port_name": "MIDI Keyboard",
    })
    assert_dict_contains(binding["action"], {
        "type": "command",
        "label": "Open editor",
        "command": "echo editor",
        "execution_mode": "argv",
        "timeout_ms": 1000,
        "cooldown_ms": 250,
        "notify_text": "Opened",
        "notify_emoji": "*",
    })


def test_create_cc_fader_binding_with_value_threshold_range(client, app_module):
    _, layer = create_profile_layer(client)
    with sqlite3.connect(app_module.DB_PATH) as con:
        con.execute(
            "INSERT INTO devices(id, name, port_name) VALUES (3, 'Fader Box', 'Fader Box')"
        )
        con.commit()

    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {
                "event_type": "control_change",
                "channel": 2,
                "controller": 74,
                "value_min": 32,
                "value_max": 96,
                "device_id": 3,
            },
            "action": {
                "type": "command",
                "label": "Filter",
                "command": "echo filter",
            },
        },
    )

    assert response.status_code == 200
    binding = response.json()
    assert_dict_contains(binding["trigger"], {
        "event_type": "control_change",
        "channel": 2,
        "controller": 74,
        "value_min": 32,
        "value_max": 96,
        "device_id": 3,
    })


def test_create_velocity_threshold_note_binding(client):
    _, layer = create_profile_layer(client)

    response = create_note_binding(
        client,
        layer["id"],
        trigger={
            "event_type": "note_on",
            "note": 36,
            "velocity_min": 100,
            "velocity_max": 127,
        },
        action={
            "type": "command",
            "label": "Accent",
            "command": "echo accent",
        },
    )

    assert response.status_code == 200
    assert_dict_contains(response.json()["trigger"], {
        "event_type": "note_on",
        "note": 36,
        "velocity_min": 100,
        "velocity_max": 127,
    })


def test_patch_binding_action_and_trigger(client):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    response = client.patch(
        f"/api/bindings/{binding['id']}",
        json={
            "trigger": {
                "event_type": "control_change",
                "controller": 10,
                "value_min": 12,
                "value_max": 100,
            },
            "action": {
                "label": "Updated",
                "command": "echo updated",
                "timeout_ms": 500,
                "notify_text": "Updated",
            },
            "enabled": 0,
            "require_armed": 0,
            "cooldown_ms": 300,
            "notes": "Updated note",
            "display_label": "Updated display",
        },
    )

    assert response.status_code == 200
    updated = response.json()
    assert_dict_contains(updated, {
        "enabled": 0,
        "require_armed": 0,
        "cooldown_ms": 300,
        "notes": "Updated note",
        "display_label": "Updated display",
    })
    assert_dict_contains(updated["trigger"], {
        "event_type": "control_change",
        "controller": 10,
        "value_min": 12,
        "value_max": 100,
    })
    assert_dict_contains(updated["action"], {
        "label": "Updated",
        "command": "echo updated",
        "timeout_ms": 500,
        "notify_text": "Updated",
    })


def test_delete_binding_removes_related_trigger_and_action_when_safe(client, app_module):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    response = client.delete(f"/api/bindings/{binding['id']}")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "deleted_binding_id": binding["id"],
        "deleted_trigger_id": binding["trigger_id"],
        "deleted_action_id": binding["action_id"],
    }
    assert client.get(f"/api/layers/{layer['id']}/bindings").json() == []
    with sqlite3.connect(app_module.DB_PATH) as con:
        assert con.execute("SELECT COUNT(*) FROM triggers").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0


def test_dry_run_does_not_execute(client, monkeypatch):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    async def fail_if_called(command):
        raise AssertionError(f"unexpected execute: {command}")

    import backend.api.actions as actions_api

    monkeypatch.setattr(actions_api, "safe_execute_command", fail_if_called)
    response = client.post(f"/api/actions/{binding['action_id']}/dry_run")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "action_id": binding["action_id"],
        "type": "command",
        "label": "Open editor",
        "command": "echo editor",
        "execution_mode": "argv",
        "summary": "echo editor",
        "would_execute": False,
    }


def test_action_test_uses_existing_safe_executor(client, monkeypatch):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()
    calls = []

    async def fake_execute(command):
        calls.append(command)
        return {"ok": True, "pid": 123, "argv": ["echo", "editor"]}

    import backend.api.actions as actions_api

    monkeypatch.setattr(actions_api, "safe_execute_command", fake_execute)
    response = client.post(f"/api/actions/{binding['action_id']}/test")

    assert response.status_code == 200
    assert calls == ["echo editor"]
    assert_dict_contains(response.json(), {
        "ok": True,
        "pid": 123,
        "action_id": binding["action_id"],
        "command": "echo editor",
    })


def test_unsupported_action_type_is_rejected(client, app_module):
    _, layer = create_profile_layer(client)

    response = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 60},
            "action": {"type": "python", "command": "print('no')"},
        },
    )

    assert response.status_code == 400
    with sqlite3.connect(app_module.DB_PATH) as con:
        assert con.execute("SELECT COUNT(*) FROM bindings_v2").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 0
        assert con.execute("SELECT COUNT(*) FROM triggers").fetchone()[0] == 0
