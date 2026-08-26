from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from smart_search.research_contracts import (
    CandidateCard,
    ClaimRecord,
    ClaimSpec,
    DelegateRequest,
    DelegateResult,
    DiscoveryCandidate,
    EvidenceItem,
    EvidenceMiningTask,
    ExecutionAttempt,
    KeySourceProposal,
    ResearchFrame,
    ResearchRun,
    SearchTask,
)
from smart_search.research_runtime import ResearchDossier
from smart_search.research_workspace import ResearchWorkspace, ResearchWorkspaceError


QUALITY = {
    "authority": "primary",
    "directness": "direct",
    "freshness": "current",
    "methodological_fit": "fit",
    "independence": "independent",
    "locator_quality": "exact",
}


def _stage_g_dossier() -> ResearchDossier:
    run_id = "run-stage-g-workspace"
    frame = ResearchFrame(
        run_id=run_id,
        question="Which research architecture and benchmarks are supported?",
        mode="deep",
        scope={"topic": "multi-source research"},
        user_constraints={"public_sources_only": True},
        permissions=["public_web"],
    )
    claims = [
        ClaimSpec(
            run_id=run_id,
            claim_spec_id="claim-architecture",
            statement="The architecture has public support.",
        ),
        ClaimSpec(
            run_id=run_id,
            claim_spec_id="claim-benchmarks",
            statement="A benchmark combination is required.",
        ),
    ]
    search_tasks = [
        SearchTask(
            run_id=run_id,
            task_id=f"scout:{index}",
            step_id=f"step-scout-{index}",
            question=f"Find sources for shard {index}",
            claim_spec_id=claims[index - 1].claim_spec_id,
            permissions=["public_web"],
            delegate_target="search_scout",
            expected_output="DelegateResult:candidates",
        )
        for index in (1, 2)
    ]
    search_tasks.extend(
        SearchTask(
            run_id=run_id,
            task_id=f"curator:{index}",
            step_id=f"step-curator-{index}",
            question=f"Curate source shard {index}",
            permissions=["public_web"],
            delegate_target="source_curator",
            expected_output="DelegateResult:key_source_proposal",
        )
        for index in (1, 2)
    )
    mining_tasks = [
        EvidenceMiningTask(
            run_id=run_id,
            task_id=f"miner:{index}",
            step_id=f"step-miner-{index}",
            claim_spec_id=claims[(index - 1) % 2].claim_spec_id,
            artifact_ids=[f"artifact-{index}"],
            artifact_refs=[f"artifact-{index}"],
        )
        for index in (1, 2, 3)
    ]
    all_tasks = search_tasks + mining_tasks
    requests = [
        DelegateRequest(
            request_id=f"request-{index}",
            run_id=run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=1,
            target=(task.delegate_target if isinstance(task, SearchTask) else "evidence_miner"),
            source_task_id=task.task_id,
            input_artifact_ids=(list(task.artifact_ids) if isinstance(task, EvidenceMiningTask) else []),
            permissions=["public_web"],
            output_schema=task.expected_output,
            artifact_refs=list(task.artifact_refs),
        )
        for index, task in enumerate(all_tasks, start=1)
    ]
    results = [
        DelegateResult(
            result_id=f"result-{index}",
            request_id=request.request_id,
            run_id=run_id,
            task_id=request.task_id,
            step_id=request.step_id,
            attempt_no=1,
            status="success",
            payload={},
            gaps=["One public coverage gap"] if index == 1 else [],
            suggestions=[],
            termination_reason="public task exhausted",
            artifact_refs=list(request.artifact_refs),
        )
        for index, request in enumerate(requests, start=1)
    ]
    attempts = [
        ExecutionAttempt(
            attempt_id=f"attempt-{index}",
            run_id=run_id,
            task_id=request.task_id,
            step_id=request.step_id,
            attempt_no=1,
            execution_kind="project_agent",
            capability=request.target,
            status="success",
            provider=request.target,
            completed_at=f"2026-08-24T00:00:0{index}Z",
            artifact_refs=list(request.artifact_refs),
        )
        for index, request in enumerate(requests, start=1)
    ]

    candidates = []
    cards = []
    for index in range(113):
        task = search_tasks[index % 2]
        candidate = DiscoveryCandidate(
            candidate_id=f"candidate-{index:03d}",
            run_id=run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=1,
            title=f"Candidate {index}",
            canonical_url=f"https://sources.example/{index}",
            summary=f"Normalized candidate summary {index}",
            source_type="search_scout",
            discovery_path=["delegate:search_scout"],
            artifact_refs=[f"candidate-artifact-{index:03d}"],
        )
        candidates.append(candidate)
        cards.append(
            CandidateCard(
                candidate_id=candidate.candidate_id,
                run_id=run_id,
                title=candidate.title,
                canonical_url=candidate.canonical_url,
                summary=candidate.summary,
                source_type=candidate.source_type,
                raw_record_ref=candidate.artifact_refs[0],
            )
        )

    proposals = []
    shards = (candidates[:50], candidates[50:])
    for index, shard in enumerate(shards, start=1):
        keep = [item.candidate_id for item in shard[:2]]
        defer = [item.candidate_id for item in shard[2:3]]
        reject = [item.candidate_id for item in shard[3:]]
        proposals.append(
            KeySourceProposal(
                proposal_id=f"proposal-{index}",
                run_id=run_id,
                task_id=f"curator:{index}",
                step_id=f"step-curator-{index}",
                attempt_no=1,
                input_candidate_ids=[item.candidate_id for item in shard],
                keep_candidate_ids=keep,
                defer_candidate_ids=defer,
                reject_candidate_ids=reject,
                reasons={
                    **{item: "Direct and relevant" for item in keep},
                    **{item: "Useful if a gap remains" for item in defer},
                    **{item: "Lower-priority duplicate" for item in reject},
                },
                coverage_gaps=["Need one independent source"] if index == 2 else [],
                artifact_refs=[f"curator-artifact-{index}"],
            )
        )

    evidence_items = []
    for index in range(16):
        task = mining_tasks[index % 3]
        evidence_items.append(
            EvidenceItem(
                evidence_id=f"evidence-{index:02d}",
                run_id=run_id,
                task_id=task.task_id,
                step_id=task.step_id,
                attempt_no=1,
                claim_spec_id=task.claim_spec_id,
                source_id=f"source-{index:02d}",
                canonical_url=f"https://evidence.example/{index}",
                artifact_id=task.artifact_ids[0],
                snapshot_id=f"snapshot-{index:02d}",
                retrieved_at="2026-08-24T00:00:00Z",
                content_type="text/markdown",
                locator={"type": "character_range", "start": index, "end": index + 8},
                text=f"Evidence {index}",
                stance="support" if index % 2 == 0 else "qualify",
                quality=QUALITY,
                artifact_refs=[task.artifact_ids[0]],
            )
        )

    records = []
    for claim in claims:
        linked = [item for item in evidence_items if item.claim_spec_id == claim.claim_spec_id]
        support = [item.evidence_id for item in linked if item.stance == "support"]
        qualify = [item.evidence_id for item in linked if item.stance == "qualify"]
        records.append(
            ClaimRecord(
                claim_record_id=f"record-{claim.claim_spec_id}",
                run_id=run_id,
                claim_spec_id=claim.claim_spec_id,
                statement=claim.statement,
                status="weakly_supported",
                support_evidence_ids=support,
                qualify_evidence_ids=qualify,
                gaps=["Public evidence is partial"],
                citation_map={f"citation-{item.evidence_id}": item.evidence_id for item in linked},
            )
        )

    run = ResearchRun(
        run_id=run_id,
        frame=frame,
        claims=claims,
        task_refs=[item.task_id for item in all_tasks],
        capability_snapshot={"observed": True},
        capability_observed_at="2026-08-24T00:00:00Z",
        attempts=attempts,
        delegate_refs=[item.request_id for item in requests],
        candidate_summary={"count": len(candidates)},
        evidence_gaps=["One public coverage gap"],
        stop_reason="Root stopped after recording explicit evidence gaps",
        trace_ref="trace.jsonl",
        artifact_index_ref="artifacts.jsonl",
    )
    return ResearchDossier(
        run=run,
        search_tasks=search_tasks,
        evidence_mining_tasks=mining_tasks,
        delegate_requests=requests,
        delegate_results=results,
        candidates=candidates,
        candidate_cards=cards,
        key_source_proposals=proposals,
        evidence_items=evidence_items,
        claim_records=records,
    )


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _citation_verification(dossier: ResearchDossier) -> dict:
    evidence = dossier.evidence_items[0]
    return {
        "ok": True,
        "citation_count": 16,
        "backtrace": {
            "citation-evidence-00": {
                "claim_record_id": dossier.claim_records[0].claim_record_id,
                "claim_spec_id": evidence.claim_spec_id,
                "evidence_id": evidence.evidence_id,
                "task_id": evidence.task_id,
                "attempt_id": next(
                    item.attempt_id
                    for item in dossier.run.attempts
                    if item.task_id == evidence.task_id
                    and item.step_id == evidence.step_id
                    and item.attempt_no == evidence.attempt_no
                ),
                "artifact_id": evidence.artifact_id,
                "snapshot_id": evidence.snapshot_id,
                "raw_ref": "raw/snapshot.bin",
            }
        },
        "locator_checks": {"evidence-00": {"locator_type": "character_range"}},
        "trace_ref": dossier.run.trace_ref,
        "artifact_index_ref": dossier.run.artifact_index_ref,
    }


