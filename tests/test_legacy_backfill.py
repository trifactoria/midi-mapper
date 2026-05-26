import sqlite3

from backend.legacy.backfill import backfill_v2_from_legacy
from backend.migrations import init_schema


def create_legacy_fixture(db_path, *, with_label=False):
    init_schema(db_path)
    with sqlite3.connect(db_path) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS context_labels (
                context_id INTEGER PRIMARY KEY REFERENCES contexts(id) ON DELETE CASCADE,
                label TEXT NOT NULL
            )
            """
        )
        con.execute("INSERT INTO ports(id, name) VALUES (1, 'Legacy MIDI')")
        con.execute(
            """
            INSERT INTO contexts(
              id,
              daw_slot,
              preset_slot,
              port_id,
              channel,
              bank_msb,
              bank_lsb,
              program
            )
            VALUES (10, 0, 1, 1, 2, 3, 4, 5)
            """
        )
        con.execute(
            """
            INSERT INTO bindings(
              id,
              context_id,
              enabled,
              trig_type,
              note,
              cc,
              value_min,
              value_max,
              command,
              debounce_ms,
              require_armed,
              notes,
              notify_text,
              notify_emoji
            )
            VALUES (20, 10, 1, 1, 60, NULL, 1, 127, 'echo legacy', 250, 1, 'Launch clip', 'Done', '*')
            """
        )
        con.execute("INSERT INTO settings(key, value) VALUES ('custom', 'legacy')")
        if with_label:
            con.execute(
                "INSERT INTO context_labels(context_id, label) VALUES (10, 'Clip Launch')"
            )
        con.commit()


def fetch_counts(db_path, table_names):
    with sqlite3.connect(db_path) as con:
        return {
            table_name: con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            for table_name in table_names
        }


def legacy_snapshot(db_path):
    with sqlite3.connect(db_path) as con:
        return {
            "ports": con.execute("SELECT * FROM ports ORDER BY id").fetchall(),
            "contexts": con.execute("SELECT * FROM contexts ORDER BY id").fetchall(),
            "bindings": con.execute("SELECT * FROM bindings ORDER BY id").fetchall(),
            "settings": con.execute("SELECT * FROM settings ORDER BY key").fetchall(),
            "context_labels": con.execute(
                "SELECT * FROM context_labels ORDER BY context_id"
            ).fetchall(),
        }


def assert_row_contains(row, expected):
    assert expected.items() <= dict(row).items()


def test_legacy_port_context_binding_backfills_one_v2_mapping(tmp_path):
    db_path = tmp_path / "backfill.db"
    create_legacy_fixture(db_path)

    backfill_v2_from_legacy(db_path)

    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row

        device = con.execute("SELECT * FROM devices").fetchone()
        assert dict(device)["name"] == "Legacy MIDI"
        assert dict(device)["port_name"] == "Legacy MIDI"

        profile = con.execute("SELECT * FROM profiles").fetchone()
        assert dict(profile)["name"] == "Legacy Mappings"
        assert dict(profile)["active"] == 1

        layer = con.execute("SELECT * FROM layers").fetchone()
        assert dict(layer)["profile_id"] == profile["id"]
        assert dict(layer)["legacy_context_id"] == 10

        trigger = con.execute("SELECT * FROM triggers").fetchone()
        assert_row_contains(trigger, {
            "event_type": "note_on",
            "channel": 2,
            "note": 60,
            "port_name": "Legacy MIDI",
            "bank_msb": 3,
            "bank_lsb": 4,
            "program_filter": 5,
            "legacy_context_id": 10,
            "legacy_binding_id": 20,
        })

        action = con.execute("SELECT * FROM actions").fetchone()
        assert_row_contains(action, {
            "type": "command",
            "command": "echo legacy",
            "execution_mode": "argv",
            "cooldown_ms": 250,
            "notify_text": "Done",
            "notify_emoji": "*",
            "legacy_binding_id": 20,
        })

        binding = con.execute("SELECT * FROM bindings_v2").fetchone()
        assert_row_contains(binding, {
            "profile_id": profile["id"],
            "layer_id": layer["id"],
            "trigger_id": trigger["id"],
            "action_id": action["id"],
            "enabled": 1,
            "require_armed": 1,
            "cooldown_ms": 250,
            "notes": "Launch clip",
            "display_emoji": "*",
            "legacy_binding_id": 20,
        })

        assert con.execute("SELECT COUNT(*) FROM legacy_context_migrations").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM legacy_binding_migrations").fetchone()[0] == 1


def test_context_label_maps_to_layer_name(tmp_path):
    db_path = tmp_path / "labels.db"
    create_legacy_fixture(db_path, with_label=True)

    backfill_v2_from_legacy(db_path)

    with sqlite3.connect(db_path) as con:
        assert con.execute("SELECT name FROM layers").fetchone()[0] == "Clip Launch"


def test_backfill_is_idempotent(tmp_path):
    db_path = tmp_path / "idempotent.db"
    create_legacy_fixture(db_path, with_label=True)

    backfill_v2_from_legacy(db_path)
    backfill_v2_from_legacy(db_path)

    assert fetch_counts(
        db_path,
        (
            "devices",
            "profiles",
            "layers",
            "triggers",
            "actions",
            "bindings_v2",
            "legacy_context_migrations",
            "legacy_binding_migrations",
        ),
    ) == {
        "devices": 1,
        "profiles": 1,
        "layers": 1,
        "triggers": 1,
        "actions": 1,
        "bindings_v2": 1,
        "legacy_context_migrations": 1,
        "legacy_binding_migrations": 1,
    }


def test_backfill_leaves_legacy_rows_unchanged(tmp_path):
    db_path = tmp_path / "legacy-unchanged.db"
    create_legacy_fixture(db_path, with_label=True)
    before = legacy_snapshot(db_path)

    backfill_v2_from_legacy(db_path)

    assert legacy_snapshot(db_path) == before
