import dataclasses

import pytest

from smart_search.research_contracts import (
    ClaimSpec,
    ContractValidationError,
    ExecutionAttempt,
    ResearchFrame,
    SearchTask,
    TraceEvent,
    stable_id,
)
from smart_search.research_kernel import (
    ArtifactRegistry,
    JsonlTraceStore,
    PlanCompiler,
    build_candidate_cards,
    create_evidence_item,
    derive_claim_record,
    normalize_candidates,
    validate_evidence_locator,
    validate_citation_backtrace,
)


QUALITY = {
    "authority": "primary",
    "directness": "direct",
    "freshness": "current",
    "methodological_fit": "fit",
    "independence": "independent",
    "locator_quality": "exact",
}


def _frame_and_claim():
    frame = ResearchFrame(
        run_id="run_alpha",
        question="Question",
        permissions=["public_web"],
    )
    claim = ClaimSpec(
        run_id="run_alpha",
        claim_spec_id="claim_one",
        statement="The observed fact is true.",
    )
    return frame, claim


def test_plan_compiler_only_emits_available_root_authored_work():
    frame, claim = _frame_and_claim()
    internal = SearchTask(
        run_id=frame.run_id,
        task_id="task_internal",
        step_id="step_search",
        question="Find evidence",
        claim_spec_id=claim.claim_spec_id,
        allowed_capabilities=["web_search"],
        allowed_tools=["search"],
        permissions=["public_web"],
    )
    delegated = SearchTask(
        run_id=frame.run_id,
        task_id="task_delegate",
        step_id="step_delegate",
        question="Supplement discovery",
        claim_spec_id=claim.claim_spec_id,
        delegate_target="anysearch",
        permissions=["public_web"],
        expected_output="DelegateResult",
    )
    snapshot = {
        "web_search": {
            "configured": True,
            "reachable": True,
            "entitled": True,
            "provider": "tavily",
            "tools": ["search"],
            "observed_at": "2026-08-24T00:00:00Z",
        }
    }

    compiled = PlanCompiler().compile(frame, [claim], [internal, delegated], snapshot)

    assert [(item.capability, item.tool, item.providers) for item in compiled.internal_steps] == [
        ("web_search", "search", ("tavily",))
    ]
    assert [item.target for item in compiled.delegate_requests] == ["anysearch"]


def test_plan_compiler_rejects_broken_refs_unavailable_capabilities_and_tools():
    frame, claim = _frame_and_claim()
    broken = SearchTask(
        run_id=frame.run_id,
        task_id="task_one",
        step_id="step_one",
        question="Question",
        claim_spec_id="claim_missing",
        allowed_capabilities=["web_search"],
        allowed_tools=["search"],
    )
    available = {
        "web_search": {
            "configured": True,
            "reachable": True,
            "entitled": True,
            "tools": ["search"],
        }
    }
    with pytest.raises(ContractValidationError, match="unknown claim_spec_id"):
        PlanCompiler().compile(frame, [claim], [broken], available)

    unavailable = dataclasses.replace(broken, claim_spec_id=claim.claim_spec_id)
    with pytest.raises(ContractValidationError, match="not configured, reachable, and entitled"):
        PlanCompiler().compile(
            frame,
            [claim],
            [unavailable],
            {"web_search": {"configured": True, "reachable": False, "entitled": True, "tools": ["search"]}},
        )

    unsupported = dataclasses.replace(unavailable, allowed_tools=["shell"])
    with pytest.raises(ContractValidationError, match="unsupported internal tool"):
        PlanCompiler().compile(frame, [claim], [unsupported], available)


def test_plan_compiler_does_not_cap_root_task_count():
    frame, claim = _frame_and_claim()
    tasks = [
        SearchTask(
            run_id=frame.run_id,
            task_id=f"task_{index}",
            step_id=f"step_{index}",
            question=f"Question {index}",
            claim_spec_id=claim.claim_spec_id,
            allowed_capabilities=["web_search"],
            allowed_tools=["search"],
        )
        for index in range(40)
    ]
    snapshot = {
        "web_search": {
            "configured": True,
            "reachable": True,
            "entitled": True,
            "tools": ["search"],
        }
    }

    assert len(PlanCompiler().compile(frame, [claim], tasks, snapshot).internal_steps) == len(tasks)