def _rendered_report_and_register(dossier: ResearchDossier) -> tuple[str, dict]:
    evidence = dossier.evidence_items[0]
    claim = dossier.claim_records[0]
    report = (
        "# Final\n\nThe evidence supports the conclusion [1].\n\n"
        "## References\n\n1. https://evidence.example/0.\n"
    )
    register = {
        "schema_version": "1",
        "run_id": dossier.run.run_id,
        "projection": "derived_audit_reference_register",
        "reference_count": 1,
        "references": [
            {
                "number": 1,
                "source": {
                    "source_id": evidence.source_id,
                    "canonical_url": evidence.canonical_url,
                    "canonical_urls": [evidence.canonical_url],
                    "bibliographic": {},
                },
                "citation_ids": ["citation-evidence-00"],
                "claim_records": [
                    {
                        "claim_record_id": claim.claim_record_id,
                        "claim_spec_id": claim.claim_spec_id,
                    }
                ],
                "evidence_items": [
                    {
                        "evidence_id": evidence.evidence_id,
                        "claim_record_id": claim.claim_record_id,
                        "claim_spec_id": evidence.claim_spec_id,
                        "task_id": evidence.task_id,
                        "step_id": evidence.step_id,
                        "attempt_no": evidence.attempt_no,
                        "attempt_id": next(
                            item.attempt_id
                            for item in dossier.run.attempts
                            if item.task_id == evidence.task_id
                            and item.step_id == evidence.step_id
                            and item.attempt_no == evidence.attempt_no
                        ),
                        "artifact_id": evidence.artifact_id,
                        "snapshot_id": evidence.snapshot_id,
                        "canonical_url": evidence.canonical_url,
                        "retrieved_at": evidence.retrieved_at,
                        "locator": evidence.locator,
                    }
                ],
                "artifacts": [
                    {
                        "artifact_id": evidence.artifact_id,
                        "snapshot_id": evidence.snapshot_id,
                        "raw_ref": "raw/snapshot.bin",
                        "canonical_url": evidence.canonical_url,
                    }
                ],
            }
        ],
    }
    return report, register


