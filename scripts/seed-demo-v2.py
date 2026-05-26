#!/usr/bin/env python3
"""Seed idempotent v2 demo data for local /v2 verification."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.config import DB_PATH  # noqa: E402
from backend.migrations import init_schema  # noqa: E402


PROFILE_NAME = "Demo Workflow"
LAYER_NAME = "Default Layer"


def ensure_schema(db_path: Path) -> None:
    if not db_path.exists():
        init_schema(db_path)


def upsert_action(con: sqlite3.Connection, label: str, command: str) -> int:
    row = con.execute(
        "SELECT id FROM actions WHERE label = ? AND command = ? AND type = 'command'",
        (label, command),
    ).fetchone()
    if row:
        return int(row[0])
    cur = con.execute(
        """
        INSERT INTO actions(type, label, command, execution_mode, notify_text, notify_emoji)
        VALUES ('command', ?, ?, 'argv', '', '')
        """,
        (label, command),
    )
    return int(cur.lastrowid)


def upsert_trigger(
    con: sqlite3.Connection,
    *,
    event_type: str,
    channel: int,
    note: int | None = None,
    controller: int | None = None,
    value_min: int | None = None,
    value_max: int | None = None,
    velocity_min: int | None = None,
    velocity_max: int | None = None,
) -> int:
    row = con.execute(
        """
        SELECT id FROM triggers
        WHERE event_type = ?
          AND COALESCE(channel, -1) = COALESCE(?, -1)
          AND COALESCE(note, -1) = COALESCE(?, -1)
          AND COALESCE(controller, -1) = COALESCE(?, -1)
          AND COALESCE(value_min, -1) = COALESCE(?, -1)
          AND COALESCE(value_max, -1) = COALESCE(?, -1)
          AND COALESCE(velocity_min, -1) = COALESCE(?, -1)
          AND COALESCE(velocity_max, -1) = COALESCE(?, -1)
        """,
        (event_type, channel, note, controller, value_min, value_max, velocity_min, velocity_max),
    ).fetchone()
    if row:
        return int(row[0])
    cur = con.execute(
        """
        INSERT INTO triggers(
          event_type, channel, note, controller, value_min, value_max, velocity_min, velocity_max
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (event_type, channel, note, controller, value_min, value_max, velocity_min, velocity_max),
    )
    return int(cur.lastrowid)


def upsert_binding(
    con: sqlite3.Connection,
    *,
    profile_id: int,
    layer_id: int,
    trigger_id: int,
    action_id: int,
    label: str,
    notes: str,
) -> int:
    row = con.execute(
        """
        SELECT id FROM bindings_v2
        WHERE profile_id = ? AND layer_id = ? AND trigger_id = ? AND action_id = ?
        """,
        (profile_id, layer_id, trigger_id, action_id),
    ).fetchone()
    if row:
        binding_id = int(row[0])
        con.execute(
            """
            UPDATE bindings_v2
            SET enabled = 1,
                require_armed = 1,
                cooldown_ms = 200,
                notes = ?,
                display_label = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (notes, label, binding_id),
        )
        return binding_id
    cur = con.execute(
        """
        INSERT INTO bindings_v2(
          profile_id, layer_id, trigger_id, action_id, enabled, require_armed,
          cooldown_ms, notes, display_label, display_emoji
        )
        VALUES (?, ?, ?, ?, 1, 1, 200, ?, ?, '')
        """,
        (profile_id, layer_id, trigger_id, action_id, notes, label),
    )
    return int(cur.lastrowid)


def seed() -> dict[str, int | str]:
    db_path = Path(os.environ.get("MIDI_MAPPER_DB_PATH") or DB_PATH)
    ensure_schema(db_path)

    with sqlite3.connect(db_path) as con:
        con.execute("PRAGMA foreign_keys=ON")

        con.execute("UPDATE profiles SET active = 0")
        profile = con.execute("SELECT id FROM profiles WHERE name = ?", (PROFILE_NAME,)).fetchone()
        if profile:
            profile_id = int(profile[0])
            con.execute(
                """
                UPDATE profiles
                SET description = 'Seeded local v2 demo data',
                    active = 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (profile_id,),
            )
        else:
            cur = con.execute(
                """
                INSERT INTO profiles(name, description, active)
                VALUES (?, 'Seeded local v2 demo data', 1)
                """,
                (PROFILE_NAME,),
            )
            profile_id = int(cur.lastrowid)

        con.execute("UPDATE layers SET active = 0 WHERE profile_id = ?", (profile_id,))
        layer = con.execute(
            "SELECT id FROM layers WHERE profile_id = ? AND name = ?",
            (profile_id, LAYER_NAME),
        ).fetchone()
        if layer:
            layer_id = int(layer[0])
            con.execute(
                """
                UPDATE layers
                SET active = 1,
                    sort_order = 0,
                    color = '#00d4ff',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (layer_id,),
            )
        else:
            cur = con.execute(
                """
                INSERT INTO layers(profile_id, name, sort_order, color, active)
                VALUES (?, ?, 0, '#00d4ff', 1)
                """,
                (profile_id, LAYER_NAME),
            )
            layer_id = int(cur.lastrowid)

        note_action_id = upsert_action(con, "C3 triggered", 'echo "C3 triggered"')
        note_trigger_id = upsert_trigger(
            con,
            event_type="note_on",
            channel=1,
            note=60,
            velocity_min=1,
            velocity_max=127,
        )
        note_binding_id = upsert_binding(
            con,
            profile_id=profile_id,
            layer_id=layer_id,
            trigger_id=note_trigger_id,
            action_id=note_action_id,
            label="C3 triggered",
            notes="Seed demo note binding",
        )

        cc_action_id = upsert_action(con, "CC 21 high", 'echo "CC 21 high"')
        cc_trigger_id = upsert_trigger(
            con,
            event_type="control_change",
            channel=1,
            controller=21,
            value_min=100,
            value_max=127,
        )
        cc_binding_id = upsert_binding(
            con,
            profile_id=profile_id,
            layer_id=layer_id,
            trigger_id=cc_trigger_id,
            action_id=cc_action_id,
            label="CC 21 high",
            notes="Seed demo CC threshold binding",
        )

        con.commit()

    return {
        "db_path": str(db_path),
        "profile_id": profile_id,
        "layer_id": layer_id,
        "note_binding_id": note_binding_id,
        "cc_binding_id": cc_binding_id,
    }


if __name__ == "__main__":
    result = seed()
    print("Seeded v2 demo data")
    for key, value in result.items():
        print(f"{key}: {value}")
