"""Tests for binding clone (trigger remap with sequence copy)."""


def create_profile_layer_binding(client, note=60, command="echo hi"):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": note, "channel": 0},
            "action": {"type": "command", "label": "Cmd", "command": command},
        },
    ).json()
    return profile, layer, binding


def test_clone_binding_to_different_note(client):
    _, layer, binding = create_profile_layer_binding(client, note=60)

    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_note": 62, "target_channel": 0},
    )
    assert response.status_code == 200
    cloned = response.json()

    assert cloned["id"] != binding["id"]
    assert cloned["trigger"]["note"] == 62
    assert cloned["trigger"]["channel"] == 0
    assert cloned["trigger"]["event_type"] == "note_on"
    assert cloned["enabled"] == 0  # clones start disabled


def test_clone_binding_preserves_action_sequence(client):
    _, layer, binding = create_profile_layer_binding(client, note=60, command="echo original")
    # Add extra steps
    client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={"type": "delay", "label": "Wait", "duration_ms": 1000},
    )

    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_note": 65},
    )
    assert response.status_code == 200
    cloned = response.json()

    # Should have cloned action steps
    assert len(cloned["actions"]) >= 1


def test_clone_binding_to_same_layer(client):
    _, layer, binding = create_profile_layer_binding(client, note=60)

    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_note": 64},
    )
    assert response.status_code == 200
    cloned = response.json()
    assert cloned["layer_id"] == binding["layer_id"]


def test_clone_binding_to_different_layer(client):
    profile, _, binding = create_profile_layer_binding(client, note=60)
    other_layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Other Layer"},
    ).json()

    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_note": 66, "target_layer_id": other_layer["id"]},
    )
    assert response.status_code == 200
    cloned = response.json()
    assert cloned["layer_id"] == other_layer["id"]
    assert cloned["trigger"]["note"] == 66


def test_clone_binding_not_found(client):
    response = client.post("/api/bindings/99999/clone", json={"target_note": 60})
    assert response.status_code == 404


def test_clone_cc_binding(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "control_change", "controller": 10, "value_min": 0, "value_max": 127},
            "action": {"type": "command", "label": "CC cmd", "command": "echo cc"},
        },
    ).json()

    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_controller": 20},
    )
    assert response.status_code == 200
    cloned = response.json()
    assert cloned["trigger"]["controller"] == 20
    assert cloned["trigger"]["event_type"] == "control_change"


def test_clone_enabled_flag(client):
    _, _, binding = create_profile_layer_binding(client, note=60)

    # Clone with enabled=1
    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_note": 70, "enabled": 1},
    )
    assert response.status_code == 200
    assert response.json()["enabled"] == 1


def test_clone_preserves_metadata(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 60},
            "action": {"type": "command", "label": "Cmd", "command": "echo hi"},
            "notes": "My notes",
            "display_label": "My Label",
            "display_color": "#ff0000",
        },
    ).json()

    response = client.post(
        f"/api/bindings/{binding['id']}/clone",
        json={"target_note": 72},
    )
    assert response.status_code == 200
    cloned = response.json()
    assert cloned["notes"] == "My notes"
    assert cloned["display_label"] == "My Label"
    assert cloned["display_color"] == "#ff0000"
