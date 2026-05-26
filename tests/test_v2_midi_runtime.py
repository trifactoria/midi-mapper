import asyncio
from types import SimpleNamespace


def test_v2_runtime_executes_action_records_run_and_enriches_payload(monkeypatch):
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "action": {
            "id": 4,
            "type": "command",
            "command": "echo live",
            "notify_text": "",
            "notify_emoji": "",
        },
    }
    calls = []
    recorded = []

    async def fake_match(port_name, msg, derived_flat):
        assert port_name == "Test MIDI In"
        assert derived_flat == {"bank_msb": 0, "bank_lsb": 0, "program": 0}
        return binding

    async def fake_execute(command):
        calls.append(command)
        return {"ok": True, "stdout": "live"}

    async def fake_record(**kwargs):
        recorded.append(kwargs)
        return 9

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    payload = {}
    match = asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={"bank_msb": 0, "bank_lsb": 0, "program": 0},
            payload=payload,
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert match == binding
    assert calls == ["echo live"]
    assert recorded[0]["binding_id"] == 5
    assert recorded[0]["action_id"] == 4
    assert recorded[0]["profile_id"] == 1
    assert recorded[0]["layer_id"] == 2
    assert recorded[0]["action_summary"] == "echo live"
    assert payload["matched_binding_id"] == 5
    assert payload["matched_layer_id"] == 2
    assert payload["matched_profile_id"] == 1
    assert payload["matched_action_id"] == 4
    assert payload["execution_status"] == "success"
    assert payload["action_execution"]["run_id"] == 9


def test_selected_input_port_filter_skips_unselected_port():
    import backend.midi.listener as listener

    assert listener._input_is_selected("Keyboard A", None) is True
    assert listener._input_is_selected("Keyboard A", "") is True
    assert listener._input_is_selected("Keyboard A", "Keyboard A") is True
    assert listener._input_is_selected("Keyboard B", "Keyboard A") is False
