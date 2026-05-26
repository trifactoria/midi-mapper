import logging
import time
from typing import Any, Dict, List, Optional

import mido


logger = logging.getLogger("midi_mapper.midi")

_status: Dict[str, Any] = {
    "available": True,
    "degraded": False,
    "input_ports": [],
    "output_ports": [],
    "message": "MIDI status has not been checked yet",
    "error": None,
    "last_checked_at": None,
}


def _error_message(exc: BaseException) -> str:
    return f"{exc.__class__.__name__}: {exc}"


def _mark_available(*, input_ports: Optional[List[str]] = None, output_ports: Optional[List[str]] = None) -> None:
    if input_ports is not None:
        _status["input_ports"] = input_ports
        _status.update(
            {
                "available": True,
                "degraded": False,
                "message": "No MIDI input ports detected" if input_ports == [] else "MIDI available",
                "error": None,
            }
        )
    if output_ports is not None:
        _status["output_ports"] = output_ports
    _status["last_checked_at"] = time.time()


def mark_unavailable(exc: BaseException, *, context: str) -> None:
    message = _error_message(exc)
    _status.update(
        {
            "available": False,
            "degraded": True,
            "message": f"MIDI unavailable during {context}; backend is running without MIDI input",
            "error": message,
            "last_checked_at": time.time(),
        }
    )
    logger.warning("%s: %s", _status["message"], message)


def mark_listener_disabled(reason: str) -> None:
    _status.update(
        {
            "available": False,
            "degraded": True,
            "message": reason,
            "last_checked_at": time.time(),
        }
    )
    logger.warning("%s", reason)


def safe_get_input_names(*, context: str) -> List[str]:
    try:
        names = list(mido.get_input_names())
    except Exception as exc:
        mark_unavailable(exc, context=context)
        return []
    _mark_available(input_ports=names)
    return names


def safe_get_output_names(*, context: str) -> List[str]:
    try:
        names = list(mido.get_output_names())
    except Exception as exc:
        mark_unavailable(exc, context=context)
        return []
    _mark_available(output_ports=names)
    return names


def get_midi_status() -> Dict[str, Any]:
    return dict(_status)
