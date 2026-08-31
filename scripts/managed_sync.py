#!/usr/bin/env python3
"""Smart Search managed-sync project entrypoint.

Minimal contract entrypoint referenced by .agent-infra/managed-project.json.
It never reads secret values, never pushes, and never mutates the worktree.
"""

from __future__ import annotations

import hashlib
import json
import os
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


def _git(*args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
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


def verify_live() -> dict:
    """Gate-aware live probe: config presence first, then one doctor run.

    The probe uses the npm bin wrapper (node npm/bin/smart-search.js), which
    owns the project Python runtime and repairs it when missing.  The raw
    ``python -m smart_search`` module is not installed system-wide, so it is
    never invoked directly.  Doctor output is masked upstream, but it is
    discarded here anyway: only the exit code enters the receipt.
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
            timeout=240,
        )
        result["probe"] = "doctor_once"
        result["probe_exit"] = proc.returncode
        if proc.returncode != 0:
            result["errors"].append("SS_VERIFY_PROVIDER_ERROR")
            result["status"] = "failed"
        else:
            result["status"] = "live"
    except Exception as exc:  # noqa: BLE001 - surfaced as structured error
        result["probe"] = "doctor_once"
        result["errors"].append("SS_VERIFY_PROVIDER_ERROR")
        result["probe_error"] = type(exc).__name__
        result["status"] = "failed"
    return result


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in {"inspect", "verify-live"}:
        print(json.dumps({"error": "usage: managed_sync.py inspect|verify-live"}))
        return 2
    payload = inspect() if sys.argv[1] == "inspect" else verify_live()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("status") in {"ok", "live"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
