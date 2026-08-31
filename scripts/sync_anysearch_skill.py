#!/usr/bin/env python3
"""Refresh Smart Search's bundled AnySearch Skill from GitHub.

The preferred source is ``jason-liao-skills/main``. The official AnySearch
repository is used only when that checkout succeeds but does not contain
``skill-packages/anysearch``. Network or authentication failures never trigger the
official fallback, so an existing bundled snapshot is left untouched.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PREFERRED_REPOSITORY = "https://github.com/whycantfindaname/jason-liao-skills.git"
PREFERRED_REF = "main"
PREFERRED_SKILL_PATH = Path("skill-packages/anysearch")
OFFICIAL_REPOSITORY = "https://github.com/anysearch-ai/anysearch-skill.git"
OFFICIAL_REF = "v3.1.0"

# These files are machine-local or Smart Search-owned. They are deliberately
# absent from the upstream file set so a snapshot refresh cannot overwrite or
# delete them. ``config.json`` is the parent Smart Search config and must never
# be copied into an embedded AnySearch Skill.
PRESERVED_NAMES = {".env", "runtime.conf", "config.json"}
PRESERVED_RELATIVE_NAMES = {"scripts/smart_search_anysearch.py"}
SMART_SEARCH_OVERLAY_RELATIVE_NAMES = {
    ".env.example",
    "CONTRACT.md",
    "README.md",
    "runtime.conf.example",
    "scripts/smart_search_anysearch.py",
}
UPSTREAM_ENTRYPOINT_NAME = "SKILL.md"
IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_PARTS = {".git"}
REQUIRED_FILES = {"SKILL.md", "LICENSE", "NOTICE"}
PROVENANCE_NAME = "anysearch-source.json"


class SyncError(RuntimeError):
    """A source checkout or snapshot validation failed."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _destinations(repo_root: Path) -> list[Path]:
    return [
        repo_root
        / "skills"
        / "smart-search-cli"
        / "bundled-skills"
        / "anysearch",
        repo_root
        / "src"
        / "smart_search"
        / "assets"
        / "skills"
        / "smart-search-cli"
        / "bundled-skills"
        / "anysearch",
    ]


def _run_git(args: list[str], *, cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"})
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            check=True,
            text=True,
            capture_output=True,
            timeout=60,
        )
    except FileNotFoundError as exc:
        raise SyncError("git is required to refresh the AnySearch snapshot") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "git command failed").strip()
        raise SyncError(detail) from exc
    except subprocess.TimeoutExpired as exc:
        raise SyncError("git command timed out after 60 seconds") from exc
    return result.stdout.strip()


def _clone_repository(
    repository: str,
    ref: str,
    destination: Path,
    *,
    sparse_path: Path | None = None,
) -> tuple[str, str]:
    _run_git(
        [
            "clone",
            "--quiet",
            "--filter=blob:none",
            "--no-checkout",
            "--depth",
            "1",
            "--single-branch",
            "--branch",
            ref,
            repository,
            str(destination),
        ]
    )
    if sparse_path is not None:
        _run_git(["sparse-checkout", "init", "--cone"], cwd=destination)
        _run_git(["sparse-checkout", "set", sparse_path.as_posix()], cwd=destination)
    _run_git(["checkout", "--quiet", ref], cwd=destination)
    commit = _run_git(["rev-parse", "HEAD"], cwd=destination)
    commit_date = _run_git(["show", "-s", "--format=%cI", "HEAD"], cwd=destination)
    return commit, commit_date


def _included_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in IGNORED_PARTS or part in IGNORED_NAMES for part in rel.parts):
            continue
        if (
            rel.name in PRESERVED_NAMES
            or rel.as_posix() in PRESERVED_RELATIVE_NAMES
            or rel.suffix == ".pyc"
        ):
            continue
        files[rel.as_posix()] = path
    return files


def _included_source_files(root: Path) -> dict[str, Path]:
    """Return upstream runtime files without exposing its Skill entrypoint."""

    files = _included_files(root)
    files.pop(UPSTREAM_ENTRYPOINT_NAME, None)
    return files


def _validate_source(source: Path) -> None:
    if not source.is_dir():
        raise SyncError(f"AnySearch Skill source not found: {source}")
    missing = sorted(name for name in REQUIRED_FILES if not (source / name).is_file())
    if missing:
        raise SyncError(f"AnySearch Skill source is incomplete: {', '.join(missing)}")


