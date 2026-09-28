"""The downstream command resolves the registered Skills owner without writing it."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path
from unittest import mock

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts/managed_sync.py"
SPEC = importlib.util.spec_from_file_location("smartsearch_managed_sync", MODULE_PATH)
assert SPEC and SPEC.loader
managed_sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(managed_sync)


def test_downstream_uses_registry_common_target(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    workspace = tmp_path / "workspace"
    infra = tmp_path / "infra"
    source = tmp_path / "source"
    target = workspace / "Skills/custom-main"
    helper = target / "scripts/inspect_upstream_delivery.py"
    helper.parent.mkdir(parents=True)
    helper.write_text("# fixture\n", encoding="utf-8")
    updater = target / "scripts/update_global_skill.py"
    updater.write_text(
        "import argparse\n"
        "p=argparse.ArgumentParser()\n"
        "p.add_argument('skill')\n"
        "p.add_argument('--repo-root')\n"
        "p.add_argument('--source-checkout')\n"
        "p.add_argument('--target')\n"
        "a=p.parse_args()\n"
        "assert a.skill=='smart-search-cli' and a.repo_root and a.target\n",
        encoding="utf-8",
    )
    (infra / "manifests").mkdir(parents=True)
    (infra / "manifests/workspace-repositories.json").write_text(
        json.dumps(
            {
                "skills": {
                    "repository": "https://fixture.test/skills.git",
                    "common": {"branch": "main", "target": "Skills/custom-main"},
                }
            }
        ),
        encoding="utf-8",
    )
    source.mkdir()
    (source / "package.json").write_text('{"version":"1.2.3"}\n', encoding="utf-8")
    monkeypatch.setenv("AGENT_INFRA_WORKSPACE_ROOT", str(workspace))
    monkeypatch.setenv("AGENT_INFRA_REPOSITORY_ROOT", str(infra))
    monkeypatch.setattr(managed_sync, "REPO_ROOT", source)
    monkeypatch.setattr(
        managed_sync, "SOURCE_SKILL", source / "skills/smart-search-cli"
    )
    sha = "a" * 40
    report = {
        "status": "committed",
        "producer_commit": sha,
        "artifact_path": "skills/smart-search-cli",
        "artifact_name": "smart-search-cli",
        "consumer_commit": "b" * 40,
        "consumer_source_commit": sha,
        "source_relation": "exact_current_pin",
    }

    def committed_git(*args: str) -> str:
        return '{"version":"1.2.3"}' if args == ("show", "HEAD:package.json") else sha

    with (
        mock.patch.object(managed_sync, "_git", side_effect=committed_git),
        mock.patch.object(
            managed_sync.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, json.dumps(report), ""),
        ) as called,
    ):
        payload = managed_sync.downstream_handoff()
    assert payload["status"] == "completed"
    assert payload["artifacts"][0]["consumer_repository"] == "skills-common"
    assert payload["artifacts"][0]["artifact_version"] == "1.2.3"
    assert str(helper) in called.call_args.args[0]
    assert called.call_args.kwargs["cwd"] == source
    assert called.call_args.kwargs["encoding"] == "utf-8"

    for field, wrong in (
        ("artifact_path", "skills/other"),
        ("artifact_name", "other-skill"),
    ):
        bad = dict(report, **{field: wrong})
        with (
            mock.patch.object(managed_sync, "_git", side_effect=committed_git),
            mock.patch.object(
                managed_sync.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, json.dumps(bad), ""),
            ),
        ):
            rejected = managed_sync.downstream_handoff()
        assert rejected["status"] == "handoff_required"
        assert rejected["artifacts"] == []
        assert "different source artifact" in rejected["reason"]

    stale = {
        "status": "handoff_required",
        "error": "handoff_required: selected source artifact is not adopted",
    }
    with (
        mock.patch.object(managed_sync, "_git", side_effect=committed_git),
        mock.patch.object(
            managed_sync.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 2, json.dumps(stale), ""),
        ),
    ):
        pending = managed_sync.downstream_handoff()
    preview = pending["next_step_argv"]
    assert preview[1] == str(updater) and Path(preview[1]).is_file()
    assert preview[preview.index("--repo-root") + 1] == str(target)
    assert "--apply" not in preview
    subprocess.run(
        preview,
        cwd=source,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    missing_field = dict(report)
    del missing_field["consumer_commit"]
    monkeypatch.setattr(
        managed_sync.sys, "argv", [str(MODULE_PATH), "downstream-handoff"]
    )
    invalid_oid = dict(report, consumer_commit="not-an-oid")
    invalid_relation = dict(
        report, source_relation="exact_current_pin", consumer_source_commit="c" * 40
    )
    non_string_relation = dict(report, source_relation={"invalid": "shape"})
    for bad_stdout in (
        json.dumps(missing_field),
        json.dumps(invalid_oid),
        json.dumps(invalid_relation),
        json.dumps(non_string_relation),
        json.dumps([]),
        "not json",
    ):
        with (
            mock.patch.object(managed_sync, "_git", side_effect=committed_git),
            mock.patch.object(
                managed_sync.subprocess,
                "run",
                return_value=subprocess.CompletedProcess([], 0, bad_stdout, ""),
            ),
        ):
            exit_code = managed_sync.main()
        failed = json.loads(capsys.readouterr().out)
        assert exit_code == 1
        assert failed["status"] == "handoff_required"
        assert failed["errors"] == ["SS_SYNC_DOWNSTREAM_HANDOFF_REQUIRED"]
        assert failed["artifacts"] == []


def test_missing_helper_requires_handoff(tmp_path: Path, monkeypatch) -> None:
    infra = tmp_path / "infra"
    (infra / "manifests").mkdir(parents=True)
    (infra / "manifests/workspace-repositories.json").write_text(
        json.dumps(
            {
                "skills": {
                    "repository": "https://fixture.test/skills.git",
                    "common": {"branch": "main", "target": "Skills/missing"},
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_INFRA_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("AGENT_INFRA_REPOSITORY_ROOT", str(infra))
    with mock.patch.object(managed_sync, "_git", return_value="a" * 40):
        payload = managed_sync.downstream_handoff()
    assert payload["status"] == "handoff_required"
    assert payload["artifacts"] == []
    assert "missing" in payload["reason"]


@pytest.mark.parametrize("platform", ["win32", "linux", "darwin"])
@pytest.mark.parametrize("layout", ["missing", "default", "legacy", "override"])
def test_live_config_selection_matches_runtime(tmp_path, monkeypatch, platform, layout):
    from smart_search.config import Config

    home = tmp_path / "home"
    local = tmp_path / "local"
    monkeypatch.setattr(Path, "home", lambda: home)
    monkeypatch.setattr(managed_sync.sys, "platform", platform)
    monkeypatch.setenv("LOCALAPPDATA", str(local))
    paths = {
        "default": local / "smart-search/config.json",
        "legacy": home / ".config/smart-search/config.json",
        "override": tmp_path / "override/config.json",
    }
    if layout != "missing":
        path = paths[layout]
        path.parent.mkdir(parents=True)
        path.write_text("private-fixture", encoding="utf-8")
    if layout == "override":
        monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(paths[layout].parent))
    expected = Config._resolve_config_dir()[0] / "config.json"
    with mock.patch.object(Path, "read_text", side_effect=AssertionError("no secret reads")):
        assert managed_sync._live_config_path() == expected


@pytest.mark.parametrize("doctor_exit,search_exit,status,calls", [
    (0, 0, "live", 2), (1, 0, "failed", 1), (0, 1, "activated", 2),
])
def test_live_uses_one_installed_entry(tmp_path, monkeypatch, doctor_exit, search_exit, status, calls):
    config = tmp_path / "config.json"
    config.write_text("secret-fixture", encoding="utf-8")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path))
    entry = str(tmp_path / "installed-smart-search")
    with (
        mock.patch.object(managed_sync.shutil, "which", return_value=entry) as resolve,
        mock.patch.object(managed_sync.subprocess, "run", side_effect=[
            subprocess.CompletedProcess([], doctor_exit, "private-provider-output", "secret"),
            subprocess.CompletedProcess([], search_exit, "private-provider-output", "secret"),
        ]) as run,
    ):
        result = managed_sync.verify_live()
    assert result["status"] == status
    assert result["command_entry"] == entry
    assert resolve.call_count == 1
    assert run.call_count == calls
    assert run.call_args_list[0].args[0] == [entry, "doctor", "--format", "json"]
    if calls == 2:
        assert run.call_args_list[1].args[0] == [
            entry, "search", "RFC 9110 HTTP Semantics", "--format", "json",
            "--validation", "fast", "--fallback", "off", "--max-try", "1", "--timeout", "90",
        ]
    assert "secret" not in json.dumps(result)
    assert "private-provider-output" not in json.dumps(result)


def test_live_missing_installed_entry_does_not_probe(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path))
    with (
        mock.patch.object(managed_sync.shutil, "which", return_value=None),
        mock.patch.object(managed_sync.subprocess, "run") as run,
    ):
        result = managed_sync.verify_live()
    assert result["status"] == "blocked"
    assert result["errors"] == ["SS_VERIFY_EXTERNAL_GATE_MISSING"]
    run.assert_not_called()


def test_live_missing_config_does_not_probe(tmp_path, monkeypatch):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path))
    with mock.patch.object(managed_sync.subprocess, "run") as run:
        result = managed_sync.verify_live()
    assert result["status"] == "blocked"
    assert result["config_present"] is False
    run.assert_not_called()


@pytest.mark.parametrize("doctor_passes,status,calls", [(False, "failed", 1), (True, "activated", 2)])
def test_live_timeout_does_not_retry(tmp_path, monkeypatch, doctor_passes, status, calls):
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path))
    responses = [subprocess.CompletedProcess([], 0)] if doctor_passes else []
    responses.append(subprocess.TimeoutExpired("private-provider-output", 1))
    with (
        mock.patch.object(managed_sync.shutil, "which", return_value="installed-command"),
        mock.patch.object(managed_sync.subprocess, "run", side_effect=responses) as run,
    ):
        result = managed_sync.verify_live()
    assert result["status"] == status
    assert run.call_count == calls
    assert "private-provider-output" not in json.dumps(result)


@pytest.mark.skipif(os.name != "nt", reason="Windows npm command shim")
def test_live_windows_cmd_entry_with_spaces(tmp_path, monkeypatch):
    directory = tmp_path / "native prefix & fixture"
    directory.mkdir()
    command = directory / "smart-search.cmd"
    command.write_text(
        '@echo off\n'
        'if "%~1"=="doctor" if "%~2"=="--format" if "%~3"=="json" '
        '(echo private-provider-output & exit /b 0)\n'
        'if "%~1"=="search" if "%~2"=="RFC 9110 HTTP Semantics" '
        '(echo private-provider-output & exit /b 0)\n'
        'exit /b 9\n', encoding="utf-8",
    )
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("PATH", str(directory))
    result = managed_sync.verify_live()
    assert result["status"] == "live", result
    assert Path(result["command_entry"]) == command
    assert "private-provider-output" not in json.dumps(result)
