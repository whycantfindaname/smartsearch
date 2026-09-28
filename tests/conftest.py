import sys
from pathlib import Path

import pytest

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


@pytest.fixture(autouse=True)
def isolate_smart_search_config(monkeypatch, tmp_path):
    from smart_search.config import Config
    from smart_search import skill_maintenance

    monkeypatch.setattr(skill_maintenance, "state_directory", lambda home=None: (Path(home) if home else tmp_path) / ".local/share/smart-search-tools/skills")

    config = Config()
    monkeypatch.setattr(config, "_config_file", tmp_path / "config.json")
    monkeypatch.setattr(config, "_config_dir_source", "override")
    monkeypatch.setattr(config, "_cached_model", None)
    for key in config._CONFIG_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("SMART_SEARCH_CONFIG_DIR", raising=False)
    monkeypatch.setenv("SMART_SEARCH_MINIMUM_PROFILE", "off")
