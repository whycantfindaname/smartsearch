import dataclasses

import pytest

from smart_search import research_runtime
from smart_search.research_contracts import (
    ClaimSpec,
    EvidenceMiningTask,
    ResearchFrame,
    SearchTask,
)
from smart_search.research_kernel import ArtifactRegistry, JsonlTraceStore


CAPABILITIES = {
    "main_search": {
        "providers": [
            {"name": "openai-compatible", "configured": True, "reachable": True, "entitled": True}
        ],
        "tools": ["search"],
    },
    "web_fetch": {
        "providers": [
            {"name": "jina", "configured": True, "reachable": True, "entitled": True}
        ],
        "tools": ["fetch"],
    },
    "provider_research": {
        "providers": [
            {"name": name, "configured": True, "reachable": True, "entitled": True}
            for name in ("firecrawl", "jina", "exa", "tavily")
        ],
        "tools": ["provider-research"],
    },
}


def _frame(run_id="run-runtime", mode="deep"):
    return ResearchFrame(
        run_id=run_id,
        question="How does the system work?",
        mode=mode,
        permissions=["public_web"],
    )


def _claim(run_id="run-runtime"):
    return ClaimSpec(
        run_id=run_id,
        claim_spec_id="claim-runtime",
        statement="The documented mechanism exists.",
    )


def _task(tool="search", capability="main_search", **overrides):
    values = {
        "run_id": "run-runtime",
        "task_id": f"task-{tool}",
        "step_id": f"step-{tool}",
        "question": "Find official mechanism documentation",
        "claim_spec_id": "claim-runtime",
        "allowed_capabilities": [capability],
        "allowed_tools": [tool],
        "permissions": ["public_web"],
    }
    values.update(overrides)
    return SearchTask(**values)


def _create(tmp_path, tasks):
    return research_runtime.create_dossier(
        frame=_frame(),
        claims=[_claim()],
        search_tasks=tasks,
        capability_snapshot=CAPABILITIES,
        artifact_root=tmp_path,
        capability_observed_at="2026-08-24T00:00:00Z",
    )


def test_capability_snapshot_does_not_promote_configured_only_to_live_eligibility():
    doctor = {
        "capability_status": {
            "provider_research": {"configured": ["firecrawl"]},
            "academic_search": {"configured": ["firecrawl"]},
            "academic_read": {"configured": ["firecrawl"]},
            "academic_related": {"configured": ["firecrawl"]},
            "developer_search": {"configured": ["firecrawl"]},
        },
        "firecrawl_connection_test": {
            "status": "configured",
            "message": "key exists but no live probe",
        },
    }

    configured_only = research_runtime.capability_snapshot_from_doctor(doctor)
    assert configured_only["provider_research"]["providers"][0]["reachable"] is False
    assert configured_only["academic_search"]["providers"][0]["entitled"] is False

    doctor["firecrawl_connection_test"] = {
        "status": "ok",
        "message": "read-only credit probe succeeded",
    }
    live = research_runtime.capability_snapshot_from_doctor(doctor)
    for capability in (
        "provider_research",
        "academic_search",
        "academic_read",
        "academic_related",
        "developer_search",
    ):
        assert live[capability]["providers"] == [
            {
                "name": "firecrawl",
                "configured": True,
                "reachable": True,
                "entitled": True,
                "observed_status": "ok",
            }
        ]


@pytest.mark.asyncio
async def test_root_plan_executes_internal_search_and_preserves_raw_trace(monkeypatch, tmp_path):
    async def fake_search(query, **kwargs):
        assert query == "Find official mechanism documentation"
        assert kwargs["timeout_seconds"] == 120
        return {
            "ok": True,
            "sources": [
                {
                    "title": "Official mechanism",
                    "url": "https://example.test/docs?utm_source=test",
                    "description": "Primary documentation",
                }
            ],
            "elapsed_ms": 12,
        }

    monkeypatch.setattr(research_runtime.service, "search", fake_search)
    dossier = _create(tmp_path, [_task()])
    updated = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)

    assert len(updated.run.attempts) == 1
    assert updated.run.attempts[0].status == "success"
    assert updated.run.candidate_summary["count"] == 1
    assert updated.candidates[0].canonical_url == "https://example.test/docs"
    registry = ArtifactRegistry(tmp_path, dossier.run.run_id)
    assert len(registry.records()) == 1
    events = JsonlTraceStore(tmp_path, dossier.run.run_id).events()
    assert [event.event_type for event in events] == ["plan_compiled", "internal_step_completed"]


