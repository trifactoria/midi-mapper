"""Tests for profile and layer delete with FK cleanup and safety guards."""
import sqlite3


def _counts(db_path):
    with sqlite3.connect(db_path) as con:
        return {
            "profiles": con.execute("SELECT COUNT(*) FROM profiles").fetchone()[0],
            "layers": con.execute("SELECT COUNT(*) FROM layers").fetchone()[0],
            "bindings_v2": con.execute("SELECT COUNT(*) FROM bindings_v2").fetchone()[0],
            "triggers": con.execute("SELECT COUNT(*) FROM triggers").fetchone()[0],
            "actions": con.execute("SELECT COUNT(*) FROM actions").fetchone()[0],
            "runs": con.execute("SELECT COUNT(*) FROM runs").fetchone()[0],
        }


def _run_refs(db_path, run_id):
    with sqlite3.connect(db_path) as con:
        row = con.execute(
            "SELECT binding_id, layer_id, profile_id, action_id FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        return row


def setup_profile_with_binding(client):
    """Creates profile → layer → binding, returns (profile, layer, binding)."""
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Layer"},
    ).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "channel": 0, "note": 60},
            "action": {"type": "command", "label": "Test", "command": "echo test"},
            "cooldown_ms": 0,
        },
    ).json()
    return profile, layer, binding


def insert_run(db_path, *, action_id, binding_id, profile_id, layer_id):
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=OFF")
        cur = con.execute(
            """
            INSERT INTO runs(action_id, binding_id, profile_id, layer_id,
                             trigger_snapshot_json, action_summary, status)
            VALUES (?, ?, ?, ?, '{}', 'test', 'success')
            """,
            (action_id, binding_id, profile_id, layer_id),
        )
        con.commit()
        return cur.lastrowid


# ── Profile delete ─────────────────────────────────────────────────────────────

def test_delete_last_profile_returns_400(client):
    # Fresh DB has exactly one profile (Default Profile). Deleting it must be blocked.
    profiles = client.get("/api/profiles").json()
    assert len(profiles) == 1
    response = client.delete(f"/api/profiles/{profiles[0]['id']}")
    assert response.status_code == 400


def test_profile_delete_cascades_layers_bindings_triggers_actions(client, app_module):
    profile, layer, binding = setup_profile_with_binding(client)
    extra = client.post("/api/profiles", json={"name": "Other"}).json()

    before = _counts(app_module.DB_PATH)
    assert before["bindings_v2"] == 1
    assert before["triggers"] == 1
    assert before["actions"] == 1

    resp = client.delete(f"/api/profiles/{profile['id']}")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    after = _counts(app_module.DB_PATH)
    # Default Profile + "Other" remain; Default Layer from Default Profile remains
    assert after["profiles"] == 2
    assert after["layers"] == 1
    assert after["bindings_v2"] == 0
    assert after["triggers"] == 0
    assert after["actions"] == 0


def test_profile_delete_nulls_runs_refs_and_preserves_run(client, app_module):
    profile, layer, binding = setup_profile_with_binding(client)
    extra = client.post("/api/profiles", json={"name": "Other"}).json()

    run_id = insert_run(
        app_module.DB_PATH,
        action_id=binding["action_id"],
        binding_id=binding["id"],
        profile_id=profile["id"],
        layer_id=layer["id"],
    )

    client.delete(f"/api/profiles/{profile['id']}")

    after = _counts(app_module.DB_PATH)
    assert after["runs"] == 1, "run must be preserved"
    assert after["actions"] == 1, "action must survive when referenced by run"

    refs = _run_refs(app_module.DB_PATH, run_id)
    assert refs[0] is None, "binding_id must be NULLed"
    assert refs[1] is None, "layer_id must be NULLed"
    assert refs[2] is None, "profile_id must be NULLed"
    assert refs[3] is not None, "action_id preserved (run references it)"


