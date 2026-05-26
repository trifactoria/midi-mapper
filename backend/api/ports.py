from typing import Any, Dict, List

import mido
from fastapi import APIRouter

from backend.db import db_fetchall
from backend.services import ensure_ports_registered


router = APIRouter()


@router.get("/api/ports")
async def list_ports() -> List[Dict[str, Any]]:
    """List all registered ports with online status."""
    rows = await db_fetchall("SELECT id, name FROM ports ORDER BY name")
    online_ports = set(mido.get_input_names())

    return [
        {
            "id": r["id"],
            "name": r["name"],
            "online": r["name"] in online_ports,
        }
        for r in rows
    ]


@router.post("/api/ports/refresh")
async def refresh_ports() -> Dict[str, Any]:
    """Refresh ports list - register any new MIDI devices."""
    await ensure_ports_registered()
    rows = await db_fetchall("SELECT id, name FROM ports ORDER BY name")
    online_ports = set(mido.get_input_names())

    return {
        "ok": True,
        "ports": [
            {
                "id": r["id"],
                "name": r["name"],
                "online": r["name"] in online_ports,
            }
            for r in rows
        ],
    }
