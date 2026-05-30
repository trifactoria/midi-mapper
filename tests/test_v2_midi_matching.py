import asyncio
import sqlite3


def seed_v2_match_binding(
    db_path,
    *,
    enabled=1,
    require_armed=1,
    event_type="note_on",
    channel=1,
    note=60,
    controller=None,
    value_min=None,
    value_max=None,
    velocity_min=None,
    velocity_max=None,
    device_id=None,
    port_name="Test MIDI In",
    automation_armed=None,
):
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        if device_id is not None:
            con.execute(
                "INSERT INTO devices(id, name, port_name) VALUES (?, ?, ?)",
                (device_id, port_name, port_name),
            )
        con.execute("INSERT INTO profiles(id, name, active) VALUES (1, 'Profile', 1)")
        con.execute(
            "INSERT INTO layers(id, profile_id, name, active) VALUES (2, 1, 'Layer', 1)"
        )
        con.execute(
            """
            INSERT INTO triggers(
              id,
              event_type,
              channel,
              note,
              controller,
              value_min,
              value_max,
              velocity_min,
              velocity_max,
              device_id,
              port_name
            )
            VALUES (3, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                channel,
                note,
                controller,
                value_min,
                value_max,
                velocity_min,
                velocity_max,
                device_id,
                port_name,
            ),
        )
        con.execute(
            """
            INSERT INTO actions(id, type, label, command, execution_mode)
            VALUES (4, 'command', 'Action', 'echo match', 'argv')
            """
        )
        con.execute(
            """
            INSERT INTO bindings_v2(
              id,
              profile_id,
              layer_id,
              trigger_id,
              action_id,
              enabled,
              require_armed
            )
            VALUES (5, 1, 2, 3, 4, ?, ?)
            """,
            (enabled, require_armed),
        )
        con.execute(
            "INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled) VALUES (5, 4, 0, 1)"
        )
        if automation_armed is not None:
            con.execute(
                "INSERT INTO settings(key, value) VALUES ('automation_armed', ?)",
                ("true" if automation_armed else "false",),
            )
        con.commit()


def match_v2(app_module, port_name, msg):
    return asyncio.run(app_module.binding_matches_message_v2(port_name, msg))


def test_default_matching_mode_is_v2(app_module):
    assert asyncio.run(app_module.get_setting("matching_mode")) is None
    assert asyncio.run(app_module.get_matching_mode()) == "v2"


def test_v2_note_binding_matches_synthetic_midi_event(app_module):
    seed_v2_match_binding(app_module.DB_PATH)

    msg = app_module.mido.Message("note_on", channel=1, note=60, velocity=100)
    match = match_v2(app_module, "Test MIDI In", msg)

    assert match["id"] == 5
    assert match["trigger"]["event_type"] == "note_on"
    assert match["action"]["command"] == "echo match"


def test_v2_same_trigger_bindings_match_as_one_action_sequence(app_module):
    seed_v2_match_binding(app_module.DB_PATH)
    with sqlite3.connect(app_module.DB_PATH) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("INSERT INTO actions(id, type, label, command, execution_mode) VALUES (6, 'command', 'Second', 'echo second', 'argv')")
        con.execute(
            """
            INSERT INTO bindings_v2(id, profile_id, layer_id, trigger_id, action_id, enabled, require_armed)
            VALUES (7, 1, 2, 3, 6, 1, 1)
            """
        )
        con.execute("INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled) VALUES (7, 6, 1, 1)")
        con.commit()

    msg = app_module.mido.Message("note_on", channel=1, note=60, velocity=100)
    match = match_v2(app_module, "Test MIDI In", msg)

    assert [step["command"] for step in match["actions"]] == ["echo match", "echo second"]
    assert [binding["id"] for binding in match["bindings"]] == [5, 7]


def test_v2_cc_threshold_binding_matches_value_range(app_module):
    seed_v2_match_binding(
        app_module.DB_PATH,
        event_type="control_change",
        note=None,
        controller=74,
        value_min=32,
        value_max=96,
    )

    msg = app_module.mido.Message("control_change", channel=1, control=74, value=64)
    match = match_v2(app_module, "Test MIDI In", msg)

    assert match["id"] == 5
    assert match["trigger"]["controller"] == 74


def test_v2_cc_threshold_binding_does_not_match_outside_range(app_module):
    seed_v2_match_binding(
        app_module.DB_PATH,
        event_type="control_change",
        note=None,
        controller=74,
        value_min=32,
        value_max=96,
    )

    msg = app_module.mido.Message("control_change", channel=1, control=74, value=12)

    assert match_v2(app_module, "Test MIDI In", msg) is None


def test_v2_velocity_threshold_matches_and_does_not_match(app_module):
    seed_v2_match_binding(
        app_module.DB_PATH,
        note=36,
        velocity_min=100,
        velocity_max=127,
    )

    matching = app_module.mido.Message("note_on", channel=1, note=36, velocity=110)
    too_soft = app_module.mido.Message("note_on", channel=1, note=36, velocity=80)

    assert match_v2(app_module, "Test MIDI In", matching)["id"] == 5
    assert match_v2(app_module, "Test MIDI In", too_soft) is None


def test_v2_disabled_binding_does_not_match(app_module):
    seed_v2_match_binding(app_module.DB_PATH, enabled=0)

    msg = app_module.mido.Message("note_on", channel=1, note=60, velocity=100)

    assert match_v2(app_module, "Test MIDI In", msg) is None


def test_v2_automation_disarmed_blocks_require_armed_binding(app_module):
    seed_v2_match_binding(app_module.DB_PATH, require_armed=1, automation_armed=False)

    msg = app_module.mido.Message("note_on", channel=1, note=60, velocity=100)

    assert match_v2(app_module, "Test MIDI In", msg) is None


def test_v2_automation_disarmed_does_not_block_unarmed_binding(app_module):
    seed_v2_match_binding(app_module.DB_PATH, require_armed=0, automation_armed=False)

    msg = app_module.mido.Message("note_on", channel=1, note=60, velocity=100)

    assert match_v2(app_module, "Test MIDI In", msg)["id"] == 5


def test_v2_notification_binding_action_steps_include_title_message_urgency(app_module):
    with sqlite3.connect(app_module.DB_PATH) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("INSERT INTO profiles(id, name, active) VALUES (1, 'Profile', 1)")
        con.execute("INSERT INTO layers(id, profile_id, name, active) VALUES (2, 1, 'Layer', 1)")
        con.execute("INSERT INTO triggers(id, event_type, channel, note) VALUES (3, 'note_on', 1, 60)")
        con.execute(
            """INSERT INTO actions(id, type, label, command, title, message, urgency, execution_mode)
               VALUES (4, 'notification', 'Notify', '', 'Recording Started', 'Scene is live', 'normal', 'argv')"""
        )
        con.execute(
            "INSERT INTO bindings_v2(id, profile_id, layer_id, trigger_id, action_id, enabled, require_armed) VALUES (5, 1, 2, 3, 4, 1, 0)"
        )
        con.execute(
            "INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled) VALUES (5, 4, 0, 1)"
        )
        con.commit()

    msg = app_module.mido.Message("note_on", channel=1, note=60, velocity=100)
    match = match_v2(app_module, "Test MIDI In", msg)

    assert match is not None
    assert match["action"]["title"] == "Recording Started"
    assert match["action"]["message"] == "Scene is live"
    assert match["action"]["urgency"] == "normal"
    assert match["actions"][0]["title"] == "Recording Started"
    assert match["actions"][0]["message"] == "Scene is live"
    assert match["actions"][0]["urgency"] == "normal"
