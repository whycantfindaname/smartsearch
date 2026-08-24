import shutil
from pathlib import Path

from smart_search import cli


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SIDECAR_SOURCE = REPOSITORY_ROOT / "sidecar"
PACKAGED_SIDECAR = REPOSITORY_ROOT / "src" / "smart_search" / "assets" / "sidecar"


def _installable_manifest(root: Path) -> set[Path]:
    manifest = {Path("pyproject.toml"), Path("README.md")}
    manifest.update(path.relative_to(root) for path in (root / "src").rglob("*.py"))
    return manifest


def test_packaged_sidecar_snapshot_matches_installable_source():
    expected_manifest = _installable_manifest(SIDECAR_SOURCE)
    packaged_manifest = {
        path.relative_to(PACKAGED_SIDECAR)
        for path in PACKAGED_SIDECAR.rglob("*")
        if path.is_file()
    }

    assert packaged_manifest == expected_manifest
    for relative_path in sorted(expected_manifest):
        assert (PACKAGED_SIDECAR / relative_path).read_bytes() == (SIDECAR_SOURCE / relative_path).read_bytes()


def test_sidecar_source_resolver_prefers_checkout_source():
    assert cli._sidecar_install_source() == SIDECAR_SOURCE


def test_sidecar_source_resolver_falls_back_to_packaged_asset(tmp_path):
    installed_package = tmp_path / "site-packages" / "smart_search"
    packaged_asset = installed_package / "assets" / "sidecar"
    shutil.copytree(PACKAGED_SIDECAR, packaged_asset)

    resolved = cli._sidecar_install_source(installed_package / "cli.py")

    assert resolved == packaged_asset
    assert (resolved / "pyproject.toml").is_file()
    assert (resolved / "src" / "smart_search_sidecar" / "__init__.py").is_file()