def test_profile_delete_active_activates_next(client, app_module):
    # Default Profile (lowest id) is present from startup bootstrap.
    default_id = client.get("/api/profiles").json()[0]["id"]

    first = client.post("/api/profiles", json={"name": "First"}).json()
    second = client.post("/api/profiles", json={"name": "Second"}).json()
    client.post(f"/api/profiles/{second['id']}/activate")

    resp = client.delete(f"/api/profiles/{second['id']}").json()
    # Delete activates the remaining profile with the lowest id (Default Profile).
    assert resp["activated_profile_id"] == default_id

    profiles = client.get("/api/profiles").json()
    active = [p for p in profiles if p["active"]]
    assert len(active) == 1
    assert active[0]["id"] == default_id


def test_profile_delete_inactive_does_not_change_active(client, app_module):
    first = client.post("/api/profiles", json={"name": "First"}).json()
    second = client.post("/api/profiles", json={"name": "Second"}).json()
    client.post(f"/api/profiles/{first['id']}/activate")

    resp = client.delete(f"/api/profiles/{second['id']}").json()
    assert resp["activated_profile_id"] is None

    profiles = client.get("/api/profiles").json()
    active = [p for p in profiles if p["active"]]
    assert active[0]["id"] == first["id"]


# ── Layer delete ───────────────────────────────────────────────────────────────

def test_delete_last_layer_of_active_profile_returns_400(client):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    client.post(f"/api/profiles/{profile['id']}/activate")
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Only Layer"},
    ).json()

    response = client.delete(f"/api/layers/{layer['id']}")
    assert response.status_code == 400


def test_delete_last_layer_of_inactive_profile_allowed(client):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Only Layer"},
    ).json()

    response = client.delete(f"/api/layers/{layer['id']}")
    assert response.status_code == 200


def test_layer_delete_cleans_bindings_triggers_actions(client, app_module):
    profile, layer, binding = setup_profile_with_binding(client)
    extra_layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Extra"},
    ).json()
    client.post(f"/api/profiles/{profile['id']}/activate")
    client.post(f"/api/layers/{extra_layer['id']}/activate")

    before = _counts(app_module.DB_PATH)
    assert before["bindings_v2"] == 1

    resp = client.delete(f"/api/layers/{layer['id']}")
    assert resp.status_code == 200

    after = _counts(app_module.DB_PATH)
    assert after["bindings_v2"] == 0
    assert after["triggers"] == 0
    assert after["actions"] == 0


def test_layer_delete_nulls_runs_refs_and_preserves_run(client, app_module):
    profile, layer, binding = setup_profile_with_binding(client)
    extra_layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Extra"},
    ).json()
    client.post(f"/api/profiles/{profile['id']}/activate")
    client.post(f"/api/layers/{extra_layer['id']}/activate")

    run_id = insert_run(
        app_module.DB_PATH,
        action_id=binding["action_id"],
        binding_id=binding["id"],
        profile_id=profile["id"],
        layer_id=layer["id"],
    )

    client.delete(f"/api/layers/{layer['id']}")

    after = _counts(app_module.DB_PATH)
    assert after["runs"] == 1
    assert after["actions"] == 1, "action kept while referenced by run"

    refs = _run_refs(app_module.DB_PATH, run_id)
    assert refs[0] is None, "binding_id must be NULLed"
    assert refs[1] is None, "layer_id must be NULLed"
    assert refs[2] is not None, "profile_id not touched"
    assert refs[3] is not None, "action_id not touched by layer delete"


def test_layer_delete_active_activates_next_by_sort_order(client, app_module):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    client.post(f"/api/profiles/{profile['id']}/activate")
    first = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "First", "sort_order": 20},
    ).json()
    second = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Second", "sort_order": 10},
    ).json()
    client.post(f"/api/layers/{second['id']}/activate")

    resp = client.delete(f"/api/layers/{second['id']}").json()
    assert resp["activated_layer_id"] == first["id"]
