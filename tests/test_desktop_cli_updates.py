"""Manager ownership and exact-target updates without touching real installs."""
import json
import os
from pathlib import Path
import sys

import pytest

from smart_search.i18n import use_language


@pytest.fixture(autouse=True)
def chinese_presentation():
    with use_language("zh"):
        yield

from smart_search import desktop_cli
from smart_search.desktop_backend import Backend, manager_environment
from smart_search.desktop_updates import Updates


def test_mise_ownership_options_and_conflicting_path(tmp_path, monkeypatch):
    shim = tmp_path / "mise/shims/smart-search.exe"
    install = tmp_path / "mise/installs/smart-search/0.1.19"
    entry = install / "node_modules/.bin/smart-search"
    root = install / "node_modules/@konbakuyomu/smart-search"
    root.mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"name": desktop_cli.PACKAGE, "version": "0.1.19"}))
    source = tmp_path / "config.toml"
    source.write_text('[tools]\n"npm:@konbakuyomu/smart-search" = {version="0.1.19", allow_low_downloads="true"}\n')
    monkeypatch.setenv("MISE_GLOBAL_CONFIG_FILE", str(source))
    monkeypatch.delenv("MISE_CONFIG_FILE", raising=False)
    monkeypatch.delenv("MISE_ENV", raising=False)
    monkeypatch.setattr(desktop_cli.shutil, "which", lambda _: "mise.exe")
    monkeypatch.setattr(desktop_cli, "path_entries", lambda: [])
    def read(argv, env):
        if argv[1] == "which":
            return str(entry)
        return json.dumps([{"active": True, "installed": True, "install_path": str(install), "requested_version": "0.1.19",
                           "source": {"path": str(source), "type": "mise.toml"}}])
    monkeypatch.setattr(desktop_cli, "run_read", read)
    if desktop_cli.tomllib is None:
        assert not desktop_cli.discover(str(shim), {})["can_update"]
        return
    info = desktop_cli.discover(str(shim), {})
    assert info["manager"] == "mise" and info["can_update"]
    argv = desktop_cli.update_command(info, "0.2.0")
    assert argv == ["mise.exe", "use", "--global", "--pin", "--tool-option", 'allow_low_downloads="true"',
                    "npm:@konbakuyomu/smart-search@0.2.0"]
    monkeypatch.setattr(desktop_cli, "path_entries", lambda: [tmp_path / "other/smart-search.exe"])
    assert not desktop_cli.discover(str(shim), {})["can_update"]
    monkeypatch.setattr(desktop_cli, "path_entries", lambda: [])
    source.write_text('[tools]\n"npm:@konbakuyomu/smart-search" = {version="0.1.19", postinstall="custom command"}\n')
    assert not desktop_cli.discover(str(shim), {})["can_update"]


def test_npm_only_updates_proven_global_root(tmp_path, monkeypatch):
    entry = tmp_path / "prefix/smart-search.cmd"
    root = entry.parent / "node_modules/@konbakuyomu/smart-search"
    root.mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"name": desktop_cli.PACKAGE, "version": "0.1.19"}))
    monkeypatch.setattr(desktop_cli.shutil, "which", lambda _: None)
    monkeypatch.setattr(desktop_cli, "npm_command", lambda *_: ["node", "npm-cli.js"])
    monkeypatch.setattr(desktop_cli, "run_read", lambda *_: str(entry.parent / "node_modules"))
    monkeypatch.setattr(desktop_cli, "path_entries", lambda: [])
    info = desktop_cli.discover(str(entry), {})
    assert info["manager"] == "npm" and info["can_update"]
    assert desktop_cli.update_command(info, "0.2.0") == ["node", "npm-cli.js", "install", "--global", "@konbakuyomu/smart-search@0.2.0"]
    monkeypatch.setattr(desktop_cli, "run_read", lambda *_: str(tmp_path / "different/node_modules"))
    assert not desktop_cli.discover(str(entry), {})["can_update"]
    with pytest.raises(ValueError):
        desktop_cli.update_command(info, "latest; bad-command")


@pytest.mark.asyncio
@pytest.mark.parametrize("actual,exit_code,expected", [("0.2.0", 0, "finished"), ("0.1.19", 0, "failed"), ("0.2.0", 1, "failed")])
async def test_update_executes_exact_manager_and_checks_effective_version(tmp_path, monkeypatch, actual, exit_code, expected):
    b = Backend(lambda *_: None)
    b.directory = str(tmp_path / "config")
    b.updates = Updates(lambda *_: None, directory=tmp_path / "cache")
    manager_script = tmp_path / "manager.py"
    argv_file = tmp_path / "arguments.json"
    manager_script.write_text('import json,sys,os\nfrom pathlib import Path\n'
                              f'Path({str(argv_file)!r}).write_text(json.dumps(sys.argv[1:]))\n'
                              'assert "TYPESAFE_API_KEY" not in os.environ\n'
                              'assert "PYTHONPATH" not in os.environ\n'
                              f'print("package manager completed")\nsys.exit({exit_code})\n')
    info = {"external_path": "same", "resolved_path": "same", "external_version": "0.1.19", "manager": "npm",
            "manager_command": [sys.executable, str(manager_script)], "manager_options": [], "can_update": True, "external_runtime_verified": True}
    calls = []
    def status():
        calls.append(1)
        return {**info, "external_version": actual if len(calls) > 2 else "0.1.19"}
    monkeypatch.setattr(b, "cli_status", status)
    monkeypatch.setattr(b, "activity", lambda: {"runs": []})
    monkeypatch.setenv("TYPESAFE_API_KEY", "synthetic-private-key")
    monkeypatch.setenv("PYTHONPATH", "synthetic-wrong-python")
    b.updates.state["cli"] = {"current_version": "0.1.19", "latest_version": "0.2.0", "available": True}
    b.update_cli({"confirm": True, "version": "0.2.0"})
    first = b.updates.cli_task
    b.update_cli({"confirm": True, "version": "0.2.0"})
    assert b.updates.cli_task is first
    await first
    assert b.updates.state["cli_update"]["status"] == expected
    assert json.loads(argv_file.read_text()) == ["install", "--global", "@konbakuyomu/smart-search@0.2.0"]
    assert "synthetic-private-key" not in (tmp_path / "cache/cli-update.log").read_text()


def test_cli_update_requires_explicit_target_and_preserves_running_tasks(tmp_path, monkeypatch):
    b = Backend(lambda *_: None)
    b.updates = Updates(lambda *_: None, directory=tmp_path)
    info = {"external_version": "0.1.19", "manager": "unknown", "can_update": False}
    monkeypatch.setattr(b, "cli_status", lambda: info)
    monkeypatch.setattr(b, "activity", lambda: {"runs": []})
    with pytest.raises(ValueError, match="明确"):
        b.update_cli({})
    b.updates.state["cli"] = {"current_version": "0.1.19", "latest_version": "0.2.0", "available": True}
    with pytest.raises(ValueError, match="来源"):
        b.update_cli({"confirm": True, "version": "0.2.0"})
    b.runs["own"] = {"status": "running"}
    with pytest.raises(ValueError, match="任务"):
        b.update_cli({"confirm": True, "version": "0.2.0"})
    assert b.runs["own"]["status"] == "running"
