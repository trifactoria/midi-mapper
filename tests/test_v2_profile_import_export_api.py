def create_exportable_profile(client):
    profile = client.post(
        "/api/profiles",
        json={"name": "Studio Profile", "description": "Portable layout"},
    ).json()
    layer_a = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Keys", "sort_order": 10, "color": "#111111"},
    ).json()
    layer_b = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Faders", "sort_order": 20, "color": "#222222"},
    ).json()
    client.post(f"/api/layers/{layer_a['id']}/activate")
    note_binding = client.post(
        f"/api/layers/{layer_a['id']}/bindings",
        json={
            "trigger": {
                "event_type": "note_on",
                "channel": 1,
                "note": 60,
                "velocity_min": 64,
                "velocity_max": 127,
                "port_name": "Keyboard",
            },
            "action": {
                "type": "command",
                "label": "Editor",
                "command": "code .",
                "execution_mode": "argv",
                "timeout_ms": 1000,
                "notify_text": "Opened",
                "notify_emoji": "*",
            },
            "enabled": 1,
            "require_armed": 1,
            "cooldown_ms": 250,
            "notes": "Middle C",
            "display_label": "Open editor",
            "display_color": "#333333",
            "display_emoji": "*",
        },
    ).json()
    cc_binding = client.post(
        f"/api/layers/{layer_b['id']}/bindings",
        json={
            "trigger": {
                "event_type": "control_change",
                "channel": 2,
                "controller": 74,
                "value_min": 32,
                "value_max": 96,
                "port_name": "Fader Box",
            },
            "action": {
                "type": "command",
                "label": "Filter",
                "command": "echo filter",
            },
            "enabled": 0,
            "require_armed": 0,
            "cooldown_ms": 500,
            "notes": "Threshold",
            "display_label": "Filter range",
        },
    ).json()
    return profile, (layer_a, layer_b), (note_binding, cc_binding)


def portable_subset(exported):
    return {
        "schema_version": exported["schema_version"],
        "kind": exported["kind"],
        "profile": exported["profile"],
        "layers": exported["layers"],
        "bindings_v2": exported["bindings_v2"],
        "triggers": exported["triggers"],
        "actions": exported["actions"],
    }


def test_export_profile_includes_expected_nested_data(client):
    profile, _, _ = create_exportable_profile(client)

    exported = client.get(f"/api/profiles/{profile['id']}/export").json()

    assert exported["schema_version"] == 1
    assert exported["kind"] == "midi-mapper-v2-profile"
    assert exported["profile"] == {
        "name": "Studio Profile",
        "description": "Portable layout",
    }
    assert [layer["name"] for layer in exported["layers"]] == ["Keys", "Faders"]
    assert [layer["key"] for layer in exported["layers"]] == ["layer_0", "layer_1"]
    assert len(exported["bindings_v2"]) == 2
    assert len(exported["triggers"]) == 2
    assert len(exported["actions"]) == 2
    assert exported["triggers"][0]["velocity_min"] == 64
    assert exported["triggers"][1]["value_min"] == 32
    assert exported["triggers"][1]["value_max"] == 96
    assert exported["actions"][0]["type"] == "command"
    assert exported["actions"][0]["command"] == "code ."


def test_import_creates_equivalent_profile_with_fresh_ids(client):
    profile, layers, bindings = create_exportable_profile(client)
    exported = client.get(f"/api/profiles/{profile['id']}/export").json()

    imported = client.post("/api/profiles/import", json={"payload": exported}).json()

    assert imported["ok"] is True
    assert imported["profile_id"] != profile["id"]
    imported_profile = imported["profile"]
    assert imported_profile["name"] == "Studio Profile"
    assert imported_profile["layer_count"] == 2
    assert imported_profile["binding_count"] == 2

    imported_layers = client.get(f"/api/profiles/{imported['profile_id']}/layers").json()
    imported_layer_ids = {layer["id"] for layer in imported_layers}
    assert imported_layer_ids.isdisjoint({layer["id"] for layer in layers})

    imported_bindings = []
    for layer in imported_layers:
        imported_bindings.extend(client.get(f"/api/layers/{layer['id']}/bindings").json())
    imported_binding_ids = {binding["id"] for binding in imported_bindings}
    assert imported_binding_ids.isdisjoint({binding["id"] for binding in bindings})


def test_export_import_round_trip_preserves_profile_layout(client):
    profile, _, _ = create_exportable_profile(client)
    exported = client.get(f"/api/profiles/{profile['id']}/export").json()

    imported = client.post("/api/profiles/import", json={"payload": exported}).json()
    round_trip = client.get(f"/api/profiles/{imported['profile_id']}/export").json()

    assert portable_subset(round_trip) == portable_subset(exported)


def test_profile_import_rejects_invalid_schema_version(client):
    response = client.post(
        "/api/profiles/import",
        json={"payload": {"schema_version": 999}},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported profile export schema_version"


def test_profile_import_rejects_unsupported_action_type(client):
    profile, _, _ = create_exportable_profile(client)
    exported = client.get(f"/api/profiles/{profile['id']}/export").json()
    exported["actions"][0]["type"] = "python"

    response = client.post("/api/profiles/import", json={"payload": exported})

    assert response.status_code == 400
    assert response.json()["detail"] == "Only command actions are supported"
