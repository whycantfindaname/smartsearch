"""The desktop and the CLI share these contracts, including concurrent writes."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys

import httpx
import pytest

from smart_search.i18n import use_language


@pytest.fixture(autouse=True)
def chinese_presentation():
    with use_language("zh"):
        yield

from smart_search import activity, service, ui_api
from smart_search.config import config


def test_rejects_stale_revision_and_preserves_broken_file(tmp_path):
    initial = config.revision()
    config.set_config_value("EXA_API_KEY", "first")
    result = ui_api.apply_config({"set": {"EXA_API_KEY": "second"}, "revision": initial})
    assert result["error_type"] == "config_conflict"
    assert config.exa_api_key == "first"
    config.config_file.write_text('{"broken":', encoding="utf-8")
    with pytest.raises(ValueError, match="原文件未修改"):
        config.set_config_value("EXA_API_KEY", "second")
    assert config.config_file.read_text() == '{"broken":'


def test_state_values_and_revision_are_one_snapshot_even_when_file_changes(monkeypatch):
    config.set_config_value("OPENAI_COMPATIBLE_MODEL", "old-model")
    before = config.revision()
    original = config.get_config_info
    def concurrent_write():
        config.set_config_value("OPENAI_COMPATIBLE_MODEL", "other-process-model")
        return original()
    monkeypatch.setattr(config, "get_config_info", concurrent_write)
    state = ui_api.state()
    assert state["values"]["OPENAI_COMPATIBLE_MODEL"] == "old-model"
    assert state["saved_values"]["OPENAI_COMPATIBLE_MODEL"] == "old-model"
    assert state["revision"] == before
    result = config.update_config_values({"OPENAI_COMPATIBLE_MODEL": "draft"}, expected_revision=state["revision"])
    assert result["conflict"] and not result["ok"]


def test_apply_inside_snapshot_returns_the_new_saved_value():
    config.set_config_value("OPENAI_COMPATIBLE_MODEL", "old-model")
    with config.snapshot():
        result = ui_api.apply_config({"set": {"OPENAI_COMPATIBLE_MODEL": "new-model"}, "revision": config.snapshot_revision()})
        assert result["saved"]["OPENAI_COMPATIBLE_MODEL"] == "new-model"
        assert result["status"]["values"]["OPENAI_COMPATIBLE_MODEL"] == "new-model"


def test_preview_matches_environment_and_disabled_provider(monkeypatch):
    monkeypatch.setenv("SMART_SEARCH_MINIMUM_PROFILE", "standard")
    monkeypatch.setenv("XAI_API_KEY", "synthetic-primary")
    monkeypatch.setenv("EXA_API_KEY", "synthetic-docs")
    config.set_config_value("TAVILY_API_KEY", "synthetic-fetch")
    state = ui_api.state()
    assert state["values"]["XAI_API_KEY"] and "synthetic-primary" not in json.dumps(state)
    assert ui_api.preview({"values": {}})["minimum_profile_ok"]
    preview = ui_api.preview({"values": {"TAVILY_ENABLED": "false"}})
    assert preview["missing"] == ["web_fetch"]
    config.set_config_value("TAVILY_ENABLED", "false")
    assert preview["capability_status"] == service.get_capability_status()
    with use_language("en"), pytest.raises(ValueError, match="Invalid XAI_TOOLS"):
        config.set_config_value("XAI_TOOLS", "web_search,bogus")


@pytest.mark.asyncio
async def test_snapshots_isolate_concurrent_drafts_and_redact_echo(monkeypatch):
    config.set_config_value("EXA_API_KEY", "saved-secret-value")
    seen = []
    async def probe():
        await asyncio.sleep(0)
        seen.append(config.exa_api_key)
        return {"status": "ok", "message": "fine"}
    monkeypatch.setitem(service._LIVE_PROBES, "exa", probe)
    results = await asyncio.gather(*[
        service.test_provider_connection("exa", overrides={"EXA_API_KEY": value})
        for value in ("candidate-first", "candidate-second")
    ])
    assert set(seen) == {"candidate-first", "candidate-second"}
    assert all(not result["recorded_as"] for result in results)
    assert config.exa_api_key == "saved-secret-value"
    original_client = httpx.AsyncClient
    secret = "candidate-echo-sensitive"
    transport = httpx.MockTransport(lambda request: httpx.Response(401, text="Rejected credential " + secret))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(transport=transport, **kwargs))
    # Restore the actual probe for the error-path check.
    monkeypatch.setitem(service._LIVE_PROBES, "exa", service._test_exa_connection)
    result = await service.test_provider_connection("exa", overrides={"EXA_API_KEY": secret})
    assert secret not in json.dumps(result)
    assert "[REDACTED]" in result["message"]


@pytest.mark.asyncio
async def test_direct_provider_parse_errors_are_redacted(monkeypatch):
    secret = "synthetic-direct-parse-secret"
    config.set_config_value("EXA_API_KEY", secret)
    async def invalid_json(*args, **kwargs):
        return "unlabelled rejection " + secret
    monkeypatch.setattr(service.ExaSearchProvider, "find_similar", invalid_json)
    with activity.observe("exa-similar"):
        result = await service.exa_find_similar("https://example.com")
    assert result["error_type"] == "parse_error" and secret not in json.dumps(result)
    result = await service._decode_provider_json("unlabelled rejection " + secret)
    assert secret not in json.dumps(result)


def test_independent_processes_merge_config_and_health(tmp_path):
    code = """
import sys,time
from pathlib import Path
from smart_search.config import config
from smart_search.provider_health import provider_health
from smart_search.state_files import file_lock
root=Path(sys.argv[1]); key=sys.argv[2]; provider=sys.argv[3]
(root / (provider+'.ready')).touch()
while not (root / 'go').exists(): time.sleep(.01)
original=config._load_config_file
def slow_read(**kwargs):
    data=original(**kwargs); time.sleep(.15); return data
config._load_config_file=slow_read
config.set_config_value(key,provider)
provider_health.record_failure(provider, 'fingerprint', 'auth_error', 'denied')
"""
    env = dict(os.environ, SMART_SEARCH_CONFIG_DIR=str(tmp_path))
    children = [subprocess.Popen([sys.executable, "-c", code, str(tmp_path), key, provider], env=env)
                for key, provider in [("EXA_API_KEY", "exa"), ("TAVILY_API_KEY", "tavily")]]
    import time
    deadline = time.monotonic() + 10
    while not all((tmp_path / (p + ".ready")).exists() for p in ("exa", "tavily")):
        assert time.monotonic() < deadline
        time.sleep(.01)
    (tmp_path / "go").touch()
    assert all(child.wait(timeout=10) == 0 for child in children)
    values = json.loads((tmp_path / "config.json").read_text())
    assert values == {"EXA_API_KEY": "exa", "TAVILY_API_KEY": "tavily"}
    health = json.loads((tmp_path / "provider_health.json").read_text())
    assert set(health["providers"]) == {"exa", "tavily"}
