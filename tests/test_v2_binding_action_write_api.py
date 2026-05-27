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


def test_delete_binding_with_run_history_succeeds_and_preserves_runs(client, app_module):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    with sqlite3.connect(app_module.DB_PATH) as con:
        con.execute("PRAGMA foreign_keys=ON")
        # Run references binding only (no action_id) — action can still be cleaned up.
        con.execute(
            "INSERT INTO runs(binding_id, action_summary, status, started_at) VALUES (?, ?, ?, ?)",
            (binding["id"], "echo editor", "success", "2024-01-01T00:00:00+00:00"),
        )
        con.commit()

    response = client.delete(f"/api/bindings/{binding['id']}")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["deleted_binding_id"] == binding["id"]
    assert client.get(f"/api/layers/{layer['id']}/bindings").json() == []
    with sqlite3.connect(app_module.DB_PATH) as con:
        row = con.execute("SELECT binding_id, action_summary FROM runs").fetchone()
        assert row is not None, "run row should be preserved"
        assert row[0] is None, "binding_id should be NULLed after binding deletion"
        assert row[1] == "echo editor"


def test_delete_binding_with_action_referenced_by_runs_does_not_crash(client, app_module):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    with sqlite3.connect(app_module.DB_PATH) as con:
        con.execute("PRAGMA foreign_keys=ON")
        # Run references both binding_id AND action_id — action must not be deleted.
        con.execute(
            "INSERT INTO runs(binding_id, action_id, action_summary, status, started_at) VALUES (?, ?, ?, ?, ?)",
            (binding["id"], binding["action_id"], "echo editor", "success", "2024-01-01T00:00:00+00:00"),
        )
        con.commit()

    response = client.delete(f"/api/bindings/{binding['id']}")

    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    assert result["deleted_binding_id"] == binding["id"]
    # Action must be preserved because a run still references it.
    assert result["deleted_action_id"] is None
    assert client.get(f"/api/layers/{layer['id']}/bindings").json() == []
    with sqlite3.connect(app_module.DB_PATH) as con:
        # Run row survives with its action_id intact.
        row = con.execute("SELECT binding_id, action_id FROM runs").fetchone()
        assert row is not None
        assert row[0] is None, "binding_id nulled"
        assert row[1] == binding["action_id"], "action_id preserved"
        # Action row still exists.
        count = con.execute("SELECT COUNT(*) FROM actions WHERE id = ?", (binding["action_id"],)).fetchone()[0]
        assert count == 1, "action row should survive when run references it"


def test_delete_nonexistent_binding_returns_404(client):
    response = client.delete("/api/bindings/99999")
    assert response.status_code == 404


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

    async def fake_execute(command, timeout_ms=None, execution_mode="argv"):
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


def test_add_delay_step_and_reorder_persists(client):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    delay = client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={"type": "delay", "label": "Pause", "duration_ms": 3000},
    ).json()

    steps = client.get(f"/api/bindings/{binding['id']}/actions").json()
    assert [step["type"] for step in steps] == ["command", "delay"]
    assert steps[1]["duration_ms"] == 3000

    response = client.post(
        f"/api/bindings/{binding['id']}/actions/reorder",
        json=[delay["binding_action_id"], steps[0]["binding_action_id"]],
    )

    assert response.status_code == 200
    reordered = client.get(f"/api/bindings/{binding['id']}/actions").json()
    assert [step["type"] for step in reordered] == ["delay", "command"]
    assert [step["execution_order"] for step in reordered] == [0, 1]


def test_add_edit_delete_command_and_delay_steps(client):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()

    command = client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={
            "type": "command",
            "label": "Browser",
            "command": "firefox https://skillkraftz.com",
            "working_directory": "/tmp",
            "execution_mode": "detached",
            "timeout_ms": 2000,
        },
    ).json()
    updated_command = client.patch(
        f"/api/bindings/{binding['id']}/actions/{command['binding_action_id']}",
        json={"command": "firefox https://example.com", "label": "Example"},
    ).json()
    assert updated_command["command"] == "firefox https://example.com"
    assert updated_command["label"] == "Example"

    delay = client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={"type": "delay", "duration_ms": 1000},
    ).json()
    updated_delay = client.patch(
        f"/api/bindings/{binding['id']}/actions/{delay['binding_action_id']}",
        json={"duration_ms": 2500},
    ).json()
    assert updated_delay["duration_ms"] == 2500

    response = client.delete(f"/api/bindings/{binding['id']}/actions/{delay['binding_action_id']}")
    assert response.status_code == 200
    assert all(step["binding_action_id"] != delay["binding_action_id"] for step in client.get(f"/api/bindings/{binding['id']}/actions").json())


def test_reorder_across_same_trigger_bindings_persists(client):
    _, layer = create_profile_layer(client)
    first = create_note_binding(client, layer["id"], action={"type": "command", "label": "First", "command": "echo first"}).json()
    second = create_note_binding(client, layer["id"], action={"type": "command", "label": "Second", "command": "echo second"}).json()
    first_step = client.get(f"/api/bindings/{first['id']}/actions").json()[0]
    second_step = client.get(f"/api/bindings/{second['id']}/actions").json()[0]

    response = client.post(
        "/api/action-groups/reorder",
        json=[second_step["binding_action_id"], first_step["binding_action_id"]],
    )

    assert response.status_code == 200
    assert client.get(f"/api/bindings/{second['id']}/actions").json()[0]["execution_order"] == 0
    assert client.get(f"/api/bindings/{first['id']}/actions").json()[0]["execution_order"] == 1


def test_toggle_action_step_persists(client):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()
    step = client.get(f"/api/bindings/{binding['id']}/actions").json()[0]

    response = client.patch(
        f"/api/bindings/{binding['id']}/actions/{step['binding_action_id']}",
        json={"enabled": 0},
    )

    assert response.status_code == 200
    assert client.get(f"/api/bindings/{binding['id']}/actions").json()[0]["enabled"] == 0


def test_delete_last_step_leaves_empty_sequence(client):
    _, layer = create_profile_layer(client)
    binding = create_note_binding(client, layer["id"]).json()
    step = client.get(f"/api/bindings/{binding['id']}/actions").json()[0]

    response = client.delete(f"/api/bindings/{binding['id']}/actions/{step['binding_action_id']}")

    assert response.status_code == 200
    assert client.get(f"/api/layers/{layer['id']}/bindings").json()[0]["actions"] == []


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
