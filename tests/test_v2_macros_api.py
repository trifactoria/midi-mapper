"""Tests for macro/template CRUD and apply APIs."""


def create_profile_layer_binding_with_steps(client):
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 60},
            "action": {"type": "command", "label": "Step 1", "command": "echo step1"},
        },
    ).json()
    # Add a second step
    client.post(
        f"/api/bindings/{binding['id']}/actions",
        json={"type": "delay", "label": "Wait", "duration_ms": 500},
    )
    return profile, layer, binding


def test_list_macros_empty(client):
    response = client.get("/api/macros")
    assert response.status_code == 200
    assert response.json() == []


def test_create_macro_from_binding(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)

    response = client.post(
        "/api/macros",
        json={"name": "My Macro", "description": "A test macro", "binding_id": binding["id"]},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "My Macro"
    assert body["description"] == "A test macro"
    assert body["step_count"] >= 1
    assert body["id"] >= 1


def test_create_macro_name_required(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)

    response = client.post(
        "/api/macros",
        json={"name": "  ", "binding_id": binding["id"]},
    )
    assert response.status_code == 400


def test_create_macro_no_steps_fails(client):
    """Creating macro from a binding with no binding_actions should fail."""
    profile = client.post("/api/profiles", json={"name": "P"}).json()
    layer = client.post(f"/api/profiles/{profile['id']}/layers", json={"name": "L"}).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 61},
            "action": {"type": "command", "label": "X", "command": "echo x"},
        },
    ).json()
    # Remove all binding_actions so step list is empty
    steps = client.get(f"/api/layers/{layer['id']}/bindings").json()[0]["actions"]
    for step in steps:
        client.delete(f"/api/bindings/{binding['id']}/actions/{step['binding_action_id']}")

    response = client.post(
        "/api/macros",
        json={"name": "Empty", "binding_id": binding["id"]},
    )
    assert response.status_code == 400


def test_list_macros_after_create(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)
    client.post("/api/macros", json={"name": "M1", "binding_id": binding["id"]})
    client.post("/api/macros", json={"name": "M2", "binding_id": binding["id"]})

    response = client.get("/api/macros")
    assert response.status_code == 200
    names = [m["name"] for m in response.json()]
    assert "M1" in names
    assert "M2" in names


def test_delete_macro(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)
    macro = client.post("/api/macros", json={"name": "Del", "binding_id": binding["id"]}).json()

    response = client.delete(f"/api/macros/{macro['id']}")
    assert response.status_code == 200
    assert response.json()["ok"] is True

    assert client.get("/api/macros").json() == []


def test_delete_macro_not_found(client):
    response = client.delete("/api/macros/9999")
    assert response.status_code == 404


def test_apply_macro_appends_steps(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)
    macro = client.post("/api/macros", json={"name": "OBS", "binding_id": binding["id"]}).json()

    # Create target binding with no extra steps
    profile2 = client.post("/api/profiles", json={"name": "P2"}).json()
    layer2 = client.post(f"/api/profiles/{profile2['id']}/layers", json={"name": "L2"}).json()
    target_binding = client.post(
        f"/api/layers/{layer2['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 62},
            "action": {"type": "command", "label": "Base", "command": "echo base"},
        },
    ).json()

    response = client.post(
        f"/api/macros/{macro['id']}/apply",
        json={"binding_id": target_binding["id"], "replace_existing": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["action_count"] >= 1


def test_apply_macro_replace_existing(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)
    macro = client.post("/api/macros", json={"name": "Replace", "binding_id": binding["id"]}).json()

    profile2 = client.post("/api/profiles", json={"name": "P2"}).json()
    layer2 = client.post(f"/api/profiles/{profile2['id']}/layers", json={"name": "L2"}).json()
    target_binding = client.post(
        f"/api/layers/{layer2['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 63},
            "action": {"type": "command", "label": "X", "command": "echo x"},
        },
    ).json()

    response = client.post(
        f"/api/macros/{macro['id']}/apply",
        json={"binding_id": target_binding["id"], "replace_existing": True},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_apply_macro_invalid_binding(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)
    macro = client.post("/api/macros", json={"name": "M", "binding_id": binding["id"]}).json()

    response = client.post(
        f"/api/macros/{macro['id']}/apply",
        json={"binding_id": 99999},
    )
    assert response.status_code == 404


def test_apply_macro_invalid_macro(client):
    _, _, binding = create_profile_layer_binding_with_steps(client)

    response = client.post(
        "/api/macros/99999/apply",
        json={"binding_id": binding["id"]},
    )
    assert response.status_code == 404
