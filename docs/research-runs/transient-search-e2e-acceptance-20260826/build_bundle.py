#!/usr/bin/env python3
"""Build five citation-backed Workspaces from sanitized acceptance artifacts."""

from __future__ import annotations

import argparse
import dataclasses
import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

from smart_search.research_contracts import (
    ClaimRecord,
    ClaimSpec,
    EvidenceItem,
    EvidenceMiningTask,
    ExecutionAttempt,
    ResearchFrame,
    TraceEvent,
)
from smart_search.research_kernel import ArtifactRegistry, JsonlTraceStore
from smart_search.research_runtime import (
    ResearchDossier,
    add_root_evidence_tasks,
    create_dossier,
    update_root_decision,
    verify_final_citations,
)
from smart_search.research_workspace import ResearchWorkspace


BUNDLE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = BUNDLE_ROOT.parents[2]
SOURCE_ROOT = (
    REPO_ROOT
    / ".trellis/tasks/archive/2026-08/08-26-transient-search-e2e-acceptance"
    / "artifacts/acceptance-final"
)
SOURCE_COMMIT = "f3a30d4eab2dee4656e0fbdfc020f490f4fa8594"
OBSERVED_AT = "2026-08-26T00:00:00Z"

CASES = {
    "A1": "A1-provider-errors",
    "A2": "A2-iqa-papers",
    "A3": "A3-agent-workflows",
    "A4": "A4-deep-research-evaluation",
    "A5": "A5-apple-desktops",
}

GENERATED_NAMES = {
    "README.md",
    "checkpoints",
    "domain_methodology.md",
    "evidence",
    "export_manifest.json",
    "final_synthesis.md",
    "initial_context.md",
    "latest_dossier.json",
    "main_log.md",
    "project_manifest.json",
    "public_trace.jsonl",
    "runtime",
    "search-materials",
}

QUALITY = {
    "authority": "official_or_original",
    "directness": "direct",
    "freshness": "verified_2026-08-26",
    "methodological_fit": "fit",
    "independence": "source_specific",
    "locator_quality": "exact_excerpt",
}

