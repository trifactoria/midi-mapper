import sqlite3


def assert_dict_contains(actual, expected):
    assert expected.items() <= actual.items()


def seed_v2_data(db_path):
    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute(
            """
            INSERT INTO devices(id, name, port_name, port_index, connected, last_seen_at)
            VALUES (1, 'Keyboard', 'MIDI Keyboard', 0, 1, '2026-01-01T00:00:00Z')
            """
        )
        con.execute(
            """
            INSERT INTO profiles(id, name, description, active)
            VALUES (2, 'Workflow', 'Main workflow', 1)
            """
        )
        con.execute(
            """
            INSERT INTO layers(id, profile_id, name, sort_order, color, active)
            VALUES (3, 2, 'Editing', 10, '#ffcc00', 1)
            """
        )
        con.execute(
            """
            INSERT INTO triggers(
              id,
              event_type,
              channel,
              note,
              device_id,
              port_name,
              bank_msb,
              bank_lsb,
              program_filter
            )
            VALUES (4, 'note_on', 1, 60, 1, 'MIDI Keyboard', 0, 1, 2)
            """
        )
        con.execute(
            """
            INSERT INTO actions(
              id,
              type,
              label,
              command,
              execution_mode,
              cooldown_ms,
              notify_text,
              notify_emoji
            )
            VALUES (5, 'command', 'Open editor', 'code .', 'argv', 300, 'Opened', '*')
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
              require_armed,
              cooldown_ms,
              notes,
              display_label,
              display_color,
              display_emoji
            )
            VALUES (6, 2, 3, 4, 5, 1, 1, 300, 'Middle C', 'Editor', '#ffcc00', '*')
            """
        )
        con.execute(
            """
            INSERT INTO runs(
              id,
              action_id,
              binding_id,
              profile_id,
              layer_id,
              trigger_snapshot_json,
              action_summary,
              started_at,
              finished_at,
              duration_ms,
              status,
              exit_code,
              stdout_preview,
              stderr_preview,
              error_message
            )
            VALUES (
              7,
              5,
              6,
              2,
              3,
              '{"event_type":"note_on"}',
              'code .',
              '2026-01-01T00:00:00Z',
              '2026-01-01T00:00:01Z',
              1000,
              'ok',
              0,
              'done',
              '',
              ''
            )
            """
        )
        con.commit()


def test_v2_read_only_routes_return_seeded_data(client, app_module):
    seed_v2_data(app_module.DB_PATH)

    devices = client.get("/api/devices").json()
    assert len(devices) == 1
    assert_dict_contains(devices[0], {
        "id": 1,
        "name": "Keyboard",
        "port_name": "MIDI Keyboard",
        "port_index": 0,
        "connected": 1,
        "last_seen_at": "2026-01-01T00:00:00Z",
    })

    profiles = client.get("/api/profiles").json()
    assert_dict_contains(profiles[0], {
        "id": 2,
        "name": "Workflow",
        "description": "Main workflow",
        "active": 1,
        "legacy_context_id": None,
        "layer_count": 1,
        "binding_count": 1,
    })

    profile = client.get("/api/profiles/2").json()
    assert profile["name"] == "Workflow"
    assert profile["layer_count"] == 1
    assert profile["binding_count"] == 1

    layers = client.get("/api/profiles/2/layers").json()
    assert_dict_contains(layers[0], {
        "id": 3,
        "profile_id": 2,
        "name": "Editing",
        "sort_order": 10,
        "color": "#ffcc00",
        "active": 1,
        "binding_count": 1,
    })

    bindings = client.get("/api/layers/3/bindings").json()
    assert_dict_contains(bindings[0], {
        "id": 6,
        "profile_id": 2,
        "layer_id": 3,
        "trigger_id": 4,
        "action_id": 5,
        "enabled": 1,
        "require_armed": 1,
        "cooldown_ms": 300,
        "notes": "Middle C",
        "display_label": "Editor",
        "display_color": "#ffcc00",
        "display_emoji": "*",
    })
    assert_dict_contains(bindings[0]["trigger"], {
        "id": 4,
        "event_type": "note_on",
        "channel": 1,
        "note": 60,
        "device_id": 1,
        "port_name": "MIDI Keyboard",
        "bank_msb": 0,
        "bank_lsb": 1,
        "program_filter": 2,
    })
    assert_dict_contains(bindings[0]["action"], {
        "id": 5,
        "type": "command",
        "label": "Open editor",
        "command": "code .",
        "execution_mode": "argv",
        "cooldown_ms": 300,
        "notify_text": "Opened",
        "notify_emoji": "*",
    })

    action = client.get("/api/actions/5").json()
    assert action["command"] == "code ."
    assert action["execution_mode"] == "argv"

    runs = client.get("/api/runs").json()
    assert runs[0]["id"] == 7
    assert runs[0]["status"] == "ok"
    assert runs[0]["action_summary"] == "code ."

    run = client.get("/api/runs/7").json()
    assert run["id"] == 7
    assert run["trigger_snapshot_json"] == '{"event_type":"note_on"}'


def test_v2_read_only_routes_return_404_for_missing_records(client):
    assert client.get("/api/profiles/404").status_code == 404
    assert client.get("/api/profiles/404/layers").status_code == 404
    assert client.get("/api/layers/404/bindings").status_code == 404
    assert client.get("/api/actions/404").status_code == 404
    assert client.get("/api/runs/404").status_code == 404
