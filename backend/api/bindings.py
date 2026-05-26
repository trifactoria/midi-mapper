from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from backend.api.v2_bindings import (
    V2BindingPatchIn,
    V2TriggerIn,
    get_v2_binding,
    validate_trigger,
)
from backend.actions.executor import safe_execute_command
from backend.actions.notifications import send_notification
from backend.db import db_connect, db_exec, db_fetchall, db_fetchone
from backend.schemas import BindingIn, BindingRunIn


router = APIRouter()


@router.get("/api/contexts/{context_id}/bindings")
async def list_bindings(context_id: int) -> List[Dict[str, Any]]:
    rows = await db_fetchall("SELECT * FROM bindings WHERE context_id=? ORDER BY id", (context_id,))
    return [dict(r) for r in rows]


@router.post("/api/bindings/set")
async def set_binding(b: BindingIn) -> Dict[str, Any]:
    """Set/update a binding. Uses single connection to ensure correct lastrowid."""
    async with db_connect() as db:
        # If id is provided, do direct UPDATE by id (more reliable for edits)
        if b.id is not None:
            await db.execute(
                """
                UPDATE bindings
                SET context_id=?, enabled=?, trig_type=?, note=?, cc=?,
                    value_min=?, value_max=?, pitch_min=?, pitch_max=?,
                    command=?, debounce_ms=?, require_armed=?,
                    notes=?, notify_text=?, notify_emoji=?
                WHERE id=?
                """,
                (
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
                    b.notes,
                    b.notify_text,
                    b.notify_emoji,
                    b.id,
                ),
            )
            await db.commit()
            return {"ok": True, "binding_id": b.id}

        # Otherwise, use UPSERT logic (for new bindings) on same connection
        cur = await db.execute(
            """
            INSERT INTO bindings(
              context_id, enabled, trig_type, note, cc, value_min, value_max, pitch_min, pitch_max,
              command, debounce_ms, require_armed, notes, notify_text, notify_emoji
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(context_id, trig_type, note, cc)
            DO UPDATE SET
              enabled=excluded.enabled,
              value_min=excluded.value_min,
              value_max=excluded.value_max,
              pitch_min=excluded.pitch_min,
              pitch_max=excluded.pitch_max,
              command=excluded.command,
              debounce_ms=excluded.debounce_ms,
              require_armed=excluded.require_armed,
              notes=excluded.notes,
              notify_text=excluded.notify_text,
              notify_emoji=excluded.notify_emoji
            """,
            (
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
                b.notes,
                b.notify_text,
                b.notify_emoji,
            ),
        )
        await db.commit()

        return {"ok": True, "binding_id": cur.lastrowid}


@router.post("/api/bindings/remove")
async def remove_binding(
    context_id: int,
    trig_type: int,
    note: Optional[int] = None,
    cc: Optional[int] = None,
) -> Dict[str, Any]:
    await db_exec(
        "DELETE FROM bindings WHERE context_id=? AND trig_type=? AND note IS ? AND cc IS ?",
        (context_id, trig_type, note, cc),
    )

    # Check if this was the last binding for the context
    row = await db_fetchone(
        "SELECT COUNT(*) as count FROM bindings WHERE context_id=?",
        (context_id,)
    )
    remaining_bindings = row["count"] if row else 0

    deleted_context = False
    if remaining_bindings == 0:
        # Delete the context (labels cascade automatically)
        await db_exec("DELETE FROM contexts WHERE id=?", (context_id,))
        deleted_context = True

    return {"ok": True, "deleted_context": deleted_context}


@router.post("/api/bindings/run")
async def run_binding(payload: BindingRunIn) -> Dict[str, Any]:
    """Manually test-run a binding's command."""
    # Fetch binding
    binding = await db_fetchone("SELECT * FROM bindings WHERE id=?", (payload.binding_id,))
    if not binding:
        return {"ok": False, "error": "Binding not found"}

    binding_dict = dict(binding)
    command = binding_dict.get("command", "")
    notify_text = binding_dict.get("notify_text", "")
    notify_emoji = binding_dict.get("notify_emoji", "")

    # Execute command first
    if not command:
        return {"ok": False, "error": "No command configured"}

    result = await safe_execute_command(command)

    # Send notification after command execution (if configured)
    notify_result = {}
    if notify_text:
        # Prepend error indicator if command failed
        prefix = "❌ " if not result.get("ok") else ""
        notify_result = await send_notification(prefix + notify_text, notify_emoji)

    # Merge notification result into response
    if notify_result and not notify_result.get("ok") and not notify_result.get("skipped"):
        result["notify_error"] = notify_result.get("notify_error")

    return result


