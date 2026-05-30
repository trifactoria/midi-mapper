# backend/main.py
import asyncio
from contextlib import asynccontextmanager, suppress
from typing import Any, Dict

import mido
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import (
    actions,
    bindings,
    contexts,
    devices,
    health,
    layers,
    macros,
    midi,
    ports,
    profiles,
    runs,
    settings,
    websocket,
)
from .actions import executor as _executor
from .actions.executor import safe_execute_command
from .actions.notifications import send_notification
from .config import (
    ALLOW_ORIGINS,
    DB_PATH,
    DEFAULT_DB_PATH,
    DOTENV_PATH,
    EXEC_PATH,
    EXEC_USE_SHELL,
    MAX_NOTE,
    PROJECT_ROOT,
    SCHEMA_PATH,
)
from .db import db_connect, db_exec, db_fetchall, db_fetchone
from .migrations import apply_migrations, init_schema
from .midi.listener import midi_pump as run_midi_pump
from .midi.matcher import (
    binding_matches_message,
    binding_matches_message_v2,
    get_matching_mode,
    selection_matches_event,
)
from .midi.normalize import effective_channel, update_state
from .midi.state import (
    ACTIVE_SELECTION,
    CHAN_STATE,
    CHANNEL_STATE,
    DEBOUNCE_LAST,
    LAST_FIRED,
    LAST_NOTE_CHANNEL,
    PORT_STATE,
    ChanState,
    get_or_create_chan_state,
    get_or_create_port_state,
)
from .runtime import OUTPUT_PORT_CACHE, close_output_ports
from .schemas import (
    ActiveContextSetIn,
    BindingIn,
    BindingRunIn,
    ContextIn,
    ImportContextIn,
    OutputSelectIn,
    SendContextIn,
)
from .services import (
    ensure_default_profile_and_layer,
    ensure_ports_registered,
    gc_orphan_contexts,
    get_active_context_id,
    get_port_name,
    get_setting,
    load_and_apply_defaults,
    set_setting,
)
from .ws import ws_mgr

asyncio = _executor.asyncio
shutil = _executor.shutil

# -----------------------------
# Env / config
# -----------------------------
# Configuration is loaded in backend.config and re-exported here for
# compatibility with existing imports/tests.

_get_or_create_chan_state = get_or_create_chan_state
_get_or_create_port_state = get_or_create_port_state

# -----------------------------
# FastAPI
# -----------------------------
MIDI_PUMP_TASK: Any = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup()
    try:
        yield
    finally:
        await _shutdown()


app = FastAPI(title="MIDI Mapper Bridge", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    ports.router,
    health.router,
    midi.router,
    devices.router,
    profiles.router,
    layers.router,
    actions.router,
    runs.router,
    macros.router,
    contexts.router,
    bindings.router,
    settings.router,
    websocket.router,
):
    app.include_router(router)


# -----------------------------
# Lifecycle
# -----------------------------
async def _startup() -> None:
    global MIDI_PUMP_TASK
    init_schema(DB_PATH)  # idempotent: creates legacy tables if DB is brand-new
    await apply_migrations()
    await ensure_default_profile_and_layer()  # first-run: create Default Profile + Default Layer
    # Clean up orphan contexts (contexts with no bindings)
    await gc_orphan_contexts()
    await ensure_ports_registered()
    await load_and_apply_defaults()
    MIDI_PUMP_TASK = asyncio.create_task(midi_pump())


async def _shutdown() -> None:
    global MIDI_PUMP_TASK
    if MIDI_PUMP_TASK is not None and not MIDI_PUMP_TASK.done():
        MIDI_PUMP_TASK.cancel()
        with suppress(asyncio.CancelledError):
            await MIDI_PUMP_TASK
    MIDI_PUMP_TASK = None
    close_output_ports(OUTPUT_PORT_CACHE)


async def midi_pump() -> None:
    await run_midi_pump(
        get_setting=get_setting,
        get_active_context_id=get_active_context_id,
        safe_execute_command=safe_execute_command,
        send_notification=send_notification,
        broadcast=ws_mgr.broadcast,
    )
