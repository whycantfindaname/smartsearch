"""Focused contract tests for the read-only Research Workspace visualizer."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SERVER_PATH = (
    Path(__file__).parents[1]
    / "src"
    / "smart_search"
    / "assets"
    / "research_visualizer"
    / "server.py"
)
INDEX_PATH = SERVER_PATH.with_name("index.html")

SPEC = importlib.util.spec_from_file_location("research_visualizer_server", SERVER_PATH)
assert SPEC and SPEC.loader
visualizer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(visualizer)


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _write_jsonl(path: Path, values) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(value, ensure_ascii=False) + "\n" for value in values),
        encoding="utf-8",
    )


def _stage_g_workspace(root: Path) -> Path:
    _write_json(
        root / "project_manifest.json",
        {
            "project_name": "Stage G architecture review",
            "status": "complete",
            "public_trace_path": "checkpoints/public_trace.jsonl",
            "entrypoints": {
                "final_synthesis": "final_synthesis.md",
                "citation_verification": "evidence/citation_verification.json",
                "reference_register": "evidence/reference_register.json",
            },
        },
    )
    (root / "main_log.md").write_text(
        "# Run\n\n## Discovery\n- Four provider paths started\n- Exa completed while siblings remained independent\n",
        encoding="utf-8",
    )
    (root / "initial_context.md").write_text("# Initial context\n", encoding="utf-8")
    (root / "domain_methodology.md").write_text("# Method\n", encoding="utf-8")
    (root / "final_synthesis.md").write_text(
        "# Final synthesis\n\nEvidence-backed result [1].\n\n"
        "## References\n\n1. https://evidence.test/0.\n",
        encoding="utf-8",
    )

    roles = [
        "search_scout",
        "search_scout",
        "source_curator",
        "source_curator",
        "evidence_miner",
        "evidence_miner",
        "evidence_miner",
    ]
    for index, role in enumerate(roles, start=1):
        task = root / f"task_{index}_{role}"
        _write_json(
            task / "task_spec.json",
            {
                "task_name": f"{role} {index}",
                "role": role,
                "claim_spec_id": "claim-architecture" if index < 6 else "claim-benchmarks",
                "objective": "Inspect only the assigned public research boundary",
                "allowed_capabilities": ["web_search"],
            },
        )
        _write_json(task / "task_state.json", {"status": "completed"})
        _write_json(
            task / "result.json",
            {
                "status": "success",
                "gaps": [],
                "suggestions": ["Root may review"],
                "payload": {"raw_document_body": "must never be projected"},
            },
        )
        (task / "knowledge_fragments.md").write_text("# Public fragments\n", encoding="utf-8")

    attempts = []
    for provider, status, reason in (
        ("firecrawl", "timeout", "deadline reached"),
        ("jina", "timeout", "deadline reached"),
        ("exa", "success", ""),
        ("tavily", "entitlement_failure", "HTTP 432 plan limit"),
    ):
        attempts.append(
            {
                "attempt_id": f"attempt-{provider}",
                "run_id": "run-stage-g",
                "task_id": "task-provider-research",
                "step_id": f"step-{provider}",
                "attempt_no": 1,
                "execution_kind": "provider_research_agent",
                "capability": "provider_research",
                "provider": provider,
                "status": status,
                "error": reason,
            }
        )
    _write_json(
        root / "latest_dossier.json",
        {
            "run": {
                "run_id": "run-stage-g",
                "frame": {"mode": "deep"},
                "claims": [{"claim_spec_id": "claim-architecture"}, {"claim_spec_id": "claim-benchmarks"}],
                "attempts": attempts,
                "evidence_gaps": ["Complete public architecture proof remains unavailable"],
                "stop_reason": "Stage G reports complete; benchmark execution excluded",
            }
        },
    )
    _write_jsonl(
        root / "evidence" / "candidates.jsonl",
        [
            {
                "candidate_id": f"candidate-{index}",
                "canonical_url": f"https://example.test/source/{index}",
                "task_id": f"task_{(index % 7) + 1}_{roles[index % 7]}",
            }
            for index in range(113)
        ],
    )
    _write_jsonl(
        root / "evidence" / "candidate_cards.jsonl",
        [{"candidate_id": f"candidate-{index}"} for index in range(113)],
    )
    _write_jsonl(
        root / "evidence" / "key_source_proposals.jsonl",
        [{"proposal_id": "proposal-academic"}, {"proposal_id": "proposal-multisource"}],
    )
    evidence = []
    for index in range(16):
        evidence.append(
            {
                "evidence_id": f"evidence-{index}",
                "source_id": f"source-{index}",
                "canonical_url": f"https://evidence.test/{index}",
                "stance": "support" if index < 10 else "qualify",
                "locator": {"type": "character_range", "start": index * 10, "end": index * 10 + 8},
                "task_id": f"task_{(index % 7) + 1}_{roles[index % 7]}",
                "claim_spec_id": "claim-architecture" if index < 10 else "claim-benchmarks",
                "text": f"Located evidence {index}",
            }
        )
    _write_jsonl(root / "evidence" / "evidence_items.jsonl", evidence)
    _write_json(
        root / "evidence" / "claim_records.json",
        [
            {"claim_record_id": "claim-record-architecture", "status": "weakly_supported"},
            {"claim_record_id": "claim-record-benchmarks", "status": "weakly_supported"},
        ],
    )
    _write_json(
        root / "evidence" / "citation_verification.json",
        {"ok": True, "backtrace": {f"citation-{index}": {"evidence_id": f"evidence-{index}"} for index in range(16)}},
    )
    _write_json(
        root / "evidence" / "reference_register.json",
        {
            "schema_version": "1",
            "run_id": "run-stage-g",
            "reference_count": 1,
            "references": [{"number": 1, "citation_ids": ["citation-0"]}],
        },
    )
    _write_jsonl(
        root / "checkpoints" / "public_trace.jsonl",
        [
            {
                "event_id": "event-1",
                "run_id": "run-stage-g",
                "task_id": "task_1_search_scout",
                "step_id": "step-discovery",
                "attempt_no": 1,
                "event_type": "attempt_completed",
                "timestamp": "2026-08-24T00:00:00Z",
                "artifact_refs": ["artifact-public"],
                "public_payload": {"summary": "not included in metadata projection"},
                "chain_of_thought": "must never be exposed",
            }
        ],
    )
    return root


def test_stage_g_like_workspace_aggregates_exact_counts_and_isolates_failures(tmp_path):
    root = _stage_g_workspace(tmp_path)

    summary = visualizer.gather_summary(root)

    assert summary["workspace"] == {
        "project_name": "Stage G architecture review",
        "run_id": "run-stage-g",
        "mode": "deep",
        "status": "complete",
        "has_final_report": True,
        "has_report_references": True,
        "has_reference_register": True,
        "has_document_index": True,
        "updated_at": "",
    }
    assert summary["counts"] == {
        "tasks": 7,
        "provider_attempts": 4,
        "agents": 7,
        "candidates": 113,
        "candidate_cards": 113,
        "proposals": 2,
        "evidence": 16,
        "claims": 2,
        "citations": 16,
        "references": 1,
    }
    assert [node["label"] for node in summary["pipeline"]] == [
        "Root Plan",
        "Multi-source Discovery",
        "Source Curation",
        "Evidence Mining",
        "Claims / Citations",
        "Final Report / References",
    ]
    assert {failure["provider"] for failure in summary["failures"]} == {"firecrawl", "jina", "tavily"}
    assert summary["pipeline"][1]["status"] == "degraded"
    assert summary["pipeline"][-1]["status"] == "complete"
    assert summary["evidence"][0]["locator"] == "chars 0–8"
    assert summary["projections"] == {
        "report_references": {"present": True, "kind": "reader_projection"},
        "reference_register": {
            "present": True,
            "count": 1,
            "kind": "audit_projection",
        },
        "document_index": {
            "present": True,
            "count": 3,
            "kind": "workspace_navigation",
        },
    }


def test_task_projection_uses_state_role_and_original_task_identity(tmp_path):
    root = _stage_g_workspace(tmp_path)
    task_dir = root / "task_1_search_scout"
    spec = json.loads((task_dir / "task_spec.json").read_text())
    spec.pop("role")
    spec["task_id"] = "task-scout-original"
    spec["question"] = "Find architecture evidence"
    _write_json(task_dir / "task_spec.json", spec)
    _write_json(
        task_dir / "task_state.json",
        {"status": "completed", "role": "search_scout", "task_id": "task-provider-research"},
    )

    summary = visualizer.gather_summary(root)
    detail = visualizer.gather_task_detail(root, "task_1_search_scout")

    projected = next(task for task in summary["tasks"] if task["task_id"] == "task_1_search_scout")
    assert projected["role"] == "search_scout"
    assert projected["name"] == "Find architecture evidence"
    assert detail["source_task_id"] == "task-provider-research"
    assert {attempt["provider"] for attempt in detail["attempts"]} == {
        "firecrawl",
        "jina",
        "exa",
        "tavily",
    }


def test_summary_ignores_symlinked_task_directories(tmp_path):
    root = _stage_g_workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    _write_json(outside / "task_spec.json", {"question": "must not be read"})
    _write_json(outside / "task_state.json", {"status": "completed", "role": "search_scout"})
    (root / "task_escape").symlink_to(outside, target_is_directory=True)

    summary = visualizer.gather_summary(root)

    assert all(task["task_id"] != "task_escape" for task in summary["tasks"])


def test_provider_research_count_excludes_normal_tool_and_fetch_attempts(tmp_path):
    root = _stage_g_workspace(tmp_path)
    dossier = json.loads((root / "latest_dossier.json").read_text())
    dossier["run"]["attempts"].extend(
        [
            {
                "attempt_id": "attempt-fetch",
                "execution_kind": "internal",
                "provider": "tavily",
                "capability": "web_fetch",
                "status": "success",
            },
            {
                "attempt_id": "attempt-index",
                "execution_kind": "tool",
                "provider": "firecrawl",
                "capability": "developer_search",
                "status": "success",
            },
        ]
    )
    _write_json(root / "latest_dossier.json", dossier)

    assert visualizer.gather_summary(root)["counts"]["provider_attempts"] == 4


def test_traversal_and_undeclared_paths_are_rejected(tmp_path):
    root = _stage_g_workspace(tmp_path / "workspace")

    with pytest.raises(visualizer.WorkspaceError, match="invalid task"):
        visualizer.gather_task_detail(root, "../runtime")
    with pytest.raises(visualizer.WorkspaceError, match="unknown public document"):
        visualizer.get_markdown_source(root, "../../.env")
    with pytest.raises(visualizer.WorkspaceError, match="invalid task"):
        visualizer.get_markdown_source(root, "task_knowledge", task_id="task_1/../../runtime")

    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "task_escape").symlink_to(outside, target_is_directory=True)
    with pytest.raises(visualizer.WorkspaceError, match="escapes"):
        visualizer.gather_task_detail(root, "task_escape")


def test_runtime_raw_and_result_payloads_are_not_exposed(tmp_path):
    root = _stage_g_workspace(tmp_path)
    runtime = root / "runtime"
    runtime.mkdir()
    (runtime / "trace.jsonl").write_text('{"event_id":"secret"}\n', encoding="utf-8")
    _write_json(
        root / "project_manifest.json",
        {"project_name": "Unsafe declaration", "public_trace_path": "runtime/trace.jsonl"},
    )

    with pytest.raises(visualizer.WorkspaceError, match="forbidden"):
        visualizer.gather_public_trace(root)

    task = visualizer.gather_task_detail(root, "task_1_search_scout")
    serialized = json.dumps(task)
    assert "payload" not in task
    assert "raw_document_body" not in serialized
    assert "must never be projected" not in serialized
    assert "runtime" not in visualizer.FIXED_MARKDOWN.values()
    assert ".env" not in visualizer.FIXED_MARKDOWN.values()


def test_public_trace_is_explicit_and_metadata_only(tmp_path):
    root = _stage_g_workspace(tmp_path)

    events = visualizer.gather_public_trace(root)

    assert events == [
        {
            "event_id": "event-1",
            "run_id": "run-stage-g",
            "task_id": "task_1_search_scout",
            "step_id": "step-discovery",
            "attempt_no": 1,
            "event_type": "attempt_completed",
            "timestamp": "2026-08-24T00:00:00Z",
            "artifact_refs": ["artifact-public"],
        }
    ]
    assert "chain_of_thought" not in json.dumps(events)
    assert "public_payload" not in json.dumps(events)


def test_missing_and_partial_workspace_returns_stable_empty_projection(tmp_path):
    root = tmp_path / "partial"
    root.mkdir()
    (root / "main_log.md").write_text("## Planning\n- Root frame pending\n", encoding="utf-8")

    summary = visualizer.gather_summary(root)
    activity = visualizer.gather_activity(root)

    assert summary["workspace"]["project_name"] == "Smart Search Research Run"
    assert summary["workspace"]["status"] == "partial"
    assert summary["counts"]["tasks"] == 0
    assert summary["counts"]["evidence"] == 0
    assert summary["pipeline"][0]["status"] == "waiting"
    assert summary["workspace"]["has_final_report"] is False
    assert activity["log"] == [{"source": "main_log", "stage": "Planning", "detail": "Root frame pending"}]
    assert activity["trace"] == []
    assert visualizer.get_markdown_source(root, "final_synthesis") == ""


def test_page_has_required_pipeline_landmarks_and_accessibility_contract():
    html = INDEX_PATH.read_text(encoding="utf-8")

    for text in (
        "Root-led research pipeline",
        "Research inspection desk",
        "Module detail",
        "Public activity",
        "Evidence items",
        "Final report with References",
        "audit reference register",
        "Workspace document index",
        "Hidden reasoning is never displayed",
        "prefers-reduced-motion: reduce",
    ):
        assert text in html
    assert 'role="tablist"' in html
    assert 'aria-label="Close task detail"' in html
    assert ":focus-visible" in html
    assert "https://cdn." not in html
    assert "linear-gradient" not in html
    assert "radial-gradient" not in html
