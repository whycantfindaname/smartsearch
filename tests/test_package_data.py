"""Guard: every bundled asset file must be covered by setuptools package-data.

A new asset file that matches no ``[tool.setuptools.package-data]`` pattern is
silently missing from wheels (and therefore from the npm postinstall venv),
which is how the bundled AnySearch ``CONTRACT.md`` was once dropped.
"""

import re
from fnmatch import fnmatchcase
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
ASSETS_ROOT = REPO_ROOT / "src" / "smart_search" / "assets"
PYPROJECT = REPO_ROOT / "pyproject.toml"


PACKAGE_ROOT = REPO_ROOT / "src" / "smart_search"


def _package_data_patterns() -> list[str]:
    lines = PYPROJECT.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("[tool.setuptools.package-data]")
    except ValueError:
        raise AssertionError("pyproject.toml is missing [tool.setuptools.package-data]")
    patterns: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith("["):
            break
        patterns.extend(re.findall(r'"([^"]+)"', line))
    assert patterns, "no package-data patterns found"
    return patterns


# Machine-local files stripped from every distribution via package.json
# `files` exclusions; they must stay out of package-data.
MACHINE_LOCAL_FILE_NAMES = {".env", "config.json"}


def _is_package_module(path: Path) -> bool:
    """True when setuptools includes the .py automatically as a package module."""
    if path.suffix != ".py":
        return False
    directory = path.parent
    while True:
        if directory == PACKAGE_ROOT:
            return True
        if not (directory / "__init__.py").is_file():
            return False
        directory = directory.parent


# fnmatch's ``*`` crosses "/" boundaries, but setuptools package-data globs use
# path-segment semantics; escape-aware translation keeps the guard honest.
def _matches_segment_glob(relpath: str, pattern: str) -> bool:
    if relpath == pattern:
        return True
    if "*" not in pattern:
        return False
    pattern_parts = pattern.split("/")
    path_parts = relpath.split("/")
    if len(pattern_parts) != len(path_parts):
        return False
    return all(fnmatchcase(p, pat) for p, pat in zip(path_parts, pattern_parts))


def test_every_bundled_asset_file_is_covered_by_package_data():
    patterns = _package_data_patterns()
    uncovered: list[str] = []
    for path in sorted(ASSETS_ROOT.rglob("*")):
        if not path.is_file() or "__pycache__" in path.parts:
            continue
        if path.name in MACHINE_LOCAL_FILE_NAMES or _is_package_module(path):
            continue
        # package-data globs are relative to the smart_search package directory
        relpath = path.relative_to(PACKAGE_ROOT).as_posix()
        if not any(_matches_segment_glob(relpath, pattern) for pattern in patterns):
            uncovered.append(relpath)
    assert uncovered == [], (
        "asset files not matched by any pyproject package-data glob "
        f"(they will be missing from wheels): {uncovered}"
    )


def test_known_asset_entrypoints_are_covered():
    patterns = _package_data_patterns()
    for required in (
        "assets/skills/smart-search-cli/SKILL.md",
        "assets/skills/smart-search-cli/bundled-skills/anysearch/CONTRACT.md",
        "assets/skills/smart-search-cli/bundled-skills/anysearch/.env.example",
        "assets/sidecar/pyproject.toml",
        "assets/research_visualizer/index.html",
    ):
        assert any(_matches_segment_glob(required, pattern) for pattern in patterns), required
