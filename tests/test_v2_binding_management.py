"""Tests for enable/disable and duplicate binding operations."""
import asyncio
import sqlite3
from types import SimpleNamespace


def create_profile_layer_binding(client, *, note=60, command="echo test"):
    profile = client.post("/api/profiles", json={"name": "Profile"}).json()
    layer = client.post(
        f"/api/profiles/{profile['id']}/layers",
        json={"name": "Layer"},
    ).json()
    binding = client.post(
        f"/api/layers/{layer['id']}/bindings",
        json={
            "trigger": {"event_type": "note_on", "channel": 0, "note": note},
            "action": {"type": "command", "label": "Test", "command": command},
            "cooldown_ms": 0,
            "notes": "original notes",
            "display_label": "Test Binding",
            "display_color": "cyan",
        },
    ).json()
    return profile, layer, binding


# ── Enable / disable via PATCH ────────────────────────────────────────────────

def test_binding_starts_enabled(client):
    _, _, binding = create_profile_layer_binding(client)
    assert binding["enabled"] == 1


def test_patch_disables_binding(client):
    _, layer, binding = create_profile_layer_binding(client)

    response = client.patch(f"/api/bindings/{binding['id']}", json={"enabled": 0})

    assert response.status_code == 200
    assert response.json()["enabled"] == 0

    bindings = client.get(f"/api/layers/{layer['id']}/bindings").json()
    assert bindings[0]["enabled"] == 0


def test_patch_reenables_binding(client):
    _, _, binding = create_profile_layer_binding(client)
    client.patch(f"/api/bindings/{binding['id']}", json={"enabled": 0})

    response = client.patch(f"/api/bindings/{binding['id']}", json={"enabled": 1})

    assert response.status_code == 200
    assert response.json()["enabled"] == 1


# ── Runtime ignores disabled bindings ─────────────────────────────────────────

def test_disabled_binding_not_matched_at_runtime(app_module, client):
    """Disabled bindings must not be returned by the v2 matcher."""
    import backend.midi.matcher as matcher

    _, _, binding = create_profile_layer_binding(client, note=60)
    client.patch(f"/api/bindings/{binding['id']}", json={"enabled": 0})

    msg = SimpleNamespace(type="note_on", channel=0, note=60, velocity=100)
    result = asyncio.run(matcher.binding_matches_message_v2("Test MIDI In", msg))
    assert result is None, "disabled binding must not fire"


def test_reenabled_binding_is_matched_at_runtime(app_module, client):
    """Re-enabling a binding makes it fire again."""
    import backend.midi.matcher as matcher

    _, _, binding = create_profile_layer_binding(client, note=61)
    client.patch(f"/api/bindings/{binding['id']}", json={"enabled": 0})
    client.patch(f"/api/bindings/{binding['id']}", json={"enabled": 1})

    # Mark the profile/layer active so the matcher can find them.
    with sqlite3.connect(app_module.DB_PATH) as con:
        con.execute("UPDATE profiles SET active=1")
        con.execute("UPDATE layers SET active=1")
        con.commit()

    msg = SimpleNamespace(type="note_on", channel=0, note=61, velocity=100)
    result = asyncio.run(matcher.binding_matches_message_v2("Test MIDI In", msg))
    assert result is not None, "re-enabled binding should fire"
    assert int(result["id"]) == int(binding["id"])


# ── Duplicate binding ─────────────────────────────────────────────────────────

def test_duplicate_binding_returns_new_binding(client):
    _, layer, binding = create_profile_layer_binding(client)

    response = client.post(f"/api/bindings/{binding['id']}/duplicate")

    assert response.status_code == 200
    dup = response.json()
    assert dup["id"] != binding["id"]
    assert dup["layer_id"] == binding["layer_id"]
    assert dup["profile_id"] == binding["profile_id"]


def test_duplicate_binding_copies_trigger_and_action(client):
    _, _, binding = create_profile_layer_binding(client, note=42, command="echo dup")

    dup = client.post(f"/api/bindings/{binding['id']}/duplicate").json()

    assert dup["trigger"]["note"] == binding["trigger"]["note"]
    assert dup["trigger"]["event_type"] == binding["trigger"]["event_type"]
    assert dup["trigger"]["channel"] == binding["trigger"]["channel"]
    assert dup["action"]["command"] == binding["action"]["command"]
    assert dup["action"]["label"] == binding["action"]["label"]


def test_duplicate_binding_copies_metadata(client):
    _, _, binding = create_profile_layer_binding(client)

    dup = client.post(f"/api/bindings/{binding['id']}/duplicate").json()

    assert dup["display_color"] == binding["display_color"]
    assert dup["notes"] == binding["notes"]
    assert dup["display_label"] == binding["display_label"]
    assert dup["cooldown_ms"] == binding["cooldown_ms"]
    assert dup["enabled"] == 0


def test_duplicate_creates_independent_trigger_and_action(client, app_module):
    """Duplicate must own distinct trigger and action rows."""
    _, _, binding = create_profile_layer_binding(client)

    dup = client.post(f"/api/bindings/{binding['id']}/duplicate").json()

    assert dup["trigger_id"] != binding["trigger_id"]
    assert dup["action_id"] != binding["action_id"]
    with sqlite3.connect(app_module.DB_PATH) as con:
        assert con.execute("SELECT COUNT(*) FROM triggers").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM actions").fetchone()[0] == 2


def test_duplicate_then_delete_original_no_crash(client, app_module):
    """Deleting the original after duplicating must not crash (independent rows)."""
    _, layer, binding = create_profile_layer_binding(client)
    client.post(f"/api/bindings/{binding['id']}/duplicate")

    response = client.delete(f"/api/bindings/{binding['id']}")

    assert response.status_code == 200
    assert response.json()["ok"] is True
    bindings = client.get(f"/api/layers/{layer['id']}/bindings").json()
    assert len(bindings) == 1


def test_duplicate_then_delete_duplicate_no_crash(client, app_module):
    """Deleting the duplicate must not affect the original."""
    _, layer, binding = create_profile_layer_binding(client)
    dup = client.post(f"/api/bindings/{binding['id']}/duplicate").json()

    response = client.delete(f"/api/bindings/{dup['id']}")

    assert response.status_code == 200
    bindings = client.get(f"/api/layers/{layer['id']}/bindings").json()
    assert len(bindings) == 1
    assert bindings[0]["id"] == binding["id"]


def test_duplicate_nonexistent_binding_returns_404(client):
    response = client.post("/api/bindings/99999/duplicate")
    assert response.status_code == 404


def test_layer_binding_list_shows_both_after_duplicate(client):
    _, layer, binding = create_profile_layer_binding(client)

    client.post(f"/api/bindings/{binding['id']}/duplicate")

    bindings = client.get(f"/api/layers/{layer['id']}/bindings").json()
    assert len(bindings) == 2
