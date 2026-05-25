import asyncio


class FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(text)


def test_websocket_manager_broadcasts_current_event_shape(app_module):
    client = FakeWebSocket()
    app_module.ws_mgr.clients.append(client)

    payload = {
        "ts": 123.0,
        "port_name": "Test MIDI In",
        "type": "note_on",
        "channel": 0,
        "effective_channel": 0,
        "note": 60,
        "velocity": 100,
        "cc": None,
        "value": None,
        "pitch": None,
        "program": None,
        "derived": {"bank_msb": 0, "bank_lsb": 0, "program": 0},
        "derived_ch": {"bank_msb": 0, "bank_lsb": 0, "program": 0},
        "derived_port": {"bank_msb": 0, "bank_lsb": 0, "program": 0},
        "context_match": True,
        "observed_note_channel": 0,
        "keygrab_enabled": True,
        "max_note": 127,
        "active_context_id": 1,
        "binding_match": None,
    }

    asyncio.run(app_module.ws_mgr.broadcast(payload))

    assert client.sent
    for key in payload:
        assert f'"{key}"' in client.sent[0]
