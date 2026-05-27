import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.api.v2_bindings import list_binding_action_steps
from backend.db import db_connect, db_fetchall, db_fetchone

router = APIRouter()


class MacroCreateIn(BaseModel):
    name: str
    description: str = ""
    binding_id: int


class MacroApplyIn(BaseModel):
    binding_id: int
    replace_existing: bool = False


def _macro_response(row: Dict[str, Any]) -> Dict[str, Any]:
    try:
        actions = json.loads(row.get("actions_json") or "[]")
    except json.JSONDecodeError:
        actions = []
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "step_count": len(actions),
        "actions_json": row["actions_json"],
        "created_at": row["created_at"],
        "updated_at": row.get("updated_at"),
    }


@router.get("/api/macros")
async def list_macros() -> List[Dict[str, Any]]:
    rows = await db_fetchall("SELECT * FROM macros ORDER BY created_at DESC")
    return [_macro_response(dict(row)) for row in rows]


@router.post("/api/macros")
async def create_macro(payload: MacroCreateIn) -> Dict[str, Any]:
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="Macro name is required")

    steps = await list_binding_action_steps(payload.binding_id)
    if not steps:
        raise HTTPException(status_code=400, detail="Binding has no action steps to save as macro")

    actions_data = [
        {
            "type": step["type"],
            "label": step["label"],
            "command": step["command"],
            "duration_ms": step["duration_ms"],
            "working_directory": step["working_directory"],
            "execution_mode": step["execution_mode"],
            "timeout_ms": step["timeout_ms"],
            "notify_text": step["notify_text"],
            "notify_emoji": step["notify_emoji"],
            "enabled": step["enabled"],
        }
        for step in steps
    ]
    actions_json = json.dumps(actions_data)

    async with db_connect() as db:
        cursor = await db.execute(
            "INSERT INTO macros(name, description, actions_json) VALUES (?, ?, ?)",
            (payload.name.strip(), payload.description.strip(), actions_json),
        )
        macro_id = cursor.lastrowid
        await db.commit()

    row = await db_fetchone("SELECT * FROM macros WHERE id = ?", (macro_id,))
    return _macro_response(dict(row))


@router.get("/api/macros/{macro_id}")
async def get_macro(macro_id: int) -> Dict[str, Any]:
    row = await db_fetchone("SELECT * FROM macros WHERE id = ?", (macro_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Macro not found")
    return _macro_response(dict(row))


@router.delete("/api/macros/{macro_id}")
async def delete_macro(macro_id: int) -> Dict[str, Any]:
    row = await db_fetchone("SELECT id FROM macros WHERE id = ?", (macro_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Macro not found")
    async with db_connect() as db:
        await db.execute("DELETE FROM macros WHERE id = ?", (macro_id,))
        await db.commit()
    return {"ok": True, "deleted_macro_id": macro_id}


@router.post("/api/macros/{macro_id}/apply")
async def apply_macro(macro_id: int, payload: MacroApplyIn) -> Dict[str, Any]:
    macro_row = await db_fetchone("SELECT * FROM macros WHERE id = ?", (macro_id,))
    if not macro_row:
        raise HTTPException(status_code=404, detail="Macro not found")

    macro = dict(macro_row)
    try:
        actions_data: list = json.loads(macro["actions_json"])
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=500, detail="Macro data is corrupt")

    binding = await db_fetchone("SELECT id FROM bindings_v2 WHERE id = ?", (payload.binding_id,))
    if not binding:
        raise HTTPException(status_code=404, detail="Target binding not found")

    async with db_connect() as db:
        if payload.replace_existing:
            existing_rows = await db_fetchall(
                "SELECT action_id FROM binding_actions WHERE binding_id = ?",
                (payload.binding_id,),
            )
            await db.execute(
                "DELETE FROM binding_actions WHERE binding_id = ?",
                (payload.binding_id,),
            )
            for existing_row in existing_rows:
                aid = existing_row["action_id"]
                ref_cur = await db.execute(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM bindings_v2 WHERE action_id = ?) +
                      (SELECT COUNT(*) FROM binding_actions WHERE action_id = ?) +
                      (SELECT COUNT(*) FROM runs WHERE action_id = ?) AS cnt
                    """,
                    (aid, aid, aid),
                )
                row = await ref_cur.fetchone()
                if row["cnt"] == 0:
                    await db.execute("DELETE FROM actions WHERE id = ?", (aid,))

        order_cur = await db.execute(
            "SELECT COALESCE(MAX(execution_order), -1) AS max_order FROM binding_actions WHERE binding_id = ?",
            (payload.binding_id,),
        )
        order_row = await order_cur.fetchone()
        next_order = 0 if payload.replace_existing else (order_row["max_order"] + 1)

        added = 0
        for step_data in actions_data:
            cur = await db.execute(
                """
                INSERT INTO actions(
                  type, label, command, duration_ms, working_directory,
                  execution_mode, timeout_ms, notify_text, notify_emoji,
                  title, message, urgency
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_data.get("type", "command"),
                    step_data.get("label", ""),
                    step_data.get("command") or None,
                    step_data.get("duration_ms"),
                    step_data.get("working_directory") or None,
                    step_data.get("execution_mode") or "argv",
                    step_data.get("timeout_ms"),
                    step_data.get("notify_text") or "",
                    step_data.get("notify_emoji") or "",
                    step_data.get("title") or None,
                    step_data.get("message") or None,
                    step_data.get("urgency") or None,
                ),
            )
            new_action_id = cur.lastrowid
            await db.execute(
                """
                INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled)
                VALUES (?, ?, ?, ?)
                """,
                (payload.binding_id, new_action_id, next_order, 1 if step_data.get("enabled", 1) else 0),
            )
            next_order += 1
            added += 1

        await db.commit()

    return {"ok": True, "action_count": added, "binding_id": payload.binding_id}
