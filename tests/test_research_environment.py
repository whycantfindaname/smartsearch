import json
from types import SimpleNamespace

from smart_search import cli


def test_research_environment_install_creates_isolated_venv_and_saves_python(monkeypatch, tmp_path, capsys):
    environment_dir = tmp_path / "preview-config" / "research-sidecar"
    calls = []
    saved = {}

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if command[1:3] == ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"]:
            return SimpleNamespace(returncode=0, stdout="3.12\n", stderr="")
        if command[1:3] == ["-m", "smart_search_sidecar"]:
            response = {
                "id": "doctor-1",
                "ok": True,
                "result": {
                    "status": "ok",
                    "sidecar_version": "0.1.0",
                    "protocol": "stdio-jsonl-v1",
                    "mistral_api_used": False,
                    "vespa_used": False,
                    "docker_required": False,
                },
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(response) + "\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    def fake_config_set(key, value):
        saved[key] = value
        return {"ok": True, "config_file": str(tmp_path / "preview-config" / "config.json"), "value": value}

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    monkeypatch.setattr(cli.service, "config_set", fake_config_set)

    code = cli.main(
        [
            "research-environment",
            "install",
            "--python",
            "/opt/python3.12",
            "--environment",
            str(environment_dir),
            "--format",
            "json",
        ]
    )

    data = json.loads(capsys.readouterr().out)
    expected_python = environment_dir / "bin" / "python"
    assert code == cli.EXIT_OK
    assert data["health"]["protocol"] == "stdio-jsonl-v1"
    assert saved == {"SMART_SEARCH_SIDECAR_PYTHON": str(expected_python)}
    assert calls[1][0] == ["/opt/python3.12", "-m", "venv", str(environment_dir)]
    assert calls[2][0][:5] == [str(expected_python), "-m", "pip", "install", "--disable-pip-version-check"]


def test_doctor_includes_sidecar_health_without_changing_provider_result(monkeypatch, capsys):
    async def fake_doctor():
        return {"ok": True, "config_status": "ok", "minimum_profile_ok": True}

    health = {
        "ok": True,
        "python": "/preview/bin/python",
        "health": {"status": "ok", "protocol": "stdio-jsonl-v1"},
    }
    monkeypatch.setattr(cli.service, "doctor", fake_doctor)
    monkeypatch.setattr(cli, "_configured_sidecar_health", lambda: health)

    code = cli.main(["doctor", "--format", "json"])
    data = json.loads(capsys.readouterr().out)

    assert code == cli.EXIT_OK
    assert data["ok"] is True
    assert data["research_environment"] == health


def test_research_environment_rejects_non_python312_before_writing_config(monkeypatch, tmp_path, capsys):
    def fake_run(command, **kwargs):
        return SimpleNamespace(returncode=0, stdout="3.13\n", stderr="")

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    code = cli.main(
        [
            "research-environment",
            "install",
            "--python",
            "/opt/python3.13",
            "--environment",
            str(tmp_path / "sidecar"),
        ]
    )
    data = json.loads(capsys.readouterr().out)

    assert code == cli.EXIT_CONFIG_ERROR
    assert data["observed_python"] == "3.13"


def test_config_list_exposes_effective_research_values_and_sources(monkeypatch, tmp_path, capsys):
    config = cli.service.config
    monkeypatch.setattr(config, "_config_file", None)
    monkeypatch.setattr(config, "_config_dir_source", None)
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "preview-config"))
    monkeypatch.setenv("JINA_SEARCH_API_URL", "https://search.example/v1")

    code = cli.main(["config", "list", "--format", "json"])
    data = json.loads(capsys.readouterr().out)

    assert code == cli.EXIT_OK
    assert data["effective_research_config"]["JINA_SEARCH_API_URL"] == {
        "value": "https://search.example/v1",
        "source": "environment",
    }
    assert data["effective_research_config"]["SMART_SEARCH_SIDECAR_PYTHON"]["value"].startswith(
        str(tmp_path / "preview-config")
    )
