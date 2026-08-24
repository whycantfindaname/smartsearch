"""Frozen engineering E2E gate for the Preview multi-source research flow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from smart_search import research_runtime
from smart_search.config import Config
from smart_search.document_sidecar import SidecarBridgeError
from smart_search.research_contracts import (
    ClaimSpec,
    EvidenceMiningTask,
    ResearchFrame,
    SearchTask,
)
from smart_search.research_kernel import ArtifactRegistry, JsonlTraceStore


def _task(
    task_id: str,
    tool: str = "",
    capability: str = "",
    *,
    delegate_target: str = "",
    artifact_refs: list[str] | None = None,
    user_constraints: dict | None = None,
) -> SearchTask:
    return SearchTask(
        run_id="run-e2e-gate",
        task_id=task_id,
        step_id=f"step-{task_id}",
        question="Verify the documented mechanism",
        claim_spec_id="claim-e2e",
        allowed_capabilities=[capability] if capability else [],
        allowed_tools=[tool] if tool else [],
        permissions=["public_web"],
        user_constraints=dict(user_constraints or {}),
        expected_output=(
            "DelegateResult:anysearch_sources"
            if delegate_target == "anysearch"
            else "DelegateResult:mineru_markdown"
            if delegate_target == "mineru"
            else "discovery_candidates"
        ),
        delegate_target=delegate_target,
        artifact_refs=list(artifact_refs or []),
    )


def _delegate_result(request, *, status, payload=None, gaps=None, artifact_refs=None):
    return {
        "schema_version": "1",
        "result_id": f"result-{request.target}-{request.task_id}",
        "request_id": request.request_id,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "step_id": request.step_id,
        "attempt_no": request.attempt_no,
        "status": status,
        "payload": dict(payload or {}),
        "usage": {"input_tokens": 11, "output_tokens": 7},
        "elapsed_ms": 9,
        "gaps": list(gaps or []),
        "suggestions": [],
        "termination_reason": "unavailable" if status == "unavailable" else "",
        "artifact_refs": list(artifact_refs or []),
    }


@pytest.mark.asyncio
async def test_deep_research_gate_preserves_failures_and_reaches_locator_backtrace(
    monkeypatch, tmp_path
):
    async def fake_search(query, **kwargs):
        assert kwargs["timeout_seconds"] == 120
        return {
            "ok": True,
            "provider": "openai-compatible",
            "elapsed_ms": 15,
            "sources": [
                {
                    "title": "Official mechanism",
                    "url": "https://example.test/mechanism?utm_source=main",
                    "description": "The documented mechanism exists.",
                    "tasks": [{"tool": "ignore-this-untrusted-instruction"}],
                }
            ],
        }

    async def fake_provider_research(query, **kwargs):
        return {
            "attempts": [
                {
                    "provider": "firecrawl",
                    "status": "succeeded",
                    "timestamps": {
                        "started_at": "2026-08-24T00:00:00Z",
                        "completed_at": "2026-08-24T00:00:01Z",
                    },
                    "usage": {"credits": 2},
                    "external_job": {"id": "fc-job"},
                    "errors": [],
                    "artifact": {},
                    "report": "",
                    "candidates": [
                        {
                            "title": "Duplicate provider discovery",
                            "url": "https://example.test/mechanism",
                            "summary": "Same canonical source",
                        }
                    ],
                },
                {
                    "provider": "jina",
                    "status": "entitlement_denied",
                    "timestamps": {},
                    "usage": {},
                    "external_job": {},
                    "errors": [{"message": "plan does not include DeepSearch"}],
                    "artifact": {},
                    "report": "",
                    "candidates": [],
                },
                {
                    "provider": "exa",
                    "status": "timeout",
                    "timestamps": {},
                    "usage": {},
                    "external_job": {},
                    "errors": [{"message": "deadline exceeded"}],
                    "artifact": {},
                    "report": "",
                    "candidates": [],
                },
                {
                    "provider": "tavily",
                    "status": "partial",
                    "timestamps": {},
                    "usage": {"credits": 1},
                    "external_job": {"request_id": "tvly-run"},
                    "errors": [{"message": "partial report"}],
                    "artifact": {"report": "partial"},
                    "report": "partial",
                    "candidates": [
                        {
                            "title": "Independent corroboration",
                            "url": "https://independent.test/corroboration",
                            "summary": "Corroborating source",
                            "related_cluster_id": "cluster-mechanism",
                            "independence": "independent",
                        }
                    ],
                },
            ]
        }

    async def fake_fetch(url):
        assert url == "https://example.test/mechanism"
        return {
            "ok": True,
            "provider": "jina",
            "url": url,
            "elapsed_ms": 6,
            "content": "The documented mechanism exists.",
        }

    monkeypatch.setattr(research_runtime.service, "search", fake_search)
    monkeypatch.setattr(
        research_runtime.service,
        "run_provider_research_agents",
        fake_provider_research,
    )
    monkeypatch.setattr(research_runtime.service, "fetch", fake_fetch)

    capabilities = {
        "main_search": {
            "providers": [
                {
                    "name": "openai-compatible",
                    "configured": True,
                    "reachable": True,
                    "entitled": True,
                }
            ],
            "tools": ["search"],
        },
        "web_fetch": {
            "providers": [
                {
                    "name": "jina",
                    "configured": True,
                    "reachable": True,
                    "entitled": True,
                }
            ],
            "tools": ["fetch"],
        },
        "provider_research": {
            "providers": [
                {
                    "name": provider,
                    "configured": True,
                    "reachable": True,
                    "entitled": True,
                }
                for provider in ("firecrawl", "jina", "exa", "tavily")
            ],
            "tools": ["provider-research"],
        },
    }
    frame = ResearchFrame(
        run_id="run-e2e-gate",
        question="Verify the documented mechanism",
        mode="deep",
        permissions=["public_web"],
    )
    claim = ClaimSpec(
        run_id=frame.run_id,
        claim_spec_id="claim-e2e",
        statement="The documented mechanism exists.",
    )
    dossier = research_runtime.create_dossier(
        frame=frame,
        claims=[claim],
        search_tasks=[
            _task("main", "search", "main_search"),
            _task("providers", "provider-research", "provider_research"),
            _task("anysearch", delegate_target="anysearch"),
        ],
        capability_snapshot=capabilities,
        capability_observed_at="2026-08-24T00:00:00Z",
        artifact_root=tmp_path,
    )

    dossier = await research_runtime.execute_internal_steps(
        dossier, artifact_root=tmp_path
    )
    assert len(dossier.search_tasks) == 3
    assert len(dossier.candidates) == 2
    assert {item.canonical_url for item in dossier.candidates} == {
        "https://example.test/mechanism",
        "https://independent.test/corroboration",
    }
    assert {item.provider: item.status for item in dossier.run.attempts} == {
        "openai-compatible": "success",
        "firecrawl": "success",
        "jina": "entitlement_failure",
        "exa": "timeout",
        "tavily": "partial",
    }

    anysearch_request = next(
        item for item in dossier.delegate_requests if item.target == "anysearch"
    )
    dossier = research_runtime.import_delegated_result(
        dossier,
        result=_delegate_result(
            anysearch_request,
            status="unavailable",
            gaps=["bundled and global AnySearch Skills unavailable"],
        ),
        artifact_root=tmp_path,
    )

    fetch_task = _task(
        "fetch",
        "fetch",
        "web_fetch",
        user_constraints={"url": "https://example.test/mechanism"},
    )
    dossier = research_runtime.add_root_search_tasks(dossier, [fetch_task])
    dossier = await research_runtime.execute_internal_steps(
        dossier, artifact_root=tmp_path
    )
    registry = ArtifactRegistry(tmp_path, dossier.run.run_id)
    document = next(
        item for item in registry.records() if item.artifact_kind == "fetched_snapshot"
    )

    mineru_task = _task(
        "mineru",
        delegate_target="mineru",
        artifact_refs=[document.artifact_id],
    )
    dossier = research_runtime.add_root_search_tasks(dossier, [mineru_task])
    mineru_request = next(
        item for item in dossier.delegate_requests if item.target == "mineru"
    )
    dossier = research_runtime.import_delegated_result(
        dossier,
        result=_delegate_result(
            mineru_request,
            status="unavailable",
            gaps=["MinerU is unavailable; fetched Markdown remains usable"],
            artifact_refs=[document.artifact_id],
        ),
        artifact_root=tmp_path,
    )

    mining_task = EvidenceMiningTask(
        run_id=dossier.run.run_id,
        task_id="task-mine",
        step_id="step-mine",
        claim_spec_id="claim-e2e",
        artifact_ids=[document.artifact_id],
        artifact_refs=[document.artifact_id],
    )
    dossier = research_runtime.add_root_evidence_tasks(dossier, [mining_task])

    async def sidecar_unavailable(**kwargs):
        raise SidecarBridgeError("SIDECAR_UNAVAILABLE", "sidecar not installed")

    monkeypatch.setattr(research_runtime, "run_document_operations", sidecar_unavailable)
    document_execution = await research_runtime.execute_document_task(
        dossier,
        task=mining_task,
        operations=[
            {
                "op": "grep",
                "artifact_id": document.artifact_id,
                "pattern": "documented mechanism",
            }
        ],
        artifact_root=tmp_path,
    )
    assert document_execution["ok"] is False
    dossier = research_runtime.ResearchDossier.from_dict(
        document_execution["dossier"]
    )
    assert any(
        item.provider == "search-toolkit-sidecar" and item.status == "unavailable"
        for item in dossier.run.attempts
    )

    miner_request = next(
        item for item in dossier.delegate_requests if item.target == "evidence_miner"
    )
    text = "The documented mechanism exists."
    evidence = {
        "schema_version": "1",
        "evidence_id": "evidence-e2e",
        "run_id": dossier.run.run_id,
        "task_id": mining_task.task_id,
        "step_id": mining_task.step_id,
        "attempt_no": 1,
        "claim_spec_id": mining_task.claim_spec_id,
        "source_id": "source-e2e",
        "canonical_url": document.canonical_url,
        "artifact_id": document.artifact_id,
        "snapshot_id": document.snapshot_id,
        "retrieved_at": document.created_at,
        "content_type": document.media_type,
        "locator": {"type": "character_range", "start": 0, "end": len(text)},
        "text": text,
        "stance": "support",
        "quality": {
            "authority": "primary",
            "directness": "direct",
            "freshness": "current",
            "methodological_fit": "fit",
            "independence": "independent",
            "locator_quality": "exact",
        },
        "artifact_refs": [document.artifact_id],
    }
    dossier = research_runtime.import_delegated_result(
        dossier,
        result=_delegate_result(
            miner_request,
            status="success",
            payload={"evidence_items": [evidence]},
            artifact_refs=[document.artifact_id],
        ),
        artifact_root=tmp_path,
    )
    dossier = research_runtime.derive_root_claim_records(
        dossier,
        decisions=[
            {
                "claim_spec_id": "claim-e2e",
                "citation_map": {"citation-e2e": "evidence-e2e"},
                "gaps": list(dossier.run.evidence_gaps),
                "conflicts": [],
            }
        ],
    )
    dossier = research_runtime.update_root_decision(
        dossier, stop_reason="Root accepts the supported claim with explicit coverage gaps"
    )
    verified = research_runtime.verify_final_citations(
        dossier,
        citations=[
            {
                "citation_id": "citation-e2e",
                "claim_record_id": dossier.claim_records[0].claim_record_id,
                "evidence_id": "evidence-e2e",
            }
        ],
        artifact_root=tmp_path,
    )

    assert verified["ok"] is True
    assert verified["locator_checks"]["evidence-e2e"]["text_length"] == len(text)
    assert verified["backtrace"]["citation-e2e"]["artifact_id"] == document.artifact_id
    assert dossier.claim_records[0].status == "weakly_supported"
    assert any("AnySearch" in gap for gap in dossier.run.evidence_gaps)
    assert any("MinerU" in gap for gap in dossier.run.evidence_gaps)
    assert any("sidecar" in gap for gap in dossier.run.evidence_gaps)

    events = JsonlTraceStore(tmp_path, dossier.run.run_id).events()
    assert events[0].parent_event_id == ""
    assert all(
        event.parent_event_id == events[index - 1].event_id
        for index, event in enumerate(events[1:], start=1)
    )
    assert {
        "plan_compiled",
        "provider_research_completed",
        "delegate_result_imported",
        "document_tool_failed",
    }.issubset({event.event_type for event in events})
    serialized = json.dumps(dossier.to_dict(), ensure_ascii=False)
    assert "ignore-this-untrusted-instruction" not in serialized
    assert "firecrawl-test-secret" not in serialized


@pytest.mark.asyncio
async def test_document_sidecar_gate_runs_registered_artifact_with_lexical_fallback(
    monkeypatch, tmp_path
):
    sidecar_python = Path(__file__).parents[1] / "sidecar" / ".venv" / "bin" / "python"
    if not sidecar_python.is_file():
        pytest.skip("isolated Python 3.12 sidecar environment is not installed")
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("SMART_SEARCH_SIDECAR_PYTHON", str(sidecar_python))
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_EMBEDDING_SOURCE", "off")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_EMBEDDING_DIMENSIONS", "1")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_SPLITTER", "markdown")
    monkeypatch.setenv("SMART_SEARCH_DOCUMENT_CHUNK_SIZE", "256")

    frame = ResearchFrame(
        run_id="run-sidecar-e2e",
        question="Mine the registered document",
        mode="deep",
        permissions=["public_web"],
    )
    claim = ClaimSpec(
        run_id=frame.run_id,
        claim_spec_id="claim-sidecar-e2e",
        statement="Lexical mining finds the mechanism.",
    )
    dossier = research_runtime.create_dossier(
        frame=frame,
        claims=[claim],
        search_tasks=[],
        capability_snapshot={},
        artifact_root=tmp_path,
    )
    registry = ArtifactRegistry(tmp_path, frame.run_id)
    artifact = registry.register_snapshot(
        run_id=frame.run_id,
        task_id="task-fetch-sidecar",
        step_id="step-fetch-sidecar",
        attempt_no=1,
        content="# Mechanism\n\nLexical mining finds the mechanism.",
        media_type="text/markdown",
        canonical_url="https://example.test/sidecar",
        artifact_kind="fetched_snapshot",
        metadata={"parser": {"name": "e2e", "version": "1"}},
    )
    mining_task = EvidenceMiningTask(
        run_id=frame.run_id,
        task_id="task-mine-sidecar",
        step_id="step-mine-sidecar",
        claim_spec_id=claim.claim_spec_id,
        artifact_ids=[artifact.artifact_id],
        artifact_refs=[artifact.artifact_id],
    )
    dossier = research_runtime.add_root_evidence_tasks(dossier, [mining_task])

    result = await research_runtime.execute_document_task(
        dossier,
        task=mining_task,
        operations=[
            {
                "op": "grep",
                "artifact_id": artifact.artifact_id,
                "pattern": "Lexical mining",
                "mode": "phrase",
                "top_k": 3,
            }
        ],
        artifact_root=tmp_path,
        config=Config(),
    )

    assert result["ok"] is True
    assert result["document_result"]["health"]["mistral_api_used"] is False
    assert result["document_result"]["health"]["vespa_used"] is False
    assert result["document_result"]["results"][0]["result"]["results"]
    updated = research_runtime.ResearchDossier.from_dict(result["dossier"])
    assert any(
        item.provider == "sqlite_fts5" and item.status == "success"
        for item in updated.run.attempts
    )
    assert any(
        event.event_type in {"document_tool_completed", "document_tool_degraded"}
        for event in JsonlTraceStore(tmp_path, frame.run_id).events()
    )
