# app.py
import asyncio
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import mido
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env from the same directory as app.py
load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

DB_PATH = os.environ.get("MIDI_MAPPER_DB_PATH") or str(Path(__file__).resolve().with_name("midi_map.db"))
WS_POLL_INTERVAL = float(os.environ.get("MIDI_MAPPER_WS_POLL_INTERVAL", "0.01"))
MAX_NOTE = int(os.environ.get("MIDI_MAPPER_MAX_NOTE", "127"))

# -----------------------------
# Models (match your UI header)
# -----------------------------
class ContextIn(BaseModel):
    daw_slot: int = 0
    preset_slot: int = 0
    port_id: int
    channel: int = 0
    bank_msb: int = 0
    bank_lsb: int = 0
    program: int = 0


class BindingIn(BaseModel):
    context_id: int
    enabled: int = 1
    trig_type: int  # 1 note_on, 2 cc, 3 pitchwheel, 4 program_change
    note: Optional[int] = None
    cc: Optional[int] = None
    value_min: Optional[int] = None
    value_max: Optional[int] = None
    pitch_min: Optional[int] = None
    pitch_max: Optional[int] = None
    command: str
    debounce_ms: int = 200
    require_armed: int = 1


# -----------------------------
# State
# -----------------------------
@dataclass
class ChanState:
    bank_msb: int = 0
    bank_lsb: int = 0
    program: int = 0


# Per channel state: (port_name, channel) -> ChanState
CHAN_STATE: Dict[Tuple[str, int], ChanState] = {}

# Per port state (last seen bank/prog regardless of channel): port_name -> ChanState
PORT_STATE: Dict[str, ChanState] = {}

# Output port cache for sending state back to the device
OUTPUT_PORT_CACHE: Dict[str, Any] = {}

# Track last NOTE channel separately (so top bar can show keys channel even if knobs are ch=0)
LAST_NOTE_CHANNEL: Dict[str, int] = {}

# Active selection sent by UI (for match gating)
# (This is NOT the DB "context_id"; it’s the “header filter” for when the grid should light.)
ACTIVE_SELECTION: Dict[str, Any] = {
    "port_id": None,
    "port_name": None,
    "channel": 0,
    "bank_msb": 0,
    "bank_lsb": 0,
    "program": 0,
}

