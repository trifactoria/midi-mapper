def test_context_binding_crud(client, app_module):
    assert app_module.SCHEMA_PATH == app_module.PROJECT_ROOT / "schema.sql"
    assert app_module.DOTENV_PATH == app_module.PROJECT_ROOT / ".env"
    assert app_module.DEFAULT_DB_PATH == app_module.PROJECT_ROOT / "midi_map.db"

    ports = client.get("/api/ports").json()
    assert ports == [{"id": 1, "name": "Test MIDI In", "online": True}]

    context_payload = {
        "daw_slot": 0,
        "preset_slot": 0,
        "port_id": 1,
        "channel": 0,
        "bank_msb": 0,
        "bank_lsb": 0,
        "program": 0,
    }
    context_id = client.post("/api/contexts/get_or_create", json=context_payload).json()["context_id"]

    binding_payload = {
        "context_id": context_id,
        "enabled": 1,
        "trig_type": 1,
        "note": 60,
        "cc": None,
        "command": "echo hello",
        "debounce_ms": 250,
        "require_armed": 1,
        "notes": "middle C",
        "notify_text": "ran",
        "notify_emoji": "*",
    }
    response = client.post("/api/bindings/set", json=binding_payload).json()
    assert response["ok"] is True
    assert response["binding_id"] >= 1

    bindings = client.get(f"/api/contexts/{context_id}/bindings").json()
    assert len(bindings) == 1
    assert bindings[0]["note"] == 60
    assert bindings[0]["command"] == "echo hello"
    assert bindings[0]["notes"] == "middle C"

    binding_payload["id"] = bindings[0]["id"]
    binding_payload["command"] = "echo updated"
    client.post("/api/bindings/set", json=binding_payload)

    updated = client.get(f"/api/contexts/{context_id}/bindings").json()
    assert updated[0]["id"] == bindings[0]["id"]
    assert updated[0]["command"] == "echo updated"

    removed = client.post(
        "/api/bindings/remove",
        params={"context_id": context_id, "trig_type": 1, "note": 60},
    ).json()
    assert removed == {"ok": True, "deleted_context": True}

    assert client.get(f"/api/contexts/{context_id}/bindings").json() == []


def test_defaults_and_keygrab_settings(client):
    assert client.get("/api/keygrab").json() == {"enabled": True}

    assert client.post("/api/keygrab/set", params={"enabled": "false"}).json() == {
        "ok": True,
        "enabled": False,
    }
    assert client.get("/api/keygrab").json() == {"enabled": False}

    defaults = {
        "daw_slot": 2,
        "preset_slot": 3,
        "port_id": 1,
        "channel": 4,
        "bank_msb": 5,
        "bank_lsb": 6,
        "program": 7,
    }
    assert client.post("/api/defaults/save", json=defaults).json() == {"ok": True}
    assert client.get("/api/defaults").json() == defaults
