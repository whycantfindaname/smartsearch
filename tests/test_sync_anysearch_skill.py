import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sync_anysearch_skill",
    ROOT / "scripts" / "sync_anysearch_skill.py",
)
assert SPEC and SPEC.loader
sync_anysearch_skill = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync_anysearch_skill)


def _write_skill(path: Path, *, version: str = "3.1.0") -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"---\nname: anysearch\nversion: {version}\n---\n",
        encoding="utf-8",
    )
    (path / "LICENSE").write_text("license\n", encoding="utf-8")
    (path / "NOTICE").write_text("notice\n", encoding="utf-8")


def test_resolve_source_prefers_personal_main_package(monkeypatch, tmp_path):
    calls = []

    def fake_clone(repository, ref, destination, *, sparse_path=None):
        calls.append((repository, ref, sparse_path))
        assert sparse_path == Path("skill-packages/anysearch")
        _write_skill(destination / sparse_path)
        return "personal-commit", "2026-08-23T17:35:36+08:00"

    monkeypatch.setattr(sync_anysearch_skill, "_clone_repository", fake_clone)

    source, provenance = sync_anysearch_skill._resolve_source(tmp_path)

    assert source == tmp_path / "jason-liao-skills" / "skill-packages" / "anysearch"
    assert provenance["selected_source"] == "jason-liao-skills"
    assert provenance["selected_commit"] == "personal-commit"
    assert len(calls) == 1


def test_resolve_source_uses_official_only_when_preferred_package_is_absent(monkeypatch, tmp_path):
    calls = []

    def fake_clone(repository, ref, destination, *, sparse_path=None):
        calls.append(repository)
        if repository == sync_anysearch_skill.OFFICIAL_REPOSITORY:
            _write_skill(destination)
            return "official-commit", "2026-08-21T16:00:26+08:00"
        destination.mkdir(parents=True)
        return "personal-commit", "2026-08-23T17:35:36+08:00"

    monkeypatch.setattr(sync_anysearch_skill, "_clone_repository", fake_clone)

    source, provenance = sync_anysearch_skill._resolve_source(tmp_path)

    assert source == tmp_path / "anysearch-official"
    assert calls == [
        sync_anysearch_skill.PREFERRED_REPOSITORY,
        sync_anysearch_skill.OFFICIAL_REPOSITORY,
    ]
    assert provenance["selected_source"] == "official-fallback"
    assert provenance["fallback_reason"] == "preferred_package_missing"


def test_resolve_source_does_not_fallback_after_preferred_checkout_failure(monkeypatch, tmp_path):
    calls = []

    def fake_clone(repository, ref, destination, *, sparse_path=None):
        calls.append(repository)
        raise sync_anysearch_skill.SyncError("offline")

    monkeypatch.setattr(sync_anysearch_skill, "_clone_repository", fake_clone)

    with pytest.raises(sync_anysearch_skill.SyncError, match="existing snapshot was preserved"):
        sync_anysearch_skill._resolve_source(tmp_path)

    assert calls == [sync_anysearch_skill.PREFERRED_REPOSITORY]


def test_sync_preserves_private_runtime_files_and_removes_stale_managed_files(tmp_path):
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    _write_skill(source)
    destination.mkdir()
    (destination / "CONTRACT.md").write_text("local Smart Search contract\n", encoding="utf-8")
    (destination / "SKILL.md").write_text("stale discoverable entrypoint\n", encoding="utf-8")
    (destination / ".env.example").write_text("local example\n", encoding="utf-8")
    (destination / "README.md").write_text("local README\n", encoding="utf-8")
    (destination / "runtime.conf.example").write_text("local runtime example\n", encoding="utf-8")
    (destination / "OLD.md").write_text("stale\n", encoding="utf-8")
    (destination / ".env").write_text("ANYSEARCH_API_KEY=private\n", encoding="utf-8")
    (destination / "runtime.conf").write_text("ANYSEARCH_COMMAND=python3\n", encoding="utf-8")
    (destination / "config.json").write_text('{"ANYSEARCH_API_KEY":"private"}\n', encoding="utf-8")
    local_adapter = destination / "scripts" / "smart_search_anysearch.py"
    local_adapter.parent.mkdir(parents=True)
    local_adapter.write_text("local adapter\n", encoding="utf-8")
    (source / "config.json").write_text('{"ANYSEARCH_API_KEY":"source"}\n', encoding="utf-8")
    (source / "scripts").mkdir()
    (source / "scripts" / "smart_search_anysearch.py").write_text("source adapter\n", encoding="utf-8")

    changed = sync_anysearch_skill._sync(source, destination)

    assert "OLD.md" in changed
    assert not (destination / "OLD.md").exists()
    assert (destination / ".env").read_text(encoding="utf-8") == "ANYSEARCH_API_KEY=private\n"
    assert (destination / "runtime.conf").read_text(encoding="utf-8") == "ANYSEARCH_COMMAND=python3\n"
    assert (destination / "config.json").read_text(encoding="utf-8") == '{"ANYSEARCH_API_KEY":"private"}\n'
    assert local_adapter.read_text(encoding="utf-8") == "local adapter\n"
    assert not (destination / "SKILL.md").exists()
    assert (destination / "CONTRACT.md").read_text(encoding="utf-8") == "local Smart Search contract\n"
    assert (destination / ".env.example").read_text(encoding="utf-8") == "local example\n"
    assert (destination / "README.md").read_text(encoding="utf-8") == "local README\n"
    assert (destination / "runtime.conf.example").read_text(encoding="utf-8") == "local runtime example\n"


def test_destinations_use_bundled_skills_directory(tmp_path):
    assert sync_anysearch_skill._destinations(tmp_path) == [
        tmp_path / "skills" / "smart-search-cli" / "bundled-skills" / "anysearch",
        tmp_path
        / "src"
        / "smart_search"
        / "assets"
        / "skills"
        / "smart-search-cli"
        / "bundled-skills"
        / "anysearch",
    ]
