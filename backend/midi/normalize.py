from typing import Any, Dict

from .state import LAST_NOTE_CHANNEL, ChanState, get_or_create_chan_state, get_or_create_port_state


def effective_channel(port_name: str, msg: Any) -> int:
    """Treat last note channel as 'current' for non-note messages (Oxygen-style)."""
    ch = int(getattr(msg, "channel", 0))
    if msg.type in ("note_on", "note_off"):
        return ch
    return int(LAST_NOTE_CHANNEL.get(port_name, ch))


def update_state(port_name: str, msg: Any) -> Dict[str, Any]:
    """
    Updates both:
      - per-channel state (strict)
      - per-port last-seen state (useful when device sends bank/program on a different channel)
    Returns derived (flat), derived_ch, derived_port for debug.
    """
    ch = getattr(msg, "channel", 0)
    st_ch = get_or_create_chan_state(port_name, ch)
    st_port = get_or_create_port_state(port_name)

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