def test_artifact_registry_and_trace_are_append_only_and_run_local(tmp_path):
    registry = ArtifactRegistry(tmp_path, "run_alpha")
    artifact = registry.register_snapshot(
        run_id="run_alpha",
        task_id="task_one",
        step_id="step_fetch",
        attempt_no=1,
        content="immutable body",
        media_type="text/html",
        canonical_url="https://example.com/a?utm_source=test",
        created_at="2026-08-24T00:00:00Z",
    )

    assert registry.get(artifact.artifact_id) == artifact
    assert registry.resolve_inputs([artifact.artifact_id]) == [artifact]
    assert (tmp_path / "run_alpha" / artifact.raw_ref).read_text() == "immutable body"
    assert artifact.canonical_url == "https://example.com/a"
    with pytest.raises(ContractValidationError, match="append-only"):
        registry.append(artifact)
    with pytest.raises(ContractValidationError, match="unknown artifact_id"):
        registry.resolve_inputs(["art_not_registered"])
    with pytest.raises(ContractValidationError, match="artifact_id"):
        registry.resolve_inputs(["file:///tmp/source"])

    trace = JsonlTraceStore(tmp_path, "run_alpha")
    first = TraceEvent(
        event_id="event_one",
        run_id="run_alpha",
        task_id="task_one",
        step_id="step_fetch",
        attempt_no=1,
        event_type="snapshot_registered",
        timestamp="2026-08-24T00:00:00Z",
        artifact_refs=[artifact.artifact_id],
    )
    trace.append(first)
    trace.append(
        TraceEvent(
            event_id="event_two",
            run_id="run_alpha",
            task_id="task_one",
            step_id="step_fetch",
            attempt_no=1,
            parent_event_id=first.event_id,
            event_type="evidence_created",
            timestamp="2026-08-24T00:00:01Z",
            artifact_refs=[artifact.artifact_id],
        )
    )
    assert [item.event_id for item in trace.events()] == ["event_one", "event_two"]
    with pytest.raises(ContractValidationError, match="append-only"):
        trace.append(first)


def test_trace_rejects_secrets_hidden_reasoning_and_broken_parent(tmp_path):
    trace = JsonlTraceStore(tmp_path, "run_alpha")
    with pytest.raises(ContractValidationError, match="secrets"):
        trace.append(
            TraceEvent(
                event_id="event_secret",
                run_id="run_alpha",
                task_id="task_one",
                step_id="step_one",
                attempt_no=1,
                event_type="bad",
                timestamp="2026-08-24T00:00:00Z",
                public_payload={"api_key": "must-not-persist"},
            )
        )
    with pytest.raises(ContractValidationError, match="hidden reasoning"):
        trace.append(
            TraceEvent(
                event_id="event_reasoning",
                run_id="run_alpha",
                task_id="task_one",
                step_id="step_one",
                attempt_no=1,
                event_type="bad",
                timestamp="2026-08-24T00:00:00Z",
                public_payload={"chain_of_thought": "must-not-persist"},
            )
        )
    with pytest.raises(ContractValidationError, match="parent_event_id"):
        trace.append(
            TraceEvent(
                event_id="event_orphan",
                run_id="run_alpha",
                task_id="task_one",
                step_id="step_one",
                attempt_no=1,
                parent_event_id="event_missing",
                event_type="bad",
                timestamp="2026-08-24T00:00:00Z",
            )
        )


def test_candidate_dedup_is_deterministic_and_preserves_related_sources():
    raw = [
        {
            "url": "https://example.com/report?utm_source=news#results",
            "title": "Report duplicate",
            "summary": "B",
            "artifact_refs": ["art_two"],
            "discovery_path": ["provider_b"],
            "related_cluster_id": "cluster_event",
            "independence": "related",
        },
        {
            "url": "https://example.com/report",
            "title": "Report",
            "summary": "A",
            "artifact_refs": ["art_one"],
            "discovery_path": ["provider_a"],
            "related_cluster_id": "cluster_event",
            "independence": "related",
        },
        {
            "url": "https://mirror.example.net/event",
            "title": "Related report",
            "summary": "C",
            "artifact_refs": ["art_three"],
            "discovery_path": ["provider_c"],
            "related_cluster_id": "cluster_event",
            "independence": "syndicated",
        },
    ]
    kwargs = {"run_id": "run_alpha", "task_id": "task_one", "step_id": "step_one", "attempt_no": 1}

    normalized = normalize_candidates(raw, **kwargs)
    reversed_normalized = normalize_candidates(reversed(raw), **kwargs)

    assert [item.to_dict() for item in normalized] == [item.to_dict() for item in reversed_normalized]
    assert len(normalized) == 2
    assert {item.related_cluster_id for item in normalized} == {"cluster_event"}
    report = next(item for item in normalized if item.canonical_url == "https://example.com/report")
    assert report.artifact_refs == ["art_one", "art_two"]
    assert report.discovery_path == ["provider_a", "provider_b"]
    cards, summary = build_candidate_cards(normalized)
    assert len(cards) == 2
    assert summary["count"] == 2
    assert len(summary["grouping_suggestions"]["related_clusters"]["cluster_event"]) == 2


def test_candidate_dedup_is_run_wide_across_root_tasks_and_providers():
    first = normalize_candidates(
        [
            {
                "url": "https://example.com/report?utm_source=provider-a",
                "title": "Provider A",
                "artifact_refs": ["art_a"],
                "discovery_path": ["provider_a"],
            }
        ],
        run_id="run_alpha",
        task_id="task_a",
        step_id="step_a",
    )
    second = normalize_candidates(
        [
            {
                "url": "https://example.com/report",
                "title": "Provider B",
                "artifact_refs": ["art_b"],
                "discovery_path": ["provider_b"],
            }
        ],
        run_id="run_alpha",
        task_id="task_b",
        step_id="step_b",
    )

    merged = normalize_candidates([*first, *second])

    assert len(merged) == 1
    assert merged[0].artifact_refs == ["art_a", "art_b"]
    assert merged[0].discovery_path == ["provider_a", "provider_b"]


