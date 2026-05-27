import asyncio
import importlib
import sys

import pytest


class FakeProcess:
    pid = 4321
    returncode = 0

    async def communicate(self):
        return (b"", b"")

    async def wait(self):
        return 0

    def terminate(self):
        pass

    def kill(self):
        pass


def test_shell_execution_is_disabled_by_default(tmp_path, monkeypatch):
    pytest.importorskip("aiosqlite")
    pytest.importorskip("dotenv")
    pytest.importorskip("fastapi")
    pytest.importorskip("mido")

    monkeypatch.delenv("MIDI_MAPPER_EXEC_USE_SHELL", raising=False)
    monkeypatch.setenv("MIDI_MAPPER_DB_PATH", str(tmp_path / "db.sqlite"))

    for module_name in (
        "app",
        "backend.main",
        "backend.api.websocket",
        "backend.api.settings",
        "backend.api.ports",
        "backend.api.midi",
        "backend.api.health",
        "backend.api.contexts",
        "backend.api.bindings",
        "backend.services",
        "backend.schemas",
        "backend.runtime",
        "backend.ws",
        "backend.midi.matcher",
        "backend.midi.normalize",
        "backend.midi.state",
        "backend.actions.notifications",
        "backend.actions.executor",
        "backend.migrations",
        "backend.db",
        "backend.config",
    ):
        sys.modules.pop(module_name, None)
    backend_pkg = sys.modules.get("backend")
    if backend_pkg is not None:
        for attr in ("main", "migrations", "db", "config", "midi", "api", "services", "schemas", "runtime", "ws"):
            if hasattr(backend_pkg, attr):
                delattr(backend_pkg, attr)
    api_pkg = sys.modules.get("backend.api")
    if api_pkg is not None:
        for attr in ("bindings", "contexts", "health", "midi", "ports", "settings", "websocket"):
            if hasattr(api_pkg, attr):
                delattr(api_pkg, attr)
    midi_pkg = sys.modules.get("backend.midi")
    if midi_pkg is not None:
        for attr in ("matcher", "normalize", "state"):
            if hasattr(midi_pkg, attr):
                delattr(midi_pkg, attr)
    actions_pkg = sys.modules.get("backend.actions")
    if actions_pkg is not None:
        for attr in ("executor", "notifications"):
            if hasattr(actions_pkg, attr):
                delattr(actions_pkg, attr)
    app = importlib.import_module("app")

    assert app.EXEC_USE_SHELL is False


def test_argv_mode_resolves_executable_and_does_not_invoke_bash(app_module, monkeypatch):
    calls = []

    monkeypatch.setattr(app_module.shutil, "which", lambda exe, path=None: f"/resolved/{exe}")

    async def fake_create_subprocess_exec(*args, **kwargs):
        calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr(app_module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)

    result = asyncio.run(app_module.safe_execute_command("echo hello ';' touch /tmp/should-not-run"))

    assert result["ok"] is True
    assert result["pid"] == 4321
    assert result["resolved_exe"] == "/resolved/echo"
    assert result["argv"] == ["echo", "hello", ";", "touch", "/tmp/should-not-run"]
    assert calls[0][0] == ("/resolved/echo", "hello", ";", "touch", "/tmp/should-not-run")
    assert calls[0][0][:3] != ("bash", "-lc", "echo hello ';' touch /tmp/should-not-run")


def test_argv_mode_rejects_missing_executable(app_module, monkeypatch):
    monkeypatch.setattr(app_module.shutil, "which", lambda exe, path=None: None)

    result = asyncio.run(app_module.safe_execute_command("definitely-not-installed --flag"))

    assert result["ok"] is False
    assert "not found in PATH" in result["error"]
    assert result["argv"] == ["definitely-not-installed", "--flag"]


def test_empty_command_is_rejected(app_module):
    result = asyncio.run(app_module.safe_execute_command("   "))

    assert result["ok"] is False
    assert result["error"] == "Empty command"


# ── Integration tests (real subprocesses) ────────────────────────────────────

@pytest.mark.anyio
async def test_successful_command_captures_stdout():
    from backend.actions.executor import safe_execute_command

    result = await safe_execute_command("echo hello")

    assert result["ok"] is True
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]
    assert result["stderr"] == ""


