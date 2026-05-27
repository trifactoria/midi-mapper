from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db import db_connect, db_fetchall, db_fetchone


router = APIRouter()


class ProfileCreateIn(BaseModel):
    name: str
    description: str = ""


class ProfilePatchIn(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class LayerCreateIn(BaseModel):
    name: str
    sort_order: int = 0
    color: Optional[str] = None


class ProfileImportIn(BaseModel):
    payload: Dict[str, Any]


PROFILE_SELECT = """
    SELECT
      p.id,
      p.name,
      p.description,
      p.active,
      p.legacy_context_id,
      p.created_at,
      p.updated_at,
      COUNT(DISTINCT l.id) AS layer_count,
      COUNT(DISTINCT b.id) AS binding_count
    FROM profiles p
    LEFT JOIN layers l ON l.profile_id = p.id
    LEFT JOIN bindings_v2 b ON b.profile_id = p.id
"""


def _clean_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned:
        raise HTTPException(status_code=400, detail="Name is required")
    return cleaned


def _export_key(prefix: str, index: int) -> str:
    return f"{prefix}_{index}"


def _require_command_action(action: Dict[str, Any]) -> None:
    if action.get("type", "command") != "command":
        raise HTTPException(status_code=400, detail="Only command actions are supported")


def _require_list(payload: Dict[str, Any], key: str) -> List[Dict[str, Any]]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise HTTPException(status_code=400, detail=f"{key} must be a list")
    return value


@router.get("/api/profiles")
async def list_profiles() -> List[Dict[str, Any]]:
    rows = await db_fetchall(
        f"""
        {PROFILE_SELECT}
        GROUP BY p.id
        ORDER BY p.active DESC, p.name, p.id
        """
    )
    return [dict(row) for row in rows]


@router.get("/api/profiles/{profile_id}")
async def get_profile(profile_id: int) -> Dict[str, Any]:
    row = await db_fetchone(
        f"""
        {PROFILE_SELECT}
        WHERE p.id = ?
        GROUP BY p.id
        """,
        (profile_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return dict(row)


@router.post("/api/profiles")
async def create_profile(payload: ProfileCreateIn) -> Dict[str, Any]:
    name = _clean_name(payload.name)
    async with db_connect() as db:
        cur = await db.execute(
            """
            INSERT INTO profiles(name, description, active)
            VALUES (?, ?, 0)
            """,
            (name, payload.description),
        )
        await db.commit()
        profile_id = cur.lastrowid
    return await get_profile(profile_id)


@router.post("/api/profiles/import")
async def import_profile(data: ProfileImportIn) -> Dict[str, Any]:
    payload = data.payload
    if payload.get("schema_version") != 1:
        raise HTTPException(status_code=400, detail="Unsupported profile export schema_version")

    profile_data = payload.get("profile") or {}
    if not isinstance(profile_data, dict):
        raise HTTPException(status_code=400, detail="profile must be an object")
    layers_data = _require_list(payload, "layers")
    triggers_data = _require_list(payload, "triggers")
    actions_data = _require_list(payload, "actions")
    bindings_data = _require_list(payload, "bindings_v2")

    name = _clean_name(profile_data.get("name", "Imported Profile"))
    description = profile_data.get("description", "")

    trigger_payloads = {trigger.get("key"): trigger for trigger in triggers_data}
    action_payloads = {action.get("key"): action for action in actions_data}
    for action in action_payloads.values():
        _require_command_action(action)

    async with db_connect() as db:
        profile_cur = await db.execute(
            """
            INSERT INTO profiles(name, description, active)
            VALUES (?, ?, 0)
            """,
            (name, description),
        )
        profile_id = profile_cur.lastrowid

        layer_ids: dict[str, int] = {}
        for index, layer in enumerate(layers_data):
            layer_key = layer.get("key") or _export_key("layer", index)
            layer_cur = await db.execute(
                """
                INSERT INTO layers(profile_id, name, sort_order, color, active)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    _clean_name(layer.get("name", f"Layer {index + 1}")),
                    layer.get("sort_order", index),
                    layer.get("color"),
                    layer.get("active", 0),
                ),
            )
            layer_ids[layer_key] = layer_cur.lastrowid

        trigger_ids: dict[str, int] = {}
        for index, trigger in enumerate(triggers_data):
            trigger_key = trigger.get("key") or _export_key("trigger", index)
            trigger_cur = await db.execute(
                """
                INSERT INTO triggers(
                  event_type,
                  channel,
                  note,
                  controller,
                  program,
                  pitch_min,
                  pitch_max,
                  value_min,
                  value_max,
                  velocity_min,
                  velocity_max,
                  port_name,
                  bank_msb,
                  bank_lsb,
                  program_filter,
                  raw_match_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trigger.get("event_type"),
                    trigger.get("channel"),
                    trigger.get("note"),
                    trigger.get("controller"),
                    trigger.get("program"),
                    trigger.get("pitch_min"),
                    trigger.get("pitch_max"),
                    trigger.get("value_min"),
                    trigger.get("value_max"),
                    trigger.get("velocity_min"),
                    trigger.get("velocity_max"),
                    trigger.get("port_name"),
                    trigger.get("bank_msb"),
                    trigger.get("bank_lsb"),
                    trigger.get("program_filter"),
                    trigger.get("raw_match_json"),
                ),
            )
            trigger_ids[trigger_key] = trigger_cur.lastrowid

        action_ids: dict[str, int] = {}
        for index, action in enumerate(actions_data):
            action_key = action.get("key") or _export_key("action", index)
            action_cur = await db.execute(
                """
                INSERT INTO actions(
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
                  notify_emoji
                )
                VALUES ('command', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action.get("label", ""),
                    action.get("command"),
                    action.get("args_json"),
                    action.get("working_directory"),
                    action.get("environment_json"),
                    action.get("execution_mode", "argv"),
                    action.get("timeout_ms"),
                    action.get("cooldown_ms"),
                    action.get("allow_concurrent", 0),
                    action.get("notify_text", ""),
                    action.get("notify_emoji", ""),
                ),
            )
            action_ids[action_key] = action_cur.lastrowid

        for binding in bindings_data:
            layer_id = layer_ids.get(binding.get("layer_key"))
            trigger_id = trigger_ids.get(binding.get("trigger_key"))
            action_id = action_ids.get(binding.get("action_key"))
            if layer_id is None or trigger_id is None or action_id is None:
                raise HTTPException(status_code=400, detail="Binding references missing layer, trigger, or action")
            await db.execute(
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
                  display_emoji,
                  display_icon
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    layer_id,
                    trigger_id,
                    action_id,
                    binding.get("enabled", 1),
                    binding.get("require_armed", 1),
                    binding.get("cooldown_ms", 200),
                    binding.get("notes", ""),
                    binding.get("display_label", ""),
                    binding.get("display_color"),
                    binding.get("display_emoji", ""),
                    binding.get("display_icon", ""),
                ),
            )

        await db.commit()

    imported = await get_profile(profile_id)
    return {"ok": True, "profile_id": profile_id, "profile": imported}


@router.get("/api/profiles/{profile_id}/export")
async def export_profile(profile_id: int) -> Dict[str, Any]:
    profile = await db_fetchone("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    layers = await db_fetchall(
        """
        SELECT id, name, sort_order, color, active
        FROM layers
        WHERE profile_id = ?
        ORDER BY sort_order, id
        """,
        (profile_id,),
    )
    bindings = await db_fetchall(
        """
        SELECT
          b.id,
          b.layer_id,
          b.trigger_id,
          b.action_id,
          b.enabled,
          b.require_armed,
          b.cooldown_ms,
          b.notes,
          b.display_label,
          b.display_color,
          b.display_emoji,
          b.display_icon,
          t.event_type,
          t.channel,
          t.note,
          t.controller,
          t.program,
          t.pitch_min,
          t.pitch_max,
          t.value_min,
          t.value_max,
          t.velocity_min,
          t.velocity_max,
          t.port_name,
          t.bank_msb,
          t.bank_lsb,
          t.program_filter,
          t.raw_match_json,
          a.type AS action_type,
          a.label AS action_label,
          a.command,
          a.args_json,
          a.working_directory,
          a.environment_json,
          a.execution_mode,
          a.timeout_ms,
          a.cooldown_ms AS action_cooldown_ms,
          a.allow_concurrent,
          a.notify_text,
          a.notify_emoji
        FROM bindings_v2 b
        JOIN triggers t ON t.id = b.trigger_id
        JOIN actions a ON a.id = b.action_id
        WHERE b.profile_id = ?
        ORDER BY b.layer_id, b.id
        """,
        (profile_id,),
    )

    layer_keys = {layer["id"]: _export_key("layer", index) for index, layer in enumerate(layers)}
    trigger_keys: dict[int, str] = {}
    action_keys: dict[int, str] = {}
    exported_triggers: list[Dict[str, Any]] = []
    exported_actions: list[Dict[str, Any]] = []
    exported_bindings: list[Dict[str, Any]] = []

    for row in bindings:
        if row["trigger_id"] not in trigger_keys:
            trigger_key = _export_key("trigger", len(trigger_keys))
            trigger_keys[row["trigger_id"]] = trigger_key
            exported_triggers.append({
                "key": trigger_key,
                "event_type": row["event_type"],
                "channel": row["channel"],
                "note": row["note"],
                "controller": row["controller"],
                "program": row["program"],
                "pitch_min": row["pitch_min"],
                "pitch_max": row["pitch_max"],
                "value_min": row["value_min"],
                "value_max": row["value_max"],
                "velocity_min": row["velocity_min"],
                "velocity_max": row["velocity_max"],
                "port_name": row["port_name"],
                "bank_msb": row["bank_msb"],
                "bank_lsb": row["bank_lsb"],
                "program_filter": row["program_filter"],
                "raw_match_json": row["raw_match_json"],
            })
        if row["action_id"] not in action_keys:
            action_key = _export_key("action", len(action_keys))
            action_keys[row["action_id"]] = action_key
            exported_actions.append({
                "key": action_key,
                "type": row["action_type"],
                "label": row["action_label"],
                "command": row["command"],
                "args_json": row["args_json"],
                "working_directory": row["working_directory"],
                "environment_json": row["environment_json"],
                "execution_mode": row["execution_mode"],
                "timeout_ms": row["timeout_ms"],
                "cooldown_ms": row["action_cooldown_ms"],
                "allow_concurrent": row["allow_concurrent"],
                "notify_text": row["notify_text"],
                "notify_emoji": row["notify_emoji"],
            })
        exported_bindings.append({
            "layer_key": layer_keys[row["layer_id"]],
            "trigger_key": trigger_keys[row["trigger_id"]],
            "action_key": action_keys[row["action_id"]],
            "enabled": row["enabled"],
            "require_armed": row["require_armed"],
            "cooldown_ms": row["cooldown_ms"],
            "notes": row["notes"],
            "display_label": row["display_label"],
            "display_color": row["display_color"],
            "display_emoji": row["display_emoji"],
            "display_icon": row["display_icon"],
            "debounce_ms": row["cooldown_ms"],
        })

    return {
        "app": "midi-mapper",
        "export_version": 1,
        "schema_version": 1,
        "kind": "midi-mapper-v2-profile",
        "profile": {
            "name": profile["name"],
            "description": profile["description"],
        },
        "layers": [
            {
                "key": layer_keys[layer["id"]],
                "name": layer["name"],
                "sort_order": layer["sort_order"],
                "color": layer["color"],
                "active": layer["active"],
            }
            for layer in layers
        ],
        "bindings_v2": exported_bindings,
        "triggers": exported_triggers,
        "actions": exported_actions,
    }


@router.patch("/api/profiles/{profile_id}")
async def update_profile(profile_id: int, payload: ProfilePatchIn) -> Dict[str, Any]:
    if not await db_fetchone("SELECT id FROM profiles WHERE id = ?", (profile_id,)):
        raise HTTPException(status_code=404, detail="Profile not found")

    updates = []
    params: list[Any] = []
    if payload.name is not None:
        updates.append("name = ?")
        params.append(_clean_name(payload.name))
    if payload.description is not None:
        updates.append("description = ?")
        params.append(payload.description)

    if updates:
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(profile_id)
        async with db_connect() as db:
            await db.execute(
                f"UPDATE profiles SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            await db.commit()

    return await get_profile(profile_id)


@router.post("/api/profiles/{profile_id}/activate")
async def activate_profile(profile_id: int) -> Dict[str, Any]:
    if not await db_fetchone("SELECT id FROM profiles WHERE id = ?", (profile_id,)):
        raise HTTPException(status_code=404, detail="Profile not found")

    async with db_connect() as db:
        await db.execute("UPDATE profiles SET active = 0")
        await db.execute(
            "UPDATE profiles SET active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (profile_id,),
        )
        await db.commit()
    return await get_profile(profile_id)


@router.post("/api/profiles/{profile_id}/duplicate")
async def duplicate_profile(profile_id: int) -> Dict[str, Any]:
    source = await db_fetchone("SELECT * FROM profiles WHERE id = ?", (profile_id,))
    if not source:
        raise HTTPException(status_code=404, detail="Profile not found")

    async with db_connect() as db:
        cur = await db.execute(
            """
            INSERT INTO profiles(name, description, active)
            VALUES (?, ?, 0)
            """,
            (f"{source['name']} Copy", source["description"]),
        )
        new_profile_id = cur.lastrowid
        await db.execute(
            """
            INSERT INTO layers(profile_id, name, sort_order, color, active)
            SELECT ?, name, sort_order, color, active
            FROM layers
            WHERE profile_id = ?
            ORDER BY sort_order, id
            """,
            (new_profile_id, profile_id),
        )
        await db.commit()
    return await get_profile(new_profile_id)


@router.delete("/api/profiles/{profile_id}")
async def delete_profile(profile_id: int) -> Dict[str, Any]:
    source = await db_fetchone("SELECT active FROM profiles WHERE id = ?", (profile_id,))
    if not source:
        raise HTTPException(status_code=404, detail="Profile not found")

    count_row = await db_fetchone("SELECT COUNT(*) AS cnt FROM profiles")
    if count_row and count_row["cnt"] <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last profile")

    async with db_connect() as db:
        binding_cur = await db.execute(
            "SELECT id, action_id, trigger_id FROM bindings_v2 WHERE profile_id = ?",
            (profile_id,),
        )
        binding_rows = await binding_cur.fetchall()
        binding_ids = [r["id"] for r in binding_rows]
        action_ids = [r["action_id"] for r in binding_rows]
        trigger_ids = set(r["trigger_id"] for r in binding_rows)

        layer_cur = await db.execute(
            "SELECT id, activation_trigger_id FROM layers WHERE profile_id = ?",
            (profile_id,),
        )
        layer_rows = await layer_cur.fetchall()
        layer_ids = [r["id"] for r in layer_rows]
        for r in layer_rows:
            if r["activation_trigger_id"]:
                trigger_ids.add(r["activation_trigger_id"])

        for bid in binding_ids:
            await db.execute("UPDATE runs SET binding_id = NULL WHERE binding_id = ?", (bid,))
        for lid in layer_ids:
            await db.execute("UPDATE runs SET layer_id = NULL WHERE layer_id = ?", (lid,))
        await db.execute("UPDATE runs SET profile_id = NULL WHERE profile_id = ?", (profile_id,))

        for bid in binding_ids:
            await db.execute("DELETE FROM legacy_binding_migrations WHERE binding_v2_id = ?", (bid,))

        await db.execute(
            "UPDATE layers SET activation_trigger_id = NULL WHERE profile_id = ?", (profile_id,)
        )
        await db.execute("DELETE FROM bindings_v2 WHERE profile_id = ?", (profile_id,))

        for tid in trigger_ids:
            b_cur = await db.execute(
                "SELECT COUNT(*) AS cnt FROM bindings_v2 WHERE trigger_id = ?", (tid,)
            )
            l_cur = await db.execute(
                "SELECT COUNT(*) AS cnt FROM layers WHERE activation_trigger_id = ?", (tid,)
            )
            if (await b_cur.fetchone())["cnt"] == 0 and (await l_cur.fetchone())["cnt"] == 0:
                await db.execute("DELETE FROM triggers WHERE id = ?", (tid,))

        for aid in set(action_ids):
            b_cur = await db.execute(
                "SELECT COUNT(*) AS cnt FROM bindings_v2 WHERE action_id = ?", (aid,)
            )
            r_cur = await db.execute(
                "SELECT COUNT(*) AS cnt FROM runs WHERE action_id = ?", (aid,)
            )
            if (await b_cur.fetchone())["cnt"] == 0 and (await r_cur.fetchone())["cnt"] == 0:
                await db.execute("DELETE FROM actions WHERE id = ?", (aid,))

        activated_profile_id = None
        if source["active"]:
            next_cur = await db.execute(
                "SELECT id FROM profiles WHERE id != ? ORDER BY id LIMIT 1",
                (profile_id,),
            )
            row = await next_cur.fetchone()
            if row:
                activated_profile_id = row["id"]
                await db.execute(
                    "UPDATE profiles SET active = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (activated_profile_id,),
                )

        await db.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
        await db.commit()

    return {
        "ok": True,
        "deleted_profile_id": profile_id,
        "activated_profile_id": activated_profile_id,
    }


@router.get("/api/profiles/{profile_id}/layers")
async def list_profile_layers(profile_id: int) -> List[Dict[str, Any]]:
    profile = await db_fetchone("SELECT id FROM profiles WHERE id = ?", (profile_id,))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    rows = await db_fetchall(
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
        WHERE l.profile_id = ?
        GROUP BY l.id
        ORDER BY l.sort_order, l.id
        """,
        (profile_id,),
    )
    return [dict(row) for row in rows]


@router.post("/api/profiles/{profile_id}/layers")
async def create_layer(profile_id: int, payload: LayerCreateIn) -> Dict[str, Any]:
    if not await db_fetchone("SELECT id FROM profiles WHERE id = ?", (profile_id,)):
        raise HTTPException(status_code=404, detail="Profile not found")

    name = _clean_name(payload.name)
    async with db_connect() as db:
        cur = await db.execute(
            """
            INSERT INTO layers(profile_id, name, sort_order, color, active)
            VALUES (?, ?, ?, ?, 0)
            """,
            (profile_id, name, payload.sort_order, payload.color),
        )
        await db.commit()
        layer_id = cur.lastrowid

    row = await db_fetchone(
        """
        SELECT
          id,
          profile_id,
          name,
          sort_order,
          color,
          active,
          activation_trigger_id,
          legacy_context_id,
          created_at,
          updated_at,
          0 AS binding_count
        FROM layers
        WHERE id = ?
        """,
        (layer_id,),
    )
    return dict(row)
