# app.py
import asyncio
import json
import os
import shlex
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite
import mido
from dotenv import load_dotenv
from fastapi import Body, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# -----------------------------
# Env / config
# -----------------------------
# Load .env from the same directory as app.py (safe if missing)
load_dotenv(dotenv_path=Path(__file__).resolve().with_name(".env"))

DB_PATH = os.environ.get("MIDI_MAPPER_DB_PATH") or str(Path(__file__).resolve().with_name("midi_map.db"))
WS_POLL_INTERVAL = float(os.environ.get("MIDI_MAPPER_WS_POLL_INTERVAL", "0.01"))
MAX_NOTE = int(os.environ.get("MIDI_MAPPER_MAX_NOTE", "127"))

CORS_ORIGINS = os.environ.get("MIDI_MAPPER_CORS_ORIGINS", "*")
ALLOW_ORIGINS = ["*"] if CORS_ORIGINS.strip() == "*" else [s.strip() for s in CORS_ORIGINS.split(",") if s.strip()]

# Execution configuration
EXEC_PATH_ENV = os.environ.get("MIDI_MAPPER_EXEC_PATH", "$PATH")
EXEC_USE_SHELL = os.environ.get("MIDI_MAPPER_EXEC_USE_SHELL", "false").lower() in ("true", "1", "yes")

# Build execution PATH
if EXEC_PATH_ENV == "$PATH" or not EXEC_PATH_ENV:
    EXEC_PATH = os.environ.get("PATH", "")
else:
    # Prepend custom paths to existing PATH
    custom_paths = EXEC_PATH_ENV.replace("$PATH", os.environ.get("PATH", ""))
    EXEC_PATH = custom_paths

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


class SendContextIn(ContextIn):
    # Optional explicit output selection (recommended)
    output_name: Optional[str] = None


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
    notes: str = ""
    notify_text: str = ""
    notify_emoji: str = ""


class OutputSelectIn(BaseModel):
    output_name: str


class ActiveContextSetIn(BaseModel):
    context_id: int


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
# (This is NOT the DB "context_id"; it's the "header filter" for when the grid should light.)
ACTIVE_SELECTION: Dict[str, Any] = {
    "port_id": None,
    "port_name": None,
    "channel": 0,
    "bank_msb": 0,
    "bank_lsb": 0,
    "program": 0,
}

# Debounce tracking: binding_id -> last_fired_timestamp
LAST_FIRED: Dict[int, float] = {}

# -----------------------------
# FastAPI
# -----------------------------
app = FastAPI(title="MIDI Mapper Bridge")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
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
    names = mido.get_input_names()
    for name in names:
        await db_exec("INSERT OR IGNORE INTO ports(name) VALUES (?)", (name,))


async def get_port_name(port_id: int) -> Optional[str]:
    row = await db_fetchone("SELECT name FROM ports WHERE id=?", (port_id,))
    return row["name"] if row else None


# -----------------------------
# Settings helpers
# -----------------------------
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


