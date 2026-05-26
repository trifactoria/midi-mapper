from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from backend.db import db_fetchall
from backend.midi.status import safe_get_input_names
from backend.schemas import ContextIn
from backend.services import get_setting, set_setting


router = APIRouter()


class AutomationSettingsPatchIn(BaseModel):
    armed: bool


class MatchingModePatchIn(BaseModel):
    matching_mode: str


class InputSettingsPatchIn(BaseModel):
    selected_input_port: Optional[str] = None


def _setting_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.lower() == "true"


@router.get("/api/settings")
async def get_settings() -> Dict[str, str]:
    rows = await db_fetchall("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


@router.post("/api/settings/set")
async def settings_set(key: str, value: str) -> Dict[str, Any]:
    await set_setting(key, value)
    return {"ok": True}


@router.get("/api/settings/automation")
async def automation_settings_get() -> Dict[str, Any]:
    automation_value = await get_setting("automation_armed")
    legacy_keygrab_value = await get_setting("keygrab_enabled")
    return {
        "armed": _setting_bool(automation_value, True),
        "legacy_keygrab": _setting_bool(legacy_keygrab_value, True),
        "mode": "automation_armed",
        "source": "automation_armed" if automation_value is not None else "default",
    }


@router.patch("/api/settings/automation")
async def automation_settings_patch(payload: AutomationSettingsPatchIn) -> Dict[str, Any]:
    await set_setting("automation_armed", "true" if payload.armed else "false")
    return await automation_settings_get()


@router.get("/api/settings/matching")
async def matching_settings_get() -> Dict[str, Any]:
    mode = await get_setting("matching_mode")
    if mode not in ("legacy", "v2", "dual"):
        mode = "v2"
    return {"matching_mode": mode, "source": "setting" if await get_setting("matching_mode") is not None else "default"}


@router.patch("/api/settings/matching")
async def matching_settings_patch(payload: MatchingModePatchIn) -> Dict[str, Any]:
    if payload.matching_mode not in ("legacy", "v2", "dual"):
        return {"ok": False, "error": "matching_mode must be legacy, v2, or dual"}
    await set_setting("matching_mode", payload.matching_mode)
    state = await matching_settings_get()
    return {"ok": True, **state}


@router.get("/api/settings/input")
async def input_settings_get() -> Dict[str, Any]:
    selected = await get_setting("selected_input_port")
    available = safe_get_input_names(context="input settings")
    return {
        "selected_input_port": selected or None,
        "available_input_ports": available,
        "source": "setting" if selected else "default",
    }


@router.patch("/api/settings/input")
async def input_settings_patch(payload: InputSettingsPatchIn) -> Dict[str, Any]:
    await set_setting("selected_input_port", payload.selected_input_port or "")
    return await input_settings_get()


@router.get("/api/keygrab")
async def keygrab_get() -> Dict[str, Any]:
    v = await get_setting("keygrab_enabled")
    enabled = True if v is None else (v.lower() == "true")
    return {"enabled": enabled}


@router.post("/api/keygrab/set")
async def keygrab_set(enabled: bool) -> Dict[str, Any]:
    await set_setting("keygrab_enabled", "true" if enabled else "false")
    return {"ok": True, "enabled": enabled}


@router.post("/api/defaults/save")
async def save_defaults(ctx: ContextIn) -> Dict[str, Any]:
    """Save current header as startup defaults."""
    await set_setting("default_daw_slot", str(ctx.daw_slot))
    await set_setting("default_preset_slot", str(ctx.preset_slot))
    await set_setting("default_port_id", str(ctx.port_id))
    await set_setting("default_channel", str(ctx.channel))
    await set_setting("default_bank_msb", str(ctx.bank_msb))
    await set_setting("default_bank_lsb", str(ctx.bank_lsb))
    await set_setting("default_program", str(ctx.program))
    return {"ok": True}


@router.get("/api/defaults")
async def get_defaults() -> Dict[str, Any]:
    """Get startup defaults from settings."""
    daw_slot = await get_setting("default_daw_slot")
    preset_slot = await get_setting("default_preset_slot")
    port_id = await get_setting("default_port_id")
    channel = await get_setting("default_channel")
    bank_msb = await get_setting("default_bank_msb")
    bank_lsb = await get_setting("default_bank_lsb")
    program = await get_setting("default_program")

    if port_id is not None:
        return {
            "daw_slot": int(daw_slot) if daw_slot else 0,
            "preset_slot": int(preset_slot) if preset_slot else 0,
            "port_id": int(port_id),
            "channel": int(channel) if channel else 0,
            "bank_msb": int(bank_msb) if bank_msb else 0,
            "bank_lsb": int(bank_lsb) if bank_lsb else 0,
            "program": int(program) if program else 0,
        }

    rows = await db_fetchall("SELECT id FROM ports ORDER BY id LIMIT 1")
    first_port_id = rows[0]["id"] if rows else 1

    return {
        "daw_slot": 0,
        "preset_slot": 0,
        "port_id": first_port_id,
        "channel": 0,
        "bank_msb": 0,
        "bank_lsb": 0,
        "program": 0,
    }


@router.get("/api/mouse_mode")
async def mouse_mode_get() -> Dict[str, Any]:
    """Get mouse mode state."""
    v = await get_setting("mouse_mode_enabled")
    enabled = v is not None and v.lower() == "true"
    return {"enabled": enabled}


@router.post("/api/mouse_mode/set")
async def mouse_mode_set(enabled: bool) -> Dict[str, Any]:
    """Set mouse mode state."""
    await set_setting("mouse_mode_enabled", "true" if enabled else "false")
    return {"ok": True, "enabled": enabled}
