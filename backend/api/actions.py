import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.actions.executor import safe_execute_command
from backend.actions.history import record_v2_action_test_run
from backend.db import db_fetchone


router = APIRouter()


@router.get("/api/actions/{action_id}")
async def get_action(action_id: int) -> Dict[str, Any]:
    row = await db_fetchone(
        """
        SELECT
          id,
          type,
          label,
          command,
          args_json,
          working_directory,
          environment_json,
          execution_mode,
          timeout_ms,
          cooldown_ms,
          allow_concurrent,
          notify_text,
          notify_emoji,
          legacy_binding_id,
          created_at,
          updated_at
        FROM actions
        WHERE id = ?
        """,
        (action_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Action not found")
    return dict(row)


@router.post("/api/actions/{action_id}/dry_run")
async def dry_run_action(action_id: int) -> Dict[str, Any]:
    action = await get_action(action_id)
    if action["type"] != "command":
        raise HTTPException(status_code=400, detail="Only command actions are supported")
    return {
        "ok": True,
        "action_id": action_id,
        "type": action["type"],
        "label": action["label"],
        "command": action["command"],
        "execution_mode": action["execution_mode"],
        "summary": action["command"] or "",
        "would_execute": False,
    }


@router.post("/api/actions/{action_id}/test")
async def test_action(action_id: int) -> Dict[str, Any]:
    action = await get_action(action_id)
    if action["type"] != "command":
        raise HTTPException(status_code=400, detail="Only command actions are supported")
    if not action["command"]:
        raise HTTPException(status_code=400, detail="Action command is required")
    started_at = time.time()
    result = await safe_execute_command(action["command"])
    run_id = await record_v2_action_test_run(
        action_id=action_id,
        action_summary=action["command"],
        started_at=started_at,
        result=result,
    )
    result["action_id"] = action_id
    result["command"] = action["command"]
    result["run_id"] = run_id
    return result
