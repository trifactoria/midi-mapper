import asyncio
import shlex
import time
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.actions.executor import execute_hotkey, execute_notification, safe_execute_command
from backend.actions.history import record_v2_action_test_run
from backend.db import db_connect, db_fetchall, db_fetchone

_NATIVE_ACTION_TYPES = {"notification", "open_url", "open_app", "hotkey"}


router = APIRouter()


class ActionPreviewIn(BaseModel):
    type: str = "command"
    label: str = ""
    command: str = ""
    working_directory: str | None = None
    execution_mode: str = "argv"
    timeout_ms: int | None = None
    title: str | None = None
    message: str | None = None
    urgency: str | None = None


class BindingActionCreateIn(BaseModel):
    type: str = "delay"
    label: str = ""
    command: str = ""
    duration_ms: int | None = None
    working_directory: str | None = None
    execution_mode: str = "argv"
    timeout_ms: int | None = None
    enabled: int = 1
    title: str | None = None
    message: str | None = None
    urgency: str | None = None


class BindingActionPatchIn(BaseModel):
    execution_order: int | None = None
    enabled: int | None = None
    label: str | None = None
    command: str | None = None
    duration_ms: int | None = None
    working_directory: str | None = None
    execution_mode: str | None = None
    timeout_ms: int | None = None
    title: str | None = None
    message: str | None = None
    urgency: str | None = None


@router.get("/api/actions/{action_id}")
async def get_action(action_id: int) -> Dict[str, Any]:
    row = await db_fetchone(
        """
        SELECT
          id,
          type,
          label,
          command,
          duration_ms,
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
    action_type = action["type"]
    if action_type == "delay":
        duration_ms = max(0, int(action["duration_ms"] or 0))
        return {
            "ok": True, "action_id": action_id, "type": "delay",
            "label": action["label"], "duration_ms": duration_ms,
            "summary": f"Wait {duration_ms}ms", "would_execute": False,
        }
    if action_type == "notification":
        title = (action.get("title") or "").strip() or action["label"] or "Notification"
        return {
            "ok": True, "action_id": action_id, "type": "notification",
            "label": action["label"], "title": title,
            "message": action.get("message") or "",
            "urgency": action.get("urgency") or None,
            "summary": f"Notify: {title}", "would_execute": False,
        }
    if action_type in _NATIVE_ACTION_TYPES:
        cmd = action.get("command") or ""
        return {
            "ok": True, "action_id": action_id, "type": action_type,
            "label": action["label"], "command": cmd,
            "summary": _native_summary(action_type, action), "would_execute": False,
        }
    if action_type != "command":
        raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")
    result = {
        "ok": True, "action_id": action_id, "type": action_type,
        "label": action["label"], "command": action["command"],
        "execution_mode": action["execution_mode"],
        "summary": action["command"] or "", "would_execute": False,
    }
    if action["duration_ms"] is not None:
        result["duration_ms"] = action["duration_ms"]
    return result


def _native_summary(action_type: str, action: Dict[str, Any]) -> str:
    if action_type == "notification":
        return f"Notify: {(action.get('title') or '').strip() or action.get('label') or 'Notification'}"
    if action_type == "open_url":
        return f"Open URL: {action.get('command') or ''}"
    if action_type == "open_app":
        cmd = (action.get("command") or "").split()
        return f"Open App: {cmd[0] if cmd else 'app'}"
    if action_type == "hotkey":
        return f"Hotkey: {action.get('command') or ''}"
    return action.get("command") or ""


async def _binding_exists(binding_id: int) -> bool:
    return await db_fetchone("SELECT id FROM bindings_v2 WHERE id = ?", (binding_id,)) is not None


def _validate_step_payload(payload: BindingActionCreateIn) -> None:
    valid_types = {"command", "delay", "notification", "open_url", "open_app", "hotkey"}
    if payload.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid action type: {payload.type}")
    if payload.type == "command" and not payload.command.strip():
        raise HTTPException(status_code=400, detail="Action command is required")
    if payload.type == "delay" and (payload.duration_ms is None or payload.duration_ms < 0):
        raise HTTPException(status_code=400, detail="Delay duration_ms must be 0 or greater")
    if payload.type == "notification" and not (payload.title or "").strip():
        raise HTTPException(status_code=400, detail="Notification title is required")
    if payload.type in ("open_url", "open_app", "hotkey") and not payload.command.strip():
        raise HTTPException(status_code=400, detail=f"{payload.type} requires a command/url/shortcut")
    if payload.urgency and payload.urgency not in ("low", "normal", "critical"):
        raise HTTPException(status_code=400, detail="urgency must be low, normal, or critical")


async def _list_binding_steps(binding_id: int) -> list[Dict[str, Any]]:
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
          a.working_directory,
          a.execution_mode,
          a.timeout_ms,
          a.title,
          a.message,
          a.urgency
        FROM binding_actions ba
        JOIN actions a ON a.id = ba.action_id
        WHERE ba.binding_id = ?
        ORDER BY ba.execution_order, ba.id
        """,
        (binding_id,),
    )
    return [dict(row) for row in rows]


