import pytest

from smart_search.research_contracts import (
    ClaimRecord,
    ClaimSpec,
    ContractValidationError,
    EvidenceItem,
    EvidenceMiningTask,
    ResearchFrame,
    ResearchRun,
    SearchTask,
    stable_id,
)


def test_contract_round_trip_requires_schema_version():
    frame = ResearchFrame(
        run_id="run_alpha",
        question="What is supported?",
        permissions=["public_web"],
    )
    claim = ClaimSpec(
        run_id="run_alpha",
        claim_spec_id="claim_one",
        statement="The source supports the claim.",
    )
    run = ResearchRun(run_id="run_alpha", frame=frame, claims=[claim])

    restored = ResearchRun.from_dict(run.to_dict())

    assert restored == run
    payload = frame.to_dict()
    payload.pop("schema_version")
    with pytest.raises(ContractValidationError, match="schema_version"):
        ResearchFrame.from_dict(payload)


def test_contracts_reject_broken_run_refs_and_unsupported_statuses():
    frame = ResearchFrame(run_id="run_alpha", question="Question")
    foreign_claim = ClaimSpec(
        run_id="run_other",
        claim_spec_id="claim_one",
        statement="Claim",
    )
    with pytest.raises(ContractValidationError, match="broken run reference"):
        ResearchRun(run_id="run_alpha", frame=frame, claims=[foreign_claim])

    with pytest.raises(ContractValidationError, match="unsupported claim status"):
        ClaimRecord(
            claim_record_id="record_one",
            run_id="run_alpha",
            claim_spec_id="claim_one",
            statement="Claim",
            status="probably_true",
        )


def test_agent_facing_artifacts_reject_paths_urls_and_unsupported_tools():
    common = {
        "run_id": "run_alpha",
        "task_id": "task_one",
        "step_id": "step_one",
        "claim_spec_id": "claim_one",
    }
    for untrusted_input in (
        "/tmp/source.pdf",
        "../source.pdf",
        "file:///tmp/source.pdf",
        "https://example.com/source.pdf",
    ):
        with pytest.raises(ContractValidationError, match="artifact_id"):
            EvidenceMiningTask(**common, artifact_ids=[untrusted_input])

    with pytest.raises(ContractValidationError, match="unsupported evidence mining tools"):
        EvidenceMiningTask(**common, artifact_ids=["art_registered"], allowed_tools=["read", "delete"])


def test_evidence_rejects_unknown_stance_and_untyped_locator():
    quality = {
        "authority": "primary",
        "directness": "direct",
        "freshness": "current",
        "methodological_fit": "fit",
        "independence": "independent",
        "locator_quality": "exact",
    }
    base = {
        "evidence_id": "evidence_one",
        "run_id": "run_alpha",
        "task_id": "task_one",
        "step_id": "step_one",
        "attempt_no": 1,
        "claim_spec_id": "claim_one",
        "source_id": "source_one",
        "canonical_url": "https://example.com/source",
        "artifact_id": "art_registered",
        "snapshot_id": "snap_one",
        "retrieved_at": "2026-08-24T00:00:00Z",
        "content_type": "text/html",
        "text": "Located evidence",
        "quality": quality,
        "artifact_refs": ["art_registered"],
    }
    with pytest.raises(ContractValidationError, match="unsupported evidence stance"):
        EvidenceItem(**base, locator={"type": "section", "section": "Results"}, stance="agrees")
    with pytest.raises(ContractValidationError, match="unsupported locator type"):
        EvidenceItem(**base, locator={"type": "somewhere"}, stance="support")


def test_stable_ids_are_repeatable_and_scope_bound():
    kwargs = {
        "kind": "evidence",
        "run_id": "run_alpha",
        "task_id": "task_one",
        "step_id": "step_one",
        "attempt_no": 1,
        "identity": {"artifact": "art_one", "locator": 10},
    }
    first = stable_id(**kwargs)

    assert stable_id(**kwargs) == first
    assert stable_id(**{**kwargs, "attempt_no": 2}) != first
    assert stable_id(**{**kwargs, "task_id": "task_two"}) != first


def test_search_task_requires_valid_public_artifact_refs():
    with pytest.raises(ContractValidationError, match="artifact_id"):
        SearchTask(
            run_id="run_alpha",
            task_id="task_one",
            step_id="step_one",
            question="Question",
            artifact_refs=["https://example.com/unregistered"],
        )
