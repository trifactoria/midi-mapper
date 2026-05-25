def test_context_export_import_round_trip(client):
    context_payload = {
        "daw_slot": 1,
        "preset_slot": 2,
        "port_id": 1,
        "channel": 3,
        "bank_msb": 4,
        "bank_lsb": 5,
        "program": 6,
    }
    context_id = client.post("/api/contexts/get_or_create", json=context_payload).json()["context_id"]

    assert client.post(f"/api/contexts/{context_id}/label", json={"label": "Video workflow"}).json() == {
        "ok": True,
        "label": "Video workflow",
    }

    client.post(
        "/api/bindings/set",
        json={
            "context_id": context_id,
            "enabled": 1,
            "trig_type": 1,
            "note": 61,
            "cc": None,
            "command": "echo original",
            "debounce_ms": 200,
            "require_armed": 1,
            "notes": "exported binding",
            "notify_text": "done",
            "notify_emoji": "*",
        },
    )

    exported = client.get(f"/api/contexts/{context_id}/export").json()

    assert exported["version"] == 1
    assert exported["context"] == {
        "daw_slot": 1,
        "preset_slot": 2,
        "port_name": "Test MIDI In",
        "channel": 3,
        "bank_msb": 4,
        "bank_lsb": 5,
        "program": 6,
        "label": "Video workflow",
    }
    assert exported["bindings"][0]["note"] == 61
    assert exported["bindings"][0]["command"] == "echo original"

    client.delete(f"/api/contexts/{context_id}")

    imported = client.post(
        "/api/contexts/import",
        json={"payload": exported, "mode": "replace"},
    ).json()

    assert imported["ok"] is True
    assert imported["binding_count"] == 1

    imported_bindings = client.get(f"/api/contexts/{imported['context_id']}/bindings").json()
    assert imported_bindings[0]["note"] == 61
    assert imported_bindings[0]["command"] == "echo original"
    assert imported_bindings[0]["notes"] == "exported binding"


def test_context_import_rejects_unsupported_version(client):
    response = client.post(
        "/api/contexts/import",
        json={"payload": {"version": 999, "context": {}, "bindings": []}, "mode": "merge"},
    ).json()

    assert response == {"ok": False, "error": "Unsupported export version"}
