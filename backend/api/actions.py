import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.actions.executor import safe_execute_command
from backend.actions.history import record_v2_action_test_run
from backend.db import db_fetchone


router = APIRouter()


class ActionPreviewIn(BaseModel):
    type: str = "command"
    label: str = ""
    command: str = ""
    working_directory: str | None = None
    execution_mode: str = "argv"
    timeout_ms: int | None = None


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


@router.post("/api/actions/preview/test")
async def test_action_preview(payload: ActionPreviewIn) -> Dict[str, Any]:
    if payload.type != "command":
        raise HTTPException(status_code=400, detail="Only command actions are supported")
    command = payload.command.strip()
    if not command:
        raise HTTPException(status_code=400, detail="Action command is required")

    result = await safe_execute_command(
        command,
        timeout_ms=payload.timeout_ms,
        execution_mode=payload.execution_mode or "argv",
        working_directory=payload.working_directory,
    )
    result["command"] = command
    result["label"] = payload.label or command
    result["preview"] = True
    return result


@router.post("/api/actions/{action_id}/test")
async def test_action(action_id: int) -> Dict[str, Any]:
    action = await get_action(action_id)
    if action["type"] != "command":
        raise HTTPException(status_code=400, detail="Only command actions are supported")
    if not action["command"]:
        raise HTTPException(status_code=400, detail="Action command is required")
    started_at = time.time()
    result = await safe_execute_command(
        action["command"],
        timeout_ms=action.get("timeout_ms"),
        execution_mode=action.get("execution_mode", "argv"),
    )
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
