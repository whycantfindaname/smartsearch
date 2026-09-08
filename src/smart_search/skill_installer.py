from __future__ import annotations

import os
from dataclasses import dataclass
from hashlib import sha256
from importlib import resources
from pathlib import Path
from typing import Any

SKILL_NAME = "smart-search-cli"
# Local runtime overrides stay at their destination. The Smart Search parent
# config is never part of an installed Skill tree, even if a source checkout
# accidentally contains a config.json beside the bundled files.
PRESERVED_LOCAL_FILES = {".env", "runtime.conf", "config.json"}
PACKAGE_ROOT_ENV = "SMART_SEARCH_PACKAGE_ROOT"


@dataclass(frozen=True)
class SkillTarget:
    target_id: str
    label: str
    relative_root: str
    default: bool = False

    @property
    def skill_relative_path(self) -> str:
        return f"{self.relative_root}/{SKILL_NAME}"

    def skill_relative_path_for(self, skill_name: str) -> str:
        return f"{self.relative_root}/{skill_name}"

    def skill_path_for(self, root: Path, skill_name: str) -> Path:
        destination = root / self.skill_relative_path_for(skill_name)
        if self.target_id == "qoder" and not (destination.exists() or destination.is_symlink()):
            regional = root / ".qoder-cn" / "skills" / skill_name
            if regional.parent.is_dir():
                return regional
        return destination


SKILL_TARGETS: tuple[SkillTarget, ...] = (
    SkillTarget("codex", "Codex", ".codex/skills", True),
    SkillTarget("claude", "Claude Code", ".claude/skills", True),
    SkillTarget("cursor", "Cursor", ".cursor/skills", True),
    SkillTarget("opencode", "OpenCode", ".config/opencode/skills"),
    SkillTarget("copilot", "GitHub Copilot", ".copilot/skills"),
    SkillTarget("gemini", "Gemini CLI", ".gemini/skills"),
    SkillTarget("kiro", "Kiro", ".kiro/skills"),
    SkillTarget("qoder", "Qoder", ".qoder/skills"),
    SkillTarget("codebuddy", "CodeBuddy", ".codebuddy/skills"),
    SkillTarget("droid", "Factory Droid", ".factory/skills"),
    SkillTarget("pi", "Pi Agent", ".pi/agent/skills"),
    SkillTarget("kilo", "Kilo CLI", ".kilocode/skills"),
    SkillTarget("antigravity", "Antigravity", ".agent/skills"),
    SkillTarget("windsurf", "Windsurf", ".windsurf/skills"),
    SkillTarget("hermes", "Hermes Agent", ".hermes/skills"),
)

SKILL_TARGET_BY_ID = {target.target_id: target for target in SKILL_TARGETS}
DEFAULT_SKILL_TARGET_IDS = [target.target_id for target in SKILL_TARGETS if target.default]
LEGACY_SKILL_ROOTS_BY_TARGET: dict[str, tuple[str, ...]] = {
    "opencode": (".opencode/skills",),
}

_TARGET_ALIASES = {
    "agents": "codex",
    "agentskills": "codex",
    "agent-skills": "codex",
    "claude-code": "claude",
    "github-copilot": "copilot",
    "gh-copilot": "copilot",
    "factory": "droid",
    "factory-droid": "droid",
    "pi-agent": "pi",
    "kilo-cli": "kilo",
    "hermes-agent": "hermes",
    "nous-hermes": "hermes",
}


class SkillInstallError(ValueError):
    pass


def parse_skill_targets(raw: str) -> list[str]:
    if not raw.strip():
        return []
    tokens = [part.strip().lower() for part in raw.replace(";", ",").replace("+", ",").split(",")]
    if len(tokens) == 1 and " " in tokens[0]:
        tokens = [part.strip().lower() for part in tokens[0].split()]

    selected: list[str] = []
    invalid: list[str] = []
    for token in tokens:
        if not token:
            continue
        if token in {"skip", "none", "no", "n", "跳过", "无", "否"}:
            return []
        if token in {"all", "全部"}:
            return [target.target_id for target in SKILL_TARGETS]
        target_id = _TARGET_ALIASES.get(token, token)
        if target_id not in SKILL_TARGET_BY_ID:
            invalid.append(token)
            continue
        if target_id not in selected:
            selected.append(target_id)

    if invalid:
        valid = ", ".join(target.target_id for target in SKILL_TARGETS)
        raise SkillInstallError(f"Unknown skill target(s): {', '.join(invalid)}. Valid targets: {valid}")
    return selected


