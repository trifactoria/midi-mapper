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

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
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


def test_v2_runtime_executes_sequence_in_order_with_delay(monkeypatch):
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "actions": [
            {"binding_id": 5, "action_id": 4, "type": "command", "command": "echo one", "execution_order": 0, "enabled": 1},
            {"binding_id": 8, "action_id": 6, "type": "delay", "duration_ms": 5, "execution_order": 1, "enabled": 1},
            {"binding_id": 8, "action_id": 7, "type": "command", "command": "echo two", "execution_order": 2, "enabled": 1},
        ],
        "action": {"id": 4, "type": "command", "command": "echo one"},
    }
    calls = []
    recorded = []

    async def fake_match(port_name, msg, derived_flat):
        return binding

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        calls.append(command)
        return {"ok": True, "stdout": command}

    async def fake_record(**kwargs):
        recorded.append(kwargs)
        return len(recorded)

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    payload = {}
    asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={},
            payload=payload,
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert calls == ["echo one", "echo two"]
    assert [run["action_id"] for run in recorded] == [4, 6, 7]
    assert [run["binding_id"] for run in recorded] == [5, 8, 8]
    assert [run["action_summary"] for run in recorded] == ["echo one", "Wait 5ms", "echo two"]
    assert payload["execution_status"] == "success"
    assert [step["action_id"] for step in payload["action_sequence"]] == [4, 6, 7]


def test_v2_runtime_notification_step_uses_title_message_urgency(monkeypatch):
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "actions": [
            {
                "binding_id": 5,
                "action_id": 4,
                "type": "notification",
                "title": "Recording Started",
                "message": "Scene is live",
                "urgency": "normal",
                "label": "should-not-be-used",
                "execution_order": 0,
                "enabled": 1,
            }
        ],
        "action": {"id": 4, "type": "notification", "title": "Recording Started"},
    }
    notification_calls = []
    recorded = []

    async def fake_match(port_name, msg, derived_flat):
        return binding

    async def fake_execute_notification(title, message="", urgency=None):
        notification_calls.append({"title": title, "message": message, "urgency": urgency})
        return {"ok": True, "stdout": "", "stderr": ""}

    async def fake_record(**kwargs):
        recorded.append(kwargs)
        return len(recorded)

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        return {"ok": True, "stdout": ""}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    monkeypatch.setattr(listener, "execute_notification", fake_execute_notification)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    payload = {}
    asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={},
            payload=payload,
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert len(notification_calls) == 1
    assert notification_calls[0]["title"] == "Recording Started"
    assert notification_calls[0]["message"] == "Scene is live"
    assert notification_calls[0]["urgency"] == "normal"
    assert recorded[0]["action_summary"] == "Notify: Recording Started"
    assert payload["execution_status"] == "success"


def test_v2_runtime_failed_step_does_not_abort_sequence(monkeypatch):
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "actions": [
            {"binding_id": 5, "action_id": 4, "type": "command", "command": "echo one", "execution_order": 0, "enabled": 1},
            {"binding_id": 5, "action_id": 5, "type": "command", "command": "false", "execution_order": 1, "enabled": 1},
            {"binding_id": 5, "action_id": 6, "type": "command", "command": "echo three", "execution_order": 2, "enabled": 1},
        ],
        "action": {"id": 4, "type": "command", "command": "echo one"},
    }
    calls = []

    async def fake_match(port_name, msg, derived_flat):
        return binding

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        calls.append(command)
        return {"ok": command != "false", "stdout": "", "stderr": ""}

    async def fake_record(**kwargs):
        return len(calls)

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    payload = {}
    asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={},
            payload=payload,
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert calls == ["echo one", "false", "echo three"]
    assert payload["execution_status"] == "error"
    assert len(payload["action_sequence"]) == 3


def test_v2_runtime_hotkey_and_open_url_dispatch_to_correct_executors(monkeypatch):
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "actions": [
            {"binding_id": 5, "action_id": 4, "type": "hotkey", "command": "ctrl+z", "execution_order": 0, "enabled": 1},
            {"binding_id": 5, "action_id": 5, "type": "open_url", "command": "https://example.com", "execution_order": 1, "enabled": 1},
        ],
        "action": {"id": 4, "type": "hotkey", "command": "ctrl+z"},
    }
    hotkey_calls = []
    shell_calls = []

    async def fake_match(port_name, msg, derived_flat):
        return binding

    async def fake_execute_hotkey(shortcut):
        hotkey_calls.append(shortcut)
        return {"ok": True, "stdout": "", "stderr": ""}

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        shell_calls.append((command, execution_mode))
        return {"ok": True, "stdout": "", "stderr": ""}

    async def fake_record(**kwargs):
        return 1

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    monkeypatch.setattr(listener, "execute_hotkey", fake_execute_hotkey)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    payload = {}
    asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={},
            payload=payload,
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert hotkey_calls == ["ctrl+z"]
    assert len(shell_calls) == 1
    assert "example.com" in shell_calls[0][0]
    assert shell_calls[0][1] == "detached"
    assert payload["execution_status"] == "success"


