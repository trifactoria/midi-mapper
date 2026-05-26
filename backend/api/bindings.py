from typing import Any, Dict, List, Optional

from fastapi import APIRouter

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
