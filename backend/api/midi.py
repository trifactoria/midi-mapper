from typing import Any, Dict, List, Optional

import mido
from fastapi import APIRouter

from backend.midi.status import get_midi_status, safe_get_output_names
from backend.runtime import OUTPUT_PORT_CACHE
from backend.schemas import OutputSelectIn, SendContextIn
from backend.services import get_port_name, get_setting, set_setting


router = APIRouter()


@router.get("/api/midi/outputs")
async def midi_outputs() -> Dict[str, Any]:
    preferred = await get_setting("preferred_output_port")
    return {
        "outputs": safe_get_output_names(context="MIDI output list"),
        "preferred_output_port": preferred,
        "midi": get_midi_status(),
    }


@router.post("/api/midi/output/select")
async def midi_output_select(payload: OutputSelectIn) -> Dict[str, Any]:
    out_names = safe_get_output_names(context="MIDI output selection")
    if payload.output_name not in out_names:
        return {"ok": False, "error": "Unknown output_name", "available": out_names}
    await set_setting("preferred_output_port", payload.output_name)
    return {"ok": True, "preferred_output_port": payload.output_name}


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


@router.post("/api/midi/send_context")
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

    out_names = safe_get_output_names(context="MIDI send output enumeration")
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
