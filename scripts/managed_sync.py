#!/usr/bin/env python3
"""Smart Search managed-sync project entrypoint.

Minimal contract entrypoint referenced by .jason-liao-agent-infra/managed-project.json.
It never reads secret values, never pushes, and never mutates the worktree.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_SKILL = REPO_ROOT / "skills" / "smart-search-cli"
PACKAGED_SKILL = REPO_ROOT / "src" / "smart_search" / "assets" / "skills" / "smart-search-cli"
# Mirror npm/scripts/check-skill-parity.js exclusions exactly: machine-local
# files stripped from the tarball must not count toward parity either.
EXCLUDED_SUFFIXES = {".pyc"}
EXCLUDED_NAMES = {"__pycache__", "config.json", ".env"}
MANAGED_BRANCH = "lwj_dev"
DELIVERY_ARTIFACT_SCHEMA = "jason-agent-infra.delivery-artifacts.v1"
COMMIT_OID = re.compile(r"[0-9a-f]{40}\Z")


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout.strip()


def _iter_skill_files(root: Path):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_NAMES]
        for name in sorted(filenames):
            if name in EXCLUDED_NAMES or Path(name).suffix in EXCLUDED_SUFFIXES:
                continue
            path = Path(dirpath) / name
            yield path.relative_to(root), path


def _skill_digests(root: Path) -> dict[str, str]:
    digests = {}
    for rel, path in _iter_skill_files(root):
        digests[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
    return digests


def inspect() -> dict:
    branch = _git("branch", "--show-current")
    head = _git("rev-parse", "HEAD")
    clean = _git("status", "--porcelain") == ""
    parity = {"status": "unknown", "missing": [], "extra": [], "drift": []}
    if SOURCE_SKILL.is_dir() and PACKAGED_SKILL.is_dir():
        source = _skill_digests(SOURCE_SKILL)
        packaged = _skill_digests(PACKAGED_SKILL)
        parity["missing"] = sorted(set(source) - set(packaged))
        parity["extra"] = sorted(set(packaged) - set(source))
        parity["drift"] = sorted(
            name for name in set(source) & set(packaged) if source[name] != packaged[name]
        )
        parity["status"] = (
            "consistent"
            if not parity["missing"] and not parity["extra"] and not parity["drift"]
            else "drift"
        )
    else:
        parity["status"] = "skill_path_missing"
    errors = []
    if branch != MANAGED_BRANCH:
        errors.append("SS_SYNC_BRANCH_MISMATCH")
    if not clean:
        errors.append("SS_SYNC_DIRTY_UNSCOPED")
    if parity["status"] != "consistent":
        errors.append("SS_SYNC_SKILL_PARITY_DRIFT")
    return {
        "schema": "jason-smartsearch.managed-sync-inspection.v1",
        "project_id": "smartsearch",
        "branch": branch,
        "head_commit": head,
        "clean": clean,
        "parity": parity,
        "errors": errors,
        "status": "ok" if not errors else "blocked",
    }


def downstream_handoff() -> dict:
    """Ask the Skills owner to inspect its committed common package provenance."""
    payload = {"schema": DELIVERY_ARTIFACT_SCHEMA, "status": "handoff_required",
               "errors": ["SS_SYNC_DOWNSTREAM_HANDOFF_REQUIRED"], "artifacts": []}
    workspace_value = os.environ.get("AGENT_INFRA_WORKSPACE_ROOT")
    infra_value = os.environ.get("AGENT_INFRA_REPOSITORY_ROOT")
    if not workspace_value or not infra_value:
        payload["next_step_argv"] = ["agent-infra", "sync", "project", "smartsearch",
                                     "--through", "downstream", "--workspace-root", "ABSOLUTE_PATH"]
        return payload
    workspace = Path(workspace_value)
    infra = Path(infra_value)
    consumer_root: Path | None = None
    try:
        registry = json.loads((infra / "manifests/workspace-repositories.json").read_text(encoding="utf-8"))
        consumer = registry["skills"]
        common = consumer["common"]
        if common["branch"] != "main":
            raise ValueError("Skills common registry branch is not main")
        target = Path(common["target"])
        if target.is_absolute() or ".." in target.parts:
            raise ValueError("Skills common registry target is invalid")
        consumer_root = workspace / target
        helper = consumer_root / "scripts/inspect_upstream_delivery.py"
        if not helper.is_file():
            payload["next_step_argv"] = ["agent-infra", "sync", "repositories",
                                         "--workspace-root", str(workspace)]
            raise FileNotFoundError("Skills downstream inspection helper is missing")
        argv = [sys.executable, str(helper), "smart-search-cli",
                "--source-checkout", str(REPO_ROOT),
                "--consumer-repo-root", str(consumer_root),
                "--consumer-repository-url", consumer["repository"]]
        completed = subprocess.run(argv, cwd=REPO_ROOT, capture_output=True, text=True,
                                   encoding="utf-8", check=False, timeout=120)
        if completed.returncode != 0:
            try:
                report = json.loads(completed.stdout)
            except ValueError as error:
                raise RuntimeError(
                    "Skills inspection helper returned no valid JSON; check its Python/PyYAML runtime"
                ) from error
            if not isinstance(report, dict):
                raise TypeError("Skills inspection helper returned a non-object report")
            reason = str(report.get("error", "Skills inspection failed"))
            if "selected source artifact is not adopted" in reason:
                updater = consumer_root / "scripts/update_global_skill.py"
                if not updater.is_file():
                    raise FileNotFoundError("Skills package updater is missing")
                payload["next_step_argv"] = [
                    sys.executable, str(updater), "smart-search-cli",
                    "--repo-root", str(consumer_root), "--source-checkout", str(REPO_ROOT),
                    "--target", _git("rev-parse", "HEAD"),
                ]
            else:
                payload["next_step_argv"] = ["git", "-C", str(consumer_root),
                                             "status", "--short", "--branch"]
            raise RuntimeError("Skills inspection: " + reason)
        inspected = json.loads(completed.stdout)
        if not isinstance(inspected, dict):
            raise TypeError("Skills inspection helper returned a non-object report")
        if inspected.get("status") != "committed" or inspected.get("producer_commit") != _git("rev-parse", "HEAD"):
            raise ValueError("Skills inspection did not confirm this producer commit")
        expected_path = SOURCE_SKILL.relative_to(REPO_ROOT).as_posix()
        if inspected.get("artifact_path") != expected_path or inspected.get("artifact_name") != "smart-search-cli":
            raise ValueError("Skills inspection selected a different source artifact")
        consumer_commit = inspected.get("consumer_commit")
        source_commit = inspected.get("consumer_source_commit")
        relation = inspected.get("source_relation")
        if (not isinstance(consumer_commit, str) or not COMMIT_OID.fullmatch(consumer_commit)
                or not isinstance(source_commit, str) or not COMMIT_OID.fullmatch(source_commit)
                or not isinstance(relation, str)
                or relation not in {"exact_current_pin", "artifact_equivalent"}
                or (relation == "exact_current_pin") != (source_commit == inspected["producer_commit"])):
            raise ValueError("Skills inspection returned invalid committed consumer provenance")
        version = json.loads(_git("show", "HEAD:package.json"))["version"]
        if not isinstance(version, str) or not version:
            raise ValueError("committed Smart Search package version is missing")
        artifact = {
            "producer_repository": "smartsearch",
            "producer_commit": inspected["producer_commit"],
            "artifact_path": inspected["artifact_path"],
            "artifact_name": inspected["artifact_name"],
            "artifact_version": version,
            "consumer_repository": "skills-common",
            "consumer_commit": inspected["consumer_commit"],
            "consumer_source_commit": inspected["consumer_source_commit"],
            "source_relation": inspected["source_relation"],
            "verification_level": "committed",
        }
        payload["artifacts"] = [artifact]
        payload["errors"] = []
        payload["status"] = "completed"
        return payload
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, UnicodeError,
            subprocess.TimeoutExpired) as error:
        payload["reason"] = str(error)[:300]
        if "next_step_argv" not in payload:
            payload["next_step_argv"] = (
                ["git", "-C", str(consumer_root), "status", "--short", "--branch"]
                if consumer_root is not None
                else ["agent-infra", "sync", "repositories", "--workspace-root", str(workspace)]
            )
        return payload


SEARCH_QUERY = "RFC 9110 HTTP Semantics"


def verify_live() -> dict:
    """Gate-aware live verification: config gate, one doctor probe, one real search.

    Doctor success alone is diagnostic readiness, not live evidence.  A
    ``live`` status requires the fixed, non-sensitive search case below to
    succeed against the real provider path.  If doctor passes but the search
    fails, the result is ``activated`` (diagnostic_ready), never ``live``.

    Both probes use the npm bin wrapper (node npm/bin/smart-search.js), which
    owns the project Python runtime and repairs it when missing.  The raw
    ``python -m smart_search`` module is not installed system-wide, so it is
    never invoked directly.  Probe outputs are discarded: only exit codes and
    the fixed query enter the receipt, so no provider response content or
    secret value can leak.
    """
    config_path = Path.home() / ".config" / "smart-search" / "config.json"
    result = {
        "schema": "jason-smartsearch.managed-sync-live-verify.v1",
        "project_id": "smartsearch",
        "config_authority": str(config_path).replace(str(Path.home()), "~", 1),
        "config_present": config_path.is_file(),
        "probe": "not_run",
        "errors": [],
    }
    if not result["config_present"]:
        result["errors"].append("SS_VERIFY_EXTERNAL_GATE_MISSING")
        result["status"] = "blocked"
        return result
    # Single recovery/doctor probe maximum; failures are surfaced, not retried.
    wrapper = REPO_ROOT / "npm" / "bin" / "smart-search.js"
    if not wrapper.is_file():
        result["errors"].append("SS_VERIFY_EXTERNAL_GATE_MISSING")
        result["status"] = "blocked"
        return result
    try:
        proc = subprocess.run(
            ["node", str(wrapper), "doctor", "--format", "json"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=240,
        )
        result["probe"] = "doctor_once"
        result["probe_exit"] = proc.returncode
        if proc.returncode != 0:
            result["errors"].append("SS_VERIFY_PROVIDER_ERROR")
            result["status"] = "failed"
            return result
    except Exception as exc:  # noqa: BLE001 - surfaced as structured error
        result["probe"] = "doctor_once"
        result["errors"].append("SS_VERIFY_PROVIDER_ERROR")
        result["probe_error"] = type(exc).__name__
        result["status"] = "failed"
        return result
    # One fixed, non-sensitive real search case proves the live consumer path.
    try:
        search = subprocess.run(
            [
                "node", str(wrapper), "search", SEARCH_QUERY,
                "--format", "json",
                "--validation", "fast",
                "--fallback", "off",
                "--max-try", "1",
                "--timeout", "90",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            timeout=180,
        )
        result["probe"] = "doctor_once+search_once"
        result["search_exit"] = search.returncode
        result["search_query"] = SEARCH_QUERY
        if search.returncode == 0:
            result["status"] = "live"
        else:
            # Diagnostic path works, but live consumer evidence is missing.
            result["errors"].append("SS_VERIFY_PROVIDER_ERROR")
            result["status"] = "activated"
    except Exception as exc:  # noqa: BLE001 - surfaced as structured error
        result["probe"] = "doctor_once+search_once"
        result["errors"].append("SS_VERIFY_PROVIDER_ERROR")
        result["search_error"] = type(exc).__name__
        result["status"] = "activated"
    return result


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"inspect", "downstream-handoff", "verify-live"}:
        print(json.dumps({"error": "usage: managed_sync.py inspect|downstream-handoff|verify-live"}))
        return 2
    payload = (inspect() if sys.argv[1] == "inspect" else
               downstream_handoff() if sys.argv[1] == "downstream-handoff" else verify_live())
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") in {"ok", "completed", "live"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