def _resource_skill_root(skill_name: str = SKILL_NAME) -> Any:
    try:
        root = resources.files("smart_search").joinpath("assets", "skills", skill_name)
        if root.is_dir():
            return root
    except (FileNotFoundError, ModuleNotFoundError, AttributeError):
        pass
    return None


def _filesystem_skill_root(skill_name: str = SKILL_NAME) -> Path | None:
    candidates: list[Path] = []
    package_root = os.getenv(PACKAGE_ROOT_ENV, "").strip()
    if package_root:
        base = Path(package_root)
        candidates.extend([
            base / "src" / "smart_search" / "assets" / "skills" / skill_name,
            base / "skills" / skill_name,
        ])

    repo_root = Path(__file__).resolve().parents[2]
    candidates.extend([
        repo_root / "src" / "smart_search" / "assets" / "skills" / skill_name,
        repo_root / "skills" / skill_name,
    ])

    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    return None


def _iter_resource_files(root: Any) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []

    def visit(node: Any, prefix: str = "") -> None:
        for child in node.iterdir():
            rel = f"{prefix}/{child.name}" if prefix else child.name
            if child.is_dir():
                visit(child, rel)
            elif child.is_file():
                files.append((rel, child.read_bytes()))

    visit(root)
    return files


def _iter_filesystem_files(root: Path) -> list[tuple[str, bytes]]:
    return [
        (str(path.relative_to(root)).replace("\\", "/"), path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    ]


def _load_skill_files(
    source_root: Path | None = None,
    *,
    skill_name: str = SKILL_NAME,
) -> list[tuple[str, bytes]]:
    if source_root is not None:
        if not source_root.is_dir():
            raise SkillInstallError(f"Skill source directory not found: {source_root}")
        return _iter_filesystem_files(source_root)

    resource_root = _resource_skill_root(skill_name)
    if resource_root is not None:
        files = _iter_resource_files(resource_root)
        if files:
            return files

    filesystem_root = _filesystem_skill_root(skill_name)
    if filesystem_root is not None:
        files = _iter_filesystem_files(filesystem_root)
        if files:
            return files

    raise SkillInstallError(f"Bundled {skill_name} skill files were not found.")


def _skill_digest(files: list[tuple[str, bytes]]) -> str:
    digest = sha256()
    for rel_path, content in sorted(files, key=lambda item: item[0]):
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        digest.update(b"\0")
    return digest.hexdigest()


def _target_installed_files(path: Path) -> list[tuple[str, bytes]]:
    if not path.is_dir():
        return []
    return _iter_filesystem_files(path)


def _status_for_skill(
    *,
    skill_name: str,
    root: Path,
    selected: list[SkillTarget],
    source: Path | None = None,
    preserved_files: set[str] | None = None,
) -> dict[str, Any]:
    preserved = preserved_files or set()
    source_files = [
        (rel_path, content)
        for rel_path, content in _load_skill_files(source, skill_name=skill_name)
        if Path(rel_path).name not in preserved
    ]
    source_by_path = {rel_path: content for rel_path, content in source_files}
    bundled_digest = _skill_digest(source_files)
    targets: list[dict[str, Any]] = []

    for target in selected:
        dest = root / target.skill_relative_path_for(skill_name)
        item: dict[str, Any] = {
            "target": target.target_id,
            "label": target.label,
            "path": str(dest),
            "status": "missing",
            "files": len(source_files),
            "installed_files": 0,
            "bundled_hash": bundled_digest,
            "installed_hash": "",
            "hash_match": False,
            "managed_hash_match": False,
            "extra_files": [],
            "missing_files": sorted(source_by_path),
            "stale_files": [],
        }
        try:
            dest = target.skill_path_for(root, skill_name)
            item["path"] = str(dest)
            installed_files = _target_installed_files(dest)
            installed_by_path = {rel_path: content for rel_path, content in installed_files}
            installed_managed_files = [
                (rel_path, content)
                for rel_path, content in installed_files
                if Path(rel_path).name not in preserved
            ]
            item["installed_files"] = len(installed_files)
            if not dest.exists():
                targets.append(item)
                continue
            if not dest.is_dir():
                item["status"] = "error"
                item["error"] = "Installed skill path exists but is not a directory."
                targets.append(item)
                continue

            installed_digest = _skill_digest(installed_managed_files)
            extra_files = sorted(
                rel_path
                for rel_path in installed_by_path
                if rel_path not in source_by_path and Path(rel_path).name not in preserved
            )
            missing_files = sorted(rel_path for rel_path in source_by_path if rel_path not in installed_by_path)
            stale_files = sorted(
                rel_path
                for rel_path, content in source_by_path.items()
                if rel_path in installed_by_path and installed_by_path[rel_path] != content
            )
            managed_hash_match = not missing_files and not stale_files
            hash_match = managed_hash_match and not extra_files
            item.update(
                {
                    "installed_hash": installed_digest if installed_files else "",
                    "hash_match": hash_match,
                    "managed_hash_match": managed_hash_match,
                    "extra_files": extra_files,
                    "missing_files": missing_files,
                    "stale_files": stale_files,
                }
            )
            if missing_files or stale_files:
                item["status"] = "stale"
            elif extra_files:
                item["status"] = "extra_files"
            else:
                item["status"] = "up_to_date"
        except OSError as e:
            item["status"] = "error"
            item["error"] = str(e)
        targets.append(item)

    status_counts: dict[str, int] = {}
    for item in targets:
        status = str(item.get("status", "error"))
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "ok": not any(item.get("status") == "error" for item in targets),
        "root": str(root),
        "selected": [target.target_id for target in selected],
        "skill": skill_name,
        "bundled_files": len(source_files),
        "bundled_hash": bundled_digest,
        "targets": targets,
        "status_counts": status_counts,
    }


