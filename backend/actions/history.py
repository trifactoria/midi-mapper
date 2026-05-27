import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.db import db_connect, db_fetchone


PREVIEW_LIMIT = 1000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    return text[:PREVIEW_LIMIT]


def _status_from_result(result: Dict[str, Any]) -> str:
    if result.get("ok"):
        return "success"
    error = str(result.get("error", "")).lower()
    if "timeout" in error:
        return "timeout"
    if result.get("exit_code") not in (None, 0):
        return "failed"
    return "error"


async def record_v2_action_test_run(
    *,
    action_id: int,
    action_summary: str,
    started_at: float,
    result: Dict[str, Any],
) -> int:
    """Record one v2 action test execution in runs."""
    finished_monotonic = time.time()
    finished_at = _now_iso()
    duration_ms = max(0, int((finished_monotonic - started_at) * 1000))
    binding = await db_fetchone(
        """
        SELECT id, profile_id, layer_id
        FROM bindings_v2
        WHERE action_id = ?
        ORDER BY id
        LIMIT 1
        """,
        (action_id,),
    )

    binding_id = binding["id"] if binding else None
    profile_id = binding["profile_id"] if binding else None
    layer_id = binding["layer_id"] if binding else None

    async with db_connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO runs(
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
              error_message
            )
            VALUES (?, ?, ?, ?, '{}', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                binding_id,
                profile_id,
                layer_id,
                action_summary,
                datetime.fromtimestamp(started_at, timezone.utc).isoformat(),
                finished_at,
                duration_ms,
                _status_from_result(result),
                result.get("exit_code"),
                _preview(result.get("stdout_preview") or result.get("stdout")),
                _preview(result.get("stderr_preview") or result.get("stderr")),
                _preview(result.get("error")),
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def record_v2_action_run(
    *,
    action_id: int,
    binding_id: int,
    profile_id: int,
    layer_id: int,
    trigger_snapshot_json: str,
    action_summary: str,
    started_at: float,
    result: Dict[str, Any],
    session_id: Optional[str] = None,
) -> int:
    """Record one live v2 binding action execution in runs."""
    finished_monotonic = time.time()
    finished_at = _now_iso()
    duration_ms = max(0, int((finished_monotonic - started_at) * 1000))

    async with db_connect() as db:
        cursor = await db.execute(
            """
            INSERT INTO runs(
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
              session_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                action_id,
                binding_id,
                profile_id,
                layer_id,
                trigger_snapshot_json,
                action_summary,
                datetime.fromtimestamp(started_at, timezone.utc).isoformat(),
                finished_at,
                duration_ms,
                _status_from_result(result),
                result.get("exit_code"),
                _preview(result.get("stdout_preview") or result.get("stdout")),
                _preview(result.get("stderr_preview") or result.get("stderr")),
                _preview(result.get("error")),
                session_id,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)
