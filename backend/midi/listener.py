import asyncio
import json
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

import mido

from backend.actions.history import record_v2_action_run
from backend.config import MAX_NOTE, WS_POLL_INTERVAL
from backend.midi.matcher import (
    binding_matches_message,
    binding_matches_message_v2,
    device_id_for_port,
    get_matching_mode,
    selection_matches_event,
)
from backend.midi.normalize import effective_channel, update_state
from backend.midi.state import LAST_FIRED, LAST_NOTE_CHANNEL
from backend.midi.status import mark_listener_disabled, safe_get_input_names


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
        for name in safe_get_input_names(context="MIDI listener startup"):
            try:
                inputs.append(mido.open_input(name))
            except Exception as exc:
                mark_listener_disabled(
                    f"MIDI input '{name}' could not be opened; continuing without that port: {exc}"
                )
                continue

        if not inputs:
            mark_listener_disabled("No MIDI input ports opened; MIDI runtime is disabled until backend restart")

        while True:
            v = await get_setting("keygrab_enabled")
            keygrab_enabled = True if v is None else (v.lower() == "true")
            selected_input_port = await get_setting("selected_input_port")
            selected_input_port = selected_input_port or None

            for inp in inputs:
                if not _input_is_selected(inp.name, selected_input_port):
                    continue
                for msg in inp.iter_pending():
                    # Track last NOTE channel separately
                    if msg.type in ("note_on", "note_off"):
                        LAST_NOTE_CHANNEL[inp.name] = getattr(msg, "channel", 0)

                    pack = update_state(inp.name, msg)
                    ctx_match = selection_matches_event(inp.name, msg, pack["derived"])

                    payload: Dict[str, Any] = {
                        "ts": time.time(),
                        "port_name": inp.name,
                        "source_port_name": inp.name,
                        "selected_input_port": selected_input_port,
                        "device_id": await device_id_for_port(inp.name),
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
                    matching_mode = await get_matching_mode()
                    payload["matching_mode"] = matching_mode

                    legacy_binding = None
                    v2_binding = None
                    if matching_mode in ("v2", "dual"):
                        v2_binding = await _execute_v2_match(
                            port_name=inp.name,
                            msg=msg,
                            derived_flat=pack["derived"],
                            payload=payload,
                            safe_execute_command=safe_execute_command,
                            send_notification=send_notification,
                        )

                    if matching_mode in ("legacy", "dual"):
                        legacy_binding = await _execute_legacy_match(
                            ctx_id=ctx_id,
                            keygrab_enabled=keygrab_enabled,
                            context_match=ctx_match,
                            msg=msg,
                            payload=payload,
                            safe_execute_command=safe_execute_command,
                            send_notification=send_notification,
                        )

                    payload["binding_match"] = v2_binding or legacy_binding
                    payload["legacy_binding_match"] = legacy_binding
                    await broadcast(payload)

            await asyncio.sleep(WS_POLL_INTERVAL)
    finally:
        for inp in inputs:
            try:
                inp.close()
            except Exception:
                pass


def _input_is_selected(port_name: str, selected_input_port: Optional[str]) -> bool:
    return selected_input_port in (None, "", port_name)


def _message_snapshot(port_name: str, msg: Any) -> str:
    return json.dumps(
        {
            "port_name": port_name,
            "type": msg.type,
            "channel": getattr(msg, "channel", None),
            "note": getattr(msg, "note", None),
            "velocity": getattr(msg, "velocity", None),
            "controller": getattr(msg, "control", None),
            "value": getattr(msg, "value", None),
            "pitch": getattr(msg, "pitch", None),
            "program": getattr(msg, "program", None),
        }
    )


def _execution_metadata(result: Optional[Dict[str, Any]], started_at: Optional[float]) -> Dict[str, Any]:
    if not result:
        return {}
    duration_ms = max(0, int((time.time() - started_at) * 1000)) if started_at else None
    status = "success" if result.get("ok") else "error"
    if not result.get("ok") and result.get("exit_code") not in (None, 0):
        status = "failed"
    return {
        "action_execution": result,
        "command_execution": result,
        "execution_status": status,
        "execution_duration_ms": duration_ms,
        "triggered_at": started_at,
    }


async def _execute_legacy_match(
    *,
    ctx_id: Optional[int],
    keygrab_enabled: bool,
    context_match: bool,
    msg: Any,
    payload: Dict[str, Any],
    safe_execute_command: Callable[[str], Awaitable[Dict[str, Any]]],
    send_notification: Callable[[str, str], Awaitable[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    if ctx_id is None or not keygrab_enabled or not context_match:
        return None

    binding = await binding_matches_message(ctx_id, msg)
    if not binding:
        return None

    binding_dict = dict(binding)
    binding_id = binding_dict.get("id")
    command = binding_dict.get("command", "")
    debounce_ms = binding_dict.get("debounce_ms", 200)
    require_armed = binding_dict.get("require_armed", 1)
    notify_text = binding_dict.get("notify_text", "")
    notify_emoji = binding_dict.get("notify_emoji", "")

    can_execute = True
    if require_armed and not keygrab_enabled:
        can_execute = False

    now = time.time() * 1000
    last = LAST_FIRED.get(("legacy", binding_id), 0)
    if now - last < debounce_ms:
        can_execute = False

    if can_execute:
        LAST_FIRED[("legacy", binding_id)] = now
        exec_result = None
        started_at = None
        if command:
            started_at = time.time()
            exec_result = await safe_execute_command(command)
            if "action_execution" not in payload:
                payload.update(_execution_metadata(exec_result, started_at))
            else:
                payload["legacy_action_execution"] = exec_result

        if notify_text:
            prefix = ""
            if exec_result and not exec_result.get("ok"):
                prefix = "❌ "
            notify_result = await send_notification(prefix + notify_text, notify_emoji)
            if notify_result and not notify_result.get("ok") and not notify_result.get("skipped"):
                payload["notify_error"] = notify_result.get("notify_error")

    return binding_dict


async def _execute_v2_match(
    *,
    port_name: str,
    msg: Any,
    derived_flat: Dict[str, int],
    payload: Dict[str, Any],
    safe_execute_command: Callable[[str], Awaitable[Dict[str, Any]]],
    send_notification: Callable[[str, str], Awaitable[Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    binding = await binding_matches_message_v2(port_name, msg, derived_flat)
    if not binding:
        return None

    binding_id = int(binding["id"])
    action = binding.get("action") or {}
    command = action.get("command") or ""
    cooldown_ms = binding.get("cooldown_ms", 200)

    payload.update(
        {
            "matched_binding_id": binding["id"],
            "matched_layer_id": binding["layer_id"],
            "matched_profile_id": binding["profile_id"],
            "matched_action_id": binding["action_id"],
            "v2_binding_match": binding,
        }
    )

    now = time.time() * 1000
    last = LAST_FIRED.get(("v2", binding_id), 0)
    if now - last < cooldown_ms:
        payload["execution_status"] = "cooldown"
        return binding

    if action.get("type") != "command" or not command:
        payload["execution_status"] = "skipped"
        return binding

    LAST_FIRED[("v2", binding_id)] = now
    started_at = time.time()
    result = await safe_execute_command(command)
    run_id = await record_v2_action_run(
        action_id=int(binding["action_id"]),
        binding_id=binding_id,
        profile_id=int(binding["profile_id"]),
        layer_id=int(binding["layer_id"]),
        trigger_snapshot_json=_message_snapshot(port_name, msg),
        action_summary=command,
        started_at=started_at,
        result=result,
    )
    result["run_id"] = run_id
    result["action_id"] = binding["action_id"]
    result["binding_id"] = binding["id"]
    result["command"] = command
    payload.update(_execution_metadata(result, started_at))

    notify_text = action.get("notify_text") or ""
    if notify_text:
        prefix = "" if result.get("ok") else "❌ "
        notify_result = await send_notification(prefix + notify_text, action.get("notify_emoji") or "")
        if notify_result and not notify_result.get("ok") and not notify_result.get("skipped"):
            payload["notify_error"] = notify_result.get("notify_error")

    return binding
