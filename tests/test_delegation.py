import pytest

from smart_search.delegation import (
    DelegationValidationError,
    create_anysearch_dispatch,
    create_delegate_request,
    expand_key_source_proposal,
    import_anysearch_result,
    import_delegate_result,
    summarize_candidates,
    validate_curator_shards,
    validate_key_source_proposal,
)
from smart_search.research_contracts import (
    DelegateRequest,
    DelegateResult,
    KeySourceProposal,
    SearchTask,
)


def _task(**overrides):
    values = {
        "run_id": "run-1",
        "task_id": "task-1",
        "step_id": "step-1",
        "question": "Find sources",
        "allowed_capabilities": ["web_search"],
        "permissions": ["public_web"],
        "expected_output": "discovery_candidates",
        "delegate_target": "search_scout",
    }
    values.update(overrides)
    return SearchTask(**values)


def _request(**overrides):
    values = {"request_id": "request-1", "task": _task()}
    values.update(overrides)
    return create_delegate_request(**values)


def _result(request, **overrides):
    values = {
        "schema_version": "1",
        "result_id": "result-1",
        "request_id": request["request_id"],
        "run_id": request["run_id"],
        "task_id": request["task_id"],
        "step_id": request["step_id"],
        "attempt_no": request["attempt_no"],
        "status": "success",
        "payload": {"candidates": []},
        "usage": {},
        "elapsed_ms": 5,
        "gaps": [],
        "suggestions": [],
        "termination_reason": "scope complete",
        "artifact_refs": [],
    }
    values.update(overrides)
    return values


def _anysearch_dispatch():
    return create_anysearch_dispatch(
        request_id="request-anysearch",
        task=_task(delegate_target="anysearch"),
        query="agentic search",
    )


def test_only_root_can_create_requests_and_children_cannot_return_tasks():
    with pytest.raises(DelegationValidationError, match="only Root"):
        _request(created_by="search_scout")

    request = _request()
    with pytest.raises(DelegationValidationError, match="only Root creates tasks"):
        import_delegate_result(
            _result(request, follow_up_tasks=[{"task_id": "child-task"}]), request=request
        )


def test_suggestions_stay_inert_and_are_not_converted_to_tasks():
    request = _request()
    imported = import_delegate_result(
        _result(request, suggestions=["Search another jurisdiction"]), request=request
    )

    assert imported["suggestions"] == ["Search another jurisdiction"]
    assert "tasks" not in imported
    assert "delegate_requests" not in imported


def test_current_contract_objects_duck_type_without_competing_schema():
    request_mapping = _request()
    request_contract = DelegateRequest.from_dict(request_mapping)
    result_contract = DelegateResult.from_dict(_result(request_mapping))

    imported = import_delegate_result(result_contract, request=request_contract)

    assert imported == result_contract.to_dict()


def test_delegate_request_rejects_unregistered_url_or_path_artifacts():
    with pytest.raises(DelegationValidationError, match="not paths or URLs"):
        create_delegate_request(
            request_id="request-1",
            task=_task(),
            input_artifact_ids=["https://example.test/document"],
        )
    with pytest.raises(DelegationValidationError, match="not paths or URLs"):
        create_delegate_request(
            request_id="request-1",
            task=_task(),
            input_artifact_ids=["../private/document.md"],
        )


def test_anysearch_dispatch_is_bundled_first_and_has_no_concrete_command():
    dispatch = _anysearch_dispatch()

    assert DelegateRequest.from_dict(dispatch["delegate_request"]).target == "anysearch"
    assert dispatch["skill_resolution"] == [
        {"kind": "bundled_snapshot", "path": "skills/anysearch/SKILL.md"},
        {"kind": "global_fallback", "skill": "anysearch"},
    ]
    assert "command" not in dispatch
    assert "command" not in dispatch["delegate_request"]


def test_anysearch_success_validates_query_and_source_input_boundary():
    dispatch = _anysearch_dispatch()
    request = dispatch["delegate_request"]
    imported = import_anysearch_result(
        _result(
            request,
            payload={
                "query": "agentic search",
                "sources": [
                    {
                        "title": "A paper",
                        "url": "https://example.test/paper",
                        "content": "Relevant abstract",
                        "published_at": "2026-08-24",
                    }
                ],
            },
        ),
        dispatch=dispatch,
    )
    assert imported["payload"]["sources"][0]["published_at"] == "2026-08-24"

    with pytest.raises(DelegationValidationError, match="content"):
        import_anysearch_result(
            _result(
                request,
                payload={
                    "query": "agentic search",
                    "sources": [{"title": "Missing content", "url": "https://example.test"}],
                },
            ),
            dispatch=dispatch,
        )


