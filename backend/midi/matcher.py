from typing import Any, Dict, Optional

from backend.db import db_fetchone

from .normalize import effective_channel
from .state import ACTIVE_SELECTION


def selection_matches_event(port_name: str, msg: Any, derived_flat: Dict[str, int]) -> bool:
    sel_port = ACTIVE_SELECTION.get("port_name")
    if sel_port and sel_port != port_name:
        return False

    ch = effective_channel(port_name, msg)
    if ch != int(ACTIVE_SELECTION.get("channel", 0)):
        return False

    if derived_flat.get("bank_msb", 0) != int(ACTIVE_SELECTION.get("bank_msb", 0)):
        return False
    if derived_flat.get("bank_lsb", 0) != int(ACTIVE_SELECTION.get("bank_lsb", 0)):
        return False
    if derived_flat.get("program", 0) != int(ACTIVE_SELECTION.get("program", 0)):
        return False

    return True


async def binding_matches_message(context_id: int, msg: Any) -> Optional[Any]:
    if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=1 AND note=? AND enabled=1",
            (context_id, msg.note),
        )
    if msg.type == "control_change":
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=2 AND cc=? AND enabled=1",
            (context_id, msg.control),
        )
    if msg.type == "pitchwheel":
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=3 AND enabled=1 LIMIT 1",
            (context_id,),
        )
    if msg.type == "program_change":
        return await db_fetchone(
            "SELECT * FROM bindings WHERE context_id=? AND trig_type=4 AND enabled=1 LIMIT 1",
            (context_id,),
        )
    return None