@pytest.mark.asyncio
async def test_root_replans_fetch_and_gets_a_sidecar_ready_markdown_snapshot(monkeypatch, tmp_path):
    async def fake_fetch(url):
        return {
            "ok": True,
            "url": url,
            "provider": "jina",
            "content": "# Mechanism\n\nThe documented mechanism exists.",
            "elapsed_ms": 8,
        }

    monkeypatch.setattr(research_runtime.service, "fetch", fake_fetch)
    dossier = _create(tmp_path, [])
    fetch_task = _task(
        "fetch",
        "web_fetch",
        question="Read the selected source",
        user_constraints={"url": "https://example.test/docs"},
    )
    dossier = research_runtime.add_root_search_tasks(dossier, [fetch_task])
    updated = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)

    artifacts = ArtifactRegistry(tmp_path, dossier.run.run_id).records()
    document = next(item for item in artifacts if item.artifact_kind == "fetched_snapshot")
    assert document.media_type == "text/markdown"
    assert document.canonical_url == "https://example.test/docs"
    assert document.artifact_id in updated.run.attempts[0].artifact_refs


def test_anysearch_is_imported_as_external_skill_and_suggestions_remain_inert(tmp_path):
    task = _task(
        capability="main_search",
        allowed_capabilities=[],
        allowed_tools=[],
        delegate_target="anysearch",
        expected_output="DelegateResult:anysearch_sources",
    )
    dossier = _create(tmp_path, [task])
    request = dossier.delegate_requests[0]
    result = {
        "schema_version": "1",
        "result_id": "result-anysearch",
        "request_id": request.request_id,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "step_id": request.step_id,
        "attempt_no": request.attempt_no,
        "status": "success",
        "payload": {
            "query": task.question,
            "sources": [
                {
                    "title": "Vertical result",
                    "url": "https://example.test/vertical",
                    "content": "Candidate-only summary",
                }
            ],
        },
        "usage": {},
        "elapsed_ms": 3,
        "gaps": [],
        "suggestions": ["Root may search another angle"],
        "termination_reason": "",
        "artifact_refs": [],
    }
    updated = research_runtime.import_delegated_result(
        dossier,
        result=result,
        artifact_root=tmp_path,
    )

    assert updated.candidates[0].source_type == "anysearch"
    assert updated.delegate_results[0].suggestions == ["Root may search another angle"]
    assert "tasks" not in updated.delegate_results[0].payload
    assert updated.run.attempts[0].execution_kind == "skill"


