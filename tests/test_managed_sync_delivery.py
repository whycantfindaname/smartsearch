"""The downstream command resolves the registered Skills owner without writing it."""

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from unittest import mock

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