def test_materializes_public_agent_workspace_and_stage_g_projections(tmp_path):
    dossier = _stage_g_dossier()
    root = tmp_path / "workspace"
    artifact_root = root / "runtime_artifacts"
    workspace = ResearchWorkspace(root, artifact_root=artifact_root)

    manifest = workspace.materialize(
        dossier,
        checkpoint_labels=["after-evidence"],
        citation_verification=_citation_verification(dossier),
    )

    assert manifest["counts"] == {
        "search_tasks": 4,
        "evidence_mining_tasks": 3,
        "execution_attempts": 7,
        "delegate_requests": 7,
        "delegate_results": 7,
        "candidates": 113,
        "candidate_cards": 113,
        "key_source_proposals": 2,
        "evidence_items": 16,
        "claim_records": 2,
    }
    assert manifest["entrypoints"]["artifact_run_directory"] == (
        "runtime_artifacts/run-stage-g-workspace"
    )
    for name in (
        "project_manifest.json",
        "initial_context.md",
        "domain_methodology.md",
        "main_log.md",
        "latest_dossier.json",
        "checkpoints/after-evidence.json",
        "evidence/candidates.jsonl",
        "evidence/candidate_cards.jsonl",
        "evidence/key_source_proposals.jsonl",
        "evidence/evidence_items.jsonl",
        "evidence/claim_records.json",
        "evidence/citation_verification.json",
    ):
        assert (root / name).is_file()
    assert not (root / "final_synthesis.md").exists()

    task_directories = sorted(path for path in root.glob("task_*") if path.is_dir())
    assert len(task_directories) == 7
    for directory in task_directories:
        assert {"task_spec.json", "task_state.json", "knowledge_fragments.md", "result.json", "status.txt"}.issubset(
            {path.name for path in directory.iterdir()}
        )
        assert (directory / "status.txt").read_bytes() == b"Completed"

    scout = root / manifest["entrypoints"]["tasks"]["scout:1"]
    assert "https://sources.example/0" in (scout / "knowledge_fragments.md").read_text()
    curator = root / manifest["entrypoints"]["tasks"]["curator:1"]
    curator_text = (curator / "knowledge_fragments.md").read_text()
    assert "Retained" in curator_text and "Direct and relevant" in curator_text
    miner = root / manifest["entrypoints"]["tasks"]["miner:1"]
    miner_text = (miner / "knowledge_fragments.md").read_text()
    assert "EvidenceItem" in miner_text
    assert "Stance" in miner_text
    assert "characters" in miner_text
    assert "Qualitative dimensions" in miner_text
    assert "## Phase 6: Root Decision" in (root / "main_log.md").read_text()


