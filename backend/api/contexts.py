from typing import Any, Dict, List, Optional

import mido
from fastapi import APIRouter, Body

from backend.db import db_connect, db_exec, db_fetchall, db_fetchone
from backend.schemas import ActiveContextSetIn, ContextIn, ImportContextIn
from backend.services import apply_active_selection, get_port_name, set_setting


router = APIRouter()


@router.post("/api/active_context/set")
async def set_active_context(
    # Backwards compatible: allow either JSON body or query param
    payload: Optional[ActiveContextSetIn] = Body(default=None),
    context_id: Optional[int] = None,
) -> Dict[str, Any]:
    cid = payload.context_id if payload is not None else context_id
    if cid is None:
        return {"ok": False, "error": "Missing context_id"}
    await set_setting("active_context_id", str(cid))
    return {"ok": True, "active_context_id": cid}


@router.post("/api/active_selection/set")
async def set_active_selection(sel: ContextIn) -> Dict[str, Any]:
    return await apply_active_selection(sel)


@router.post("/api/contexts/get_or_create")
async def get_or_create_context(ctx: ContextIn) -> Dict[str, Any]:
    """Get or create a context. Uses single connection to ensure correct lastrowid."""
    async with db_connect() as db:
        # Check if context exists
        cur = await db.execute(
            """
            SELECT id FROM contexts
            WHERE daw_slot=? AND preset_slot=? AND port_id=? AND channel=?
              AND bank_msb=? AND bank_lsb=? AND program=?
            """,
            (
                ctx.daw_slot,
                ctx.preset_slot,
                ctx.port_id,
                ctx.channel,
                ctx.bank_msb,
                ctx.bank_lsb,
                ctx.program,
            ),
        )
        row = await cur.fetchone()
        if row:
            return {"context_id": row["id"]}

        # Create new context on same connection
        cur = await db.execute(
            """
            INSERT INTO contexts(daw_slot, preset_slot, port_id, channel, bank_msb, bank_lsb, program)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.daw_slot,
                ctx.preset_slot,
                ctx.port_id,
                ctx.channel,
                ctx.bank_msb,
                ctx.bank_lsb,
                ctx.program,
            ),
        )
        await db.commit()
        return {"context_id": cur.lastrowid}


@router.get("/api/contexts/with_bindings")
async def contexts_with_bindings(
    daw_slot: Optional[int] = None,
    preset_slot: Optional[int] = None,
    port_id: Optional[int] = None,
    channel: Optional[int] = None,
    bank_msb: Optional[int] = None,
    bank_lsb: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Get contexts with bindings, optionally filtered by partial context match.

    This enables cascading filtering: if you select DAW=0, this returns only contexts
    with bindings where DAW=0, so the UI can highlight only relevant Preset/Port/etc values.

    Returns both 'label' (raw, nullable) and 'display_label' (computed default if no label).
    """
    # Build WHERE conditions based on provided filters
    conditions = []
    params = []

    if daw_slot is not None:
        conditions.append("c.daw_slot = ?")
        params.append(daw_slot)
    if preset_slot is not None:
        conditions.append("c.preset_slot = ?")
        params.append(preset_slot)
    if port_id is not None:
        conditions.append("c.port_id = ?")
        params.append(port_id)
    if channel is not None:
        conditions.append("c.channel = ?")
        params.append(channel)
    if bank_msb is not None:
        conditions.append("c.bank_msb = ?")
        params.append(bank_msb)
    if bank_lsb is not None:
        conditions.append("c.bank_lsb = ?")
        params.append(bank_lsb)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT DISTINCT c.id, c.daw_slot, c.preset_slot, c.port_id, c.channel,
                        c.bank_msb, c.bank_lsb, c.program,
                        COUNT(b.id) as binding_count,
                        cl.label,
                        p.name as port_name
        FROM contexts c
        INNER JOIN bindings b ON c.id = b.context_id
        LEFT JOIN context_labels cl ON c.id = cl.context_id
        LEFT JOIN ports p ON c.port_id = p.id
        WHERE {where_clause}
        GROUP BY c.id, c.daw_slot, c.preset_slot, c.port_id, c.channel, c.bank_msb, c.bank_lsb, c.program, cl.label, p.name
        ORDER BY binding_count DESC
    """

    rows = await db_fetchall(query, tuple(params))
    online_ports = set(mido.get_input_names())

    results = []
    for r in rows:
        d = dict(r)
        # Add display_label: use custom label if present, else compute default
        if d["label"]:
            d["display_label"] = d["label"]
        else:
            d["display_label"] = f"Unamed Context ({d['binding_count']} bindings, ch {d['channel']})"

        # Add port_online status
        d["port_online"] = d.get("port_name") in online_ports if d.get("port_name") else False

        results.append(d)

    return results


@router.post("/api/contexts/{context_id}/label")
async def set_context_label(context_id: int, label: str = Body(..., embed=True)) -> Dict[str, Any]:
    """Set or update a friendly label for a context."""
    if not label.strip():
        # Delete label if empty
        await db_exec("DELETE FROM context_labels WHERE context_id = ?", (context_id,))
        return {"ok": True, "label": None}

    await db_exec(
        """
        INSERT INTO context_labels (context_id, label)
        VALUES (?, ?)
        ON CONFLICT(context_id) DO UPDATE SET label = excluded.label
        """,
        (context_id, label.strip()),
    )
    return {"ok": True, "label": label.strip()}


@router.get("/api/contexts/{context_id}/label")
async def get_context_label(context_id: int) -> Dict[str, Any]:
    """Get the label for a context.

    If no custom label exists, returns a computed default:
    "Unamed Context (n bindings, ch n)"
    """
    # Check for custom label
    label_row = await db_fetchone(
        "SELECT label FROM context_labels WHERE context_id = ?",
        (context_id,)
    )
    if label_row and label_row["label"]:
        return {"label": label_row["label"]}

    # No custom label - compute default
    ctx_row = await db_fetchone(
        """
        SELECT c.channel, COUNT(b.id) as binding_count
        FROM contexts c
        LEFT JOIN bindings b ON c.id = b.context_id
        WHERE c.id = ?
        GROUP BY c.id, c.channel
        """,
        (context_id,)
    )

    if not ctx_row:
        return {"label": None}

    channel = ctx_row["channel"]
    binding_count = ctx_row["binding_count"]
    default_label = f"Unamed Context ({binding_count} bindings, ch {channel})"

    return {"label": default_label}


@router.delete("/api/contexts/{context_id}")
async def delete_context(context_id: int) -> Dict[str, Any]:
    """Delete a context and all its bindings (cascade).

    This is safe because:
    - bindings have ON DELETE CASCADE
    - context_labels have ON DELETE CASCADE
    """
    # Verify context exists
    row = await db_fetchone("SELECT id FROM contexts WHERE id=?", (context_id,))
    if not row:
        return {"ok": False, "error": "Context not found"}

    # Delete the context (bindings and labels cascade automatically)
    await db_exec("DELETE FROM contexts WHERE id=?", (context_id,))
    return {"ok": True}


@router.get("/api/contexts/{context_id}/export")
async def export_context(context_id: int) -> Dict[str, Any]:
    """Export a context with all its bindings in portable JSON format.

    Includes port_name (instead of just port_id) for portability across machines.
    """
    # Get context
    ctx_row = await db_fetchone(
        """
        SELECT c.*, p.name as port_name, cl.label
        FROM contexts c
        JOIN ports p ON c.port_id = p.id
        LEFT JOIN context_labels cl ON c.id = cl.context_id
        WHERE c.id = ?
        """,
        (context_id,)
    )

    if not ctx_row:
        return {"ok": False, "error": "Context not found"}

    ctx = dict(ctx_row)

    # Get bindings (exclude id, context_id for portability)
    bindings_rows = await db_fetchall(
        """
        SELECT enabled, trig_type, note, cc, value_min, value_max,
               pitch_min, pitch_max, command, debounce_ms, require_armed,
               notes, notify_text, notify_emoji
        FROM bindings
        WHERE context_id = ?
        ORDER BY id
        """,
        (context_id,)
    )

    bindings = [dict(r) for r in bindings_rows]

    # Build export payload
    return {
        "version": 1,
        "context": {
            "daw_slot": ctx["daw_slot"],
            "preset_slot": ctx["preset_slot"],
            "port_name": ctx["port_name"],
            "channel": ctx["channel"],
            "bank_msb": ctx["bank_msb"],
            "bank_lsb": ctx["bank_lsb"],
            "program": ctx["program"],
            "label": ctx["label"],  # null if no custom label
        },
        "bindings": bindings,
    }


@router.post("/api/contexts/import")
async def import_context(data: ImportContextIn) -> Dict[str, Any]:
    """Import a context with bindings from export JSON.

    Uses single transaction for atomicity.
    Resolves port_name to port_id (creates port if needed).
    Modes:
    - "merge": Add/update bindings (keep existing ones not in payload)
    - "replace": Delete existing bindings first, then add from payload
    """
    payload = data.payload
    mode = data.mode

    if payload.get("version") != 1:
        return {"ok": False, "error": "Unsupported export version"}

    ctx_data = payload.get("context", {})
    bindings_data = payload.get("bindings", [])

    # Resolve port_name to port_id
    port_name = ctx_data.get("port_name")
    if not port_name:
        return {"ok": False, "error": "Missing port_name in payload"}

    # Use single transaction for entire import
    async with db_connect() as db:
        # Insert or ignore port
        await db.execute("INSERT OR IGNORE INTO ports(name) VALUES (?)", (port_name,))
        cur = await db.execute("SELECT id FROM ports WHERE name=?", (port_name,))
        port_row = await cur.fetchone()
        if not port_row:
            return {"ok": False, "error": f"Failed to resolve port: {port_name}"}

        port_id = port_row["id"]

        # Get or create context
        cur = await db.execute(
            """
            SELECT id FROM contexts
            WHERE daw_slot=? AND preset_slot=? AND port_id=? AND channel=?
              AND bank_msb=? AND bank_lsb=? AND program=?
            """,
            (
                ctx_data.get("daw_slot", 0),
                ctx_data.get("preset_slot", 0),
                port_id,
                ctx_data.get("channel", 0),
                ctx_data.get("bank_msb", 0),
                ctx_data.get("bank_lsb", 0),
                ctx_data.get("program", 0),
            ),
        )
        context_row = await cur.fetchone()

        if context_row:
            context_id = context_row["id"]
        else:
            # Create context on same connection
            cur = await db.execute(
                """
                INSERT INTO contexts(daw_slot, preset_slot, port_id, channel, bank_msb, bank_lsb, program)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ctx_data.get("daw_slot", 0),
                    ctx_data.get("preset_slot", 0),
                    port_id,
                    ctx_data.get("channel", 0),
                    ctx_data.get("bank_msb", 0),
                    ctx_data.get("bank_lsb", 0),
                    ctx_data.get("program", 0),
                ),
            )
            context_id = cur.lastrowid

        # Set label if provided
        label = ctx_data.get("label")
        if label and label.strip():
            await db.execute(
                """
                INSERT INTO context_labels (context_id, label)
                VALUES (?, ?)
                ON CONFLICT(context_id) DO UPDATE SET label = excluded.label
                """,
                (context_id, label.strip()),
            )

        # Replace mode: delete existing bindings first
        if mode == "replace":
            await db.execute("DELETE FROM bindings WHERE context_id=?", (context_id,))

        # Import bindings
        for b in bindings_data:
            await db.execute(
                """
                INSERT INTO bindings(
                  context_id, enabled, trig_type, note, cc, value_min, value_max,
                  pitch_min, pitch_max, command, debounce_ms, require_armed,
                  notes, notify_text, notify_emoji
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(context_id, trig_type, note, cc)
                DO UPDATE SET
                  enabled=excluded.enabled,
                  value_min=excluded.value_min,
                  value_max=excluded.value_max,
                  pitch_min=excluded.pitch_min,
                  pitch_max=excluded.pitch_max,
                  command=excluded.command,
                  debounce_ms=excluded.debounce_ms,
                  require_armed=excluded.require_armed,
                  notes=excluded.notes,
                  notify_text=excluded.notify_text,
                  notify_emoji=excluded.notify_emoji
                """,
                (
                    context_id,
                    b.get("enabled", 1),
                    b.get("trig_type"),
                    b.get("note"),
                    b.get("cc"),
                    b.get("value_min"),
                    b.get("value_max"),
                    b.get("pitch_min"),
                    b.get("pitch_max"),
                    b.get("command", ""),
                    b.get("debounce_ms", 200),
                    b.get("require_armed", 1),
                    b.get("notes", ""),
                    b.get("notify_text", ""),
                    b.get("notify_emoji", ""),
                ),
            )

        # Commit entire transaction
        await db.commit()

        # Count final bindings
        cur = await db.execute(
            "SELECT COUNT(*) as count FROM bindings WHERE context_id=?",
            (context_id,)
        )
        count_row = await cur.fetchone()
        binding_count = count_row["count"] if count_row else 0

        return {"ok": True, "context_id": context_id, "binding_count": binding_count}