async def apply_migrations() -> None:
    """Apply database migrations if needed."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Check if new columns exist
        cursor = await db.execute("PRAGMA table_info(bindings)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        # Apply migration 002 if needed
        if "notes" not in column_names:
            await db.execute("ALTER TABLE bindings ADD COLUMN notes TEXT DEFAULT ''")
            await db.execute("ALTER TABLE bindings ADD COLUMN notify_text TEXT DEFAULT ''")
            await db.execute("ALTER TABLE bindings ADD COLUMN notify_emoji TEXT DEFAULT ''")
            await db.commit()


# -----------------------------
# Lifecycle
# -----------------------------
@app.on_event("startup")
async def _startup() -> None:
    await apply_migrations()
    await ensure_ports_registered()
    asyncio.create_task(midi_pump())


@app.on_event("shutdown")
async def _shutdown() -> None:
    # Close cached output ports cleanly
    for name, out in list(OUTPUT_PORT_CACHE.items()):
        try:
            out.close()
        except Exception:
            pass
        OUTPUT_PORT_CACHE.pop(name, None)


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


@app.get("/api/midi/outputs")
async def midi_outputs() -> Dict[str, Any]:
    preferred = await get_setting("preferred_output_port")
    return {"outputs": mido.get_output_names(), "preferred_output_port": preferred}


@app.post("/api/midi/output/select")
async def midi_output_select(payload: OutputSelectIn) -> Dict[str, Any]:
    out_names = mido.get_output_names()
    if payload.output_name not in out_names:
        return {"ok": False, "error": "Unknown output_name", "available": out_names}
    await set_setting("preferred_output_port", payload.output_name)
    return {"ok": True, "preferred_output_port": payload.output_name}


@app.post("/api/active_context/set")
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


@app.post("/api/active_selection/set")
async def set_active_selection(sel: ContextIn) -> Dict[str, Any]:
    port_name = await get_port_name(sel.port_id)
    ACTIVE_SELECTION["port_id"] = sel.port_id
    ACTIVE_SELECTION["port_name"] = port_name
    ACTIVE_SELECTION["channel"] = int(sel.channel)
    ACTIVE_SELECTION["bank_msb"] = int(sel.bank_msb)
    ACTIVE_SELECTION["bank_lsb"] = int(sel.bank_lsb)
    ACTIVE_SELECTION["program"] = int(sel.program)
    return {"ok": True, "active_selection": dict(ACTIVE_SELECTION)}


def _guess_output_from_input_name(input_port_name: str, out_names: List[str]) -> Optional[str]:
    # Exact match first
    if input_port_name in out_names:
        return input_port_name
    # Substring match
    for n in out_names:
        if input_port_name in n:
            return n
    # Last resort: try shared prefix token (often "Oxygen Pro 61")
    token = input_port_name.split("USB MIDI")[0].strip()
    if token:
        for n in out_names:
            if token in n:
                return n
    return None


@app.post("/api/midi/send_context")
async def midi_send_context(ctx: SendContextIn) -> Dict[str, Any]:
    """Attempt to push the selected channel/bank/program back to the controller.

    Best-effort send:
      - CC 0 (Bank Select MSB)
      - CC 32 (Bank Select LSB)
      - Program Change

    IMPORTANT: Many controllers won't visibly update their UI even if they accept the messages.
    """
    port_name = await get_port_name(ctx.port_id)
    if not port_name:
        return {"ok": False, "error": "Unknown port_id"}

    out_names = mido.get_output_names()
    preferred = await get_setting("preferred_output_port")

    out_name: Optional[str] = None

    # Priority:
    # 1) explicit ctx.output_name (from UI)
    # 2) settings preferred_output_port
    # 3) guess based on input port name
    if ctx.output_name:
        if ctx.output_name not in out_names:
            return {"ok": False, "error": "Unknown output_name", "available": out_names}
        out_name = ctx.output_name
    elif preferred and preferred in out_names:
        out_name = preferred
    else:
        out_name = _guess_output_from_input_name(port_name, out_names)

    if not out_name:
        return {
            "ok": False,
            "error": f"No matching MIDI output port (input='{port_name}', preferred='{preferred}')",
            "available": out_names,
        }

    ch = int(ctx.channel)
    msb = int(ctx.bank_msb)
    lsb = int(ctx.bank_lsb)
    prog = int(ctx.program)

    sent = [
        {"type": "control_change", "channel": ch, "control": 0, "value": msb},
        {"type": "control_change", "channel": ch, "control": 32, "value": lsb},
        {"type": "program_change", "channel": ch, "program": prog},
    ]

    try:
        out = OUTPUT_PORT_CACHE.get(out_name)
        if out is None:
            out = mido.open_output(out_name)
            OUTPUT_PORT_CACHE[out_name] = out

        out.send(mido.Message("control_change", channel=ch, control=0, value=msb))
        out.send(mido.Message("control_change", channel=ch, control=32, value=lsb))
        out.send(mido.Message("program_change", channel=ch, program=prog))

        return {"ok": True, "output_port": out_name, "sent": sent, "preferred_output_port": preferred}
    except Exception as e:
        return {"ok": False, "error": str(e), "output_port": out_name, "sent": sent}


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


# -----------------------------
# Command execution helpers
# -----------------------------
async def safe_execute_command(command: str) -> Dict[str, Any]:
    """Execute a command using PATH resolution.

    Returns:
        dict with keys: ok (bool), pid (int if ok), error (str if not ok),
        started_at (float), resolved_exe (str), argv (list), path_used (str)
    """
    if not command or not command.strip():
        return {"ok": False, "error": "Empty command", "argv": [], "path_used": EXEC_PATH}

    started_at = time.time()

    # Shell mode (opt-in only)
    if EXEC_USE_SHELL:
        try:
            env = os.environ.copy()
            env["PATH"] = EXEC_PATH
            proc = await asyncio.create_subprocess_exec(
                "bash",
                "-lc",
                command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                env=env,
            )
            return {
                "ok": True,
                "pid": proc.pid,
                "started_at": started_at,
                "resolved_exe": "bash",
                "argv": ["bash", "-lc", command],
                "path_used": EXEC_PATH,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": f"Shell execution failed: {e}",
                "started_at": started_at,
                "resolved_exe": "bash",
                "argv": ["bash", "-lc", command],
                "path_used": EXEC_PATH,
            }

    # Parse command (argv mode)
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return {
            "ok": False,
            "error": f"Invalid command syntax: {e}",
            "argv": [],
            "path_used": EXEC_PATH,
        }

    if not parts:
        return {"ok": False, "error": "Empty command after parsing", "argv": [], "path_used": EXEC_PATH}

    # Resolve executable
    exe = parts[0]
    resolved_exe = None

    # If exe contains '/', treat as path and expand ~
    if "/" in exe:
        exe_path = Path(exe).expanduser()
        if exe_path.exists() and os.access(exe_path, os.X_OK):
            resolved_exe = str(exe_path.resolve())
        else:
            return {
                "ok": False,
                "error": f"Path '{exe}' not found or not executable",
                "resolved_exe": str(exe_path) if exe_path.exists() else None,
                "argv": parts,
                "path_used": EXEC_PATH,
            }
    else:
        # Use shutil.which to resolve via PATH
        resolved_exe = shutil.which(exe, path=EXEC_PATH)
        if not resolved_exe:
            return {
                "ok": False,
                "error": f"Command '{exe}' not found in PATH",
                "resolved_exe": None,
                "argv": parts,
                "path_used": EXEC_PATH,
            }

    # Execute command (detached, non-blocking)
    try:
        env = os.environ.copy()
        env["PATH"] = EXEC_PATH
        proc = await asyncio.create_subprocess_exec(
            resolved_exe,
            *parts[1:],
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
            env=env,
        )
        return {
            "ok": True,
            "pid": proc.pid,
            "started_at": started_at,
            "resolved_exe": resolved_exe,
            "argv": parts,
            "path_used": EXEC_PATH,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to execute: {e}",
            "started_at": started_at,
            "resolved_exe": resolved_exe,
            "argv": parts,
            "path_used": EXEC_PATH,
        }


async def send_notification(notify_text: str, notify_emoji: str = "") -> Dict[str, Any]:
    """Send desktop notification via notify-send using PATH resolution.

    Returns:
        dict with keys: ok (bool), error (str if not ok), notify_error (str if failed)
    """
    if not notify_text:
        return {"ok": True, "skipped": True}

    title = "MIDI Mapper"
    message = f"{notify_emoji} {notify_text}".strip()

    # Resolve notify-send via PATH
    notify_send = shutil.which("notify-send", path=EXEC_PATH)
    if not notify_send:
        return {
            "ok": False,
            "notify_error": "notify-send not found in PATH",
            "path_used": EXEC_PATH,
        }

    try:
        env = os.environ.copy()
        env["PATH"] = EXEC_PATH
        proc = await asyncio.create_subprocess_exec(
            notify_send,
            title,
            message,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            return {
                "ok": False,
                "notify_error": f"notify-send failed with code {proc.returncode}: {stderr.decode()[:200]}",
            }

        return {"ok": True}
    except Exception as e:
        return {"ok": False, "notify_error": f"Failed to execute notify-send: {e}"}


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
          command, debounce_ms, require_armed, notes, notify_text, notify_emoji
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
            b.notes,
            b.notify_text,
            b.notify_emoji,
        ),
    )
    return {"ok": True}


@app.post("/api/bindings/remove")
async def remove_binding(
    context_id: int,
    trig_type: int,
    note: Optional[int] = None,
    cc: Optional[int] = None,
) -> Dict[str, Any]:
    await db_exec(
        "DELETE FROM bindings WHERE context_id=? AND trig_type=? AND note IS ? AND cc IS ?",
        (context_id, trig_type, note, cc),
    )
    return {"ok": True}


class BindingRunIn(BaseModel):
    binding_id: int


@app.post("/api/bindings/run")
async def run_binding(payload: BindingRunIn) -> Dict[str, Any]:
    """Manually test-run a binding's command."""
    # Fetch binding
    binding = await db_fetchone("SELECT * FROM bindings WHERE id=?", (payload.binding_id,))
    if not binding:
        return {"ok": False, "error": "Binding not found"}

    binding_dict = dict(binding)
    command = binding_dict.get("command", "")
    notify_text = binding_dict.get("notify_text", "")
    notify_emoji = binding_dict.get("notify_emoji", "")

    # Execute command first
    if not command:
        return {"ok": False, "error": "No command configured"}

    result = await safe_execute_command(command)

    # Send notification after command execution (if configured)
    notify_result = {}
    if notify_text:
        # Prepend error indicator if command failed
        prefix = "❌ " if not result.get("ok") else ""
        notify_result = await send_notification(prefix + notify_text, notify_emoji)

    # Merge notification result into response
    if notify_result and not notify_result.get("ok") and not notify_result.get("skipped"):
        result["notify_error"] = notify_result.get("notify_error")

    return result