def test_projects_only_trace_identity_metadata(tmp_path):
    dossier = _stage_g_dossier()
    root = tmp_path / "workspace"
    artifact_root = root / "runtime_artifacts"
    run_dir = artifact_root / dossier.run.run_id
    run_dir.mkdir(parents=True)
    (run_dir / "trace.jsonl").write_text(
        json.dumps(
            {
                "event_id": "event-one",
                "run_id": dossier.run.run_id,
                "task_id": "scout:1",
                "step_id": "step-scout-1",
                "attempt_no": 1,
                "event_type": "delegate_completed",
                "timestamp": "2026-08-24T00:00:00Z",
                "artifact_refs": ["artifact-1"],
                "public_payload": {"summary": "must not be copied"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    manifest = ResearchWorkspace(root, artifact_root=artifact_root).materialize(dossier)

    projected = json.loads((root / "public_trace.jsonl").read_text())
    assert projected["event_id"] == "event-one"
    assert "public_payload" not in projected
    assert manifest["public_trace_path"] == "public_trace.jsonl"
    assert manifest["entrypoints"]["public_trace"] == "public_trace.jsonl"


def test_rematerialization_is_byte_idempotent(tmp_path):
    dossier = _stage_g_dossier()
    root = tmp_path / "workspace"
    workspace = ResearchWorkspace(root)
    verification = _citation_verification(dossier)

    workspace.materialize(
        dossier,
        checkpoint_labels=["stable"],
        final_synthesis="# Final\n\nExplicit synthesis.\n",
        citation_verification=verification,
    )
    before = _tree_bytes(root)
    workspace.materialize(
        dossier,
        checkpoint_labels=["stable"],
        final_synthesis="# Final\n\nExplicit synthesis.\n",
        citation_verification=verification,
    )

    assert _tree_bytes(root) == before


def test_legacy_report_replacement_removes_stale_reference_register(tmp_path):
    dossier = _stage_g_dossier()
    report, register = _rendered_report_and_register(dossier)
    verification = _citation_verification(dossier)
    root = tmp_path / "workspace"
    workspace = ResearchWorkspace(root)

    workspace.materialize(
        dossier,
        final_synthesis=report,
        citation_verification=verification,
        reference_register=register,
    )
    workspace.materialize(
        dossier,
        final_synthesis="# Legacy replacement\n\nNo evidence-backed references here.\n",
    )

    assert not (root / "evidence/reference_register.json").exists()
    manifest = json.loads((root / "project_manifest.json").read_text())
    assert "reference_register" not in manifest["entrypoints"]


def test_wrong_run_legacy_report_does_not_remove_existing_reference_register(tmp_path):
    dossier = _stage_g_dossier()
    report, register = _rendered_report_and_register(dossier)
    verification = _citation_verification(dossier)
    root = tmp_path / "workspace"
    workspace = ResearchWorkspace(root)
    workspace.materialize(
        dossier,
        final_synthesis=report,
        citation_verification=verification,
        reference_register=register,
    )
    before = _tree_bytes(root)
    other_payload = json.loads(
        json.dumps(dossier.to_dict()).replace(dossier.run.run_id, "run-other")
    )
    other = ResearchDossier.from_dict(other_payload)

    with pytest.raises(ResearchWorkspaceError, match="different research run"):
        workspace.materialize(
            other,
            final_synthesis="# Wrong run\n\nLegacy report.\n",
        )

    assert _tree_bytes(root) == before


def test_checkpoint_labels_are_safe_and_different_snapshots_are_not_overwritten(tmp_path):
    dossier = _stage_g_dossier()
    workspace = ResearchWorkspace(tmp_path / "workspace")
    workspace.materialize(dossier, checkpoint_labels=["phase-1"])

    with pytest.raises(ResearchWorkspaceError, match="safe filesystem label"):
        workspace.write_checkpoint(dossier, "../escape")
    with pytest.raises(ResearchWorkspaceError, match="safe filesystem label"):
        workspace.materialize(dossier, checkpoint_labels=["bad/name"])

    changed = dataclasses.replace(
        dossier,
        run=dataclasses.replace(dossier.run, root_next_decision="Continue", stop_reason=""),
    )
    with pytest.raises(ResearchWorkspaceError, match="different dossier snapshot"):
        workspace.write_checkpoint(changed, "phase-1")
    saved = json.loads((tmp_path / "workspace/checkpoints/phase-1.json").read_text())
    assert saved == dossier.to_dict()


@pytest.mark.parametrize(
    "unsafe_key",
    ["hidden_reasoning", "analysis", "reasoning", "scratchpad", "thoughts", "api_key", "access-token"],
)
def test_rejects_hidden_reasoning_and_secret_public_payloads(tmp_path, unsafe_key):
    dossier = _stage_g_dossier()
    unsafe_result = dataclasses.replace(
        dossier.delegate_results[0], payload={unsafe_key: "must-not-leak"}
    )
    dossier = dataclasses.replace(
        dossier,
        delegate_results=[unsafe_result] + dossier.delegate_results[1:],
    )
    root = tmp_path / "workspace"

    with pytest.raises(ResearchWorkspaceError, match="may not be projected"):
        ResearchWorkspace(root).materialize(dossier)

    assert not root.exists()


def test_final_synthesis_is_only_created_or_updated_when_supplied(tmp_path):
    dossier = _stage_g_dossier()
    root = tmp_path / "workspace"
    workspace = ResearchWorkspace(root)

    workspace.materialize(dossier)
    assert not (root / "final_synthesis.md").exists()
    workspace.materialize(dossier, final_synthesis="# Supplied conclusion\n")
    assert (root / "final_synthesis.md").read_text() == "# Supplied conclusion\n"
    workspace.materialize(dossier)
    assert (root / "final_synthesis.md").read_text() == "# Supplied conclusion\n"


def test_citation_verification_projection_is_supplied_data(tmp_path):
    dossier = _stage_g_dossier()
    root = tmp_path / "workspace"
    verification = _citation_verification(dossier)

    manifest = ResearchWorkspace(root).materialize(
        dossier, citation_verification=verification
    )

    saved = json.loads((root / "evidence/citation_verification.json").read_text())
    assert saved == verification
    assert manifest["entrypoints"]["citation_verification"] == (
        "evidence/citation_verification.json"
    )
    assert "## Phase 7: Citation Verification" in (root / "main_log.md").read_text()


@pytest.mark.parametrize("mode", ["quick", "standard", "deep"])
def test_citation_backed_report_register_is_materialized_for_every_mode(tmp_path, mode):
    dossier = _stage_g_dossier()
    dossier = dataclasses.replace(
        dossier,
        run=dataclasses.replace(
            dossier.run,
            frame=dataclasses.replace(dossier.run.frame, mode=mode),
        ),
    )
    report, register = _rendered_report_and_register(dossier)
    verification = _citation_verification(dossier)
    root = tmp_path / mode

    manifest = ResearchWorkspace(root).materialize(
        dossier,
        final_synthesis=report,
        citation_verification=verification,
        reference_register=register,
    )

    assert (root / "final_synthesis.md").read_text() == report
    assert json.loads((root / "evidence/reference_register.json").read_text()) == register
    assert manifest["mode"] == mode
    assert manifest["entrypoints"]["reference_register"] == (
        "evidence/reference_register.json"
    )
    references = report.split("## References", 1)[1]
    assert "evidence-00" not in references
    assert "record-claim-architecture" not in references
    assert "artifact-1" not in references


def test_invalid_reference_register_is_rejected_before_final_projection_changes(tmp_path):
    dossier = _stage_g_dossier()
    report, register = _rendered_report_and_register(dossier)
    verification = _citation_verification(dossier)
    root = tmp_path / "workspace"
    workspace = ResearchWorkspace(root)
    workspace.materialize(
        dossier,
        final_synthesis=report,
        citation_verification=verification,
        reference_register=register,
    )
    before = {
        path: (root / path).read_bytes()
        for path in (
            "final_synthesis.md",
            "evidence/citation_verification.json",
            "evidence/reference_register.json",
            "project_manifest.json",
        )
    }
    broken = json.loads(json.dumps(register))
    broken["references"][0]["evidence_items"][0]["snapshot_id"] = "snapshot-wrong"

    with pytest.raises(ResearchWorkspaceError, match="conflicts on snapshot_id"):
        workspace.materialize(
            dossier,
            final_synthesis=report.replace("supports", "still supports"),
            citation_verification=verification,
            reference_register=broken,
        )

    assert {
        path: (root / path).read_bytes()
        for path in before
    } == before


def test_reference_register_rejects_unused_reference_and_internal_id_leak(tmp_path):
    dossier = _stage_g_dossier()
    report, register = _rendered_report_and_register(dossier)
    verification = _citation_verification(dossier)

    with pytest.raises(ResearchWorkspaceError, match="not used by an in-text citation"):
        ResearchWorkspace(tmp_path / "unused").materialize(
            dossier,
            final_synthesis=report.replace(" [1]", ""),
            citation_verification=verification,
            reference_register=register,
        )
    assert not (tmp_path / "unused").exists()

    leaked_report = report.replace(
        "https://evidence.example/0.",
        "https://evidence.example/0. evidence-00",
    )
    with pytest.raises(ResearchWorkspaceError, match="internal audit identifiers"):
        ResearchWorkspace(tmp_path / "leaked").materialize(
            dossier,
            final_synthesis=leaked_report,
            citation_verification=verification,
            reference_register=register,
        )
    assert not (tmp_path / "leaked").exists()


def test_reference_register_rejects_projection_and_source_identity_conflicts(tmp_path):
    dossier = _stage_g_dossier()
    report, register = _rendered_report_and_register(dossier)
    verification = _citation_verification(dossier)

    wrong_projection = json.loads(json.dumps(register))
    wrong_projection["projection"] = "authoritative_reference_database"
    with pytest.raises(ResearchWorkspaceError, match="derived audit projection"):
        ResearchWorkspace(tmp_path / "projection").materialize(
            dossier,
            final_synthesis=report,
            citation_verification=verification,
            reference_register=wrong_projection,
        )
    assert not (tmp_path / "projection").exists()

    wrong_source = json.loads(json.dumps(register))
    wrong_source["references"][0]["source"]["source_id"] = "source-conflict"
    with pytest.raises(ResearchWorkspaceError, match="source or claim identity"):
        ResearchWorkspace(tmp_path / "source").materialize(
            dossier,
            final_synthesis=report,
            citation_verification=verification,
            reference_register=wrong_source,
        )
    assert not (tmp_path / "source").exists()


def test_workspace_and_task_paths_reject_traversal(tmp_path):
    with pytest.raises(ResearchWorkspaceError, match="parent traversal"):
        ResearchWorkspace(tmp_path / "safe" / ".." / "escape")

    dossier = _stage_g_dossier()
    root = tmp_path / "workspace"
    manifest = ResearchWorkspace(root).materialize(dossier)
    assert all(
        value.startswith("task_") and ".." not in value
        for value in manifest["entrypoints"]["tasks"].values()
    )