async def _next_group_order(binding_id: int) -> int:
    row = await db_fetchone(
        """
        SELECT COALESCE(MAX(ba.execution_order), -1) + 1 AS next_order
        FROM binding_actions ba
        JOIN bindings_v2 b ON b.id = ba.binding_id
        JOIN triggers t ON t.id = b.trigger_id
        JOIN bindings_v2 source ON source.id = ?
        JOIN triggers source_t ON source_t.id = source.trigger_id
        WHERE b.layer_id = source.layer_id
          AND t.event_type = source_t.event_type
          AND COALESCE(t.channel, -1) = COALESCE(source_t.channel, -1)
          AND COALESCE(t.note, -1) = COALESCE(source_t.note, -1)
          AND COALESCE(t.controller, -1) = COALESCE(source_t.controller, -1)
          AND COALESCE(t.velocity_min, -1) = COALESCE(source_t.velocity_min, -1)
          AND COALESCE(t.velocity_max, -1) = COALESCE(source_t.velocity_max, -1)
          AND COALESCE(t.value_min, -1) = COALESCE(source_t.value_min, -1)
          AND COALESCE(t.value_max, -1) = COALESCE(source_t.value_max, -1)
          AND COALESCE(t.port_name, '') = COALESCE(source_t.port_name, '')
        """,
        (binding_id,),
    )
    return int(row["next_order"] if row else 0)


@router.get("/api/bindings/{binding_id}/actions")
async def list_binding_actions(binding_id: int) -> list[Dict[str, Any]]:
    if not await _binding_exists(binding_id):
        raise HTTPException(status_code=404, detail="Binding not found")
    return await _list_binding_steps(binding_id)


