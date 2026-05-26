from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.v2_bindings import (
    V2BindingCreateIn,
    get_v2_binding,
    list_v2_bindings_for_layer,
    validate_action,
    validate_trigger,
)
from backend.db import db_connect, db_fetchone


router = APIRouter()


class LayerPatchIn(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    color: Optional[str] = None


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required")
    return cleaned


async def _get_layer(layer_id: int) -> Dict[str, Any]:
    row = await db_fetchone(
        """
        SELECT
          l.id,
          l.profile_id,
          l.name,
          l.sort_order,
          l.color,
          l.active,
          l.activation_trigger_id,
          l.legacy_context_id,
          l.created_at,
          l.updated_at,
          COUNT(b.id) AS binding_count
        FROM layers l
        LEFT JOIN bindings_v2 b ON b.layer_id = l.id
        WHERE l.id = ?
        GROUP BY l.id
        """,
        (layer_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Layer not found")
    return dict(row)


@router.get("/api/layers/{layer_id}/bindings")
async def list_layer_bindings(layer_id: int) -> List[Dict[str, Any]]:
    layer = await db_fetchone("SELECT id FROM layers WHERE id = ?", (layer_id,))
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    return await list_v2_bindings_for_layer(layer_id)


@router.post("/api/layers/{layer_id}/bindings")
async def create_layer_binding(layer_id: int, payload: V2BindingCreateIn) -> Dict[str, Any]:
    layer = await _get_layer(layer_id)
    validate_trigger(payload.trigger)
    validate_action(payload.action)

    async with db_connect() as db:
        trigger_cursor = await db.execute(
            """
            INSERT INTO triggers(
              event_type,
              channel,
              note,
              controller,
              value_min,
              value_max,
              velocity_min,
              velocity_max,
              device_id,
              port_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.trigger.event_type.strip(),
                payload.trigger.channel,
                payload.trigger.note,
                payload.trigger.controller,
                payload.trigger.value_min,
                payload.trigger.value_max,
                payload.trigger.velocity_min,
                payload.trigger.velocity_max,
                payload.trigger.device_id,
                payload.trigger.port_name,
            ),
        )
        trigger_id = trigger_cursor.lastrowid

        action_cursor = await db.execute(
            """
            INSERT INTO actions(
              type,
              label,
              command,
              args_json,
              working_directory,
              execution_mode,
              timeout_ms,
              cooldown_ms,
              notify_text,
              notify_emoji
            )
            VALUES ('command', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.action.label,
                payload.action.command,
                payload.action.args_json,
                payload.action.working_directory,
                payload.action.execution_mode,
                payload.action.timeout_ms,
                payload.cooldown_ms,
                payload.action.notify_text,
                payload.action.notify_emoji,
            ),
        )
        action_id = action_cursor.lastrowid

        binding_cursor = await db.execute(
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
              display_label,
              display_color,
              display_emoji
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                layer["profile_id"],
                layer_id,
                trigger_id,
                action_id,
                payload.enabled,
                payload.require_armed,
                payload.cooldown_ms,
                payload.notes,
                payload.display_label,
                payload.display_color,
                payload.display_emoji,
            ),
        )
        binding_id = binding_cursor.lastrowid
        await db.commit()

    return await get_v2_binding(binding_id)


@router.patch("/api/layers/{layer_id}")
async def update_layer(layer_id: int, payload: LayerPatchIn) -> Dict[str, Any]:
    await _get_layer(layer_id)

    updates = []
    params: list[Any] = []
    if payload.name is not None:
        updates.append("name = ?")
        params.append(_clean_name(payload.name))
    if payload.sort_order is not None:
        updates.append("sort_order = ?")
        params.append(payload.sort_order)
    if payload.color is not None:
        updates.append("color = ?")
        params.append(payload.color)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(layer_id)
        async with db_connect() as db:
            await db.execute(
                f"UPDATE layers SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            await db.commit()

    return await _get_layer(layer_id)


@router.post("/api/layers/{layer_id}/activate")
async def activate_layer(layer_id: int) -> Dict[str, Any]:
    layer = await _get_layer(layer_id)

    async with db_connect() as db:
        await db.execute(
            "UPDATE layers SET active = 0 WHERE profile_id = ?",
            (layer["profile_id"],),
        )
        await db.execute(
            "UPDATE layers SET active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (layer_id,),
        )
        await db.commit()
    return await _get_layer(layer_id)


@router.delete("/api/layers/{layer_id}")
async def delete_layer(layer_id: int) -> Dict[str, Any]:
    layer = await _get_layer(layer_id)
    activated_layer_id = None

    async with db_connect() as db:
        await db.execute("DELETE FROM layers WHERE id = ?", (layer_id,))
        if layer["active"]:
            cursor = await db.execute(
                """
                SELECT id
                FROM layers
                WHERE profile_id = ?
                ORDER BY sort_order, id
                LIMIT 1
                """,
                (layer["profile_id"],),
            )
            row = await cursor.fetchone()
            if row:
                activated_layer_id = row["id"]
                await db.execute(
                    "UPDATE layers SET active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (activated_layer_id,),
                )
        await db.commit()

    return {
        "ok": True,
        "deleted_layer_id": layer_id,
        "activated_layer_id": activated_layer_id,
    }
