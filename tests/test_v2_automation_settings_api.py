import sqlite3


def create_profile_layer(client):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Layer"},
    ).json()
    return profile, layer


def test_automation_armed_default_is_predictable(client):
    assert client.get("/api/settings/automation").json() == {
        "armed": True,
        "legacy_keygrab": True,
        "mode": "automation_armed",
        "source": "default",
    }


def test_automation_patch_false_pauses_state_without_changing_keygrab(client):
    assert client.patch("/api/settings/automation", json={"armed": False}).json() == {
        "armed": False,
        "legacy_keygrab": True,
        "mode": "automation_armed",
        "source": "automation_armed",
    }
    assert client.get("/api/keygrab").json() == {"enabled": True}


def test_automation_patch_true_arms_state(client):
    client.patch("/api/settings/automation", json={"armed": False})

    assert client.patch("/api/settings/automation", json={"armed": True}).json() == {
        "armed": True,
        "legacy_keygrab": True,
        "mode": "automation_armed",
        "source": "automation_armed",
    }


def test_legacy_keygrab_remains_independent_of_automation_state(client):
    assert client.post("/api/keygrab/set", params={"enabled": "false"}).json() == {
        "ok": True,
        "enabled": False,
    }
    assert client.get("/api/settings/automation").json() == {
        "armed": True,
        "legacy_keygrab": False,
        "mode": "automation_armed",
        "source": "default",
    }


def test_v2_binding_require_armed_remains_stored_with_automation_setting(client, app_module):
    _, layer = create_profile_layer(client)
    client.patch("/api/settings/automation", json={"armed": False})

    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "note": 60},
            "action": {"type": "command", "command": "echo armed"},
            "require_armed": 0,
        },
    ).json()

    assert binding["require_armed"] == 0
    with sqlite3.connect(app_module.DB_PATH) as con:
        assert con.execute(
            "SELECT value FROM settings WHERE key = 'automation_armed'"
        ).fetchone()[0] == "false"
        assert con.execute(
            "SELECT require_armed FROM bindings_v2 WHERE id = ?",
            (binding["id"],),
        ).fetchone()[0] == 0


def test_matching_mode_defaults_to_v2_and_can_be_changed(client):
    assert client.get("/api/settings/matching").json() == {
        "matching_mode": "v2",
        "source": "default",
    }

    assert client.patch(
        "/api/settings/matching",
        json={"matching_mode": "dual"},
    ).json() == {
        "ok": True,
        "matching_mode": "dual",
        "source": "setting",
    }

    assert client.patch(
        "/api/settings/matching",
        json={"matching_mode": "invalid"},
    ).json() == {
        "ok": False,
        "error": "matching_mode must be legacy, v2, or dual",
    }
