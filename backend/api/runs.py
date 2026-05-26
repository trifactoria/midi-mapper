from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from backend.db import db_fetchall, db_fetchone


router = APIRouter()


RUN_SELECT = """
    SELECT
      id,
      action_id,
      binding_id,
      profile_id,
      layer_id,
      trigger_snapshot_json,
      action_summary,
      started_at,
      finished_at,
      duration_ms,
      status,
      exit_code,
      stdout_preview,
      stderr_preview,
      error_message,
      created_at
    FROM runs
"""


@router.get("/api/runs")
async def list_runs() -> List[Dict[str, Any]]:
    rows = await db_fetchall(
        f"""
        {RUN_SELECT}
        ORDER BY started_at DESC, id DESC
        """
    )
    return [dict(row) for row in rows]


@router.get("/api/runs/{run_id}")
async def get_run(run_id: int) -> Dict[str, Any]:
    row = await db_fetchone(
        f"""
        {RUN_SELECT}
        WHERE id = ?
        """,
        (run_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")
    return dict(row)