@router.post("/api/bindings/{binding_id}/actions")
async def create_binding_action(binding_id: int, payload: BindingActionCreateIn) -> Dict[str, Any]:
    if not await _binding_exists(binding_id):
        raise HTTPException(status_code=404, detail="Binding not found")
    _validate_step_payload(payload)

    next_order = await _next_group_order(binding_id)
    async with db_connect() as db:
        _cmd_types = {"command", "open_url", "open_app", "hotkey"}
        action_cur = await db.execute(
            """
            INSERT INTO actions(
              type, label, command, duration_ms, working_directory,
              execution_mode, timeout_ms, title, message, urgency
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.type,
                payload.label,
                payload.command if payload.type in _cmd_types else None,
                payload.duration_ms if payload.type == "delay" else None,
                payload.working_directory,
                payload.execution_mode,
                payload.timeout_ms,
                payload.title if payload.type == "notification" else None,
                payload.message if payload.type == "notification" else None,
                payload.urgency if payload.type == "notification" else None,
            ),
        )
        action_id = action_cur.lastrowid
        link_cur = await db.execute(
            """
            INSERT INTO binding_actions(binding_id, action_id, execution_order, enabled)
            VALUES (?, ?, ?, ?)
            """,
            (binding_id, action_id, next_order, payload.enabled),
        )
        await db.commit()
    steps = await _list_binding_steps(binding_id)
    return next(step for step in steps if step["binding_action_id"] == link_cur.lastrowid)


@router.patch("/api/bindings/{binding_id}/actions/{binding_action_id}")
async def update_binding_action(
    binding_id: int,
    binding_action_id: int,
    payload: BindingActionPatchIn,
) -> Dict[str, Any]:
    step = await db_fetchone(
        """
        SELECT ba.id, ba.action_id, a.type
        FROM binding_actions ba
        JOIN actions a ON a.id = ba.action_id
        WHERE ba.id = ? AND ba.binding_id = ?
        """,
        (binding_action_id, binding_id),
    )
    if not step:
        raise HTTPException(status_code=404, detail="Binding action not found")

    link_updates = []
    link_params: list[Any] = []
    if payload.execution_order is not None:
        link_updates.append("execution_order = ?")
        link_params.append(payload.execution_order)
    if payload.enabled is not None:
        link_updates.append("enabled = ?")
        link_params.append(payload.enabled)

    action_updates = []
    action_params: list[Any] = []
    for field_name in ("label", "command", "duration_ms", "working_directory", "execution_mode", "timeout_ms", "title", "message", "urgency"):
        value = getattr(payload, field_name)
        if value is not None:
            action_updates.append(f"{field_name} = ?")
            action_params.append(value)

    if step["type"] == "delay" and payload.duration_ms is not None and payload.duration_ms < 0:
        raise HTTPException(status_code=400, detail="Delay duration_ms must be 0 or greater")
    if step["type"] == "command" and payload.command is not None and not payload.command.strip():
        raise HTTPException(status_code=400, detail="Action command is required")

    async with db_connect() as db:
        if link_updates:
            link_updates.append("updated_at = CURRENT_TIMESTAMP")
            await db.execute(
                f"UPDATE binding_actions SET {', '.join(link_updates)} WHERE id = ? AND binding_id = ?",
                (*link_params, binding_action_id, binding_id),
            )
        if action_updates:
            action_updates.append("updated_at = CURRENT_TIMESTAMP")
            await db.execute(
                f"UPDATE actions SET {', '.join(action_updates)} WHERE id = ?",
                (*action_params, step["action_id"]),
            )
        await db.commit()

    return next(step for step in await _list_binding_steps(binding_id) if step["binding_action_id"] == binding_action_id)


@router.delete("/api/bindings/{binding_id}/actions/{binding_action_id}")
async def delete_binding_action(binding_id: int, binding_action_id: int) -> Dict[str, Any]:
    step = await db_fetchone(
        "SELECT action_id FROM binding_actions WHERE id = ? AND binding_id = ?",
        (binding_action_id, binding_id),
    )
    if not step:
        raise HTTPException(status_code=404, detail="Binding action not found")
    action_id = int(step["action_id"])
    deleted_action_id = None
    async with db_connect() as db:
        await db.execute(
            "DELETE FROM binding_actions WHERE id = ? AND binding_id = ?",
            (binding_action_id, binding_id),
        )
        refs_cur = await db.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM binding_actions WHERE action_id = ?) +
              (SELECT COUNT(*) FROM bindings_v2 WHERE action_id = ?) +
              (SELECT COUNT(*) FROM runs WHERE action_id = ?) AS count
            """,
            (action_id, action_id, action_id),
        )
        if (await refs_cur.fetchone())["count"] == 0:
            await db.execute("DELETE FROM actions WHERE id = ?", (action_id,))
            deleted_action_id = action_id
        await db.commit()
    return {
        "ok": True,
        "deleted_binding_action_id": binding_action_id,
        "deleted_action_id": deleted_action_id,
    }


@router.post("/api/bindings/{binding_id}/actions/reorder")
async def reorder_binding_actions(binding_id: int, ordered_ids: list[int]) -> Dict[str, Any]:
    existing = await _list_binding_steps(binding_id)
    existing_ids = {int(step["binding_action_id"]) for step in existing}
    if set(ordered_ids) != existing_ids:
        raise HTTPException(status_code=400, detail="ordered_ids must include every binding action id exactly once")
    async with db_connect() as db:
        for index, binding_action_id in enumerate(ordered_ids):
            await db.execute(
                "UPDATE binding_actions SET execution_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND binding_id = ?",
                (index, binding_action_id, binding_id),
            )
        await db.commit()
    return {"ok": True, "actions": await _list_binding_steps(binding_id)}


