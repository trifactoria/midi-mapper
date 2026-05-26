def test_update_state_tracks_channel_and_port_bank_program(app_module):
    port = "Test MIDI In"
    Message = app_module.mido.Message

    pack = app_module.update_state(port, Message("control_change", channel=2, control=0, value=7))
    assert pack["derived"] == {"bank_msb": 7, "bank_lsb": 0, "program": 0}
    assert pack["derived_ch"] == {"bank_msb": 7, "bank_lsb": 0, "program": 0}

    pack = app_module.update_state(port, Message("control_change", channel=9, control=32, value=11))
    assert pack["derived"] == {"bank_msb": 7, "bank_lsb": 11, "program": 0}
    assert pack["derived_ch"] == {"bank_msb": 0, "bank_lsb": 11, "program": 0}

    pack = app_module.update_state(port, Message("program_change", channel=9, program=4))
    assert pack["derived"] == {"bank_msb": 7, "bank_lsb": 11, "program": 4}
    assert pack["derived_ch"] == {"bank_msb": 0, "bank_lsb": 11, "program": 4}


def test_effective_channel_uses_last_note_channel_for_non_note_messages(app_module):
    port = "Test MIDI In"
    Message = app_module.mido.Message
    app_module.LAST_NOTE_CHANNEL[port] = 5

    cc = Message("control_change", channel=0, control=1, value=64)
    note = Message("note_on", channel=3, note=60, velocity=100)

    assert app_module.effective_channel(port, cc) == 5
    assert app_module.effective_channel(port, note) == 3


def test_selection_matching_uses_port_effective_channel_and_derived_state(app_module):
    port = "Test MIDI In"
    Message = app_module.mido.Message
    app_module.LAST_NOTE_CHANNEL[port] = 4
    app_module.ACTIVE_SELECTION.update(
        {
            "port_name": port,
            "channel": 4,
            "bank_msb": 1,
            "bank_lsb": 2,
            "program": 3,
        }
    )

    msg = Message("control_change", channel=0, control=10, value=64)
    derived = {"bank_msb": 1, "bank_lsb": 2, "program": 3}

    assert app_module.selection_matches_event(port, msg, derived) is True

    assert app_module.selection_matches_event("Other MIDI In", msg, derived) is False
    assert app_module.selection_matches_event(port, msg, {**derived, "program": 9}) is False
