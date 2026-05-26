from typing import Any, Dict

from fastapi import APIRouter

from backend.db import db_fetchall
from backend.schemas import ContextIn
from backend.services import get_setting, set_setting


router = APIRouter()


@router.get("/api/settings")
async def get_settings() -> Dict[str, str]:
    rows = await db_fetchall("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


@router.post("/api/settings/set")
async def settings_set(key: str, value: str) -> Dict[str, Any]:
    await set_setting(key, value)
    return {"ok": True}


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