def _skill_version(source: Path) -> str:
    text = (source / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*['\"]?([^'\"\s]+)", text, flags=re.MULTILINE)
    return match.group(1) if match else ""


def _resolve_source(temp_root: Path) -> tuple[Path, dict[str, object]]:
    preferred_root = temp_root / "jason-liao-skills"
    try:
        preferred_commit, preferred_date = _clone_repository(
            PREFERRED_REPOSITORY,
            PREFERRED_REF,
            preferred_root,
            sparse_path=PREFERRED_SKILL_PATH,
        )
    except SyncError as exc:
        raise SyncError(
            "preferred AnySearch source could not be read; existing snapshot was preserved: "
            f"{exc}"
        ) from exc

    preferred_skill = preferred_root / PREFERRED_SKILL_PATH
    if preferred_skill.is_dir():
        _validate_source(preferred_skill)
        return preferred_skill, {
            "schema_version": 1,
            "preferred_repository": PREFERRED_REPOSITORY,
            "preferred_ref": PREFERRED_REF,
            "preferred_commit": preferred_commit,
            "selected_source": "jason-liao-skills",
            "selected_repository": PREFERRED_REPOSITORY,
            "selected_ref": PREFERRED_REF,
            "selected_commit": preferred_commit,
            "selected_commit_date": preferred_date,
            "skill_version": _skill_version(preferred_skill),
            "fallback_reason": "",
        }

    official_root = temp_root / "anysearch-official"
    official_commit, official_date = _clone_repository(
        OFFICIAL_REPOSITORY,
        OFFICIAL_REF,
        official_root,
    )
    _validate_source(official_root)
    return official_root, {
        "schema_version": 1,
        "preferred_repository": PREFERRED_REPOSITORY,
        "preferred_ref": PREFERRED_REF,
        "preferred_commit": preferred_commit,
        "selected_source": "official-fallback",
        "selected_repository": OFFICIAL_REPOSITORY,
        "selected_ref": OFFICIAL_REF,
        "selected_commit": official_commit,
        "selected_commit_date": official_date,
        "skill_version": _skill_version(official_root),
        "fallback_reason": "preferred_package_missing",
    }


def _different(source: Path, destination: Path) -> list[str]:
    source_files = _included_source_files(source)
    destination_files = _included_files(destination) if destination.is_dir() else {}
    for rel in SMART_SEARCH_OVERLAY_RELATIVE_NAMES:
        if rel in destination_files:
            source_files.pop(rel, None)
            destination_files.pop(rel, None)
    changed = set(source_files) ^ set(destination_files)
    for rel in set(source_files) & set(destination_files):
        if source_files[rel].read_bytes() != destination_files[rel].read_bytes():
            changed.add(rel)
    return sorted(changed)


def _sync(source: Path, destination: Path) -> list[str]:
    changed = _different(source, destination)
    source_files = _included_source_files(source)
    destination_files = _included_files(destination) if destination.is_dir() else {}
    overlays = {
        rel: (destination / rel).read_bytes()
        for rel in SMART_SEARCH_OVERLAY_RELATIVE_NAMES
        if (destination / rel).is_file()
    }

    destination.mkdir(parents=True, exist_ok=True)
    for rel in sorted(set(destination_files) - set(source_files)):
        if rel in SMART_SEARCH_OVERLAY_RELATIVE_NAMES:
            continue
        destination_files[rel].unlink()
    for rel, source_path in source_files.items():
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or source_path.read_bytes() != target.read_bytes():
            shutil.copy2(source_path, target)
    for rel, content in overlays.items():
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != content:
            target.write_bytes(content)

    for directory in sorted(
        (path for path in destination.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if not any(directory.iterdir()):
            directory.rmdir()
    return changed


def _provenance_path(destination: Path) -> Path:
    return destination.parent / PROVENANCE_NAME


def _serialized_provenance(provenance: dict[str, object]) -> bytes:
    return (json.dumps(provenance, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report drift without writing files.")
    args = parser.parse_args(argv)

    repo_root = _repo_root()
    try:
        with tempfile.TemporaryDirectory(prefix="smart-search-anysearch-") as temp_dir:
            source, provenance = _resolve_source(Path(temp_dir))
            provenance_bytes = _serialized_provenance(provenance)
            drift: dict[str, list[str]] = {}
            for destination in _destinations(repo_root):
                changed = _different(source, destination)
                provenance_path = _provenance_path(destination)
                if not provenance_path.is_file() or provenance_path.read_bytes() != provenance_bytes:
                    changed.append(f"../{PROVENANCE_NAME}")
                drift[str(destination.relative_to(repo_root))] = sorted(changed)

            if args.check:
                for destination, changed in drift.items():
                    state = "up_to_date" if not changed else f"drift ({len(changed)} files)"
                    print(f"{destination}: {state}")
                return 1 if any(drift.values()) else 0

            for destination in _destinations(repo_root):
                changed = _sync(source, destination)
                provenance_path = _provenance_path(destination)
                if not provenance_path.is_file() or provenance_path.read_bytes() != provenance_bytes:
                    provenance_path.write_bytes(provenance_bytes)
                    changed.append(f"../{PROVENANCE_NAME}")
                print(f"{destination.relative_to(repo_root)}: synced ({len(changed)} changed files)")
            print(
                "source: "
                f"{provenance['selected_source']} "
                f"{provenance['selected_ref']}@{provenance['selected_commit']}"
            )
            return 0
    except SyncError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