@pytest.mark.asyncio
async def test_mineru_markdown_is_registered_before_sidecar_use(monkeypatch, tmp_path):
    dossier = _create(tmp_path, [])
    registry = ArtifactRegistry(tmp_path, dossier.run.run_id)
    source = registry.register_snapshot(
        run_id=dossier.run.run_id,
        task_id="task-source",
        step_id="step-source",
        attempt_no=1,
        content="Fetched fallback text",
        media_type="text/markdown",
        canonical_url="https://example.test/source.pdf",
    )
    mineru_task = _task(
        task_id="task-mineru",
        step_id="step-mineru",
        allowed_capabilities=[],
        allowed_tools=[],
        delegate_target="mineru",
        expected_output="DelegateResult:mineru_markdown",
        artifact_refs=[source.artifact_id],
    )
    dossier = research_runtime.add_root_search_tasks(dossier, [mineru_task])
    request = next(item for item in dossier.delegate_requests if item.target == "mineru")
    dossier = research_runtime.import_delegated_result(
        dossier,
        result={
            "schema_version": "1",
            "result_id": "result-mineru-success",
            "request_id": request.request_id,
            "run_id": request.run_id,
            "task_id": request.task_id,
            "step_id": request.step_id,
            "attempt_no": request.attempt_no,
            "status": "success",
            "payload": {
                "source_artifact_id": source.artifact_id,
                "markdown": "# Parsed\n\nMinerU parsed evidence.",
                "parser_version": "mineru-test-1",
            },
            "usage": {},
            "elapsed_ms": 10,
            "gaps": [],
            "suggestions": [],
            "termination_reason": "",
            "artifact_refs": [source.artifact_id],
        },
        artifact_root=tmp_path,
    )

    stored_result = next(item for item in dossier.delegate_results if item.request_id == request.request_id)
    assert "markdown" not in stored_result.payload
    derived = registry.get(stored_result.payload["artifact_ref"])
    assert derived.parent_artifact_id == source.artifact_id
    assert derived.artifact_kind == "document_snapshot"
    assert derived.canonical_url == source.canonical_url

    mining_task = EvidenceMiningTask(
        run_id=dossier.run.run_id,
        task_id="task-mine-mineru",
        step_id="step-mine-mineru",
        claim_spec_id="claim-runtime",
        artifact_ids=[source.artifact_id],
        artifact_refs=[source.artifact_id],
    )
    dossier = research_runtime.add_root_evidence_tasks(dossier, [mining_task])
    captured = {}

    async def fake_document_operations(**kwargs):
        captured.update(kwargs)
        return {
            "ok": True,
            "results": [],
            "component_attempts": [
                {
                    "component": "mineru",
                    "status": "success",
                    "execution_kind": "parser",
                    "artifact_refs": [derived.artifact_id],
                }
            ],
        }

    monkeypatch.setattr(research_runtime, "run_document_operations", fake_document_operations)
    result = await research_runtime.execute_document_task(
        dossier,
        task=mining_task,
        operations=[
            {
                "op": "grep",
                "artifact_id": source.artifact_id,
                "pattern": "parsed evidence",
            }
        ],
        artifact_root=tmp_path,
    )

    assert result["ok"] is True
    assert captured["mineru_results"] == {
        source.artifact_id: {
            "status": "success",
            "markdown": "# Parsed\n\nMinerU parsed evidence.",
            "artifact_ref": derived.artifact_id,
            "parser_version": "mineru-test-1",
        }
    }


def test_mineru_cannot_bind_markdown_to_an_unassigned_artifact(tmp_path):
    dossier = _create(tmp_path, [])
    registry = ArtifactRegistry(tmp_path, dossier.run.run_id)
    assigned = registry.register_snapshot(
        run_id=dossier.run.run_id,
        task_id="task-source-a",
        step_id="step-source-a",
        attempt_no=1,
        content="Assigned",
        media_type="text/markdown",
        canonical_url="https://example.test/a",
    )
    other = registry.register_snapshot(
        run_id=dossier.run.run_id,
        task_id="task-source-b",
        step_id="step-source-b",
        attempt_no=1,
        content="Other",
        media_type="text/markdown",
        canonical_url="https://example.test/b",
    )
    task = _task(
        task_id="task-mineru-boundary",
        step_id="step-mineru-boundary",
        allowed_capabilities=[],
        allowed_tools=[],
        delegate_target="mineru",
        expected_output="DelegateResult:mineru_markdown",
        artifact_refs=[assigned.artifact_id],
    )
    dossier = research_runtime.add_root_search_tasks(dossier, [task])
    request = next(item for item in dossier.delegate_requests if item.target == "mineru")
    result = {
        "schema_version": "1",
        "result_id": "result-mineru-wrong-source",
        "request_id": request.request_id,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "step_id": request.step_id,
        "attempt_no": request.attempt_no,
        "status": "success",
        "payload": {
            "source_artifact_id": other.artifact_id,
            "markdown": "Unassigned parsed content",
            "parser_version": "mineru-test-1",
        },
        "usage": {},
        "elapsed_ms": 1,
        "gaps": [],
        "suggestions": [],
        "termination_reason": "",
        "artifact_refs": [assigned.artifact_id],
    }

    with pytest.raises(Exception, match="outside the originating request"):
        research_runtime.import_delegated_result(
            dossier,
            result=result,
            artifact_root=tmp_path,
        )


