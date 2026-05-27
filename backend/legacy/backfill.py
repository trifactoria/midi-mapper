import sqlite3
from pathlib import Path

from backend.config import DB_PATH


LEGACY_PROFILE_NAME = "Legacy Mappings"

TRIGGER_TYPES = {
    1: "note_on",
    2: "control_change",
    3: "pitch_bend",
    4: "program_change",
}


def _table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    return (
        con.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
        is not None
    )


def _legacy_binding_columns(con: sqlite3.Connection) -> set[str]:
    return {row["name"] for row in con.execute("PRAGMA table_info(bindings)")}


def _generated_layer_name(context: sqlite3.Row) -> str:
    return (
        f"Context {context['id']} - ch {context['channel']} "
        f"msb {context['bank_msb']} lsb {context['bank_lsb']} program {context['program']}"
    )


def _get_or_create_legacy_profile(con: sqlite3.Connection) -> int:
    row = con.execute(
        "SELECT id FROM profiles WHERE name = ? ORDER BY id LIMIT 1",
        (LEGACY_PROFILE_NAME,),
    ).fetchone()
    if row:
        return int(row["id"])

    has_active_profile = (
        con.execute("SELECT 1 FROM profiles WHERE active = 1 LIMIT 1").fetchone()
        is not None
    )
    cursor = con.execute(
        "INSERT INTO profiles(name, active) VALUES (?, ?)",
        (LEGACY_PROFILE_NAME, 0 if has_active_profile else 1),
    )
    return int(cursor.lastrowid)


def _backfill_devices(con: sqlite3.Connection) -> None:
    con.execute(
        """
        INSERT OR IGNORE INTO devices(name, port_name)
        SELECT name, name
        FROM ports
        """
    )


def _backfill_layers(con: sqlite3.Connection, profile_id: int) -> None:
    has_context_labels = _table_exists(con, "context_labels")
    label_select = "cl.label" if has_context_labels else "NULL"
    label_join = (
        "LEFT JOIN context_labels cl ON cl.context_id = c.id"
        if has_context_labels
        else ""
    )
    contexts = con.execute(
        f"""
        SELECT c.*, {label_select} AS label
        FROM contexts c
        {label_join}
        ORDER BY c.id
        """
    ).fetchall()

    for context in contexts:
        existing = con.execute(
            """
            SELECT layer_id
            FROM legacy_context_migrations
            WHERE legacy_context_id = ?
            """,
            (context["id"],),
        ).fetchone()
        if existing:
            continue

        layer_name = context["label"] or _generated_layer_name(context)
        cursor = con.execute(
            """
            INSERT INTO layers(profile_id, name, sort_order, legacy_context_id)
            VALUES (?, ?, ?, ?)
            """,
            (profile_id, layer_name, context["id"], context["id"]),
        )
        layer_id = int(cursor.lastrowid)
        con.execute(
            """
            INSERT INTO legacy_context_migrations(legacy_context_id, profile_id, layer_id)
            VALUES (?, ?, ?)
            """,
            (context["id"], profile_id, layer_id),
        )


def _backfill_bindings(con: sqlite3.Connection, profile_id: int) -> None:
    binding_columns = _legacy_binding_columns(con)
    optional_columns = {
        "notes": "''",
        "notify_text": "''",
        "notify_emoji": "''",
    }
    select_optional = [
        f"b.{column} AS {column}" if column in binding_columns else f"{fallback} AS {column}"
        for column, fallback in optional_columns.items()
    ]
    bindings = con.execute(
        f"""
        SELECT
          b.id,
          b.context_id,
          b.enabled,
          b.trig_type,
          b.note,
          b.cc,
          b.value_min,
          b.value_max,
          b.pitch_min,
          b.pitch_max,
          b.command,
          b.debounce_ms,
          b.require_armed,
          {", ".join(select_optional)},
          c.port_id,
          c.channel,
          c.bank_msb,
          c.bank_lsb,
          c.program,
          p.name AS port_name,
          d.id AS device_id,
          lcm.layer_id
        FROM bindings b
        JOIN contexts c ON c.id = b.context_id
        JOIN ports p ON p.id = c.port_id
        LEFT JOIN devices d ON d.port_name = p.name
        JOIN legacy_context_migrations lcm ON lcm.legacy_context_id = c.id
        ORDER BY b.id
        """
    ).fetchall()

    for binding in bindings:
        existing = con.execute(
            """
            SELECT 1
            FROM legacy_binding_migrations
            WHERE legacy_binding_id = ?
            """,
            (binding["id"],),
        ).fetchone()
        if existing:
            continue

        event_type = TRIGGER_TYPES.get(binding["trig_type"], str(binding["trig_type"]))
        trigger_cursor = con.execute(
            """
            INSERT INTO triggers(
              event_type,
              channel,
              note,
              controller,
              pitch_min,
              pitch_max,
              value_min,
              value_max,
              device_id,
              port_name,
              bank_msb,
              bank_lsb,
              program_filter,
              legacy_context_id,
              legacy_binding_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_type,
                binding["channel"],
                binding["note"],
                binding["cc"],
                binding["pitch_min"],
                binding["pitch_max"],
                binding["value_min"],
                binding["value_max"],
                binding["device_id"],
                binding["port_name"],
                binding["bank_msb"],
                binding["bank_lsb"],
                binding["program"],
                binding["context_id"],
                binding["id"],
            ),
        )
        trigger_id = int(trigger_cursor.lastrowid)

        action_cursor = con.execute(
            """
            INSERT INTO actions(
              type,
              command,
              execution_mode,
              cooldown_ms,
              notify_text,
              notify_emoji,
              legacy_binding_id
            )
            VALUES ('command', ?, 'argv', ?, ?, ?, ?)
            """,
            (
                binding["command"],
                binding["debounce_ms"],
                binding["notify_text"],
                binding["notify_emoji"],
                binding["id"],
            ),
        )
        action_id = int(action_cursor.lastrowid)

        binding_cursor = con.execute(
            """
            INSERT INTO bindings_v2(
              profile_id,
              layer_id,
              trigger_id,
              action_id,
              enabled,
              require_armed,
              cooldown_ms,
              notes,
              display_emoji,
              legacy_binding_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile_id,
                binding["layer_id"],
                trigger_id,
                action_id,
                binding["enabled"],
                binding["require_armed"],
                binding["debounce_ms"],
                binding["notes"],
                binding["notify_emoji"],
                binding["id"],
            ),
        )
        binding_v2_id = int(binding_cursor.lastrowid)

        con.execute(
            """
            INSERT OR IGNORE INTO binding_actions(
              binding_id,
              action_id,
              execution_order,
              enabled
            )
            VALUES (?, ?, 0, 1)
            """,
            (binding_v2_id, action_id),
        )

        con.execute(
            """
            INSERT INTO legacy_binding_migrations(
              legacy_binding_id,
              trigger_id,
              action_id,
              binding_v2_id
            )
            VALUES (?, ?, ?, ?)
            """,
            (binding["id"], trigger_id, action_id, binding_v2_id),
        )


def backfill_v2_from_legacy(db_path: str | Path | None = None) -> None:
    """Backfill v2 tables from legacy ports, contexts, labels, and bindings."""
    target_path = str(db_path or DB_PATH)
    con = sqlite3.connect(target_path)
    con.row_factory = sqlite3.Row
    try:
        con.execute("PRAGMA foreign_keys=ON")
        with con:
            _backfill_devices(con)
            profile_id = _get_or_create_legacy_profile(con)
            _backfill_layers(con, profile_id)
            _backfill_bindings(con, profile_id)
    finally:
        con.close()
