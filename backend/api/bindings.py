from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.v2_bindings import (
    V2ActionIn,
    V2BindingPatchIn,
    V2TriggerIn,
    get_v2_binding,
    list_binding_action_steps,
    validate_action,
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
        "display_icon",
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
        merged_action = V2ActionIn(
            type=payload.action.type if payload.action.type is not None else existing["action"]["type"],
            label=payload.action.label if payload.action.label is not None else existing["action"]["label"],
            command=payload.action.command if payload.action.command is not None else existing["action"]["command"] or "",
            duration_ms=payload.action.duration_ms if payload.action.duration_ms is not None else existing["action"].get("duration_ms"),
            args_json=payload.action.args_json if payload.action.args_json is not None else existing["action"]["args_json"],
            working_directory=payload.action.working_directory if payload.action.working_directory is not None else existing["action"]["working_directory"],
            execution_mode=payload.action.execution_mode if payload.action.execution_mode is not None else existing["action"]["execution_mode"],
            timeout_ms=payload.action.timeout_ms if payload.action.timeout_ms is not None else existing["action"]["timeout_ms"],
            notify_text=payload.action.notify_text if payload.action.notify_text is not None else existing["action"]["notify_text"],
            notify_emoji=payload.action.notify_emoji if payload.action.notify_emoji is not None else existing["action"]["notify_emoji"],
            title=payload.action.title if payload.action.title is not None else existing["action"].get("title"),
            message=payload.action.message if payload.action.message is not None else existing["action"].get("message"),
            urgency=payload.action.urgency if payload.action.urgency is not None else existing["action"].get("urgency"),
        )
        validate_action(merged_action)
        for field_name in (
            "type",
            "label",
            "command",
            "duration_ms",
            "args_json",
            "working_directory",
            "execution_mode",
            "timeout_ms",
            "notify_text",
            "notify_emoji",
            "title",
            "message",
            "urgency",
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


@router.post("/api/bindings/{binding_id}/duplicate")
async def duplicate_v2_binding(binding_id: int) -> Dict[str, Any]:
    existing = await get_v2_binding(binding_id)

    async with db_connect() as db:
        cur = await db.execute(
            """
            INSERT INTO triggers(
              event_type, channel, note, controller, program,
              pitch_min, pitch_max, value_min, value_max,
              velocity_min, velocity_max, device_id, port_name,
              bank_msb, bank_lsb, program_filter, raw_match_json
            )
            SELECT
              event_type, channel, note, controller, program,
              pitch_min, pitch_max, value_min, value_max,
              velocity_min, velocity_max, device_id, port_name,
              bank_msb, bank_lsb, program_filter, raw_match_json
            FROM triggers WHERE id = ?
            """,
            (existing["trigger_id"],),
        )
        new_trigger_id = cur.lastrowid

        cur = await db.execute(
            """
            INSERT INTO actions(
              type, label, command, args_json, working_directory,
              duration_ms, environment_json, execution_mode, timeout_ms,
              cooldown_ms, allow_concurrent, notify_text, notify_emoji,
              title, message, urgency
            )
            SELECT
              type, label, command, args_json, working_directory,
              duration_ms, environment_json, execution_mode, timeout_ms,
              cooldown_ms, allow_concurrent, notify_text, notify_emoji,
              title, message, urgency
            FROM actions WHERE id = ?
            """,
            (existing["action_id"],),
        )
        new_action_id = cur.lastrowid

        cur = await db.execute(
            """
            INSERT INTO bindings_v2(
              profile_id, layer_id, trigger_id, action_id,
              enabled, require_armed, cooldown_ms, notes,
              display_label, display_color, display_emoji, display_icon
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                existing["profile_id"],
                existing["layer_id"],
                new_trigger_id,
                new_action_id,
                0,  # duplicates start disabled to avoid accidental double-firing
                existing["require_armed"],
                existing["cooldown_ms"],
                existing["notes"],
                existing["display_label"],
                existing["display_color"],
                existing["display_emoji"],
                existing["display_icon"],
            ),
        )
        new_binding_id = cur.lastrowid
        await db.execute(
            """
            INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled)
            VALUES (?, ?, 0, 1)
            """,
            (new_binding_id, new_action_id),
        )
        await db.commit()

    return await get_v2_binding(new_binding_id)


class BindingCloneIn(BaseModel):
    target_note: Optional[int] = None
    target_channel: Optional[int] = None
    target_controller: Optional[int] = None
    target_event_type: Optional[str] = None
    target_layer_id: Optional[int] = None
    enabled: int = 0


@router.post("/api/bindings/{binding_id}/clone")
async def clone_v2_binding(binding_id: int, payload: BindingCloneIn) -> Dict[str, Any]:
    """Clone a binding's full action sequence to a new trigger key."""
    existing = await get_v2_binding(binding_id)
    current_trigger = existing["trigger"]
    target_layer_id = payload.target_layer_id or existing["layer_id"]

    async with db_connect() as db:
        cur = await db.execute(
            """
            INSERT INTO triggers(
              event_type, channel, note, controller, program,
              pitch_min, pitch_max, value_min, value_max,
              velocity_min, velocity_max, device_id, port_name,
              bank_msb, bank_lsb, program_filter, raw_match_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.target_event_type or current_trigger["event_type"],
                payload.target_channel if payload.target_channel is not None else current_trigger["channel"],
                payload.target_note if payload.target_note is not None else current_trigger["note"],
                payload.target_controller if payload.target_controller is not None else current_trigger["controller"],
                current_trigger["program"],
                current_trigger["pitch_min"],
                current_trigger["pitch_max"],
                current_trigger["value_min"],
                current_trigger["value_max"],
                current_trigger["velocity_min"],
                current_trigger["velocity_max"],
                current_trigger["device_id"],
                current_trigger["port_name"],
                current_trigger["bank_msb"],
                current_trigger["bank_lsb"],
                current_trigger["program_filter"],
                current_trigger["raw_match_json"],
            ),
        )
        new_trigger_id = cur.lastrowid

        cur = await db.execute(
            """
            INSERT INTO actions(
              type, label, command, args_json, working_directory,
              duration_ms, environment_json, execution_mode, timeout_ms,
              cooldown_ms, allow_concurrent, notify_text, notify_emoji
            )
            SELECT type, label, command, args_json, working_directory,
              duration_ms, environment_json, execution_mode, timeout_ms,
              cooldown_ms, allow_concurrent, notify_text, notify_emoji
            FROM actions WHERE id = ?
            """,
            (existing["action_id"],),
        )
        new_action_id = cur.lastrowid

        cur = await db.execute(
            """
            INSERT INTO bindings_v2(
              profile_id, layer_id, trigger_id, action_id,
              enabled, require_armed, cooldown_ms, notes,
              display_label, display_color, display_emoji, display_icon
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                existing["profile_id"],
                target_layer_id,
                new_trigger_id,
                new_action_id,
                payload.enabled,
                existing["require_armed"],
                existing["cooldown_ms"],
                existing["notes"],
                existing["display_label"],
                existing["display_color"],
                existing["display_emoji"],
                existing["display_icon"],
            ),
        )
        new_binding_id = cur.lastrowid

        # Clone all binding_actions (deep-copy each action row)
        existing_steps = await list_binding_action_steps(binding_id)
        for step in existing_steps:
            cur = await db.execute(
                """
                INSERT INTO actions(
                  type, label, command, args_json, working_directory,
                  duration_ms, environment_json, execution_mode, timeout_ms,
                  cooldown_ms, allow_concurrent, notify_text, notify_emoji
                )
                SELECT type, label, command, args_json, working_directory,
                  duration_ms, environment_json, execution_mode, timeout_ms,
                  cooldown_ms, allow_concurrent, notify_text, notify_emoji
                FROM actions WHERE id = ?
                """,
                (step["action_id"],),
            )
            cloned_action_id = cur.lastrowid
            await db.execute(
                """
                INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled)
                VALUES (?, ?, ?, ?)
                """,
                (new_binding_id, cloned_action_id, step["execution_order"], step["enabled"]),
            )

        await db.commit()

    return await get_v2_binding(new_binding_id)


@router.delete("/api/bindings/{binding_id}")
async def delete_v2_binding(binding_id: int) -> Dict[str, Any]:
    existing = await get_v2_binding(binding_id)
    trigger_id = existing["trigger_id"]
    action_id = existing["action_id"]
    deleted_trigger_id = None
    deleted_action_id = None

    async with db_connect() as db:
        # Preserve run history: NULL out the FK reference so runs survive.
        await db.execute("UPDATE runs SET binding_id = NULL WHERE binding_id = ?", (binding_id,))
        # Migration tracking rows have a NOT NULL FK — remove them before the binding.
        await db.execute("DELETE FROM legacy_binding_migrations WHERE binding_v2_id = ?", (binding_id,))
        action_link_cur = await db.execute(
            "SELECT action_id FROM binding_actions WHERE binding_id = ?",
            (binding_id,),
        )
        linked_action_ids = {r["action_id"] for r in await action_link_cur.fetchall()}
        linked_action_ids.add(action_id)
        await db.execute("DELETE FROM bindings_v2 WHERE id = ?", (binding_id,))

        # Only delete trigger if nothing else references it.
        # layers.activation_trigger_id has no ON DELETE clause and would block deletion.
        trigger_binding_cur = await db.execute(
            "SELECT COUNT(*) AS count FROM bindings_v2 WHERE trigger_id = ?", (trigger_id,)
        )
        trigger_layer_cur = await db.execute(
            "SELECT COUNT(*) AS count FROM layers WHERE activation_trigger_id = ?", (trigger_id,)
        )
        trigger_binding_refs = (await trigger_binding_cur.fetchone())["count"]
        trigger_layer_refs = (await trigger_layer_cur.fetchone())["count"]
        if trigger_binding_refs == 0 and trigger_layer_refs == 0:
            await db.execute("DELETE FROM triggers WHERE id = ?", (trigger_id,))
            deleted_trigger_id = trigger_id

        # Only delete action if no bindings and no runs still reference it.
        # runs.action_id has no ON DELETE clause and would block deletion.
        for linked_action_id in linked_action_ids:
            action_binding_cur = await db.execute(
                """
                SELECT
                  (SELECT COUNT(*) FROM bindings_v2 WHERE action_id = ?) +
                  (SELECT COUNT(*) FROM binding_actions WHERE action_id = ?) AS count
                """,
                (linked_action_id, linked_action_id),
            )
            action_run_cur = await db.execute(
                "SELECT COUNT(*) AS count FROM runs WHERE action_id = ?", (linked_action_id,)
            )
            action_binding_refs = (await action_binding_cur.fetchone())["count"]
            action_run_refs = (await action_run_cur.fetchone())["count"]
            if action_binding_refs == 0 and action_run_refs == 0:
                await db.execute("DELETE FROM actions WHERE id = ?", (linked_action_id,))
                if linked_action_id == action_id:
                    deleted_action_id = action_id

        await db.commit()

    return {
        "ok": True,
        "deleted_binding_id": binding_id,
        "deleted_trigger_id": deleted_trigger_id,
        "deleted_action_id": deleted_action_id,
    }