@pytest.mark.asyncio
async def test_deep_attempts_all_four_provider_research_paths_independently(monkeypatch, tmp_path):
    async def fake_provider_research(query, **kwargs):
        statuses = {
            "firecrawl": "succeeded",
            "jina": "entitlement_denied",
            "exa": "timeout",
            "tavily": "partial",
        }
        attempts = []
        for provider, status in statuses.items():
            attempts.append(
                {
                    "provider": provider,
                    "status": status,
                    "timestamps": {"started_at": "2026-08-24T00:00:00Z", "completed_at": "2026-08-24T00:00:01Z"},
                    "usage": {},
                    "external_job": {},
                    "errors": [] if status == "succeeded" else [{"message": status}],
                    "artifact": {},
                    "report": "",
                    "candidates": [],
                }
            )
        return {"attempts": attempts}

    monkeypatch.setattr(research_runtime.service, "run_provider_research_agents", fake_provider_research)
    task = _task("provider-research", "provider_research")
    dossier = _create(tmp_path, [task])
    updated = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)

    assert {item.provider: item.status for item in updated.run.attempts} == {
        "firecrawl": "success",
        "jina": "entitlement_failure",
        "exa": "timeout",
        "tavily": "partial",
    }
    events = JsonlTraceStore(tmp_path, dossier.run.run_id).events()
    provider_events = [event for event in events if event.event_type == "provider_research_completed"]
    assert len(provider_events) == 4
    assert {event.public_payload["provider"] for event in provider_events} == {
        "firecrawl", "jina", "exa", "tavily"
    }


@pytest.mark.asyncio
async def test_extended_provider_capability_results_join_common_candidate_pipeline(monkeypatch, tmp_path):
    async def fake_extended(tool, arguments, **kwargs):
        assert tool == "deep-search"
        assert arguments["query"] == "Find official mechanism documentation"
        assert kwargs["providers"] == ["exa"]
        return {
            "ok": True,
            "attempts": [
                {
                    "provider": "exa",
                    "capability": "deep_search",
                    "status": "succeeded",
                    "result": {
                        "results": [
                            {
                                "title": "Deep result",
                                "url": "https://example.test/deep",
                                "text": "Deep-search candidate",
                            }
                        ]
                    },
                    "errors": [],
                }
            ],
        }

    monkeypatch.setattr(research_runtime.service, "run_extended_provider_capability", fake_extended)
    capabilities = {
        **CAPABILITIES,
        "deep_search": {
            "providers": [
                {"name": "exa", "configured": True, "reachable": True, "entitled": True}
            ],
            "tools": ["deep-search"],
        },
    }
    task = _task("deep-search", "deep_search")
    dossier = research_runtime.create_dossier(
        frame=_frame(),
        claims=[_claim()],
        search_tasks=[task],
        capability_snapshot=capabilities,
        artifact_root=tmp_path,
    )
    updated = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)

    assert updated.run.attempts[0].provider == "exa"
    assert updated.run.attempts[0].status == "success"
    assert updated.candidates[0].canonical_url == "https://example.test/deep"