SENSITIVE_KEY = re.compile(
    r"(?:^|_)(?:api_?key|access_?token|auth(?:orization)?|cookie|credential|password|secret|token)(?:$|_)",
    re.IGNORECASE,
)
LOCAL_PATH = re.compile(r"/Users/[^/\s]+(?:/[^\s\"'<>)]*)?")
PRIVATE_URL = re.compile(
    r"(?:https?|wss?)://(?:localhost|127\.0\.0\.1|10(?:\.\d{1,3}){3}|"
    r"192\.168(?:\.\d{1,3}){2}|172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})"
    r"(?::\d+)?(?:/[^\s\"'<>)]*)?",
    re.IGNORECASE,
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _sanitize_string(value: str) -> str:
    value = LOCAL_PATH.sub("[REDACTED_LOCAL_PATH]", value)
    value = PRIVATE_URL.sub("[REDACTED_PRIVATE_URL]", value)
    return value.replace("jasonliao", "[REDACTED_USER]")


def _sanitize_data(value: Any, *, key: str = "") -> Any:
    if key and SENSITIVE_KEY.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {item_key: _sanitize_data(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_data(item) for item in value]
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def _write_sanitized_json(source: Path, destination: Path) -> None:
    payload = json.loads(source.read_text(encoding="utf-8"))
    destination.write_text(
        json.dumps(_sanitize_data(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_sanitized_jsonl(source: Path, destination: Path) -> None:
    rendered: list[str] = []
    for raw_line in source.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        try:
            value = json.loads(raw_line)
        except json.JSONDecodeError:
            rendered.append(_sanitize_string(raw_line))
        else:
            rendered.append(json.dumps(_sanitize_data(value), ensure_ascii=False, sort_keys=True))
    destination.write_text("\n".join(rendered) + ("\n" if rendered else ""), encoding="utf-8")


def _contains_exact_string(value: Any, excerpt: str) -> bool:
    if isinstance(value, str):
        return excerpt in value
    if isinstance(value, list):
        return any(_contains_exact_string(item, excerpt) for item in value)
    if isinstance(value, dict):
        return any(_contains_exact_string(item, excerpt) for item in value.values())
    return False


def _arxiv_query_ids(url: str) -> set[str]:
    match = re.search(r"[?&]id_list=([^&]+)", url)
    if not match:
        return set()
    return {item for item in match.group(1).split(",") if item}


def _arxiv_abs_id(url: str) -> str:
    match = re.fullmatch(r"https://arxiv\.org/abs/([0-9.]+)", url)
    return match.group(1) if match else ""


def _validate_input(case_id: str, case_dir: Path) -> tuple[dict[str, Any], str]:
    input_dir = case_dir / "input"
    spec = _read_json(input_dir / "migration_input.json")
    draft = (input_dir / "draft_report.md").read_text(encoding="utf-8")
    draft = draft.replace("](../search-materials/", "](search-materials/")
    if spec.get("case_id") != case_id:
        raise ValueError(f"{case_id}: case_id mismatch")
    if spec.get("mode") != "standard":
        raise ValueError(f"{case_id}: migration mode must be standard")
    expected_run_id = f"run-transient-{case_id.lower()}-20260826"
    if spec.get("run_id") != expected_run_id:
        raise ValueError(f"{case_id}: run_id must be {expected_run_id}")
    if re.search(r"^#{1,6}\s+References\s*$", draft, flags=re.IGNORECASE | re.MULTILINE):
        raise ValueError(f"{case_id}: draft must not contain a References heading")

    claims = spec.get("claims")
    sources = spec.get("sources")
    if not isinstance(claims, list) or not claims:
        raise ValueError(f"{case_id}: claims must be a non-empty list")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"{case_id}: sources must be a non-empty list")

    claim_ids = [str(item.get("claim_spec_id") or "") for item in claims]
    if any(not item for item in claim_ids) or len(claim_ids) != len(set(claim_ids)):
        raise ValueError(f"{case_id}: claim_spec_id values must be unique and non-empty")

    source_result = _read_json(SOURCE_ROOT / case_id / "output/run-result.json")
    verified_sources = {
        str(item["url"]): item
        for item in source_result.get("sources", [])
        if item.get("evidence_status") == "verified"
    }
    supplied_urls = {str(item.get("url") or "") for item in sources}
    accepted_query_ids = set().union(*(_arxiv_query_ids(url) for url in verified_sources))
    supplied_query_ids = set().union(*(_arxiv_query_ids(url) for url in supplied_urls))
    missing = []
    for url in verified_sources:
        query_ids = _arxiv_query_ids(url)
        if url not in supplied_urls and not (
            (query_ids and query_ids.issubset({_arxiv_abs_id(item) for item in supplied_urls}))
            or (_arxiv_abs_id(url) and _arxiv_abs_id(url) in supplied_query_ids)
        ):
            missing.append(url)
    extra = sorted(
        url
        for url in supplied_urls
        if url not in verified_sources
        and not url.startswith("local://commands/")
        and _arxiv_abs_id(url) not in accepted_query_ids
    )
    if missing or extra:
        raise ValueError(f"{case_id}: source URL set mismatch; missing={missing}, extra={extra}")

    source_ids: set[str] = set()
    citation_ids: set[str] = set()
    command_root = SOURCE_ROOT / case_id / "output/commands"
    for source in sources:
        source_id = str(source.get("source_id") or "")
        citation_id = str(source.get("citation_id") or "")
        claim_id = str(source.get("claim_spec_id") or "")
        excerpt = str(source.get("excerpt") or "")
        command_file = str(source.get("command_file") or "")
        if not source_id or source_id in source_ids:
            raise ValueError(f"{case_id}: source_id values must be unique and non-empty")
        if not citation_id or citation_id in citation_ids:
            raise ValueError(f"{case_id}: citation_id values must be unique and non-empty")
        if claim_id not in claim_ids:
            raise ValueError(f"{case_id}: source {source_id} references unknown claim {claim_id}")
        if not excerpt.strip():
            raise ValueError(f"{case_id}: source {source_id} excerpt is empty")
        command_path = Path(command_file)
        if (
            command_path.suffix != ".json"
            or command_path.is_absolute()
            or ".." in command_path.parts
            or command_path.parts[:-1] not in {(), ("commands",)}
        ):
            raise ValueError(f"{case_id}: unsafe command_file {command_file!r}")
        command_payload = _read_json(command_root / command_path.name)
        if not _contains_exact_string(command_payload, excerpt):
            raise ValueError(
                f"{case_id}: source {source_id} excerpt is absent from {command_file}"
            )
        source_url = str(source["url"])
        saved = verified_sources.get(source_url)
        title = str(source.get("title") or "")
        if saved is not None and title != str(saved.get("title") or ""):
            raise ValueError(f"{case_id}: source title differs from saved run-result for {source_id}")
        if source_url.startswith("local://"):
            if source_url != f"local://commands/{command_path.name}":
                raise ValueError(f"{case_id}: local source URL does not match command file for {source_id}")
        elif saved is None and not _contains_exact_string(command_payload, title):
            raise ValueError(f"{case_id}: derived source title is absent from {command_file}")
        marker = f"[cite:{citation_id}]"
        if marker not in draft:
            raise ValueError(f"{case_id}: draft does not use {marker}")
        source_ids.add(source_id)
        citation_ids.add(citation_id)

    draft_markers = set(re.findall(r"\[cite:([A-Za-z0-9_.:-]+)\]", draft))
    if draft_markers != citation_ids:
        raise ValueError(
            f"{case_id}: draft/source citation mismatch; draft={sorted(draft_markers)}, "
            f"sources={sorted(citation_ids)}"
        )
    if set(claim_ids) != {str(item["claim_spec_id"]) for item in sources}:
        raise ValueError(f"{case_id}: every ClaimSpec must have at least one cited source")
    return spec, draft


def _build_dossier(
    spec: dict[str, Any],
    *,
    runtime_root: Path,
) -> tuple[ResearchDossier, list[dict[str, str]]]:
    run_id = str(spec["run_id"])
    claims = [
        ClaimSpec(
            run_id=run_id,
            claim_spec_id=str(item["claim_spec_id"]),
            statement=str(item["statement"]),
        )
        for item in spec["claims"]
    ]
    dossier = create_dossier(
        frame=ResearchFrame(
            run_id=run_id,
            question=str(spec["question"]),
            mode="standard",
            scope={
                "source": "sanitized transient-search acceptance evidence",
                "migration_commit": SOURCE_COMMIT,
            },
            user_constraints={
                "no_live_search": True,
                "direct_sources_only": True,
                "preserve_original_acceptance_archive": True,
            },
            permissions=["public_web_saved_evidence"],
        ),
        claims=claims,
        search_tasks=[],
        capability_snapshot={
            "evidence_migration": {
                "providers": [
                    {
                        "name": "saved-acceptance-artifacts",
                        "configured": True,
                        "reachable": True,
                        "entitled": True,
                    }
                ],
                "tools": ["document"],
            }
        },
        capability_observed_at=OBSERVED_AT,
        artifact_root=runtime_root,
    )
    registry = ArtifactRegistry(runtime_root, run_id)
    tasks: list[EvidenceMiningTask] = []
    attempts: list[ExecutionAttempt] = []
    evidence_items: list[EvidenceItem] = []
    citations: list[dict[str, str]] = []
    artifacts = []

    for index, source in enumerate(spec["sources"], start=1):
        task_id = f"task-source-{index:02d}"
        step_id = f"step-source-{index:02d}"
        excerpt = str(source["excerpt"])
        artifact = registry.register_snapshot(
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
            attempt_no=1,
            content=excerpt,
            media_type="text/plain",
            canonical_url=str(source["url"]),
            metadata={
                "bibliographic": {
                    "title": str(source["title"]),
                    "accessed_at": "2026-08-26",
                },
                "migration": {
                    "case_id": str(spec["case_id"]),
                    "command_file": str(source["command_file"]),
                    "locator_label": str(source["locator_label"]),
                    "source_commit": SOURCE_COMMIT,
                    "snapshot_scope": "verified evidence excerpt",
                },
            },
            created_at=OBSERVED_AT,
        )
        artifacts.append((source, artifact, task_id, step_id))
        task = EvidenceMiningTask(
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
            claim_spec_id=str(source["claim_spec_id"]),
            artifact_ids=[artifact.artifact_id],
            artifact_refs=[artifact.artifact_id],
        )
        tasks.append(task)
        attempts.append(
            ExecutionAttempt(
                attempt_id=f"attempt-source-{index:02d}",
                run_id=run_id,
                task_id=task_id,
                step_id=step_id,
                attempt_no=1,
                execution_kind="project_agent",
                capability="evidence_migration",
                provider="saved-acceptance-artifacts",
                status="success",
                completed_at=OBSERVED_AT,
                request_summary={
                    "command_file": str(source["command_file"]),
                    "locator_label": str(source["locator_label"]),
                },
                artifact_refs=[artifact.artifact_id],
            )
        )
        evidence_id = f"evidence-source-{index:02d}"
        evidence_items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                run_id=run_id,
                task_id=task_id,
                step_id=step_id,
                attempt_no=1,
                claim_spec_id=str(source["claim_spec_id"]),
                source_id=str(source["source_id"]),
                canonical_url=str(source["url"]),
                artifact_id=artifact.artifact_id,
                snapshot_id=artifact.snapshot_id,
                retrieved_at=OBSERVED_AT,
                content_type="text/plain",
                locator={"type": "section", "section": str(source["locator_label"])},
                text=excerpt,
                stance="support",
                quality=dict(QUALITY),
                artifact_refs=[artifact.artifact_id],
            )
        )
        citations.append(
            {
                "citation_id": str(source["citation_id"]),
                "claim_record_id": f"record-{source['claim_spec_id']}",
                "evidence_id": evidence_id,
            }
        )

    dossier = add_root_evidence_tasks(dossier, tasks)
    records: list[ClaimRecord] = []
    for claim in claims:
        linked = [item for item in evidence_items if item.claim_spec_id == claim.claim_spec_id]
        citation_map = {
            str(source["citation_id"]): evidence.evidence_id
            for source, evidence in zip(spec["sources"], evidence_items, strict=True)
            if str(source["claim_spec_id"]) == claim.claim_spec_id
        }
        records.append(
            ClaimRecord(
                claim_record_id=f"record-{claim.claim_spec_id}",
                run_id=run_id,
                claim_spec_id=claim.claim_spec_id,
                statement=claim.statement,
                status="supported",
                support_evidence_ids=[item.evidence_id for item in linked],
                citation_map=citation_map,
            )
        )

    dossier = dataclasses.replace(
        dossier,
        run=dataclasses.replace(dossier.run, attempts=attempts),
        evidence_items=evidence_items,
        claim_records=records,
    )
    dossier = update_root_decision(
        dossier,
        stop_reason="Existing accepted evidence was migrated and all displayed citations were verified.",
    )

    trace = JsonlTraceStore(runtime_root, run_id)
    parent = trace.events()[-1].event_id
    for index, (_, artifact, task_id, step_id) in enumerate(artifacts, start=1):
        event = TraceEvent(
            event_id=f"event-source-{index:02d}",
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
            attempt_no=1,
            event_type="evidence_migrated",
            timestamp=OBSERVED_AT,
            parent_event_id=parent,
            artifact_refs=[artifact.artifact_id],
            public_payload={"case_id": str(spec["case_id"]), "source_number": index},
        )
        trace.append(event)
        parent = event.event_id
    return dossier, citations


def _copy_search_materials(case_id: str, destination: Path) -> int:
    source = SOURCE_ROOT / case_id
    destination.mkdir(parents=True, exist_ok=True)
    command_destination = destination / "commands"
    command_destination.mkdir()
    for source_path in sorted((source / "output/commands").glob("*.json")):
        _write_sanitized_json(source_path, command_destination / source_path.name)
    for source_path, name in (
        (source / "invocations.jsonl", "invocations.jsonl"),
        (source / "gateway-events.jsonl", "gateway-events.jsonl"),
        (source / "output/run-result.json", "run-result.json"),
        (source / "verdict.json", "verdict.json"),
    ):
        target = destination / name
        if source_path.suffix == ".jsonl":
            _write_sanitized_jsonl(source_path, target)
        else:
            _write_sanitized_json(source_path, target)
    return len(list(command_destination.glob("*.json")))


def _case_readme(spec: dict[str, Any]) -> str:
    return f"""# {spec['case_id']} Citation-backed Research Workspace

This directory is the durable Workspace for **{spec['question']}**. It was
generated from the accepted, sanitized local evidence using Smart Search commit
`f3a30d4`; no live provider call or diagnostic probe was made during migration.

## Entry points

- [Final report](final_synthesis.md)
- [Citation verification](evidence/citation_verification.json)
- [Reference register](evidence/reference_register.json)
- [Latest Research Dossier](latest_dossier.json)
- [Public Trace](public_trace.jsonl)
- [Artifact registry](runtime/{spec['run_id']}/artifacts.jsonl)
- [Sanitized search materials](search-materials/)
- [Migration input](input/migration_input.json)

The reader-facing report contains no internal audit IDs. Use the reference
register and citation verification when auditing ClaimRecord, EvidenceItem,
artifact snapshot, locator, attempt, and Trace links.
"""


def _install_case(staged_workspace: Path, case_dir: Path) -> None:
    existing = {item.name for item in case_dir.iterdir()} if case_dir.exists() else set()
    generated = GENERATED_NAMES | {name for name in existing if name.startswith("task_")}
    unknown = existing - generated - {"input"}
    if unknown:
        raise ValueError(f"refusing to replace unknown case paths in {case_dir}: {sorted(unknown)}")
    case_dir.mkdir(parents=True, exist_ok=True)
    for name in generated:
        target = case_dir / name
        if target.is_dir():
            shutil.rmtree(target)
        elif target.exists():
            target.unlink()
    for source in staged_workspace.iterdir():
        target = case_dir / source.name
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)


def build_case(case_id: str, directory_name: str) -> dict[str, Any]:
    case_dir = BUNDLE_ROOT / directory_name
    spec, draft = _validate_input(case_id, case_dir)
    with tempfile.TemporaryDirectory(prefix=f"smart-search-{case_id.lower()}-") as temp:
        staging_root = Path(temp)
        workspace_root = staging_root / "workspace"
        runtime_root = workspace_root / "runtime"
        dossier, citations = _build_dossier(spec, runtime_root=runtime_root)
        result = verify_final_citations(
            dossier,
            citations=citations,
            artifact_root=runtime_root,
            draft_report=draft,
        )
        verification = {
            key: value
            for key, value in result.items()
            if key not in {"rendered_report", "reference_register"}
        }
        manifest = ResearchWorkspace(
            workspace_root,
            artifact_root=runtime_root,
        ).materialize(
            dossier,
            checkpoint_labels=["migrated-final"],
            final_synthesis=str(result["rendered_report"]),
            citation_verification=verification,
            reference_register=result["reference_register"],
        )
        command_count = _copy_search_materials(
            case_id,
            workspace_root / "search-materials",
        )
        (workspace_root / "README.md").write_text(_case_readme(spec), encoding="utf-8")
        case_export = {
            "schema_version": "1",
            "case_id": case_id,
            "run_id": str(spec["run_id"]),
            "source_commit": SOURCE_COMMIT,
            "source_archive": str(
                SOURCE_ROOT.relative_to(REPO_ROOT) / case_id
            ),
            "included": [
                "citation-backed Research Workspace projections",
                "registered evidence excerpt snapshots and artifact registry",
                "public Trace",
                "sanitized command JSON and acceptance records",
            ],
            "excluded": [
                "duplicate CLI stdout and stderr captures",
                "superseded failed attempts",
                "credentials, private configuration, and hidden test manifests",
            ],
            "counts": {
                "claims": len(spec["claims"]),
                "cited_sources": len(spec["sources"]),
                "citations": int(result["citation_count"]),
                "displayed_references": int(result["reference_register"]["reference_count"]),
                "search_commands": command_count,
            },
            "workspace_manifest": manifest,
        }
        (workspace_root / "export_manifest.json").write_text(
            json.dumps(case_export, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        _install_case(workspace_root, case_dir)
    return case_export


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=[*CASES, "all"], default="all")
    args = parser.parse_args()
    selected = CASES if args.case == "all" else {args.case: CASES[args.case]}
    results = [build_case(case_id, name) for case_id, name in selected.items()]
    if args.case == "all":
        shutil.copy2(
            SOURCE_ROOT / "acceptance-summary.md",
            BUNDLE_ROOT / "source-acceptance-summary.md",
        )
        bundle_export = {
            "schema_version": "1",
            "source_commit": SOURCE_COMMIT,
            "source_archive": str(SOURCE_ROOT.relative_to(REPO_ROOT)),
            "cases": {
                item["case_id"]: {
                    "run_id": item["run_id"],
                    "counts": item["counts"],
                }
                for item in results
            },
            "doctor_probes_replayed": 0,
            "live_searches_performed_during_migration": 0,
        }
        (BUNDLE_ROOT / "export_manifest.json").write_text(
            json.dumps(bundle_export, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps({"ok": True, "cases": results}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
