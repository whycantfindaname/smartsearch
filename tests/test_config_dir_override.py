import os
from pathlib import Path

import pytest

from smart_search.config import Config
from smart_search.i18n import use_language


def _fresh_config_file(monkeypatch):
    config = Config()
    monkeypatch.setattr(config, "_config_file", None)
    monkeypatch.setattr(config, "_config_dir_source", None)
    return config


def test_env_dir_overrides_config_file_path(monkeypatch, tmp_path):
    target = tmp_path / "custom-config-root"
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(target))
    config = _fresh_config_file(monkeypatch)
    assert config.config_file == target / "config.json"
    assert config.config_dir_source == "environment"
    info = config.config_path_info()
    assert info["config_dir_override_value"] == str(target)
    assert info["config_dir_override_matches_default"] is False
    assert target.exists() and target.is_dir()


def test_windows_env_override_matching_default_is_reported(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_local_appdata = tmp_path / "local-appdata"
    default_dir = fake_local_appdata / "smart-search"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr("smart_search.config.sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local_appdata))
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(default_dir))
    config = _fresh_config_file(monkeypatch)
    info = config.config_path_info()
    assert config.config_file == default_dir / "config.json"
    assert config.config_dir_source == "environment"
    assert info["default_config_file"] == str(default_dir / "config.json")
    assert info["config_dir_override_value"] == str(default_dir)
    assert info["config_dir_override_matches_default"] is True


def test_env_dir_pointing_at_unwritable_does_not_crash(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file, not a directory")
    bogus = blocker / "child"
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(bogus))
    config = _fresh_config_file(monkeypatch)
    assert config.config_file == bogus / "config.json"
    assert config.config_dir_source == "environment"
    assert config._load_config_file() == {}


def test_no_env_falls_back_to_platform_default(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    fake_local_appdata = tmp_path / "local-appdata"
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr("smart_search.config.sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local_appdata))
    config = _fresh_config_file(monkeypatch)
    assert config.config_file == fake_local_appdata / "smart-search" / "config.json"
    assert config.config_dir_source == "default"


def test_windows_uses_legacy_home_config_when_new_default_missing(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_local_appdata = tmp_path / "local-appdata"
    legacy_config = fake_home / ".config" / "smart-search" / "config.json"
    legacy_config.parent.mkdir(parents=True)
    legacy_config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr("smart_search.config.sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local_appdata))
    config = _fresh_config_file(monkeypatch)
    assert config.config_file == legacy_config
    assert config.config_dir_source == "legacy_windows_home"


def test_windows_prefers_new_default_when_both_new_and_legacy_exist(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_local_appdata = tmp_path / "local-appdata"
    legacy_config = fake_home / ".config" / "smart-search" / "config.json"
    new_config = fake_local_appdata / "smart-search" / "config.json"
    legacy_config.parent.mkdir(parents=True)
    legacy_config.write_text("{}", encoding="utf-8")
    new_config.parent.mkdir(parents=True)
    new_config.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr("smart_search.config.sys.platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(fake_local_appdata))
    config = _fresh_config_file(monkeypatch)
    assert config.config_file == new_config
    assert config.config_dir_source == "default"


def test_no_env_non_windows_falls_back_to_home(monkeypatch, tmp_path):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    monkeypatch.setattr("smart_search.config.sys.platform", "linux")
    config = _fresh_config_file(monkeypatch)
    assert config.config_file == fake_home / ".config" / "smart-search" / "config.json"
    assert config.config_dir_source == "default"


def test_env_dir_also_governs_log_dir_parent(monkeypatch, tmp_path):
    target = tmp_path / "shared-root"
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(target))
    config = _fresh_config_file(monkeypatch)
    assert config.log_dir == target / "logs"
    assert config.log_dir_config_value == "logs"
    assert not (target / "logs").exists()


def test_tavily_timeout_defaults_to_thirty_seconds(monkeypatch):
    monkeypatch.delenv("TAVILY_TIMEOUT_SECONDS", raising=False)
    config = _fresh_config_file(monkeypatch)
    assert config.tavily_timeout == 30.0
    info = config.get_config_info()
    assert info["TAVILY_TIMEOUT_SECONDS"] == 30.0
    assert info["config_sources"]["TAVILY_TIMEOUT_SECONDS"] == "default"


def test_tavily_timeout_can_be_configured(monkeypatch):
    monkeypatch.setenv("TAVILY_TIMEOUT_SECONDS", "45")
    config = _fresh_config_file(monkeypatch)
    assert config.tavily_timeout == 45.0
    info = config.get_config_info()
    assert info["TAVILY_TIMEOUT_SECONDS"] == 45.0
    assert info["config_sources"]["TAVILY_TIMEOUT_SECONDS"] == "environment"


def test_xai_request_monitor_timeouts_have_safe_defaults(monkeypatch):
    monkeypatch.delenv("XAI_SOFT_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("XAI_HARD_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("XAI_STATUS_POLL_SECONDS", raising=False)
    config = _fresh_config_file(monkeypatch)

    assert config.xai_soft_timeout == 120.0
    assert config.xai_hard_timeout == 7200.0
    assert config.xai_status_poll == 15.0


def test_xai_status_poll_accepts_five_minute_maximum(monkeypatch):
    monkeypatch.setenv("XAI_STATUS_POLL_SECONDS", "300")
    config = _fresh_config_file(monkeypatch)

    assert config.xai_status_poll == 300.0


def test_absolute_log_dir_is_resolved_without_creation(monkeypatch, tmp_path):
    target = tmp_path / "shared-root"
    log_dir = tmp_path / "explicit-logs"
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(target))
    monkeypatch.setenv("SMART_SEARCH_LOG_DIR", str(log_dir))
    config = _fresh_config_file(monkeypatch)
    assert config.log_dir == log_dir
    assert config.log_dir_config_value == str(log_dir)
    assert not log_dir.exists()


def test_save_unwritable_raises_with_hint(monkeypatch, tmp_path):
    blocker = tmp_path / "blocker"
    blocker.write_text("i am a file")
    bogus = blocker / "child"
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(bogus))
    config = _fresh_config_file(monkeypatch)
    with use_language("zh"), pytest.raises(ValueError) as exc:
        config._save_config_file({"x": 1})
    assert "无法保存" in str(exc.value)


def test_document_embedding_defaults_reuse_existing_intent_embedding_config(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("INTENT_EMBEDDING_API_URL", "https://embedding.example/v1/embeddings")
    monkeypatch.setenv("INTENT_EMBEDDING_API_KEY", "secret-value")
    monkeypatch.setenv("INTENT_EMBEDDING_MODEL", "example-embedding")
    monkeypatch.delenv("SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE", raising=False)
    config = _fresh_config_file(monkeypatch)

    document = config.document_embedding_config()

    assert document == {
        "source": "intent",
        "api_url": "https://embedding.example/v1/embeddings",
        "api_key": "secret-value",
        "model": "example-embedding",
        "dimensions": 0,
        "normalize": True,
        "configured": True,
    }
    assert "SMART_SEARCH_DOCUMENT_EMBEDDING_API_KEY" not in config._CONFIG_KEYS


def test_document_sidecar_config_is_non_secret_and_visible_in_masked_info(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("SMART_SEARCH_SIDECAR_PYTHON", "/opt/python3.12")
    monkeypatch.setenv("SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS", "180")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_SPLITTER", "character")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_CHUNK_SIZE", "2048")
    config = _fresh_config_file(monkeypatch)

    info = config.get_config_info()

    assert info["SMART_SEARCH_SIDECAR_PYTHON"] == "/opt/python3.12"
    assert info["SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS"] == 180.0
    assert info["SMART_SEARCH_DOCUMENT_SPLITTER"] == "character"
    assert info["SMART_SEARCH_DOCUMENT_CHUNK_SIZE"] == 2048
    assert info["config_sources"]["SMART_SEARCH_SIDECAR_PYTHON"] == "environment"


def test_default_sidecar_environment_is_scoped_to_config_dir(monkeypatch, tmp_path):
    target = tmp_path / "preview-config"
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(target))
    monkeypatch.delenv("SMART_SEARCH_SIDECAR_PYTHON", raising=False)
    config = _fresh_config_file(monkeypatch)

    assert Path(config.sidecar_python).is_relative_to(target / "research-sidecar")


def test_jina_research_urls_are_visible_and_invalid_values_fail_config_set(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    config = _fresh_config_file(monkeypatch)

    config.set_config_value("JINA_SEARCH_API_URL", "https://search.example/v1")
    config.set_config_value("JINA_RERANK_API_URL", "https://rerank.example/v1")
    info = config.get_config_info()

    assert info["JINA_SEARCH_API_URL"] == "https://search.example/v1"
    assert info["JINA_RERANK_API_URL"] == "https://rerank.example/v1"
    assert info["config_sources"]["JINA_SEARCH_API_URL"] == "config_file"
    with pytest.raises(ValueError, match="absolute HTTP"):
        config.set_config_value("JINA_SEARCH_API_URL", "ftp://search.example")


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE", "mistral"),
        ("SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS", "-1"),
        ("SMART_SEARCH_DOCUMENT_EMBEDDING_NORMALIZE", "sometimes"),
        ("SMART_SEARCH_DOCUMENT_SPLITTER", "semantic-magic"),
        ("SMART_SEARCH_DOCUMENT_CHUNK_SIZE", "32"),
        ("SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS", "0"),
        ("SMART_SEARCH_SIDECAR_TIMEOUT_SECONDS", "nan"),
    ],
)
def test_invalid_document_sidecar_config_is_reported(monkeypatch, tmp_path, key, value):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv(key, value)
    config = _fresh_config_file(monkeypatch)

    info = config.get_config_info()

    assert info["config_parameter_errors"]
    assert info["config_status"].startswith("config_error:")


def test_log_level_config_set_rejects_invalid_values(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    config = _fresh_config_file(monkeypatch)

    with pytest.raises(ValueError, match="SMART_SEARCH_LOG_LEVEL"):
        config.set_config_value("SMART_SEARCH_LOG_LEVEL", "verbose")

    config.set_config_value("SMART_SEARCH_LOG_LEVEL", "warning")
    assert config.log_level == "WARNING"
    with pytest.raises(ValueError, match="SMART_SEARCH_LOG_LEVEL"):
        config.set_config_value("SMART_SEARCH_LOG_LEVEL", "loud")


def test_log_level_property_falls_back_when_config_file_is_hand_edited(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    config = _fresh_config_file(monkeypatch)
    config.set_config_value("SMART_SEARCH_LOG_LEVEL", "DEBUG")
    config_file = config.config_file
    config_file.write_text('{"SMART_SEARCH_LOG_LEVEL": "VERBOSE"}', encoding="utf-8")

    assert config.log_level == "INFO"
    config_file.write_text('{"SMART_SEARCH_LOG_LEVEL": "ERROR"}', encoding="utf-8")
    assert config.log_level == "ERROR"


@pytest.mark.skipif(os.name == "nt", reason="POSIX file permissions are not emulated on Windows")
def test_saved_config_file_is_owner_only(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    config = _fresh_config_file(monkeypatch)

    config.set_config_value("XAI_MODEL", "grok-4-fast")

    mode = config.config_file.stat().st_mode & 0o777
    assert mode == 0o600