@pytest.mark.asyncio
async def test_nested_provider_data_joins_common_candidate_pipeline(monkeypatch, tmp_path):
    async def fake_extended(tool, arguments, **kwargs):
        return {
            "ok": True,
            "attempts": [
                {
                    "provider": "jina",
                    "capability": "jina_search",
                    "status": "succeeded",
                    "result": {
                        "terminal": {
                            "data": [
                                {
                                    "title": "Jina result",
                                    "url": "https://example.test/jina",
                                    "description": "Nested provider result",
                                }
                            ]
                        }
                    },
                    "errors": [],
                }
            ],
        }

    monkeypatch.setattr(research_runtime.service, "run_extended_provider_capability", fake_extended)
    capabilities = {
        **CAPABILITIES,
        "jina_search": {
            "providers": [
                {"name": "jina", "configured": True, "reachable": True, "entitled": True}
            ],
            "tools": ["jina-search"],
        },
    }
    task = _task("jina-search", "jina_search")
    dossier = research_runtime.create_dossier(
        frame=_frame(),
        claims=[_claim()],
        search_tasks=[task],
        capability_snapshot=capabilities,
        artifact_root=tmp_path,
    )
    updated = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)

    assert [item.canonical_url for item in updated.candidates] == ["https://example.test/jina"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool", "capability", "provider_result", "expected_url"),
    [
        (
            "academic-search",
            "academic_search",
            {
                "success": True,
                "results": [
                    {
                        "paperId": "paper-1",
                        "primaryId": "arxiv:2105.05233",
                        "title": "Diffusion Models Beat GANs",
                        "abstract": "Academic candidate",
                    }
                ],
            },
            "https://arxiv.org/abs/2105.05233",
        ),
        (
            "developer-search",
            "developer_search",
            {
                "success": True,
                "results": [
                    {
                        "id": "issue:acme/sdk#1",
                        "type": "issue",
                        "url": "https://github.com/acme/sdk/issues/1",
                        "title": "Retry bug",
                        "passages": [{"text": "The retry loop was fixed."}],
                    }
                ],
                "coverage": {"issue": "ok"},
                "reranked": True,
            },
            "https://github.com/acme/sdk/issues/1",
        ),
    ],
)
async def test_firecrawl_indexes_join_the_common_candidate_pipeline(
    monkeypatch, tmp_path, tool, capability, provider_result, expected_url
):
    async def fake_extended(selected_tool, arguments, **kwargs):
        assert selected_tool == tool
        assert kwargs["providers"] == ["firecrawl"]
        return {
            "ok": True,
            "attempts": [
                {
                    "provider": "firecrawl",
                    "capability": capability,
                    "status": "succeeded",
                    "result": provider_result,
                    "errors": [],
                }
            ],
        }

    monkeypatch.setattr(
        research_runtime.service, "run_extended_provider_capability", fake_extended
    )
    capabilities = {
        **CAPABILITIES,
        capability: {
            "providers": [
                {
                    "name": "firecrawl",
                    "configured": True,
                    "reachable": True,
                    "entitled": True,
                }
            ],
            "tools": [tool],
        },
    }
    task = _task(tool, capability)
    dossier = research_runtime.create_dossier(
        frame=_frame(),
        claims=[_claim()],
        search_tasks=[task],
        capability_snapshot=capabilities,
        artifact_root=tmp_path,
    )

    updated = await research_runtime.execute_internal_steps(
        dossier, artifact_root=tmp_path
    )

    assert updated.run.attempts[0].provider == "firecrawl"
    assert updated.run.attempts[0].status == "success"
    assert [item.canonical_url for item in updated.candidates] == [expected_url]