def test_evidence_stances_claim_statuses_and_full_citation_reverse_trace(tmp_path):
    frame, claim = _frame_and_claim()
    task = SearchTask(
        run_id=frame.run_id,
        task_id="task_one",
        step_id="step_fetch",
        question="Fetch the source",
        claim_spec_id=claim.claim_spec_id,
        allowed_capabilities=["web_fetch"],
        allowed_tools=["fetch"],
    )
    registry = ArtifactRegistry(tmp_path, frame.run_id)
    artifact = registry.register_snapshot(
        run_id=frame.run_id,
        task_id=task.task_id,
        step_id=task.step_id,
        attempt_no=1,
        content="Evidence text",
        media_type="text/html",
        canonical_url="https://example.com/source",
        created_at="2026-08-24T00:00:00Z",
    )
    evidence = {
        stance: create_evidence_item(
            claim=claim,
            artifact=artifact,
            source_id="source_one",
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=1,
            locator={"type": "character_range", "start": index * 10, "end": index * 10 + 8},
            text=f"{stance} evidence",
            stance=stance,
            quality=QUALITY,
        )
        for index, stance in enumerate(("support", "contradict", "qualify"))
    }
    assert derive_claim_record(claim, [evidence["support"]]).status == "supported"
    assert derive_claim_record(claim, [evidence["contradict"]]).status == "unsupported"
    assert derive_claim_record(claim, [evidence["qualify"]]).status == "weakly_supported"

    contested = derive_claim_record(
        claim,
        [evidence["support"], evidence["contradict"], evidence["qualify"]],
        citation_map={"cite_one": evidence["support"].evidence_id},
    )
    assert contested.status == "contested"
    attempt = ExecutionAttempt(
        attempt_id=stable_id(
            "attempt",
            run_id=frame.run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=1,
        ),
        run_id=frame.run_id,
        task_id=task.task_id,
        step_id=task.step_id,
        attempt_no=1,
        execution_kind="internal",
        capability="web_fetch",
        provider="tavily",
        status="success",
        artifact_refs=[artifact.artifact_id],
    )
    trace = TraceEvent(
        event_id="event_fetch",
        run_id=frame.run_id,
        task_id=task.task_id,
        step_id=task.step_id,
        attempt_no=1,
        event_type="snapshot_registered",
        timestamp="2026-08-24T00:00:00Z",
        artifact_refs=[artifact.artifact_id],
    )

    backtrace = validate_citation_backtrace(
        [
            {
                "citation_id": "cite_one",
                "claim_record_id": contested.claim_record_id,
                "evidence_id": evidence["support"].evidence_id,
            }
        ],
        claim_records=[contested],
        evidence_items=list(evidence.values()),
        tasks=[task],
        attempts=[attempt],
        artifacts=[artifact],
        trace_events=[trace],
    )
    assert backtrace["cite_one"] == {
        "claim_record_id": contested.claim_record_id,
        "claim_spec_id": claim.claim_spec_id,
        "evidence_id": evidence["support"].evidence_id,
        "task_id": task.task_id,
        "attempt_id": attempt.attempt_id,
        "artifact_id": artifact.artifact_id,
        "snapshot_id": artifact.snapshot_id,
        "raw_ref": artifact.raw_ref,
    }

    broken_artifact = dataclasses.replace(artifact, snapshot_id="snap_other")
    with pytest.raises(ContractValidationError, match="snapshot backtrace"):
        validate_citation_backtrace(
            [
                {
                    "citation_id": "cite_one",
                    "claim_record_id": contested.claim_record_id,
                    "evidence_id": evidence["support"].evidence_id,
                }
            ],
            claim_records=[contested],
            evidence_items=list(evidence.values()),
            tasks=[task],
            attempts=[attempt],
            artifacts=[broken_artifact],
        )


def test_evidence_locator_reopens_exact_snapshot_text(tmp_path):
    _, claim = _frame_and_claim()
    registry = ArtifactRegistry(tmp_path, claim.run_id)
    content = "Prefix. Exact evidence sentence. Suffix."
    artifact = registry.register_snapshot(
        run_id=claim.run_id,
        task_id="task_locator",
        step_id="step_locator",
        attempt_no=1,
        content=content,
        media_type="text/markdown",
        canonical_url="https://example.test/locator",
    )
    text = "Exact evidence sentence."
    start = content.index(text)
    evidence = create_evidence_item(
        claim=claim,
        artifact=artifact,
        source_id="source_locator",
        task_id="task_locator",
        step_id="step_locator",
        attempt_no=1,
        locator={"type": "character_range", "start": start, "end": start + len(text)},
        text=text,
        stance="support",
        quality=QUALITY,
    )

    assert validate_evidence_locator(registry, evidence)["text_length"] == len(text)
    broken = dataclasses.replace(evidence, text="Different text")
    with pytest.raises(ContractValidationError, match="does not reproduce"):
        validate_evidence_locator(registry, broken)
