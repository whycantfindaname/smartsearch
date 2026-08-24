from pathlib import Path

import pytest

from smart_search.config import Config
from smart_search.document_sidecar import SidecarBridgeError, run_document_operations
from smart_search.research_kernel import ArtifactRegistry


@pytest.mark.asyncio
async def test_real_python312_sidecar_bridge_uses_registered_artifact_only(monkeypatch, tmp_path):
    sidecar_python = Path(__file__).parents[1] / "sidecar" / ".venv" / "bin" / "python"
    if not sidecar_python.is_file():
        pytest.skip("isolated sidecar environment is not installed")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("SMART_SEARCH_SIDECAR_PYTHON", str(sidecar_python))
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE", "off")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS", "1")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_SPLITTER", "markdown")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_CHUNK_SIZE", "256")
    config = Config()

    registry = ArtifactRegistry(tmp_path / "runs", "run-sidecar-bridge")
    artifact = registry.register_snapshot(
        run_id="run-sidecar-bridge",
        task_id="task-fetch",
        step_id="step-fetch",
        attempt_no=1,
        content=(
            "# Alpha\n\nThe controlled alpha mechanism is documented here. "
            "This paragraph is deliberately long enough to remain searchable.\n\n"
            "## Beta\n\nBeta evidence is in a separate Markdown section."
        ),
        media_type="text/markdown",
        canonical_url="https://example.test/document",
        metadata={"parser": {"name": "test-fetch", "version": "1"}},
    )

    result = await run_document_operations(
        registry=registry,
        artifact_ids=[artifact.artifact_id],
        operations=[
            {
                "op": "grep",
                "artifact_id": artifact.artifact_id,
                "pattern": "Beta evidence",
                "mode": "phrase",
                "top_k": 5,
            }
        ],
        config=config,
    )

    assert result["ok"] is True
    assert result["health"]["mistral_api_used"] is False
    assert result["health"]["vespa_used"] is False
    assert result["results"][0]["result"]["results"]
    assert result["results"][0]["result"]["results"][0]["source_url"] == artifact.canonical_url
    assert not any(
        item["component"] == "openai_compatible_embedding"
        for item in result["component_attempts"]
    )
    assert any(
        item["component"] == "sqlite_fts5" and item["status"] == "success"
        for item in result["component_attempts"]
    )


@pytest.mark.asyncio
async def test_sidecar_bridge_rejects_operation_outside_task_artifacts(monkeypatch, tmp_path):
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    registry = ArtifactRegistry(tmp_path / "runs", "run-sidecar-boundary")
    artifact = registry.register_snapshot(
        run_id="run-sidecar-boundary",
        task_id="task-fetch",
        step_id="step-fetch",
        attempt_no=1,
        content="registered content",
        media_type="text/plain",
        canonical_url="https://example.test/document",
    )

    with pytest.raises(Exception, match="outside the task"):
        await run_document_operations(
            registry=registry,
            artifact_ids=[artifact.artifact_id],
            operations=[
                {"op": "read", "artifact_id": "artifact-not-registered", "top_k": 1}
            ],
            config=Config(),
        )


@pytest.mark.asyncio
async def test_embedding_dimension_probe_failure_degrades_to_lexical_only(monkeypatch, tmp_path):
    sidecar_python = Path(__file__).parents[1] / "sidecar" / ".venv" / "bin" / "python"
    if not sidecar_python.is_file():
        pytest.skip("isolated sidecar environment is not installed")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("SMART_SEARCH_SIDECAR_PYTHON", str(sidecar_python))
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE", "openai-compatible")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS", "8")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_URL", "https://embedding.invalid/v1")
    monkeypatch.setenv("OPENAI_COMPATIBLE_API_KEY", "test-secret")
    monkeypatch.setenv("OPENAI_COMPATIBLE_MODEL", "fake-model")
    config = Config()
    registry = ArtifactRegistry(tmp_path / "runs", "run-sidecar-degrade")
    artifact = registry.register_snapshot(
        run_id="run-sidecar-degrade",
        task_id="task-fetch",
        step_id="step-fetch",
        attempt_no=1,
        content="# Evidence\n\nLexical fallback still finds this phrase.",
        media_type="text/markdown",
        canonical_url="https://example.test/degraded",
    )

    async def fail_probe(*args, **kwargs):
        raise SidecarBridgeError("EMBEDDING_DIMENSION_PROBE_FAILED", "probe failed")

    monkeypatch.setattr("smart_search.document_sidecar.resolve_embedding_dimension", fail_probe)
    result = await run_document_operations(
        registry=registry,
        artifact_ids=[artifact.artifact_id],
        operations=[
            {
                "op": "grep",
                "artifact_id": artifact.artifact_id,
                "pattern": "Lexical fallback",
                "mode": "phrase",
                "top_k": 3,
            }
        ],
        config=config,
    )

    assert result["results"][0]["result"]["results"]
    preflight = result["component_attempts"][0]
    assert preflight["kind"] == "embedding_preflight"
    assert preflight["status"] == "degraded"
