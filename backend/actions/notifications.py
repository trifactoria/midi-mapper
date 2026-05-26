import asyncio
import os
import shutil
from typing import Any, Dict

from backend.config import EXEC_PATH


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
