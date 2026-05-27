from typing import Any, Dict, Optional

from fastapi import HTTPException
from pydantic import BaseModel

from backend.db import db_fetchall, db_fetchone


SUPPORTED_ACTION_TYPES = {"command", "delay", "notification", "open_url", "open_app", "hotkey"}


class V2TriggerIn(BaseModel):
    event_type: Optional[str] = None
    channel: Optional[int] = None
    note: Optional[int] = None
    controller: Optional[int] = None
    value_min: Optional[int] = None
    value_max: Optional[int] = None
    velocity_min: Optional[int] = None
    velocity_max: Optional[int] = None
    device_id: Optional[int] = None
    port_name: Optional[str] = None


class V2ActionIn(BaseModel):
    type: str = "command"
    label: str = ""
    command: str = ""
    duration_ms: Optional[int] = None
    args_json: Optional[str] = None
    working_directory: Optional[str] = None
    execution_mode: str = "argv"
    timeout_ms: Optional[int] = None
    notify_text: str = ""
    notify_emoji: str = ""
    title: Optional[str] = None
    message: Optional[str] = None
    urgency: Optional[str] = None


class V2ActionPatchIn(BaseModel):
    type: Optional[str] = None
    label: Optional[str] = None
    command: Optional[str] = None
    duration_ms: Optional[int] = None
    args_json: Optional[str] = None
    working_directory: Optional[str] = None
    execution_mode: Optional[str] = None
    timeout_ms: Optional[int] = None
    notify_text: Optional[str] = None
    notify_emoji: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    urgency: Optional[str] = None


class V2BindingCreateIn(BaseModel):
    trigger: V2TriggerIn
    action: V2ActionIn
    enabled: int = 1
    require_armed: int = 1
    cooldown_ms: int = 200
    notes: str = ""
    display_label: str = ""
    display_color: Optional[str] = None
    display_emoji: str = ""
    display_icon: str = ""


class V2BindingPatchIn(BaseModel):
    trigger: Optional[V2TriggerIn] = None
    action: Optional[V2ActionPatchIn] = None
    enabled: Optional[int] = None
    require_armed: Optional[int] = None
    cooldown_ms: Optional[int] = None
    notes: Optional[str] = None
    display_label: Optional[str] = None
    display_color: Optional[str] = None
    display_emoji: Optional[str] = None
    display_icon: Optional[str] = None


def _validate_midi_range(field_name: str, value: Optional[int]) -> None:
    if value is not None and not 0 <= value <= 127:
        raise HTTPException(status_code=400, detail=f"{field_name} must be between 0 and 127")


def validate_trigger(trigger: V2TriggerIn) -> None:
    if not trigger.event_type or not trigger.event_type.strip():
        raise HTTPException(status_code=400, detail="Trigger event_type is required")
    for field_name in (
        "channel",
        "note",
        "controller",
        "value_min",
        "value_max",
        "velocity_min",
        "velocity_max",
    ):
        _validate_midi_range(field_name, getattr(trigger, field_name))
    if (
        trigger.value_min is not None
        and trigger.value_max is not None
        and trigger.value_min > trigger.value_max
    ):
        raise HTTPException(status_code=400, detail="value_min cannot be greater than value_max")
    if (
        trigger.velocity_min is not None
        and trigger.velocity_max is not None
        and trigger.velocity_min > trigger.velocity_max
    ):
        raise HTTPException(status_code=400, detail="velocity_min cannot be greater than velocity_max")


def validate_action(action: V2ActionIn) -> None:
    if action.type not in SUPPORTED_ACTION_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid action type: {action.type}")
    if action.type == "command" and not action.command.strip():
        raise HTTPException(status_code=400, detail="Action command is required")
    if action.type == "delay" and (action.duration_ms is None or action.duration_ms < 0):
        raise HTTPException(status_code=400, detail="Delay duration_ms must be 0 or greater")
    if action.type == "notification" and not (action.title or "").strip():
        raise HTTPException(status_code=400, detail="Notification title is required")
    if action.type in ("open_url", "open_app", "hotkey") and not action.command.strip():
        raise HTTPException(status_code=400, detail=f"{action.type} requires a command/url/shortcut")
    if action.urgency and action.urgency not in ("low", "normal", "critical"):
        raise HTTPException(status_code=400, detail="urgency must be low, normal, or critical")


