from dataclasses import dataclass
from typing import Any, Dict, Tuple


@dataclass
class ChanState:
    bank_msb: int = 0
    bank_lsb: int = 0
    program: int = 0


# Per channel state: (port_name, channel) -> ChanState
CHAN_STATE: Dict[Tuple[str, int], ChanState] = {}
CHANNEL_STATE = CHAN_STATE

# Per port state (last seen bank/prog regardless of channel): port_name -> ChanState
PORT_STATE: Dict[str, ChanState] = {}

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
DEBOUNCE_LAST = LAST_FIRED


def get_or_create_chan_state(port_name: str, ch: int) -> ChanState:
    key = (port_name, ch)
    st = CHAN_STATE.get(key)
    if not st:
        st = ChanState()
        CHAN_STATE[key] = st
    return st


def get_or_create_port_state(port_name: str) -> ChanState:
    st = PORT_STATE.get(port_name)
    if not st:
        st = ChanState()
        PORT_STATE[port_name] = st
    return st
