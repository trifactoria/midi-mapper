from typing import Any, Dict, Optional

from backend.db import db_fetchall, db_fetchone

from .normalize import effective_channel
from .state import ACTIVE_SELECTION


def selection_matches_event(port_name: str, msg: Any, derived_flat: Dict[str, int]) -> bool:
    sel_port = ACTIVE_SELECTION.get("port_name")
    if sel_port and sel_port != port_name:
        return False

    ch = effective_channel(port_name, msg)
    if ch != int(ACTIVE_SELECTION.get("channel", 0)):
        return False

    if derived_flat.get("bank_msb", 0) != int(ACTIVE_SELECTION.get("bank_msb", 0)):
        return False
    if derived_flat.get("bank_lsb", 0) != int(ACTIVE_SELECTION.get("bank_lsb", 0)):
        return False
    if derived_flat.get("program", 0) != int(ACTIVE_SELECTION.get("program", 0)):
        return False

    return True


async def binding_matches_message(context_id: int, msg: Any) -> Optional[Any]:
    if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=1 AND note=? AND enabled=1",
            (context_id, msg.note),
        )
    if msg.type == "control_change":
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=2 AND cc=? AND enabled=1",
            (context_id, msg.control),
        )
    if msg.type == "pitchwheel":
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=3 AND enabled=1 LIMIT 1",
            (context_id,),
        )
    if msg.type == "program_change":
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=4 AND enabled=1 LIMIT 1",
            (context_id,),
        )
    return None


async def get_matching_mode() -> str:
    row = await db_fetchone("SELECT value FROM settings WHERE key = 'matching_mode'")
    mode = row["value"] if row else "legacy"
    return mode if mode in ("legacy", "v2", "dual") else "legacy"


async def _automation_armed() -> bool:
    row = await db_fetchone("SELECT value FROM settings WHERE key = 'automation_armed'")
    return True if row is None else row["value"].lower() == "true"


async def _active_profile_id() -> Optional[int]:
    row = await db_fetchone("SELECT value FROM settings WHERE key = 'active_profile_id'")
    if row and str(row["value"]).isdigit():
        return int(row["value"])
    row = await db_fetchone("SELECT id FROM profiles WHERE active = 1 ORDER BY id LIMIT 1")
    return int(row["id"]) if row else None


async def _active_layer_id(profile_id: int) -> Optional[int]:
    row = await db_fetchone("SELECT value FROM settings WHERE key = 'active_layer_id'")
    if row and str(row["value"]).isdigit():
        layer = await db_fetchone(
            "SELECT id FROM layers WHERE id = ? AND profile_id = ?",
            (int(row["value"]), profile_id),
        )
        if layer:
            return int(layer["id"])
    row = await db_fetchone(
        "SELECT id FROM layers WHERE profile_id = ? AND active = 1 ORDER BY sort_order, id LIMIT 1",
        (profile_id,),
    )
    if row:
        return int(row["id"])
    row = await db_fetchone(
        "SELECT id FROM layers WHERE profile_id = ? ORDER BY sort_order, id LIMIT 1",
        (profile_id,),
    )
    return int(row["id"]) if row else None


async def _device_id_for_port(port_name: Optional[str]) -> Optional[int]:
    if not port_name:
        return None
    row = await db_fetchone("SELECT id FROM devices WHERE port_name = ?", (port_name,))
    return int(row["id"]) if row else None


def _message_event_type(msg: Any) -> Optional[str]:
    if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
        return "note_on"
    if msg.type == "control_change":
        return "control_change"
    if msg.type in ("pitchwheel", "pitch_bend"):
        return "pitch_bend"
    if msg.type == "program_change":
        return "program_change"
    return None


def _range_matches(value: Optional[int], min_value: Optional[int], max_value: Optional[int]) -> bool:
    if value is None:
        return min_value is None and max_value is None
    if min_value is not None and value < min_value:
        return False
    if max_value is not None and value > max_value:
        return False
    return True