@router.patch("/api/bindings/{binding_id}")
async def update_v2_binding(binding_id: int, payload: V2BindingPatchIn) -> Dict[str, Any]:
    existing = await get_v2_binding(binding_id)
    binding_updates = []
    binding_params: list[Any] = []

    for field_name in (
        "enabled",
        "require_armed",
        "cooldown_ms",
        "notes",
        "display_label",
        "display_color",
        "display_emoji",
    ):
        value = getattr(payload, field_name)
        if value is not None:
            binding_updates.append(f"{field_name} = ?")
            binding_params.append(value)

    trigger_updates = []
    trigger_params: list[Any] = []
    if payload.trigger is not None:
        merged_trigger = V2TriggerIn(
            event_type=payload.trigger.event_type if payload.trigger.event_type is not None else existing["trigger"]["event_type"],
            channel=payload.trigger.channel if payload.trigger.channel is not None else existing["trigger"]["channel"],
            note=payload.trigger.note if payload.trigger.note is not None else existing["trigger"]["note"],
            controller=payload.trigger.controller if payload.trigger.controller is not None else existing["trigger"]["controller"],
            value_min=payload.trigger.value_min if payload.trigger.value_min is not None else existing["trigger"]["value_min"],
            value_max=payload.trigger.value_max if payload.trigger.value_max is not None else existing["trigger"]["value_max"],
            velocity_min=payload.trigger.velocity_min if payload.trigger.velocity_min is not None else existing["trigger"]["velocity_min"],
            velocity_max=payload.trigger.velocity_max if payload.trigger.velocity_max is not None else existing["trigger"]["velocity_max"],
            device_id=payload.trigger.device_id if payload.trigger.device_id is not None else existing["trigger"]["device_id"],
            port_name=payload.trigger.port_name if payload.trigger.port_name is not None else existing["trigger"]["port_name"],
        )
        validate_trigger(merged_trigger)
        for field_name in (
            "event_type",
            "channel",
            "note",
            "controller",
            "value_min",
            "value_max",
            "velocity_min",
            "velocity_max",
            "device_id",
            "port_name",
        ):
            value = getattr(payload.trigger, field_name)
            if value is not None:
                trigger_updates.append(f"{field_name} = ?")
                trigger_params.append(value.strip() if field_name == "event_type" else value)

    action_updates = []
    action_params: list[Any] = []
    if payload.action is not None:
        if payload.action.type is not None and payload.action.type != "command":
            raise HTTPException(status_code=400, detail="Only command actions are supported")
        if payload.action.command is not None and not payload.action.command.strip():
            raise HTTPException(status_code=400, detail="Action command is required")
        for field_name in (
            "label",
            "command",
            "args_json",
            "working_directory",
            "execution_mode",
            "timeout_ms",
            "notify_text",
            "notify_emoji",
        ):
            value = getattr(payload.action, field_name)
            if value is not None:
                action_updates.append(f"{field_name} = ?")
                action_params.append(value)

    async with db_connect() as db:
        if binding_updates:
            binding_updates.append("updated_at = CURRENT_TIMESTAMP")
            await db.execute(
                f"UPDATE bindings_v2 SET {', '.join(binding_updates)} WHERE id = ?",
                (*binding_params, binding_id),
            )
        if trigger_updates:
            trigger_updates.append("updated_at = CURRENT_TIMESTAMP")
            await db.execute(
                f"UPDATE triggers SET {', '.join(trigger_updates)} WHERE id = ?",
                (*trigger_params, existing["trigger_id"]),
            )
        if action_updates:
            action_updates.append("updated_at = CURRENT_TIMESTAMP")
            await db.execute(
                f"UPDATE actions SET {', '.join(action_updates)} WHERE id = ?",
                (*action_params, existing["action_id"]),
            )
        await db.commit()

    return await get_v2_binding(binding_id)


@router.delete("/api/bindings/{binding_id}")
async def delete_v2_binding(binding_id: int) -> Dict[str, Any]:
    existing = await get_v2_binding(binding_id)
    trigger_id = existing["trigger_id"]
    action_id = existing["action_id"]
    deleted_trigger_id = None
    deleted_action_id = None

    async with db_connect() as db:
        await db.execute("DELETE FROM bindings_v2 WHERE id = ?", (binding_id,))

        trigger_cursor = await db.execute(
            "SELECT COUNT(*) AS count FROM bindings_v2 WHERE trigger_id = ?",
            (trigger_id,),
        )
        trigger_refs = await trigger_cursor.fetchone()
        if trigger_refs["count"] == 0:
            await db.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
            deleted_trigger_id = trigger_id

        action_cursor = await db.execute(
            "SELECT COUNT(*) AS count FROM bindings_v2 WHERE action_id = ?",
            (action_id,),
        )
        action_refs = await action_cursor.fetchone()
        if action_refs["count"] == 0:
            await db.execute("DELETE FROM actions WHERE id = ?", (action_id,))
            deleted_action_id = action_id

        await db.commit()

    return {
        "ok": True,
        "deleted_binding_id": binding_id,
        "deleted_trigger_id": deleted_trigger_id,
        "deleted_action_id": deleted_action_id,
    }