def test_v2_runtime_delay_step_actually_blocks_sequence_for_specified_duration(monkeypatch):
    import time
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "actions": [
            {"binding_id": 5, "action_id": 4, "type": "command", "command": "echo before", "execution_order": 0, "enabled": 1},
            {"binding_id": 5, "action_id": 5, "type": "delay", "duration_ms": 50, "execution_order": 1, "enabled": 1},
            {"binding_id": 5, "action_id": 6, "type": "command", "command": "echo after", "execution_order": 2, "enabled": 1},
        ],
        "action": {"id": 4, "type": "command", "command": "echo before"},
    }
    timestamps = []

    async def fake_match(port_name, msg, derived_flat):
        return binding

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        timestamps.append(time.monotonic())
        return {"ok": True, "stdout": command}

    async def fake_record(**kwargs):
        return len(timestamps)

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={},
            payload={},
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert len(timestamps) == 2
    elapsed_ms = (timestamps[1] - timestamps[0]) * 1000
    assert elapsed_ms >= 40, f"Delay step did not block: elapsed={elapsed_ms:.1f}ms, expected >= 40ms"


def test_v2_runtime_open_url_fires_only_after_delay_step(monkeypatch):
    """Regression: open_url must not fire concurrently with or before a preceding delay."""
    import time
    import backend.midi.listener as listener

    binding = {
        "id": 5,
        "profile_id": 1,
        "layer_id": 2,
        "trigger_id": 3,
        "action_id": 4,
        "cooldown_ms": 0,
        "actions": [
            {"binding_id": 5, "action_id": 4, "type": "command", "command": "echo hello", "execution_order": 0, "enabled": 1},
            {"binding_id": 5, "action_id": 5, "type": "delay", "duration_ms": 50, "execution_order": 1, "enabled": 1},
            {"binding_id": 5, "action_id": 6, "type": "open_url", "command": "https://example.com", "execution_order": 2, "enabled": 1},
        ],
        "action": {"id": 4, "type": "command", "command": "echo hello"},
    }
    call_log: list[tuple[str, float]] = []

    async def fake_match(port_name, msg, derived_flat):
        return binding

    async def fake_execute(command, execution_mode="argv", timeout_ms=None, working_directory=None):
        call_log.append((command, time.monotonic()))
        return {"ok": True, "stdout": ""}

    async def fake_record(**kwargs):
        return len(call_log)

    async def fake_notify(text, emoji):
        return {"ok": True, "skipped": True}

    monkeypatch.setattr(listener, "binding_matches_message_v2", fake_match)
    monkeypatch.setattr(listener, "record_v2_action_run", fake_record)
    listener.LAST_FIRED.clear()

    msg = SimpleNamespace(type="note_on", channel=1, note=60, velocity=100)
    asyncio.run(
        listener._execute_v2_match(
            port_name="Test MIDI In",
            msg=msg,
            derived_flat={},
            payload={},
            safe_execute_command=fake_execute,
            send_notification=fake_notify,
        )
    )

    assert len(call_log) == 2
    echo_t = next(t for cmd, t in call_log if "echo" in cmd)
    url_t = next(t for cmd, t in call_log if "xdg-open" in cmd)
    elapsed_ms = (url_t - echo_t) * 1000
    assert elapsed_ms >= 40, (
        f"open_url fired before delay elapsed: {elapsed_ms:.1f}ms after echo (need >= 40ms)"
    )


def test_selected_input_port_filter_skips_unselected_port():
    import backend.midi.listener as listener

    assert listener._input_is_selected("Keyboard A", None) is True
    assert listener._input_is_selected("Keyboard A", "") is True
    assert listener._input_is_selected("Keyboard A", "Keyboard A") is True
    assert listener._input_is_selected("Keyboard B", "Keyboard A") is False
