import asyncio
import os
import shlex
import shutil
import time
from pathlib import Path
from typing import Any, Dict

from backend.config import EXEC_PATH, EXEC_USE_SHELL


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
