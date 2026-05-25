import asyncio
import importlib
import sys


class FakeProcess:
    pid = 4321


def test_shell_execution_is_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.delenv("MIDI_MAPPER_EXEC_USE_SHELL", raising=False)
    monkeypatch.setenv("MIDI_MAPPER_DB_PATH", str(tmp_path / "db.sqlite"))

    sys.modules.pop("app", None)
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