@pytest.mark.asyncio
async def test_evidence_miner_roundtrip_claim_and_final_citation_backtrace(monkeypatch, tmp_path):
    async def fake_fetch(url):
        return {
            "ok": True,
            "url": url,
            "provider": "jina",
            "content": "The documented mechanism exists.",
            "elapsed_ms": 5,
        }

    monkeypatch.setattr(research_runtime.service, "fetch", fake_fetch)
    dossier = _create(
        tmp_path,
        [
            _task(
                "fetch",
                "web_fetch",
                question="Read selected source",
                user_constraints={"url": "https://example.test/source"},
            )
        ],
    )
    dossier = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)
    registry = ArtifactRegistry(tmp_path, dossier.run.run_id)
    document = next(item for item in registry.records() if item.artifact_kind == "fetched_snapshot")
    mining_task = EvidenceMiningTask(
        run_id=dossier.run.run_id,
        task_id="task-mine",
        step_id="step-mine",
        claim_spec_id="claim-runtime",
        artifact_ids=[document.artifact_id],
        artifact_refs=[document.artifact_id],
    )
    dossier = research_runtime.add_root_evidence_tasks(dossier, [mining_task])
    request = next(item for item in dossier.delegate_requests if item.target == "evidence_miner")
    quality = {
        "authority": "primary",
        "directness": "direct",
        "freshness": "current",
        "methodological_fit": "fit",
        "independence": "independent",
        "locator_quality": "exact",
    }
    evidence = {
        "schema_version": "1",
        "evidence_id": "evidence-runtime",
        "run_id": dossier.run.run_id,
        "task_id": mining_task.task_id,
        "step_id": mining_task.step_id,
        "attempt_no": 1,
        "claim_spec_id": mining_task.claim_spec_id,
        "source_id": "source-runtime",
        "canonical_url": document.canonical_url,
        "artifact_id": document.artifact_id,
        "snapshot_id": document.snapshot_id,
        "retrieved_at": document.created_at,
        "content_type": document.media_type,
        "locator": {
            "type": "character_range",
            "start": 0,
            "end": len("The documented mechanism exists."),
        },
        "text": "The documented mechanism exists.",
        "stance": "support",
        "quality": quality,
        "artifact_refs": [document.artifact_id],
    }
    delegate_result = {
        "schema_version": "1",
        "result_id": "result-miner",
        "request_id": request.request_id,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "step_id": request.step_id,
        "attempt_no": 1,
        "status": "success",
        "payload": {"evidence_items": [evidence]},
        "usage": {},
        "elapsed_ms": 7,
        "gaps": [],
        "suggestions": [],
        "termination_reason": "document exhausted",
        "artifact_refs": [document.artifact_id],
    }
    dossier = research_runtime.import_delegated_result(
        dossier,
        result=delegate_result,
        artifact_root=tmp_path,
    )
    dossier = research_runtime.derive_root_claim_records(
        dossier,
        decisions=[
            {
                "claim_spec_id": "claim-runtime",
                "citation_map": {"citation-1": "evidence-runtime"},
                "gaps": [],
                "conflicts": [],
            }
        ],
    )
    dossier = research_runtime.update_root_decision(dossier, stop_reason="evidence sufficient")
    result = research_runtime.verify_final_citations(
        dossier,
        citations=[
            {
                "citation_id": "citation-1",
                "claim_record_id": dossier.claim_records[0].claim_record_id,
                "evidence_id": "evidence-runtime",
            }
        ],
        artifact_root=tmp_path,
    )

    assert dossier.claim_records[0].status == "supported"
    assert result["ok"] is True
    assert result["backtrace"]["citation-1"]["artifact_id"] == document.artifact_id