def status_skill_targets(
    target_ids: list[str],
    *,
    project_root: str | Path | None = None,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve() if project_root else Path.home().expanduser().resolve()
    selected = [SKILL_TARGET_BY_ID[target_id] for target_id in target_ids]
    source = Path(source_root).expanduser().resolve() if source_root is not None else None
    result = _status_for_skill(
        skill_name=SKILL_NAME,
        root=root,
        selected=selected,
        source=source,
        preserved_files=PRESERVED_LOCAL_FILES,
    )
    for target, item in zip(selected, result["targets"]):
        legacy_locations: list[dict[str, Any]] = []
        for legacy_relative_root in LEGACY_SKILL_ROOTS_BY_TARGET.get(target.target_id, ()):
            legacy_target = SkillTarget(
                target_id=target.target_id,
                label=target.label,
                relative_root=legacy_relative_root,
            )
            legacy_item = _status_for_skill(
                skill_name=SKILL_NAME,
                root=root,
                selected=[legacy_target],
                source=source,
                preserved_files=PRESERVED_LOCAL_FILES,
            )["targets"][0]
            if Path(legacy_item["path"]).exists():
                legacy_locations.append(legacy_item)
        if legacy_locations:
            item["legacy_locations"] = legacy_locations
    return result


def _install_skill(
    *,
    skill_name: str,
    files: list[tuple[str, bytes]],
    root: Path,
    selected: list[SkillTarget],
    preserved_files: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    installed: list[dict[str, Any]] = []
    failed: list[dict[str, str]] = []
    preserved = preserved_files or set()

    for target in selected:
        dest = root / target.skill_relative_path_for(skill_name)
        try:
            dest = target.skill_path_for(root, skill_name)
            if target.target_id == "qoder" and dest.is_symlink():
                raise OSError(
                    "Qoder skill is a symbolic link; update it through the tool that manages the link."
                )
            for rel_path, content in files:
                if Path(rel_path).name in preserved:
                    continue
                file_path = dest / Path(rel_path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(content)
            installed.append(
                {
                    "skill": skill_name,
                    "target": target.target_id,
                    "label": target.label,
                    "path": str(dest),
                    "files": len([rel_path for rel_path, _ in files if Path(rel_path).name not in preserved]),
                    "preserved_files": sorted(preserved),
                }
            )
        except OSError as e:
            failed.append(
                {
                    "skill": skill_name,
                    "target": target.target_id,
                    "label": target.label,
                    "path": str(dest),
                    "error": str(e),
                }
            )
    return installed, failed


def install_skill_targets(
    target_ids: list[str],
    *,
    project_root: str | Path | None = None,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(project_root).expanduser().resolve() if project_root else Path.home().expanduser().resolve()
    selected = [SKILL_TARGET_BY_ID[target_id] for target_id in target_ids]
    if not selected:
        return {
            "ok": True,
            "root": str(root),
            "installed": [],
            "skipped": [],
            "failed": [],
            "selected": [],
            "installed_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
        }

    source = Path(source_root).expanduser().resolve() if source_root is not None else None
    files = _load_skill_files(source, skill_name=SKILL_NAME)
    installed, failed = _install_skill(
        skill_name=SKILL_NAME,
        files=files,
        root=root,
        selected=selected,
        preserved_files=PRESERVED_LOCAL_FILES,
    )

    return {
        "ok": not failed,
        "root": str(root),
        "installed": installed,
        "skipped": [],
        "failed": failed,
        "selected": [target.target_id for target in selected],
        "installed_count": len(installed),
        "skipped_count": 0,
        "failed_count": len(failed),
    }
