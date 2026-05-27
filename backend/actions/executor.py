import asyncio
import os
import shlex
import shutil
import time
from pathlib import Path
from typing import Any, Dict, Optional

from backend.config import EXEC_PATH, EXEC_TIMEOUT_MS, EXEC_USE_SHELL

_OUTPUT_LIMIT = 4096


def _decode(b: Optional[bytes]) -> str:
    if not b:
        return ""
    return b.decode("utf-8", errors="replace")[:_OUTPUT_LIMIT]


async def safe_execute_command(
    command: str,
    timeout_ms: Optional[int] = None,
    execution_mode: str = "argv",
) -> Dict[str, Any]:
    """Execute a command, capture stdout/stderr, and enforce a timeout.

    execution_mode="argv" (default): blocking, captures stdout/stderr, enforces timeout.
    execution_mode="detached": launches in a new session (setsid), probes 200ms for
      immediate failure, returns launched=True if still running after the probe.

    Returns a dict with:
      ok (bool), exit_code (int|None), stdout (str), stderr (str),
      pid (int if launched), error (str if failed), started_at (float),
      resolved_exe (str), argv (list), path_used (str)
    """
    if not command or not command.strip():
        return {
            "ok": False,
            "error": "Empty command",
            "argv": [],
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "path_used": EXEC_PATH,
        }

    timeout_sec = (timeout_ms if timeout_ms is not None else EXEC_TIMEOUT_MS) / 1000.0
    started_at = time.time()

    # ── Shell mode (opt-in only) ─────────────────────────────────────────────
    if EXEC_USE_SHELL:
        try:
            env = os.environ.copy()
            env["PATH"] = EXEC_PATH
            proc = await asyncio.create_subprocess_exec(
                "bash",
                "-lc",
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
        except Exception as e:
            return {
                "ok": False,
                "error": f"Shell execution failed: {e}",
                "started_at": started_at,
                "resolved_exe": "bash",
                "argv": ["bash", "-lc", command],
                "stdout": "",
                "stderr": "",
                "exit_code": None,
                "path_used": EXEC_PATH,
            }
        return await _wait_for_proc(
            proc,
            timeout_sec=timeout_sec,
            started_at=started_at,
            resolved_exe="bash",
            argv=["bash", "-lc", command],
        )

    # ── Argv mode ────────────────────────────────────────────────────────────
    try:
        parts = shlex.split(command)
    except ValueError as e:
        return {
            "ok": False,
            "error": f"Invalid command syntax: {e}",
            "argv": [],
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "path_used": EXEC_PATH,
        }

    if not parts:
        return {
            "ok": False,
            "error": "Empty command after parsing",
            "argv": [],
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "path_used": EXEC_PATH,
        }

    exe = parts[0]
    resolved_exe: Optional[str] = None

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
                "stdout": "",
                "stderr": "",
                "exit_code": None,
                "path_used": EXEC_PATH,
            }
    else:
        resolved_exe = shutil.which(exe, path=EXEC_PATH)
        if not resolved_exe:
            return {
                "ok": False,
                "error": f"Command '{exe}' not found in PATH",
                "resolved_exe": None,
                "argv": parts,
                "stdout": "",
                "stderr": "",
                "exit_code": None,
                "path_used": EXEC_PATH,
            }

    if execution_mode == "detached":
        return await _launch_detached(resolved_exe, parts, started_at)

    try:
        env = os.environ.copy()
        env["PATH"] = EXEC_PATH
        proc = await asyncio.create_subprocess_exec(
            resolved_exe,
            *parts[1:],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to execute: {e}",
            "started_at": started_at,
            "resolved_exe": resolved_exe,
            "argv": parts,
            "stdout": "",
            "stderr": "",
            "exit_code": None,
            "path_used": EXEC_PATH,
        }

    return await _wait_for_proc(
        proc,
        timeout_sec=timeout_sec,
        started_at=started_at,
        resolved_exe=resolved_exe,
        argv=parts,
    )


async def _wait_for_proc(
    proc: asyncio.subprocess.Process,
    *,
    timeout_sec: float,
    started_at: float,
    resolved_exe: str,
    argv: list,
) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "pid": proc.pid,
        "started_at": started_at,
        "resolved_exe": resolved_exe,
        "argv": argv,
        "path_used": EXEC_PATH,
    }
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            proc.communicate(), timeout=timeout_sec
        )
        exit_code = proc.returncode
        stdout = _decode(stdout_bytes)
        stderr = _decode(stderr_bytes)
        ok = exit_code == 0
        result: Dict[str, Any] = {
            **base,
            "ok": ok,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
        }
        if not ok:
            result["error"] = f"Exited with code {exit_code}"
        return result
    except asyncio.TimeoutError:
        try:
            proc.terminate()
        except Exception:
            pass
        try:
            await asyncio.wait_for(proc.wait(), timeout=2.0)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        return {
            **base,
            "ok": False,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"Timeout after {timeout_sec:.0f}s",
        }


_DETACHED_PROBE_SEC = 0.2


async def _launch_detached(
    resolved_exe: str,
    parts: list,
    started_at: float,
) -> Dict[str, Any]:
    """Launch a process detached (new session) for GUI/app-launch use cases.

    Probes for _DETACHED_PROBE_SEC to catch immediate failures.  If the process
    is still running after the probe window, returns ok=True, launched=True.
    """
    base: Dict[str, Any] = {
        "pid": None,
        "started_at": started_at,
        "resolved_exe": resolved_exe,
        "argv": parts,
        "path_used": EXEC_PATH,
        "stdout": "",
        "stderr": "",
    }
    env = os.environ.copy()
    env["PATH"] = EXEC_PATH
    try:
        proc = await asyncio.create_subprocess_exec(
            resolved_exe,
            *parts[1:],
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=True,
        )
    except Exception as e:
        return {**base, "ok": False, "error": f"Failed to launch: {e}", "exit_code": None}

    base["pid"] = proc.pid
    try:
        await asyncio.wait_for(proc.wait(), timeout=_DETACHED_PROBE_SEC)
    except asyncio.TimeoutError:
        # Still running after probe window — successful background launch.
        return {**base, "ok": True, "launched": True, "exit_code": None}

    # Process exited within probe window.
    exit_code = proc.returncode
    stderr = ""
    if proc.stderr:
        try:
            raw = await asyncio.wait_for(proc.stderr.read(4096), timeout=0.1)
            stderr = _decode(raw)
        except Exception:
            pass
    base["stderr"] = stderr
    if exit_code == 0:
        return {**base, "ok": True, "launched": True, "exit_code": 0}
    return {**base, "ok": False, "exit_code": exit_code, "error": f"Exited with code {exit_code}"}
