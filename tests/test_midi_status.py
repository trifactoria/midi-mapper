def test_safe_midi_status_reports_degraded_when_backend_raises(monkeypatch):
    from backend.midi import status

    def unavailable():
        raise RuntimeError("ALSA sequencer unavailable")

    monkeypatch.setattr(status.mido, "get_input_names", unavailable)

    assert status.safe_get_input_names(context="test") == []
    midi_status = status.get_midi_status()
    assert midi_status["available"] is False
    assert midi_status["degraded"] is True
    assert "test" in midi_status["message"]
    assert "ALSA sequencer unavailable" in midi_status["error"]