# -----------------------------
# FastAPI
# -----------------------------
app = FastAPI(title="MIDI Mapper Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# DB helpers
# -----------------------------
async def db_exec(sql: str, params: tuple = ()) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(sql, params)
        await db.commit()


async def db_fetchall(sql: str, params: tuple = ()) -> List[aiosqlite.Row]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(sql, params)
        return await cur.fetchall()


async def db_fetchone(sql: str, params: tuple = ()) -> Optional[aiosqlite.Row]:
    rows = await db_fetchall(sql, params)
    return rows[0] if rows else None


async def ensure_ports_registered() -> None:
    # Register all visible INPUT ports in DB (UI selects from this list).
    # Output ports are discovered dynamically for send_context.
    names = mido.get_input_names()
    for name in names:
        await db_exec("INSERT OR IGNORE INTO ports(name) VALUES (?)", (name,))


async def get_port_name(port_id: int) -> Optional[str]:
    row = await db_fetchone("SELECT name FROM ports WHERE id=?", (port_id,))
    return row["name"] if row else None


# -----------------------------
# Settings helpers
# -----------------------------
async def get_active_context_id() -> Optional[int]:
    row = await db_fetchone("SELECT value FROM settings WHERE key='active_context_id'")
    if not row:
        return None
    v = row["value"]
    return int(v) if isinstance(v, str) and v.isdigit() else None


async def set_setting(key: str, value: str) -> None:
    await db_exec(
        """
        INSERT INTO settings(key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """,
        (key, value),
    )


@app.on_event("startup")
async def _startup() -> None:
    await ensure_ports_registered()
    asyncio.create_task(midi_pump())


# -----------------------------
# API
# -----------------------------
@app.get("/api/ports")
async def list_ports() -> List[Dict[str, Any]]:
    rows = await db_fetchall("SELECT id, name FROM ports ORDER BY name")
    return [{"id": r["id"], "name": r["name"]} for r in rows]


@app.get("/api/capabilities")
async def capabilities() -> Dict[str, Any]:
    return {
        "max_note": MAX_NOTE,
        "input_ports": mido.get_input_names(),
        "output_ports": mido.get_output_names(),
    }


@app.post("/api/active_context/set")
async def set_active_context(context_id: int) -> Dict[str, Any]:
    await set_setting("active_context_id", str(context_id))
    return {"ok": True, "active_context_id": context_id}


@app.post("/api/midi/send_context")
async def midi_send_context(ctx: ContextIn) -> Dict[str, Any]:
    """Attempt to push the selected channel/bank/program back to the controller.

    Not all devices support this consistently. We best-effort send:
      - CC 0 (Bank Select MSB)
      - CC 32 (Bank Select LSB)
      - Program Change
    """
    port_name = await get_port_name(ctx.port_id)
    if not port_name:
        return {"ok": False, "error": "Unknown port_id"}

    out_name: Optional[str] = None
    out_names = mido.get_output_names()

    # Prefer exact name match; else fuzzy substring match.
    if port_name in out_names:
        out_name = port_name
    else:
        for n in out_names:
            if port_name in n:
                out_name = n
                break

    if not out_name:
        return {"ok": False, "error": f"No matching MIDI output port for '{port_name}'", "available": out_names}

    try:
        out = OUTPUT_PORT_CACHE.get(out_name)
        if out is None:
            out = mido.open_output(out_name)
            OUTPUT_PORT_CACHE[out_name] = out

        ch = int(ctx.channel)
        # Bank select is typically CC0 then CC32, then program change.
        out.send(mido.Message("control_change", channel=ch, control=0, value=int(ctx.bank_msb)))
        out.send(mido.Message("control_change", channel=ch, control=32, value=int(ctx.bank_lsb)))
        out.send(mido.Message("program_change", channel=ch, program=int(ctx.program)))
        return {"ok": True, "output_port": out_name}
    except Exception as e:
        return {"ok": False, "error": str(e), "output_port": out_name}


@app.post("/api/active_selection/set")
async def set_active_selection(sel: ContextIn) -> Dict[str, Any]:
    # Store selection in memory for fast match gating in the pump
    port_name = await get_port_name(sel.port_id)
    ACTIVE_SELECTION["port_id"] = sel.port_id
    ACTIVE_SELECTION["port_name"] = port_name
    ACTIVE_SELECTION["channel"] = int(sel.channel)
    ACTIVE_SELECTION["bank_msb"] = int(sel.bank_msb)
    ACTIVE_SELECTION["bank_lsb"] = int(sel.bank_lsb)
    ACTIVE_SELECTION["program"] = int(sel.program)
    return {"ok": True, "active_selection": dict(ACTIVE_SELECTION)}


@app.post("/api/contexts/get_or_create")
async def get_or_create_context(ctx: ContextIn) -> Dict[str, Any]:
    row = await db_fetchone(
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
    if row:
        return {"context_id": row["id"]}

    await db_exec(
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
    row2 = await db_fetchone("SELECT last_insert_rowid() AS id")
    return {"context_id": row2["id"]}


@app.get("/api/contexts/{context_id}/bindings")
async def list_bindings(context_id: int) -> List[Dict[str, Any]]:
    rows = await db_fetchall("SELECT * FROM bindings WHERE context_id=? ORDER BY id", (context_id,))
    return [dict(r) for r in rows]


@app.post("/api/bindings/set")
async def set_binding(b: BindingIn) -> Dict[str, Any]:
    await db_exec(
        """
        INSERT INTO bindings(
          context_id, enabled, trig_type, note, cc, value_min, value_max, pitch_min, pitch_max,
          command, debounce_ms, require_armed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(context_id, trig_type, note, cc)
        DO UPDATE SET
          enabled=excluded.enabled,
          value_min=excluded.value_min,
          value_max=excluded.value_max,
          pitch_min=excluded.pitch_min,
          pitch_max=excluded.pitch_max,
          command=excluded.command,
          debounce_ms=excluded.debounce_ms,
          require_armed=excluded.require_armed
        """,
        (
            b.context_id,
            b.enabled,
            b.trig_type,
            b.note,
            b.cc,
            b.value_min,
            b.value_max,
            b.pitch_min,
            b.pitch_max,
            b.command,
            b.debounce_ms,
            b.require_armed,
        ),
    )
    return {"ok": True}


@app.post("/api/bindings/remove")
async def remove_binding(context_id: int, trig_type: int, note: Optional[int] = None, cc: Optional[int] = None) -> Dict[str, Any]:
    await db_exec(
        "DELETE FROM bindings WHERE context_id=? AND trig_type=? AND note IS ? AND cc IS ?",
        (context_id, trig_type, note, cc),
    )
    return {"ok": True}


@app.get("/api/settings")
async def get_settings() -> Dict[str, str]:
    rows = await db_fetchall("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


@app.post("/api/settings/set")
async def settings_set(key: str, value: str) -> Dict[str, Any]:
    await set_setting(key, value)
    return {"ok": True}


# Keygrab state (UI toggle)
@app.get("/api/keygrab")
async def keygrab_get() -> Dict[str, Any]:
    row = await db_fetchone("SELECT value FROM settings WHERE key='keygrab_enabled'")
    enabled = True
    if row and isinstance(row["value"], str):
        enabled = row["value"].lower() == "true"
    return {"enabled": enabled}


@app.post("/api/keygrab/set")
async def keygrab_set(enabled: bool) -> Dict[str, Any]:
    await set_setting("keygrab_enabled", "true" if enabled else "false")
    return {"ok": True, "enabled": enabled}


# -----------------------------
# Matching helpers
# -----------------------------
def effective_channel(port_name: str, msg: mido.Message) -> int:
    """Return the channel we should treat the *current mode* as.

    Many controllers (including the Oxygen Pro series) will emit knob/fader CC on a fixed
    channel (often ch=0) even when notes are on the currently selected keyboard channel.

    The UI (and user expectations) typically treat 'the current channel' as the last note channel.
    """
    ch = int(getattr(msg, "channel", 0))
    if msg.type in ("note_on", "note_off"):
        return ch
    return int(LAST_NOTE_CHANNEL.get(port_name, ch))


def _get_or_create_chan_state(port_name: str, ch: int) -> ChanState:
    key = (port_name, ch)
    st = CHAN_STATE.get(key)
    if not st:
        st = ChanState()
        CHAN_STATE[key] = st
    return st


def _get_or_create_port_state(port_name: str) -> ChanState:
    st = PORT_STATE.get(port_name)
    if not st:
        st = ChanState()
        PORT_STATE[port_name] = st
    return st


def update_state(port_name: str, msg: mido.Message) -> Dict[str, Any]:
    """
    Updates both:
      - per-channel state (strict)
      - per-port last-seen state (useful when device sends bank/program on a different channel)
    Returns a pack that includes:
      - derived (flat) for UI
      - derived_ch and derived_port for debug
    """
    ch = getattr(msg, "channel", 0)
    st_ch = _get_or_create_chan_state(port_name, ch)
    st_port = _get_or_create_port_state(port_name)

    def apply(st: ChanState) -> None:
        if msg.type == "control_change":
            if msg.control == 0:
                st.bank_msb = msg.value
            elif msg.control == 32:
                st.bank_lsb = msg.value
        elif msg.type == "program_change":
            st.program = msg.program

    apply(st_ch)
    apply(st_port)

    # Use port-level as the primary "derived" so it "sticks" across channels
    derived_flat = {"bank_msb": st_port.bank_msb, "bank_lsb": st_port.bank_lsb, "program": st_port.program}

    return {
        "derived": derived_flat,
        "derived_ch": {"bank_msb": st_ch.bank_msb, "bank_lsb": st_ch.bank_lsb, "program": st_ch.program},
        "derived_port": {"bank_msb": st_port.bank_msb, "bank_lsb": st_port.bank_lsb, "program": st_port.program},
    }


def selection_matches_event(port_name: str, msg: mido.Message, derived_flat: Dict[str, int]) -> bool:
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


# -----------------------------
# WebSocket event stream
# -----------------------------
class WSManager:
    def __init__(self) -> None:
        self.clients: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.clients.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self, payload: Dict[str, Any]) -> None:
        if not self.clients:
            return
        msg = json.dumps(payload)
        dead: List[WebSocket] = []
        for c in self.clients:
            try:
                await c.send_text(msg)
            except Exception:
                dead.append(c)
        for d in dead:
            self.disconnect(d)


ws_mgr = WSManager()


async def midi_pump() -> None:
    inputs: List[mido.ports.BaseInput] = []
    try:
        for name in mido.get_input_names():
            try:
                inputs.append(mido.open_input(name))
            except Exception:
                continue

        while True:
            # keygrab toggle stored in DB settings; default true
            row = await db_fetchone("SELECT value FROM settings WHERE key='keygrab_enabled'")
            keygrab_enabled = True
            if row and isinstance(row["value"], str):
                keygrab_enabled = row["value"].lower() == "true"

            for inp in inputs:
                for msg in inp.iter_pending():
                    # Track last NOTE channel separately
                    if msg.type in ("note_on", "note_off"):
                        LAST_NOTE_CHANNEL[inp.name] = getattr(msg, "channel", 0)

                    # Update derived state pack
                    pack = update_state(inp.name, msg)

                    # Compute match against active selection (what UI header says)
                    ctx_match = selection_matches_event(inp.name, msg, pack["derived"])

                    payload: Dict[str, Any] = {
                        "ts": time.time(),
                        "port_name": inp.name,
                        "type": msg.type,
                        "channel": getattr(msg, "channel", None),
                        "effective_channel": effective_channel(inp.name, msg),
                        "note": getattr(msg, "note", None),
                        "velocity": getattr(msg, "velocity", None),
                        "cc": getattr(msg, "control", None),
                        "value": getattr(msg, "value", None),
                        "pitch": getattr(msg, "pitch", None),
                        "program": getattr(msg, "program", None),
                        "derived": pack["derived"],
                        "derived_ch": pack["derived_ch"],
                        "derived_port": pack["derived_port"],
                        "context_match": ctx_match,
                        "observed_note_channel": LAST_NOTE_CHANNEL.get(inp.name),
                        # Expose keygrab state (optional, useful for UI)
                        "keygrab_enabled": keygrab_enabled,
                        "max_note": MAX_NOTE,
                    }

                    # Binding lookup uses ACTIVE CONTEXT ID (contextId in UI), not ACTIVE_SELECTION
                    ctx_id = await get_active_context_id()
                    payload["active_context_id"] = ctx_id

                    binding = None
                    if ctx_id is not None and keygrab_enabled:
                        # Only try to match bindings if header selection matches the event.
                        if ctx_match:
                            if msg.type == "note_on" and getattr(msg, "velocity", 0) > 0:
                                binding = await db_fetchone(
                                    "SELECT * FROM bindings WHERE context_id=? AND trig_type=1 AND note=? AND enabled=1",
                                    (ctx_id, msg.note),
                                )
                            elif msg.type == "control_change":
                                binding = await db_fetchone(
                                    "SELECT * FROM bindings WHERE context_id=? AND trig_type=2 AND cc=? AND enabled=1",
                                    (ctx_id, msg.control),
                                )
                            elif msg.type == "pitchwheel":
                                binding = await db_fetchone(
                                    "SELECT * FROM bindings WHERE context_id=? AND trig_type=3 AND enabled=1 LIMIT 1",
                                    (ctx_id,),
                                )
                            elif msg.type == "program_change":
                                binding = await db_fetchone(
                                    "SELECT * FROM bindings WHERE context_id=? AND trig_type=4 AND enabled=1 LIMIT 1",
                                    (ctx_id,),
                                )

                    payload["binding_match"] = dict(binding) if binding else None
                    await ws_mgr.broadcast(payload)

            await asyncio.sleep(WS_POLL_INTERVAL)
    finally:
        for inp in inputs:
            try:
                inp.close()
            except Exception:
                pass


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket) -> None:
    await ws_mgr.connect(ws)
    try:
        while True:
            # Keepalive; client can send "ping"
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_mgr.disconnect(ws)
    except Exception:
        ws_mgr.disconnect(ws)