@pytest.mark.anyio
async def test_failing_command_captures_exit_code_and_stderr():
    from backend.actions.executor import safe_execute_command

    # sh -c 'exit 42' exits with code 42 without needing external binaries
    result = await safe_execute_command("sh -c 'exit 42'")

    assert result["ok"] is False
    assert result["exit_code"] == 42


@pytest.mark.anyio
async def test_timeout_terminates_long_running_process():
    from backend.actions.executor import safe_execute_command

    result = await safe_execute_command("sleep 30", timeout_ms=150)

    assert result["ok"] is False
    assert result["exit_code"] is None
    assert "timeout" in result["error"].lower()


@pytest.mark.anyio
async def test_invalid_command_returns_useful_error(app_module):
    from backend.actions.executor import safe_execute_command

    result = await safe_execute_command("definitely-nonexistent-command-xyz")

    assert result["ok"] is False
    assert "not found" in result["error"].lower()


@pytest.mark.anyio
async def test_stdout_and_stderr_are_captured_separately():
    from backend.actions.executor import safe_execute_command

    # Write to both stdout and stderr, exit with failure
    result = await safe_execute_command("sh -c 'echo out; echo err >&2; exit 1'")

    assert result["exit_code"] == 1
    assert "out" in result["stdout"]
    assert "err" in result["stderr"]


# ── Detached mode tests ───────────────────────────────────────────────────────

def test_detached_mode_uses_start_new_session(app_module, monkeypatch):
    """Detached mode must pass start_new_session=True to subprocess."""
    launched = []

    class FakeDetachedProcess:
        pid = 9999
        returncode = None
        stderr = None

        async def wait(self):
            # Simulate a long-running process (never returns within probe)
            await asyncio.sleep(10)
            return 0

    async def fake_create_subprocess_exec(*args, **kwargs):
        launched.append(kwargs)
        return FakeDetachedProcess()

    monkeypatch.setattr(app_module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(app_module.shutil, "which", lambda exe, path=None: f"/usr/bin/{exe}")

    result = asyncio.run(app_module.safe_execute_command("firefox", execution_mode="detached"))

    assert result["ok"] is True
    assert result.get("launched") is True
    assert result["pid"] == 9999
    assert launched[0].get("start_new_session") is True


def test_detached_mode_reports_failure_when_process_exits_quickly_nonzero(app_module, monkeypatch):
    """Detached mode reports failure if the process exits within the probe window with non-zero code."""

    class FakeQuickFailProcess:
        pid = 8888
        returncode = 127
        stderr = None

        async def wait(self):
            return 127

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeQuickFailProcess()

    monkeypatch.setattr(app_module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(app_module.shutil, "which", lambda exe, path=None: f"/usr/bin/{exe}")

    result = asyncio.run(app_module.safe_execute_command("bad-app", execution_mode="detached"))

    assert result["ok"] is False
    assert result["exit_code"] == 127


def test_detached_mode_succeeds_when_process_exits_zero_immediately(app_module, monkeypatch):
    """Detached mode returns ok=True, launched=True even when process exits 0 immediately (e.g., firefox opens existing instance)."""

    class FakeQuickExitProcess:
        pid = 7777
        returncode = 0
        stderr = None

        async def wait(self):
            return 0

    async def fake_create_subprocess_exec(*args, **kwargs):
        return FakeQuickExitProcess()

    monkeypatch.setattr(app_module.asyncio, "create_subprocess_exec", fake_create_subprocess_exec)
    monkeypatch.setattr(app_module.shutil, "which", lambda exe, path=None: f"/usr/bin/{exe}")

    result = asyncio.run(app_module.safe_execute_command("firefox", execution_mode="detached"))

    assert result["ok"] is True
    assert result.get("launched") is True
    assert result["exit_code"] == 0


@pytest.mark.anyio
async def test_detached_mode_integration_long_running():
    """Integration: sleep in detached mode returns launched=True (still running after probe)."""
    from backend.actions.executor import safe_execute_command

    result = await safe_execute_command("sleep 30", execution_mode="detached")

    assert result["ok"] is True
    assert result.get("launched") is True
    assert result["exit_code"] is None
    assert result["pid"] > 0


@pytest.mark.anyio
async def test_detached_mode_integration_nonexistent_command():
    """Integration: nonexistent command in detached mode returns ok=False."""
    from backend.actions.executor import safe_execute_command

    result = await safe_execute_command("definitely-nonexistent-xyz", execution_mode="detached")

    assert result["ok"] is False
    assert "not found" in result["error"].lower()