@router.post("/api/action-groups/reorder")
async def reorder_action_group_steps(ordered_ids: list[int]) -> Dict[str, Any]:
    if not ordered_ids:
        raise HTTPException(status_code=400, detail="ordered_ids is required")
    placeholders = ",".join("?" for _ in ordered_ids)
    rows = await db_fetchall(
        f"SELECT id FROM binding_actions WHERE id IN ({placeholders})",
        tuple(ordered_ids),
    )
    found = {int(row["id"]) for row in rows}
    if found != set(ordered_ids):
        raise HTTPException(status_code=400, detail="ordered_ids contains unknown binding action id")
    async with db_connect() as db:
        for index, binding_action_id in enumerate(ordered_ids):
            await db.execute(
                "UPDATE binding_actions SET execution_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (index, binding_action_id),
            )
        await db.commit()
    return {"ok": True}


@router.post("/api/actions/preview/test")
async def test_action_preview(payload: ActionPreviewIn) -> Dict[str, Any]:
    action_type = payload.type

    if action_type == "notification":
        title = (payload.title or "").strip() or payload.label or "Notification"
        result = await execute_notification(title, payload.message or "", payload.urgency or None)
        result["label"] = payload.label or title
        result["summary"] = f"Notify: {title}"
        result["preview"] = True
        return result

    if action_type == "open_url":
        url = payload.command.strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        result = await safe_execute_command(f"xdg-open {shlex.quote(url)}", execution_mode="detached")
        result["label"] = payload.label or url
        result["summary"] = f"Open URL: {url}"
        result["preview"] = True
        return result

    if action_type == "open_app":
        app_cmd = payload.command.strip()
        if not app_cmd:
            raise HTTPException(status_code=400, detail="App command is required")
        result = await safe_execute_command(app_cmd, execution_mode="detached")
        exe = app_cmd.split()[0]
        result["label"] = payload.label or exe
        result["summary"] = f"Open App: {exe}"
        result["preview"] = True
        return result

    if action_type == "hotkey":
        shortcut = payload.command.strip()
        if not shortcut:
            raise HTTPException(status_code=400, detail="Shortcut is required")
        result = await execute_hotkey(shortcut)
        result["label"] = payload.label or shortcut
        result["summary"] = f"Hotkey: {shortcut}"
        result["preview"] = True
        return result

    if action_type != "command":
        raise HTTPException(status_code=400, detail=f"Unsupported action type for preview: {action_type}")

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
    action_type = action["type"]
    started_at = time.time()

    if action_type == "delay":
        duration_ms = max(0, int(action["duration_ms"] or 0))
        await asyncio.sleep(duration_ms / 1000)
        return {
            "ok": True, "action_id": action_id, "duration_ms": duration_ms,
            "summary": f"Wait {duration_ms}ms",
            "duration_actual_ms": int((time.time() - started_at) * 1000),
        }

    if action_type == "notification":
        title = (action.get("title") or "").strip() or action["label"] or "Notification"
        result = await execute_notification(
            title, action.get("message") or "", action.get("urgency") or None
        )
        summary = f"Notify: {title}"
    elif action_type == "open_url":
        url = (action.get("command") or "").strip()
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")
        result = await safe_execute_command(f"xdg-open {shlex.quote(url)}", execution_mode="detached")
        summary = f"Open URL: {url}"
    elif action_type == "open_app":
        app_cmd = (action.get("command") or "").strip()
        if not app_cmd:
            raise HTTPException(status_code=400, detail="App command is required")
        result = await safe_execute_command(app_cmd, execution_mode="detached")
        summary = f"Open App: {app_cmd.split()[0]}"
    elif action_type == "hotkey":
        shortcut = (action.get("command") or "").strip()
        if not shortcut:
            raise HTTPException(status_code=400, detail="Shortcut is required")
        result = await execute_hotkey(shortcut)
        summary = f"Hotkey: {shortcut}"
    elif action_type == "command":
        if not action["command"]:
            raise HTTPException(status_code=400, detail="Action command is required")
        result = await safe_execute_command(
            action["command"],
            timeout_ms=action.get("timeout_ms"),
            execution_mode=action.get("execution_mode", "argv"),
        )
        summary = action["command"]
        result["command"] = action["command"]
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action type: {action_type}")

    run_id = await record_v2_action_test_run(
        action_id=action_id,
        action_summary=summary,
        started_at=started_at,
        result=result,
    )
    result["action_id"] = action_id
    result["summary"] = summary
    result["run_id"] = run_id
    return result
