from typing import Optional

from .db import db_connect, db_exec, db_fetchall, db_fetchone
from .midi.state import ACTIVE_SELECTION, get_or_create_port_state
from .midi.status import safe_get_input_names


async def ensure_ports_registered() -> None:
    # Register all visible INPUT ports in DB (UI selects from this list).
    names = safe_get_input_names(context="port registration")
    for name in names:
        await db_exec("INSERT OR IGNORE INTO ports(name) VALUES (?)", (name,))


async def get_port_name(port_id: int) -> Optional[str]:
    row = await db_fetchone("SELECT name FROM ports WHERE id=?", (port_id,))
    return row["name"] if row else None


async def set_setting(key: str, value: str) -> None:
    await db_exec(
        """
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, value),
    )


async def get_setting(key: str) -> Optional[str]:
    row = await db_fetchone("SELECT value FROM settings WHERE key=?", (key,))
    if not row:
        return None
    v = row["value"]
    return v if isinstance(v, str) else None


async def get_active_context_id() -> Optional[int]:
    v = await get_setting("active_context_id")
    if not v:
        return None
    return int(v) if v.isdigit() else None


async def gc_orphan_contexts() -> int:
    """Delete contexts with no bindings. Returns count of deleted contexts."""
    async with db_connect() as db:
        # Find orphan contexts
        cursor = await db.execute(
            """
            DELETE FROM contexts
            WHERE id NOT IN (SELECT DISTINCT context_id FROM bindings)
            """
        )
        await db.commit()
        return cursor.rowcount if cursor.rowcount else 0


async def ensure_default_profile_and_layer() -> None:
    """Create Default Profile + Default Layer on first run (no-op if profiles already exist)."""
    async with db_connect() as db:
        row = await (await db.execute("SELECT COUNT(*) FROM profiles")).fetchone()
        if row and row[0] > 0:
            return
        cur = await db.execute(
            "INSERT INTO profiles(name, description, active) VALUES (?, ?, 1)",
            ("Default Profile", ""),
        )
        profile_id = cur.lastrowid
        await db.execute(
            "INSERT INTO layers(profile_id, name, sort_order, active) VALUES (?, ?, 0, 1)",
            (profile_id, "Default Layer"),
        )
        await db.commit()


async def load_and_apply_defaults() -> None:
    """Load defaults from settings and apply to ACTIVE_SELECTION and active_context_id."""
    # Load defaults
    daw_slot = await get_setting("default_daw_slot")
    preset_slot = await get_setting("default_preset_slot")
    port_id = await get_setting("default_port_id")
    channel = await get_setting("default_channel")
    bank_msb = await get_setting("default_bank_msb")
    bank_lsb = await get_setting("default_bank_lsb")
    program = await get_setting("default_program")

    # If no defaults saved, use first port + zeros
    if port_id is None:
        rows = await db_fetchall("SELECT id, name FROM ports ORDER BY id LIMIT 1")
        if rows:
            port_id = str(rows[0]["id"])
            port_name = rows[0]["name"]
        else:
            return  # No ports available

        daw_slot = "0"
        preset_slot = "0"
        channel = "0"
        bank_msb = "0"
        bank_lsb = "0"
        program = "0"
    else:
        # Get port name
        port_name = await get_port_name(int(port_id))

    # Set ACTIVE_SELECTION
    ACTIVE_SELECTION["port_id"] = int(port_id)
    ACTIVE_SELECTION["port_name"] = port_name
    ACTIVE_SELECTION["channel"] = int(channel) if channel else 0
    ACTIVE_SELECTION["bank_msb"] = int(bank_msb) if bank_msb else 0
    ACTIVE_SELECTION["bank_lsb"] = int(bank_lsb) if bank_lsb else 0
    ACTIVE_SELECTION["program"] = int(program) if program else 0

    # Get or create context for these defaults (use single connection)
    async with db_connect() as db:
        cur = await db.execute(
            """
            SELECT id FROM contexts
            WHERE daw_slot=? AND preset_slot=? AND port_id=? AND channel=?
              AND bank_msb=? AND bank_lsb=? AND program=?
            """,
            (
                int(daw_slot) if daw_slot else 0,
                int(preset_slot) if preset_slot else 0,
                int(port_id),
                int(channel) if channel else 0,
                int(bank_msb) if bank_msb else 0,
                int(bank_lsb) if bank_lsb else 0,
                int(program) if program else 0,
            ),
        )
        row = await cur.fetchone()

        if row:
            context_id = row["id"]
        else:
            # Create context on same connection
            cur = await db.execute(
                """
                INSERT INTO contexts(daw_slot, preset_slot, port_id, channel, bank_msb, bank_lsb, program)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(daw_slot) if daw_slot else 0,
                    int(preset_slot) if preset_slot else 0,
                    int(port_id),
                    int(channel) if channel else 0,
                    int(bank_msb) if bank_msb else 0,
                    int(bank_lsb) if bank_lsb else 0,
                    int(program) if program else 0,
                ),
            )
            await db.commit()
            context_id = cur.lastrowid

    # Set active_context_id
    await set_setting("active_context_id", str(context_id))


async def apply_active_selection(sel) -> dict:
    port_name = await get_port_name(sel.port_id)
    ACTIVE_SELECTION["port_id"] = sel.port_id
    ACTIVE_SELECTION["port_name"] = port_name
    ACTIVE_SELECTION["channel"] = int(sel.channel)
    ACTIVE_SELECTION["bank_msb"] = int(sel.bank_msb)
    ACTIVE_SELECTION["bank_lsb"] = int(sel.bank_lsb)
    ACTIVE_SELECTION["program"] = int(sel.program)

    # Update PORT_STATE to match manual selection
    # This makes the backend "remember" manual selections as if the keyboard sent them
    # So future MIDI messages won't override unless they're different
    if port_name:
        st = get_or_create_port_state(port_name)
        st.bank_msb = int(sel.bank_msb)
        st.bank_lsb = int(sel.bank_lsb)
        st.program = int(sel.program)

    return {"ok": True, "active_selection": dict(ACTIVE_SELECTION)}
