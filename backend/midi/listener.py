import asyncio
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

import mido

from backend.config import MAX_NOTE, WS_POLL_INTERVAL
from backend.midi.matcher import binding_matches_message, selection_matches_event
from backend.midi.normalize import effective_channel, update_state
from backend.midi.state import LAST_FIRED, LAST_NOTE_CHANNEL


async def midi_pump(
    *,
    get_setting: Callable[[str], Awaitable[Optional[str]]],
    get_active_context_id: Callable[[], Awaitable[Optional[int]]],
    safe_execute_command: Callable[[str], Awaitable[Dict[str, Any]]],
    send_notification: Callable[[str, str], Awaitable[Dict[str, Any]]],
    broadcast: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
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
                        binding = await binding_matches_message(ctx_id, msg)

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
                    await broadcast(payload)

            await asyncio.sleep(WS_POLL_INTERVAL)
    finally:
        for inp in inputs:
            try:
                inp.close()
            except Exception:
                pass