def test_anysearch_unavailable_returns_explicit_gap_and_preserves_query():
    dispatch = _anysearch_dispatch()
    imported = import_anysearch_result(
        _result(
            dispatch["delegate_request"], status="unavailable", payload={}, gaps=[]
        ),
        dispatch=dispatch,
    )

    assert imported["payload"] == {"query": "agentic search", "sources": []}
    assert "unavailable" in imported["gaps"][0]


def test_candidate_summary_and_root_shards_have_no_fixed_agent_count():
    candidates = [
        {
            "candidate_id": f"candidate-{index}",
            "title": "T",
            "canonical_url": f"https://example.test/{index}",
            "summary": "body",
        }
        for index in range(7)
    ]
    summary = summarize_candidates(
        candidates,
        grouping_suggestions=[{"created_by": "root", "basis": "topic"}],
    )
    candidate_ids = [entry["candidate_id"] for entry in summary["raw_index"]]

    assert summary["count"] == 7
    assert summary["estimated_context_chars"] > 0
    assert summary["grouping_suggestions"] == [{"created_by": "root", "basis": "topic"}]
    assert validate_curator_shards(candidate_ids, []) == []
    assert len(
        validate_curator_shards(
            candidate_ids,
            [
                {"shard_id": "a", "created_by": "root", "candidate_ids": ["candidate-0"]},
                {
                    "shard_id": "b",
                    "created_by": "root",
                    "candidate_ids": ["candidate-1", "candidate-2"],
                },
                {
                    "shard_id": "c",
                    "created_by": "root",
                    "candidate_ids": [
                        "candidate-3",
                        "candidate-4",
                        "candidate-5",
                        "candidate-6",
                    ],
                },
            ],
        )
    ) == 3

    with pytest.raises(DelegationValidationError, match="Root-authored"):
        summarize_candidates(
            candidates,
            grouping_suggestions=[{"created_by": "source_curator", "basis": "topic"}],
        )


def test_curator_shards_reject_non_root_ownership_and_unknown_candidates():
    with pytest.raises(DelegationValidationError, match="Root-authored"):
        validate_curator_shards(
            ["candidate-1"],
            [
                {
                    "shard_id": "a",
                    "created_by": "source_curator",
                    "candidate_ids": ["candidate-1"],
                }
            ],
        )
    with pytest.raises(DelegationValidationError, match="unknown candidate"):
        validate_curator_shards(
            ["candidate-1"],
            [{"shard_id": "a", "created_by": "root", "candidate_ids": ["candidate-2"]}],
        )


def test_key_source_proposal_is_canonical_reversible_and_non_destructive():
    originals = {
        "candidate-1": {"candidate_id": "candidate-1", "content": "one"},
        "candidate-2": {"candidate_id": "candidate-2", "content": "two"},
        "candidate-3": {"candidate_id": "candidate-3", "content": "three"},
    }
    contract = KeySourceProposal(
        proposal_id="proposal-1",
        run_id="run-1",
        task_id="task-1",
        step_id="step-1",
        attempt_no=1,
        input_candidate_ids=list(originals),
        keep_candidate_ids=["candidate-1"],
        defer_candidate_ids=["candidate-2"],
        reject_candidate_ids=["candidate-3"],
        reasons={
            "candidate-1": "primary source",
            "candidate-2": "duplicate coverage",
            "candidate-3": "outside date range",
        },
        coverage_gaps=["No opposing view"],
        uncertainties=["candidate-2 authorship unclear"],
        artifact_refs=["artifact-proposal"],
    )

    proposal = validate_key_source_proposal(contract, originals=originals)
    expanded = expand_key_source_proposal(proposal, originals=originals)

    assert proposal == contract.to_dict()
    assert expanded["retained"][0]["original"] == originals["candidate-1"]
    assert expanded["deferred"][0]["original"]["content"] == "two"
    assert expanded["rejected"][0]["original"]["content"] == "three"
    assert set(originals) == {"candidate-1", "candidate-2", "candidate-3"}


def test_key_source_proposal_requires_reasons_and_preserves_every_input():
    originals = {
        "candidate-1": {"candidate_id": "candidate-1"},
        "candidate-2": {"candidate_id": "candidate-2"},
    }
    base = {
        "schema_version": "1",
        "proposal_id": "proposal-1",
        "run_id": "run-1",
        "task_id": "task-1",
        "step_id": "step-1",
        "attempt_no": 1,
        "input_candidate_ids": list(originals),
        "keep_candidate_ids": ["candidate-1"],
        "defer_candidate_ids": [],
        "reject_candidate_ids": [],
        "reasons": {"candidate-1": "useful"},
        "coverage_gaps": [],
        "uncertainties": [],
        "artifact_refs": [],
    }
    with pytest.raises(DelegationValidationError, match="preserve every input"):
        validate_key_source_proposal(base, originals=originals)

    complete = {
        **base,
        "defer_candidate_ids": ["candidate-2"],
    }
    with pytest.raises(DelegationValidationError, match="candidate-2"):
        validate_key_source_proposal(complete, originals=originals)