@app.get("/api/settings")
async def get_settings() -> Dict[str, str]:
    rows = await db_fetchall("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


@app.post("/api/settings/set")
async def settings_set(key: str, value: str) -> Dict[str, Any]:
    await set_setting(key, value)
    return {"ok": True}


@app.get("/api/keygrab")
async def keygrab_get() -> Dict[str, Any]:
    v = await get_setting("keygrab_enabled")
    enabled = True if v is None else (v.lower() == "true")
    return {"enabled": enabled}


@app.post("/api/keygrab/set")
async def keygrab_set(enabled: bool) -> Dict[str, Any]:
    await set_setting("keygrab_enabled", "true" if enabled else "false")
    return {"ok": True, "enabled": enabled}


# -----------------------------
# Matching helpers
# -----------------------------
def effective_channel(port_name: str, msg: mido.Message) -> int:
    """Treat last note channel as 'current' for non-note messages (Oxygen-style)."""
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
    Returns derived (flat), derived_ch, derived_port for debug.
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
        # Open all input ports that exist at startup
        for name in mido.get_input_names():
            try:
                inputs.append(mido.open_input(name))
            except Exception:
                continue

        while True:
            v = await get_setting("keygrab_enabled")
            keygrab_enabled = True if v is None else (v.lower() == "true")

            for inp in inputs:
                for msg in inp.iter_pending():
                    # Track last NOTE channel separately
                    if msg.type in ("note_on", "note_off"):
                        LAST_NOTE_CHANNEL[inp.name] = getattr(msg, "channel", 0)

                    pack = update_state(inp.name, msg)
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
                        "keygrab_enabled": keygrab_enabled,
                        "max_note": MAX_NOTE,
                    }

                    ctx_id = await get_active_context_id()
                    payload["active_context_id"] = ctx_id

                    binding = None
                    if ctx_id is not None and keygrab_enabled and ctx_match:
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

                        # Execute binding command if found
                        if binding:
                            binding_dict = dict(binding)
                            binding_id = binding_dict.get("id")
                            command = binding_dict.get("command", "")
                            debounce_ms = binding_dict.get("debounce_ms", 200)
                            require_armed = binding_dict.get("require_armed", 1)
                            notify_text = binding_dict.get("notify_text", "")
                            notify_emoji = binding_dict.get("notify_emoji", "")

                            # Check require_armed (use keygrab_enabled as armed state)
                            armed = keygrab_enabled
                            can_execute = True

                            if require_armed and not armed:
                                can_execute = False

                            # Check debounce
                            now = time.time() * 1000  # ms
                            last = LAST_FIRED.get(binding_id, 0)
                            if now - last < debounce_ms:
                                can_execute = False

                            if can_execute:
                                # Update last fired time
                                LAST_FIRED[binding_id] = now

                                # Execute command first (if configured)
                                exec_result = None
                                if command:
                                    exec_result = await safe_execute_command(command)
                                    payload["command_execution"] = exec_result

                                # Send notification after command execution (if configured)
                                if notify_text:
                                    # Prepend error indicator if command failed
                                    prefix = ""
                                    if exec_result and not exec_result.get("ok"):
                                        prefix = "❌ "
                                    notify_result = await send_notification(prefix + notify_text, notify_emoji)
                                    if notify_result and not notify_result.get("ok") and not notify_result.get("skipped"):
                                        payload["notify_error"] = notify_result.get("notify_error")

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
            await ws.receive_text()  # keepalive; client can send "ping"
    except WebSocketDisconnect:
        ws_mgr.disconnect(ws)
    except Exception:
        ws_mgr.disconnect(ws)