def _candidate_matches(
    candidate: Dict[str, Any],
    *,
    port_name: Optional[str],
    device_id: Optional[int],
    msg: Any,
    derived_flat: Optional[Dict[str, int]],
) -> bool:
    if candidate["channel"] is not None and candidate["channel"] != getattr(msg, "channel", None):
        return False
    if candidate["port_name"] is not None and candidate["port_name"] != port_name:
        return False
    if candidate["device_id"] is not None and candidate["device_id"] != device_id:
        return False
    if candidate["note"] is not None and candidate["note"] != getattr(msg, "note", None):
        return False
    if candidate["controller"] is not None and candidate["controller"] != getattr(msg, "control", None):
        return False
    if not _range_matches(getattr(msg, "value", None), candidate["value_min"], candidate["value_max"]):
        return False
    if not _range_matches(getattr(msg, "velocity", None), candidate["velocity_min"], candidate["velocity_max"]):
        return False
    if derived_flat is not None:
        if candidate["bank_msb"] is not None and candidate["bank_msb"] != derived_flat.get("bank_msb"):
            return False
        if candidate["bank_lsb"] is not None and candidate["bank_lsb"] != derived_flat.get("bank_lsb"):
            return False
        if candidate["program_filter"] is not None and candidate["program_filter"] != derived_flat.get("program"):
            return False
    return True


def _v2_response(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row["binding_id"],
        "profile_id": row["profile_id"],
        "layer_id": row["layer_id"],
        "trigger_id": row["trigger_id"],
        "action_id": row["action_id"],
        "enabled": row["enabled"],
        "require_armed": row["require_armed"],
        "cooldown_ms": row["cooldown_ms"],
        "notes": row["notes"],
        "display_label": row["display_label"],
        "display_color": row["display_color"],
        "display_emoji": row["display_emoji"],
        "trigger": {
            "id": row["trigger_id"],
            "event_type": row["event_type"],
            "channel": row["channel"],
            "note": row["note"],
            "controller": row["controller"],
            "value_min": row["value_min"],
            "value_max": row["value_max"],
            "velocity_min": row["velocity_min"],
            "velocity_max": row["velocity_max"],
            "device_id": row["device_id"],
            "port_name": row["port_name"],
            "bank_msb": row["bank_msb"],
            "bank_lsb": row["bank_lsb"],
            "program_filter": row["program_filter"],
        },
        "action": {
            "id": row["action_id"],
            "type": row["action_type"],
            "label": row["action_label"],
            "command": row["command"],
            "args_json": row["args_json"],
            "working_directory": row["working_directory"],
            "execution_mode": row["execution_mode"],
            "timeout_ms": row["timeout_ms"],
            "notify_text": row["notify_text"],
            "notify_emoji": row["notify_emoji"],
        },
    }


async def binding_matches_message_v2(
    port_name: Optional[str],
    msg: Any,
    derived_flat: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    event_type = _message_event_type(msg)
    if event_type is None:
        return None

    profile_id = await _active_profile_id()
    if profile_id is None:
        return None
    layer_id = await _active_layer_id(profile_id)
    if layer_id is None:
        return None

    armed = await _automation_armed()
    candidates = await db_fetchall(
        """
        SELECT
          b.id AS binding_id,
          b.profile_id,
          b.layer_id,
          b.trigger_id,
          b.action_id,
          b.enabled,
          b.require_armed,
          b.cooldown_ms,
          b.notes,
          b.display_label,
          b.display_color,
          b.display_emoji,
          t.event_type,
          t.channel,
          t.note,
          t.controller,
          t.value_min,
          t.value_max,
          t.velocity_min,
          t.velocity_max,
          t.device_id,
          t.port_name,
          t.bank_msb,
          t.bank_lsb,
          t.program_filter,
          a.type AS action_type,
          a.label AS action_label,
          a.command,
          a.args_json,
          a.working_directory,
          a.execution_mode,
          a.timeout_ms,
          a.notify_text,
          a.notify_emoji
        FROM bindings_v2 b
        JOIN triggers t ON t.id = b.trigger_id
        JOIN actions a ON a.id = b.action_id
        WHERE b.profile_id = ?
          AND b.layer_id = ?
          AND b.enabled = 1
          AND t.event_type = ?
        ORDER BY b.id
        """,
        (profile_id, layer_id, event_type),
    )
    device_id = await _device_id_for_port(port_name)
    for candidate_row in candidates:
        candidate = dict(candidate_row)
        if candidate["require_armed"] and not armed:
            continue
        if _candidate_matches(
            candidate,
            port_name=port_name,
            device_id=device_id,
            msg=msg,
            derived_flat=derived_flat,
        ):
            return _v2_response(candidate)
    return None
