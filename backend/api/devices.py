from typing import Any, Dict, List

from fastapi import APIRouter

from backend.db import db_fetchall


router = APIRouter()


@router.get("/api/devices")
async def list_devices() -> List[Dict[str, Any]]:
    rows = await db_fetchall(
        """
        SELECT
          id,
          name,
          port_name,
          port_index,
          connected,
          last_seen_at,
          created_at,
          updated_at
        FROM devices
        ORDER BY name, id
        """
    )
    return [dict(row) for row in rows]
