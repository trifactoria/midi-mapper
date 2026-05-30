import sqlite3


def assert_dict_contains(actual, expected):
    assert expected.items() <= actual.items()


def v2_counts(db_path):
    with sqlite3.connect(db_path) as con:
        return {
            "profiles": con.execute("SELECT COUNT(*) FROM profiles").fetchone()[0],
            "layers": con.execute("SELECT COUNT(*) FROM layers").fetchone()[0],
            "bindings_v2": con.execute("SELECT COUNT(*) FROM bindings_v2").fetchone()[0],
            "actions": con.execute("SELECT COUNT(*) FROM actions").fetchone()[0],
            "triggers": con.execute("SELECT COUNT(*) FROM triggers").fetchone()[0],
        }


def active_profile_ids(client):
    return [profile["id"] for profile in client.get("/api/profiles").json() if profile["active"]]


def active_layer_ids(client, profile_id):
    return [
        layer["id"]
        for layer in client.get(f"/api/profiles/{profile_id}/layers").json()
        if layer["active"]
    ]


def test_profile_write_endpoints_create_patch_activate_duplicate_and_delete(client, app_module):
    first = client.post(
        "/api/profiles",
        json={"name": " Editing ", "description": "Initial"},
    ).json()
    assert_dict_contains(first, {
        "name": "Editing",
        "description": "Initial",
        "active": 0,
        "layer_count": 0,
        "binding_count": 0,
    })

    second = client.post(
        "/api/profiles",
        json={"name": "Performance", "description": "Live"},
    ).json()

    patched = client.patch(
        f"/api/profiles/{first['id']}",
        json={"name": "Studio", "description": "Updated"},
    ).json()
    assert_dict_contains(patched, {
        "id": first["id"],
        "name": "Studio",
        "description": "Updated",
    })

    activated_first = client.post(f"/api/profiles/{first['id']}/activate").json()
    assert activated_first["active"] == 1
    assert active_profile_ids(client) == [first["id"]]

    activated_second = client.post(f"/api/profiles/{second['id']}/activate").json()
    assert activated_second["active"] == 1
    assert active_profile_ids(client) == [second["id"]]

    layer_one = client.post(
        f"/api/profiles/{first['id']}/layers",
        json={"name": "Base", "sort_order": 20, "color": "#111111"},
    ).json()
    layer_two = client.post(
        f"/api/profiles/{first['id']}/layers",
        json={"name": "Top", "sort_order": 30, "color": "#222222"},
    ).json()
    client.post(f"/api/layers/{layer_two['id']}/activate")

    duplicate = client.post(f"/api/profiles/{first['id']}/duplicate").json()
    assert duplicate["name"] == "Studio Copy"
    assert duplicate["active"] == 0
    assert duplicate["layer_count"] == 2
    assert duplicate["binding_count"] == 0
    assert client.get(f"/api/profiles/{duplicate['id']}/layers").json()[0]["name"] == "Base"

    before_delete_counts = v2_counts(app_module.DB_PATH)
    assert before_delete_counts["bindings_v2"] == 0
    assert before_delete_counts["actions"] == 0
    assert before_delete_counts["triggers"] == 0

    deleted = client.delete(f"/api/profiles/{second['id']}").json()
    assert deleted["ok"] is True
    assert deleted["deleted_profile_id"] == second["id"]
    # Delete activates the remaining profile with the lowest id (Default Profile).
    assert deleted["activated_profile_id"] is not None
    assert active_profile_ids(client) == [deleted["activated_profile_id"]]

    remaining_ids = {profile["id"] for profile in client.get("/api/profiles").json()}
    assert first["id"] in remaining_ids
    assert duplicate["id"] in remaining_ids
    assert second["id"] not in remaining_ids

    # Deleting profiles cascades their layers but does not create binding/action data.
    client.delete(f"/api/profiles/{duplicate['id']}")
    assert v2_counts(app_module.DB_PATH)["bindings_v2"] == 0
    assert client.get(f"/api/layers/{layer_one['id']}/bindings").json() == []


def test_layer_write_endpoints_create_patch_activate_and_delete(client):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()

    first = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": " Base ", "sort_order": 20, "color": "#111111"},
    ).json()
    assert_dict_contains(first, {
        "profile_id": profile["id"],
        "name": "Base",
        "sort_order": 20,
        "color": "#111111",
        "active": 0,
        "binding_count": 0,
    })

    second = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Top", "sort_order": 10, "color": "#222222"},
    ).json()

    patched = client.patch(
        f"/api/layers/{first['id']}",
        json={"name": "Main", "sort_order": 5, "color": "#333333"},
    ).json()
    assert_dict_contains(patched, {
        "id": first["id"],
        "name": "Main",
        "sort_order": 5,
        "color": "#333333",
    })

    client.post(f"/api/layers/{first['id']}/activate")
    assert active_layer_ids(client, profile["id"]) == [first["id"]]

    client.post(f"/api/layers/{second['id']}/activate")
    assert active_layer_ids(client, profile["id"]) == [second["id"]]

    deleted = client.delete(f"/api/layers/{second['id']}").json()
    assert deleted == {
        "ok": True,
        "deleted_layer_id": second["id"],
        "activated_layer_id": first["id"],
    }
    assert active_layer_ids(client, profile["id"]) == [first["id"]]

    deleted_last = client.delete(f"/api/layers/{first['id']}").json()
    assert deleted_last == {
        "ok": True,
        "deleted_layer_id": first["id"],
        "activated_layer_id": None,
    }
    assert client.get(f"/api/profiles/{profile['id']}/layers").json() == []


def test_v2_profile_layer_write_routes_validate_missing_records(client):
    assert client.patch("/api/profiles/404", json={"name": "Missing"}).status_code == 404
    assert client.post("/api/profiles/404/activate").status_code == 404
    assert client.post("/api/profiles/404/duplicate").status_code == 404
    assert client.delete("/api/profiles/404").status_code == 404
    assert client.post("/api/profiles/404/layers", json={"name": "Missing"}).status_code == 404
    assert client.patch("/api/layers/404", json={"name": "Missing"}).status_code == 404
    assert client.post("/api/layers/404/activate").status_code == 404
    assert client.delete("/api/layers/404").status_code == 404

    assert client.post("/api/profiles", json={"name": "   "}).status_code == 400
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    assert client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "   "},
    ).status_code == 400
