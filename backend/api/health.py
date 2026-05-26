from typing import Any, Dict

from fastapi import APIRouter

from backend.config import DB_PATH, MAX_NOTE
from backend.db import db_fetchall, db_fetchone
from backend.midi.status import get_midi_status, safe_get_input_names, safe_get_output_names
from backend.services import get_setting


router = APIRouter()


@router.get("/api/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint - verify API is reachable and using correct DB."""
    midi_status = get_midi_status()
    midi_status["selected_input_port"] = await get_setting("selected_input_port")
    return {
        "ok": True,
        "db_path": DB_PATH,
        "version": "midi-mapper",
        "midi": midi_status,
    }


@router.get("/api/diag/db_stats")
async def diag_db_stats() -> Dict[str, Any]:
    """Diagnostic endpoint - show DB state for debugging."""
    # Get counts
    ports_count = await db_fetchone("SELECT COUNT(*) as count FROM ports")
    contexts_count = await db_fetchone("SELECT COUNT(*) as count FROM contexts")
    bindings_count = await db_fetchone("SELECT COUNT(*) as count FROM bindings")

    # Count contexts that have bindings
    contexts_with_bindings_count = await db_fetchone(
        """
        SELECT COUNT(DISTINCT context_id) as count
        FROM bindings
        """
    )

    # Get sample of contexts with bindings
    sample_contexts = await db_fetchall(
        """
        SELECT c.id, c.daw_slot, c.preset_slot, c.port_id, c.channel,
               c.bank_msb, c.bank_lsb, c.program,
               p.name as port_name,
               COUNT(b.id) as binding_count,
               cl.label
        FROM contexts c
        LEFT JOIN bindings b ON c.id = b.context_id
        LEFT JOIN ports p ON c.port_id = p.id
        LEFT JOIN context_labels cl ON c.id = cl.context_id
        GROUP BY c.id
        ORDER BY c.id
        LIMIT 5
        """
    )

    return {
        "db_path": DB_PATH,
        "counts": {
            "ports": ports_count["count"] if ports_count else 0,
            "contexts": contexts_count["count"] if contexts_count else 0,
            "bindings": bindings_count["count"] if bindings_count else 0,
            "contexts_with_bindings": contexts_with_bindings_count["count"] if contexts_with_bindings_count else 0,
        },
        "sample_contexts": [dict(r) for r in sample_contexts],
    }


@router.get("/api/capabilities")
async def capabilities() -> Dict[str, Any]:
    return {
        "max_note": MAX_NOTE,
        "input_ports": safe_get_input_names(context="capabilities input port enumeration"),
        "output_ports": safe_get_output_names(context="capabilities output port enumeration"),
        "midi": get_midi_status(),
    }