@pytest.mark.asyncio
async def test_evidence_miner_cannot_return_evidence_for_another_task(monkeypatch, tmp_path):
    async def fake_fetch(url):
        return {"ok": True, "url": url, "provider": "jina", "content": "Registered source"}

    monkeypatch.setattr(research_runtime.service, "fetch", fake_fetch)
    dossier = _create(
        tmp_path,
        [_task("fetch", "web_fetch", user_constraints={"url": "https://example.test/source"})],
    )
    dossier = await research_runtime.execute_internal_steps(dossier, artifact_root=tmp_path)
    document = next(
        item
        for item in ArtifactRegistry(tmp_path, dossier.run.run_id).records()
        if item.artifact_kind == "fetched_snapshot"
    )
    mining_task = EvidenceMiningTask(
        run_id=dossier.run.run_id,
        task_id="task-mine-boundary",
        step_id="step-mine-boundary",
        claim_spec_id="claim-runtime",
        artifact_ids=[document.artifact_id],
        artifact_refs=[document.artifact_id],
    )
    dossier = research_runtime.add_root_evidence_tasks(dossier, [mining_task])
    request = next(item for item in dossier.delegate_requests if item.target == "evidence_miner")
    evidence = {
        "schema_version": "1",
        "evidence_id": "evidence-wrong-task",
        "run_id": dossier.run.run_id,
        "task_id": "task-not-assigned",
        "step_id": request.step_id,
        "attempt_no": 1,
        "claim_spec_id": "claim-runtime",
        "source_id": "source-runtime",
        "canonical_url": document.canonical_url,
        "artifact_id": document.artifact_id,
        "snapshot_id": document.snapshot_id,
        "retrieved_at": document.created_at,
        "content_type": document.media_type,
        "locator": {"type": "character_range", "start": 0, "end": 10},
        "text": "Registered",
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
    result = {
        "schema_version": "1",
        "result_id": "result-wrong-task",
        "request_id": request.request_id,
        "run_id": request.run_id,
        "task_id": request.task_id,
        "step_id": request.step_id,
        "attempt_no": 1,
        "status": "success",
        "payload": {"evidence_items": [evidence]},
        "usage": {},
        "elapsed_ms": 1,
        "gaps": [],
        "suggestions": [],
        "termination_reason": "",
        "artifact_refs": [document.artifact_id],
    }

    with pytest.raises(Exception, match="originating Evidence Miner request"):
        research_runtime.import_delegated_result(dossier, result=result, artifact_root=tmp_path)


def test_source_curator_is_limited_to_root_assigned_candidate_shard(tmp_path):
    discovery_task = _task(
        allowed_capabilities=[],
        allowed_tools=[],
        delegate_target="anysearch",
        expected_output="DelegateResult:anysearch_sources",
    )
    dossier = _create(tmp_path, [discovery_task])
    request = dossier.delegate_requests[0]
    dossier = research_runtime.import_delegated_result(
        dossier,
        result={
            "schema_version": "1",
            "result_id": "result-curator-source",
            "request_id": request.request_id,
            "run_id": request.run_id,
            "task_id": request.task_id,
            "step_id": request.step_id,
            "attempt_no": 1,
            "status": "success",
            "payload": {
                "query": discovery_task.question,
                "sources": [
                    {
                        "title": "Candidate",
                        "url": "https://example.test/candidate",
                        "content": "Candidate summary",
                    }
                ],
            },
            "usage": {},
            "elapsed_ms": 1,
            "gaps": [],
            "suggestions": [],
            "termination_reason": "",
            "artifact_refs": [],
        },
        artifact_root=tmp_path,
    )
    candidate_id = dossier.candidates[0].candidate_id
    curator_task = _task(
        tool="search",
        capability="main_search",
        task_id="task-curator",
        step_id="step-curator",
        allowed_capabilities=[],
        allowed_tools=[],
        delegate_target="source_curator",
        expected_output="DelegateResult:key_source_proposal",
        user_constraints={"candidate_ids": [candidate_id]},
    )
    dossier = research_runtime.add_root_search_tasks(dossier, [curator_task])
    curator_request = next(item for item in dossier.delegate_requests if item.target == "source_curator")
    result = {
        "schema_version": "1",
        "result_id": "result-curator",
        "request_id": curator_request.request_id,
        "run_id": curator_request.run_id,
        "task_id": curator_request.task_id,
        "step_id": curator_request.step_id,
        "attempt_no": 1,
        "status": "success",
        "payload": {
            "key_source_proposal": {
                "schema_version": "1",
                "proposal_id": "proposal-curator",
                "run_id": curator_request.run_id,
                "task_id": curator_request.task_id,
                "step_id": curator_request.step_id,
                "attempt_no": 1,
                "input_candidate_ids": [candidate_id, "candidate-outside-shard"],
                "keep_candidate_ids": [candidate_id],
                "defer_candidate_ids": [],
                "reject_candidate_ids": ["candidate-outside-shard"],
                "reasons": {},
                "coverage_gaps": [],
                "uncertainties": [],
                "artifact_refs": [],
            }
        },
        "usage": {},
        "elapsed_ms": 1,
        "gaps": [],
        "suggestions": [],
        "termination_reason": "",
        "artifact_refs": [],
    }

    with pytest.raises(Exception, match="outside the run"):
        research_runtime.import_delegated_result(dossier, result=result, artifact_root=tmp_path)


def test_dossier_rejects_child_task_injection_and_root_controls_replan(tmp_path):
    dossier = _create(tmp_path, [])
    with pytest.raises(Exception, match="exactly one"):
        research_runtime.update_root_decision(dossier)

    task = _task()
    updated = research_runtime.add_root_search_tasks(dossier, [task])
    assert updated.run.task_refs == [task.task_id]
    assert dataclasses.asdict(updated.search_tasks[0])["question"] == task.question