async def list_binding_action_steps(binding_id: int) -> list[Dict[str, Any]]:
    rows = await db_fetchall(
        """
        SELECT
          ba.id AS binding_action_id,
          ba.binding_id,
          ba.action_id,
          ba.execution_order,
          ba.enabled,
          a.type,
          a.label,
          a.command,
          a.duration_ms,
          a.args_json,
          a.working_directory,
          a.environment_json,
          a.execution_mode,
          a.timeout_ms,
          a.cooldown_ms,
          a.allow_concurrent,
          a.notify_text,
          a.notify_emoji,
          a.title,
          a.message,
          a.urgency,
          a.legacy_binding_id
        FROM binding_actions ba
        JOIN actions a ON a.id = ba.action_id
        WHERE ba.binding_id = ?
        ORDER BY ba.execution_order, ba.id
        """,
        (binding_id,),
    )
    return [
        {
            "binding_action_id": row["binding_action_id"],
            "binding_id": row["binding_id"],
            "id": row["action_id"],
            "action_id": row["action_id"],
            "execution_order": row["execution_order"],
            "enabled": row["enabled"],
            "type": row["type"],
            "label": row["label"],
            "command": row["command"],
            "duration_ms": row["duration_ms"],
            "args_json": row["args_json"],
            "working_directory": row["working_directory"],
            "environment_json": row["environment_json"],
            "execution_mode": row["execution_mode"],
            "timeout_ms": row["timeout_ms"],
            "cooldown_ms": row["cooldown_ms"],
            "allow_concurrent": row["allow_concurrent"],
            "notify_text": row["notify_text"],
            "notify_emoji": row["notify_emoji"],
            "title": row["title"],
            "message": row["message"],
            "urgency": row["urgency"],
            "legacy_binding_id": row["legacy_binding_id"],
        }
        for row in rows
    ]


def _binding_response(row: Dict[str, Any]) -> Dict[str, Any]:
    primary_action = {
        "id": row["action_id"],
        "type": row["action_type"],
        "label": row["action_label"],
        "command": row["command"],
        "duration_ms": row["duration_ms"],
        "args_json": row["args_json"],
        "working_directory": row["working_directory"],
        "environment_json": row["environment_json"],
        "execution_mode": row["execution_mode"],
        "timeout_ms": row["timeout_ms"],
        "cooldown_ms": row["action_cooldown_ms"],
        "allow_concurrent": row["allow_concurrent"],
        "notify_text": row["notify_text"],
        "notify_emoji": row["notify_emoji"],
        "title": row["action_title"],
        "message": row["action_message"],
        "urgency": row["action_urgency"],
        "legacy_binding_id": row["action_legacy_binding_id"],
    }
    actions = row["actions"] if "actions" in row else [primary_action]
    return {
        "id": row["id"],
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
        "display_icon": row["display_icon"],
        "legacy_binding_id": row["legacy_binding_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "trigger": {
            "id": row["trigger_id"],
            "event_type": row["event_type"],
            "channel": row["channel"],
            "note": row["note"],
            "controller": row["controller"],
            "program": row["program"],
            "pitch_min": row["pitch_min"],
            "pitch_max": row["pitch_max"],
            "value_min": row["value_min"],
            "value_max": row["value_max"],
            "velocity_min": row["velocity_min"],
            "velocity_max": row["velocity_max"],
            "device_id": row["device_id"],
            "port_name": row["port_name"],
            "bank_msb": row["bank_msb"],
            "bank_lsb": row["bank_lsb"],
            "program_filter": row["program_filter"],
            "raw_match_json": row["raw_match_json"],
            "legacy_context_id": row["trigger_legacy_context_id"],
            "legacy_binding_id": row["trigger_legacy_binding_id"],
        },
        "action": primary_action,
        "actions": actions,
    }


BINDING_SELECT = """
    SELECT
      b.id,
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
      b.display_icon,
      b.legacy_binding_id,
      b.created_at,
      b.updated_at,
      t.event_type,
      t.channel,
      t.note,
      t.controller,
      t.program,
      t.pitch_min,
      t.pitch_max,
      t.value_min,
      t.value_max,
      t.velocity_min,
      t.velocity_max,
      t.device_id,
      t.port_name,
      t.bank_msb,
      t.bank_lsb,
      t.program_filter,
      t.raw_match_json,
      t.legacy_context_id AS trigger_legacy_context_id,
      t.legacy_binding_id AS trigger_legacy_binding_id,
      a.type AS action_type,
      a.label AS action_label,
      a.command,
      a.duration_ms,
      a.args_json,
      a.working_directory,
      a.environment_json,
      a.execution_mode,
      a.timeout_ms,
      a.cooldown_ms AS action_cooldown_ms,
      a.allow_concurrent,
      a.notify_text,
      a.notify_emoji,
      a.title AS action_title,
      a.message AS action_message,
      a.urgency AS action_urgency,
      a.legacy_binding_id AS action_legacy_binding_id
    FROM bindings_v2 b
    JOIN triggers t ON t.id = b.trigger_id
    JOIN actions a ON a.id = b.action_id
"""


async def get_v2_binding(binding_id: int) -> Dict[str, Any]:
    row = await db_fetchone(
        f"""
        {BINDING_SELECT}
        WHERE b.id = ?
        """,
        (binding_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Binding not found")
    data = dict(row)
    data["actions"] = await list_binding_action_steps(binding_id)
    return _binding_response(data)


async def list_v2_bindings_for_layer(layer_id: int) -> list[Dict[str, Any]]:
    rows = await db_fetchall(
        f"""
        {BINDING_SELECT}
        WHERE b.layer_id = ?
        ORDER BY b.id
        """,
        (layer_id,),
    )
    result = []
    for row in rows:
        data = dict(row)
        data["actions"] = await list_binding_action_steps(int(data["id"]))
        result.append(_binding_response(data))
    return result
