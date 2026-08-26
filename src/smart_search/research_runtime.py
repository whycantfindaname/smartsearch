"""Caller-held orchestration helpers for Root-led multi-source research.

This module is deliberately a deterministic kernel API rather than a hidden
workflow engine.  Root supplies the semantic plan and later decisions; each
operation validates and returns a complete JSON dossier plus run-local refs.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import service
from .config import Config
from .delegation import import_anysearch_result, import_delegate_result
from .document_sidecar import (
    SIDECAR_MAX_ARTIFACT_BYTES,
    SidecarBridgeError,
    run_document_operations,
)
from .research_contracts import (
    SCHEMA_VERSION,
    ArtifactRecord,
    CandidateCard,
    ClaimRecord,
    ClaimSpec,
    ContractValidationError,
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
    TraceEvent,
    stable_id,
)
from .research_kernel import (
    ArtifactRegistry,
    JsonlTraceStore,
    PlanCompiler,
    build_candidate_cards,
    canonicalize_url,
    derive_claim_record,
    normalize_candidates,
    validate_evidence_locator,
    validate_citation_backtrace,
)


DOSSIER_FIELDS = frozenset(
    {
        "schema_version",
        "run",
        "search_tasks",
        "evidence_mining_tasks",
        "delegate_requests",
        "delegate_results",
        "candidates",
        "candidate_cards",
        "key_source_proposals",
        "evidence_items",
        "claim_records",
    }
)
_URL_RE = re.compile(r"https?://[^\s<>()\[\]{}\"']+")
_CITATION_MARKER_RE = re.compile(
    r"\[cite:([A-Za-z0-9][A-Za-z0-9._:-]{0,127})\]"
)
_REFERENCES_HEADING_RE = re.compile(r"(?im)^#{1,6}\s+references\s*$")
_PROVIDER_STATUS_MAP = {
    "not_configured": "missing_key",
    "unreachable": "unavailable",
    "entitlement_denied": "entitlement_failure",
    "succeeded": "success",
    "success": "success",
    "ok": "success",
    "empty": "partial",
    "error": "failed",
    "skipped": "unavailable",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContractValidationError(f"{label} must be a list")
    return value


@dataclass
class ResearchDossier:
    """Compact caller-owned state; raw bytes and Trace remain run-local."""

    run: ResearchRun
    search_tasks: list[SearchTask] = field(default_factory=list)
    evidence_mining_tasks: list[EvidenceMiningTask] = field(default_factory=list)
    delegate_requests: list[DelegateRequest] = field(default_factory=list)
    delegate_results: list[DelegateResult] = field(default_factory=list)
    candidates: list[DiscoveryCandidate] = field(default_factory=list)
    candidate_cards: list[CandidateCard] = field(default_factory=list)
    key_source_proposals: list[KeySourceProposal] = field(default_factory=list)
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    claim_records: list[ClaimRecord] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractValidationError(f"unsupported dossier schema_version: {self.schema_version}")
        run_id = self.run.run_id
        collections = (
            self.search_tasks,
            self.evidence_mining_tasks,
            self.delegate_requests,
            self.delegate_results,
            self.candidates,
            self.candidate_cards,
            self.key_source_proposals,
            self.evidence_items,
            self.claim_records,
        )
        for collection in collections:
            for item in collection:
                if getattr(item, "run_id", None) != run_id:
                    raise ContractValidationError("dossier contains an object from another ResearchRun")
        task_ids = [item.task_id for item in self.search_tasks + self.evidence_mining_tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ContractValidationError("dossier contains duplicate task_id")
        if sorted(self.run.task_refs) != sorted(task_ids):
            raise ContractValidationError("ResearchRun.task_refs do not match dossier tasks")
        request_ids = [item.request_id for item in self.delegate_requests]
        if len(request_ids) != len(set(request_ids)):
            raise ContractValidationError("dossier contains duplicate DelegateRequest")
        known_requests = set(request_ids)
        if any(item.request_id not in known_requests for item in self.delegate_results):
            raise ContractValidationError("DelegateResult has no originating request in dossier")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run": self.run.to_dict(),
            "search_tasks": [item.to_dict() for item in self.search_tasks],
            "evidence_mining_tasks": [item.to_dict() for item in self.evidence_mining_tasks],
            "delegate_requests": [item.to_dict() for item in self.delegate_requests],
            "delegate_results": [item.to_dict() for item in self.delegate_results],
            "candidates": [item.to_dict() for item in self.candidates],
            "candidate_cards": [item.to_dict() for item in self.candidate_cards],
            "key_source_proposals": [item.to_dict() for item in self.key_source_proposals],
            "evidence_items": [item.to_dict() for item in self.evidence_items],
            "claim_records": [item.to_dict() for item in self.claim_records],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResearchDossier":
        if not isinstance(value, Mapping):
            raise ContractValidationError("ResearchDossier must be an object")
        unknown = sorted(set(value) - DOSSIER_FIELDS)
        if unknown:
            raise ContractValidationError(f"ResearchDossier has unknown fields: {', '.join(unknown)}")
        if value.get("schema_version") != SCHEMA_VERSION:
            raise ContractValidationError("ResearchDossier.schema_version is required and must be 1")

        def parse_many(name: str, contract: Any) -> list[Any]:
            return [contract.from_dict(item) for item in _require_list(value.get(name, []), name)]

        return cls(
            schema_version=SCHEMA_VERSION,
            run=ResearchRun.from_dict(value.get("run", {})),
            search_tasks=parse_many("search_tasks", SearchTask),
            evidence_mining_tasks=parse_many("evidence_mining_tasks", EvidenceMiningTask),
            delegate_requests=parse_many("delegate_requests", DelegateRequest),
            delegate_results=parse_many("delegate_results", DelegateResult),
            candidates=parse_many("candidates", DiscoveryCandidate),
            candidate_cards=parse_many("candidate_cards", CandidateCard),
            key_source_proposals=parse_many("key_source_proposals", KeySourceProposal),
            evidence_items=parse_many("evidence_items", EvidenceItem),
            claim_records=parse_many("claim_records", ClaimRecord),
        )


def _trace_event(
    trace: JsonlTraceStore,
    *,
    run_id: str,
    task_id: str,
    step_id: str,
    attempt_no: int,
    event_type: str,
    artifact_refs: Sequence[str] = (),
    public_payload: Mapping[str, Any] | None = None,
) -> TraceEvent:
    existing = trace.events()
    parent = existing[-1].event_id if existing else ""
    event = TraceEvent(
        event_id=stable_id(
            "event",
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
            attempt_no=attempt_no,
            identity={"sequence": len(existing) + 1, "event_type": event_type},
        ),
        run_id=run_id,
        task_id=task_id,
        step_id=step_id,
        attempt_no=attempt_no,
        event_type=event_type,
        timestamp=_utc_now(),
        parent_event_id=parent,
        artifact_refs=list(artifact_refs),
        public_payload=dict(public_payload or {}),
    )
    return trace.append(event)


def create_dossier(
    *,
    frame: ResearchFrame,
    claims: Sequence[ClaimSpec],
    search_tasks: Sequence[SearchTask],
    capability_snapshot: Mapping[str, Any],
    artifact_root: str | Path,
    capability_observed_at: str | None = None,
) -> ResearchDossier:
    """Compile a Root-authored plan without inventing tasks or decisions."""

    compiled = PlanCompiler().compile(frame, claims, search_tasks, capability_snapshot)
    registry = ArtifactRegistry(artifact_root, frame.run_id)
    trace = JsonlTraceStore(artifact_root, frame.run_id)
    run = ResearchRun(
        run_id=frame.run_id,
        frame=frame,
        claims=list(claims),
        task_refs=[item.task_id for item in search_tasks],
        capability_snapshot=dict(capability_snapshot),
        capability_observed_at=capability_observed_at or _utc_now(),
        delegate_refs=[item.request_id for item in compiled.delegate_requests],
        trace_ref=str(trace.path.relative_to(registry.run_dir)),
        artifact_index_ref=str(registry.index_path.relative_to(registry.run_dir)),
    )
    _trace_event(
        trace,
        run_id=frame.run_id,
        task_id="root",
        step_id="plan",
        attempt_no=1,
        event_type="plan_compiled",
        public_payload={
            "mode": frame.mode,
            "claim_count": len(claims),
            "task_count": len(search_tasks),
            "internal_step_count": len(compiled.internal_steps),
            "delegate_count": len(compiled.delegate_requests),
        },
    )
    return ResearchDossier(
        run=run,
        search_tasks=list(search_tasks),
        delegate_requests=list(compiled.delegate_requests),
    )


def _connection_state(value: Any) -> tuple[bool, bool]:
    status = str((value or {}).get("status") if isinstance(value, Mapping) else value or "").lower()
    if status == "ok":
        return True, True
    if status in {"auth_error", "config_error", "rate_limited", "entitlement_denied"}:
        return True, False
    return False, False


def capability_snapshot_from_doctor(doctor: Mapping[str, Any]) -> dict[str, Any]:
    """Translate a live doctor observation into PlanCompiler facts."""

    status = doctor.get("capability_status") if isinstance(doctor.get("capability_status"), Mapping) else {}
    main_tests = doctor.get("main_search_connection_tests") if isinstance(doctor.get("main_search_connection_tests"), Mapping) else {}
    test_names = {
        "exa": "exa_connection_test",
        "tavily": "tavily_connection_test",
        "jina": "jina_connection_test",
        "firecrawl": "firecrawl_connection_test",
        "zhipu": "zhipu_connection_test",
        "zhipu-mcp": "zhipu_mcp_connection_test",
        "context7": "context7_connection_test",
    }

    def providers(capability: str) -> list[dict[str, Any]]:
        configured = (status.get(capability) or {}).get("configured", []) if isinstance(status, Mapping) else []
        values: list[dict[str, Any]] = []
        for name in configured if isinstance(configured, list) else []:
            check = main_tests.get(name) if capability == "main_search" else doctor.get(test_names.get(name, ""), {})
            reachable, entitled = _connection_state(check)
            values.append(
                {
                    "name": name,
                    "configured": True,
                    "reachable": reachable,
                    "entitled": entitled,
                    "observed_status": str(check.get("status") or "unknown") if isinstance(check, Mapping) else "unknown",
                }
            )
        return values

    observed_at = _utc_now()
    snapshot = {
        "main_search": {"providers": providers("main_search"), "tools": ["search"], "observed_at": observed_at},
        "web_search": {"providers": providers("web_search"), "tools": ["search", "zhipu-search"], "observed_at": observed_at},
        "docs_search": {"providers": providers("docs_search"), "tools": ["exa-search", "context7-library", "context7-docs"], "observed_at": observed_at},
        "web_fetch": {"providers": providers("web_fetch"), "tools": ["fetch"], "observed_at": observed_at},
        "provider_research": {
            "providers": providers("provider_research"),
            "tools": ["provider-research"],
            "observed_at": observed_at,
        },
        "crawl": {
            "providers": [item for item in providers("web_search") if item["name"] in {"firecrawl", "tavily"}],
            "tools": ["crawl"],
            "observed_at": observed_at,
        },
        "extract": {
            "providers": [item for item in providers("web_fetch") if item["name"] in {"firecrawl", "tavily"}],
            "tools": ["extract", "batch"],
            "observed_at": observed_at,
        },
        "deep_search": {
            "providers": [item for item in providers("docs_search") if item["name"] == "exa"],
            "tools": ["deep-search"],
            "observed_at": observed_at,
        },
        "jina_search": {
            "providers": [item for item in providers("web_fetch") if item["name"] == "jina"],
            "tools": ["jina-search", "rerank"],
            "observed_at": observed_at,
        },
        "academic_search": {
            "providers": providers("academic_search"),
            "tools": ["academic-search"],
            "observed_at": observed_at,
        },
        "academic_read": {
            "providers": providers("academic_read"),
            "tools": ["academic-read"],
            "observed_at": observed_at,
        },
        "academic_related": {
            "providers": providers("academic_related"),
            "tools": ["academic-related"],
            "observed_at": observed_at,
        },
        "developer_search": {
            "providers": providers("developer_search"),
            "tools": ["developer-search"],
            "observed_at": observed_at,
        },
    }
    return snapshot


async def observe_live_capabilities() -> dict[str, Any]:
    observation = await service.doctor()
    return {
        "ok": True,
        "observed_at": _utc_now(),
        "snapshot": capability_snapshot_from_doctor(observation),
        "doctor_ok": bool(observation.get("ok")),
        "minimum_profile_ok": bool(observation.get("minimum_profile_ok")),
    }


def _task_by_id(dossier: ResearchDossier, task_id: str) -> SearchTask | EvidenceMiningTask:
    for task in dossier.search_tasks + dossier.evidence_mining_tasks:
        if task.task_id == task_id:
            return task
    raise ContractValidationError(f"unknown SearchTask: {task_id}")


def _first_url(task: SearchTask) -> str:
    explicit = task.user_constraints.get("url")
    if isinstance(explicit, str) and explicit.startswith(("http://", "https://")):
        return explicit
    match = _URL_RE.search(task.question)
    if match:
        return match.group(0).rstrip(".,;:!?")
    raise ContractValidationError(f"{task.task_id} requires user_constraints.url or a URL in question")


async def _execute_tool(step: Any, task: SearchTask) -> dict[str, Any]:
    if step.tool == "search":
        return await service.search(
            task.question,
            validation=str(task.user_constraints.get("validation") or "balanced"),
            extra_sources=int(task.user_constraints.get("extra_sources") or 0),
            timeout_seconds=float(task.user_constraints.get("timeout_seconds") or 120),
        )
    if step.tool == "exa-search":
        return await service.exa_search(
            task.question,
            num_results=int(task.user_constraints.get("num_results") or 10),
            search_type=str(task.user_constraints.get("search_type") or "neural"),
            include_text=bool(task.user_constraints.get("include_text", False)),
            include_highlights=bool(task.user_constraints.get("include_highlights", True)),
            category=str(task.user_constraints.get("category") or ""),
        )
    if step.tool == "zhipu-search":
        return await service.zhipu_search(
            task.question,
            count=int(task.user_constraints.get("count") or 10),
        )
    if step.tool == "context7-library":
        return await service.context7_library(task.question, task.question)
    if step.tool == "context7-docs":
        library_id = str(task.user_constraints.get("library_id") or "")
        if not library_id:
            raise ContractValidationError("context7-docs requires user_constraints.library_id")
        return await service.context7_docs(library_id, task.question)
    if step.tool == "fetch":
        return await service.fetch(_first_url(task))
    if step.tool == "map":
        return await service.map_site(
            _first_url(task),
            instructions=str(task.user_constraints.get("instructions") or ""),
            max_depth=int(task.user_constraints.get("max_depth") or 1),
            max_breadth=int(task.user_constraints.get("max_breadth") or 20),
            limit=int(task.user_constraints.get("limit") or 50),
        )
    if step.tool == "provider-research":
        return await service.run_provider_research_agents(
            task.question,
            timeout_seconds=float(task.user_constraints.get("timeout_seconds") or 120),
            run_id=task.run_id,
            task_id=task.task_id,
            step_id=task.step_id,
        )
    if step.tool in {
        "crawl",
        "extract",
        "batch",
        "deep-search",
        "jina-search",
        "rerank",
        "academic-search",
        "academic-read",
        "academic-related",
        "developer-search",
    }:
        explicit_urls = task.user_constraints.get("urls")
        if isinstance(explicit_urls, str):
            urls = [explicit_urls]
        elif isinstance(explicit_urls, list):
            urls = [str(item) for item in explicit_urls]
        else:
            urls = []
        if not urls and step.tool in {"crawl", "extract", "batch"}:
            urls = [_first_url(task)]
        arguments: dict[str, Any] = {
            "query": task.question,
            "url": urls[0] if urls else "",
            "urls": urls,
            "documents": task.user_constraints.get("documents", []),
            "model": task.user_constraints.get("model", "jina-reranker-v3.5"),
            "search_type": task.user_constraints.get("search_type", "deep"),
            "paper_id": task.user_constraints.get("paper_id", ""),
            "intent": task.user_constraints.get("intent", task.question),
            "options": task.user_constraints.get("options", {}),
        }
        return await service.run_extended_provider_capability(
            step.tool,
            arguments,
            providers=list(step.providers),
            timeout_seconds=float(task.user_constraints.get("timeout_seconds") or 120),
        )
    raise ContractValidationError(f"runtime tool is not connected: {step.tool}")


def _result_sources(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    sources: list[Any] = []

    def collect(value: Any, *, depth: int = 0) -> None:
        if depth > 3:
            return
        if isinstance(value, list):
            sources.extend(value)
            return
        if not isinstance(value, Mapping):
            return
        for key in ("sources", "results", "candidates", "data"):
            nested = value.get(key)
            if isinstance(nested, list):
                sources.extend(nested)
            elif isinstance(nested, Mapping):
                collect(nested, depth=depth + 1)
        for key in ("result", "terminal", "output", "response", "paper"):
            nested = value.get(key)
            if key == "paper" and isinstance(nested, Mapping):
                sources.append(nested)
            elif isinstance(nested, (Mapping, list)):
                collect(nested, depth=depth + 1)

    collect(result)
    normalized: list[dict[str, Any]] = []
    for rank, source in enumerate(sources):
        if isinstance(source, str):
            url, title, summary = source, source, ""
            published_at = ""
        elif isinstance(source, Mapping):
            url = str(source.get("url") or source.get("link") or "")
            primary_id = str(source.get("primaryId") or source.get("primary_id") or "")
            identifiers = source.get("ids") if isinstance(source.get("ids"), Mapping) else {}
            if not url and primary_id.startswith("arxiv:"):
                url = f"https://arxiv.org/abs/{primary_id.removeprefix('arxiv:')}"
            elif not url and primary_id.startswith("doi:"):
                url = f"https://doi.org/{primary_id.removeprefix('doi:')}"
            elif not url and primary_id.startswith("pmid:"):
                url = f"https://pubmed.ncbi.nlm.nih.gov/{primary_id.removeprefix('pmid:')}/"
            elif not url and isinstance(identifiers.get("arxiv"), list) and identifiers["arxiv"]:
                url = f"https://arxiv.org/abs/{identifiers['arxiv'][0]}"
            elif not url and isinstance(identifiers.get("doi"), list) and identifiers["doi"]:
                url = f"https://doi.org/{identifiers['doi'][0]}"
            title = str(source.get("title") or source.get("name") or url)
            passages = source.get("passages")
            passage_text = "\n\n".join(
                str(item.get("text") or "")
                for item in passages
                if isinstance(item, Mapping) and item.get("text")
            ) if isinstance(passages, list) else ""
            summary = str(
                source.get("summary")
                or source.get("description")
                or source.get("snippet")
                or source.get("content")
                or source.get("text")
                or passage_text
                or ""
            )
            published_at = str(source.get("published_at") or source.get("publishedDate") or "")
        else:
            continue
        if url.startswith(("http://", "https://")):
            normalized.append(
                {
                    "title": title or url,
                    "canonical_url": url,
                    "summary": summary,
                    "published_at": published_at,
                    "raw_rank": rank,
                    "stable_entity_id": str(
                        source.get("paperId")
                        or source.get("paper_id")
                        or source.get("id")
                        or primary_id
                        or ""
                    ),
                }
            )
    return normalized


def _public_attempt(
    *,
    task: SearchTask | EvidenceMiningTask,
    capability: str,
    provider: str,
    status: str,
    attempt_no: int,
    artifact_refs: Sequence[str],
    started_at: str,
    completed_at: str,
    error: str = "",
    usage: Mapping[str, Any] | None = None,
    external_state: Mapping[str, Any] | None = None,
    execution_kind: str = "internal",
    tool: str = "",
) -> ExecutionAttempt:
    public_status = _PROVIDER_STATUS_MAP.get(status, status)
    if public_status not in {
        "pending", "running", "success", "partial", "failed", "timeout", "unavailable",
        "missing_key", "entitlement_failure", "cancelled", "degraded",
    }:
        public_status = "failed"
    return ExecutionAttempt(
        attempt_id=stable_id(
            "attempt",
            run_id=task.run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=attempt_no,
            identity={"capability": capability, "provider": provider, "tool": tool},
        ),
        run_id=task.run_id,
        task_id=task.task_id,
        step_id=task.step_id,
        attempt_no=attempt_no,
        execution_kind=execution_kind,
        capability=capability,
        provider=re.sub(r"[^A-Za-z0-9._:-]", "-", provider.strip().lower()) if provider else "",
        status=public_status,
        external_state=dict(external_state or {}),
        started_at=started_at,
        completed_at=completed_at,
        request_summary={"question_length": len(getattr(task, "question", "")), "tool": tool},
        usage=dict(usage or {}),
        retry_safe=public_status in {"failed", "timeout", "unavailable"},
        error=error,
        artifact_refs=list(artifact_refs),
    )


def _register_json_result(
    registry: ArtifactRegistry,
    *,
    task: SearchTask,
    attempt_no: int,
    result: Mapping[str, Any],
    artifact_kind: str,
) -> ArtifactRecord:
    return registry.register_snapshot(
        run_id=task.run_id,
        task_id=task.task_id,
        step_id=task.step_id,
        attempt_no=attempt_no,
        content=json.dumps(result, ensure_ascii=False, sort_keys=True),
        media_type="application/json",
        canonical_url="",
        artifact_kind=artifact_kind,
        metadata={"untrusted_content": True},
    )


async def execute_internal_steps(
    dossier: ResearchDossier,
    *,
    artifact_root: str | Path,
) -> ResearchDossier:
    """Execute only Root-authorized internal steps and return updated facts."""

    compiled = PlanCompiler().compile(
        dossier.run.frame,
        dossier.run.claims,
        dossier.search_tasks,
        dossier.run.capability_snapshot,
    )
    registry = ArtifactRegistry(artifact_root, dossier.run.run_id)
    trace = JsonlTraceStore(artifact_root, dossier.run.run_id)
    attempts = list(dossier.run.attempts)
    candidates = list(dossier.candidates)

    for step in compiled.internal_steps:
        task = _task_by_id(dossier, step.task_id)
        if any(
            item.task_id == task.task_id
            and item.step_id == task.step_id
            and item.capability == step.capability
            and item.request_summary.get("tool") == step.tool
            for item in attempts
        ):
            continue
        started = _utc_now()
        attempt_no = 1
        try:
            result = await _execute_tool(step, task)
        except Exception as exc:
            completed = _utc_now()
            attempt = _public_attempt(
                task=task,
                capability=step.capability,
                provider="smart-search",
                status="failed",
                attempt_no=attempt_no,
                artifact_refs=[],
                started_at=started,
                completed_at=completed,
                error=f"{type(exc).__name__}: {exc}",
                tool=step.tool,
            )
            attempts.append(attempt)
            _trace_event(
                trace,
                run_id=task.run_id,
                task_id=task.task_id,
                step_id=task.step_id,
                attempt_no=attempt_no,
                event_type="internal_step_failed",
                public_payload={"capability": step.capability, "tool": step.tool, "error_type": type(exc).__name__},
            )
            continue

        if step.tool == "provider-research":
            for provider_index, provider_result in enumerate(result.get("attempts") or [], start=1):
                if not isinstance(provider_result, Mapping):
                    continue
                artifact_refs: list[str] = []
                if provider_result.get("artifact") or provider_result.get("report") or provider_result.get("candidates"):
                    artifact = _register_json_result(
                        registry,
                        task=task,
                        attempt_no=provider_index,
                        result=provider_result,
                        artifact_kind="provider_research_artifact",
                    )
                    artifact_refs.append(artifact.artifact_id)
                    raw_candidates = []
                    for item in provider_result.get("candidates") or []:
                        if isinstance(item, Mapping):
                            candidate_url = str(item.get("canonical_url") or item.get("url") or "")
                            if not candidate_url.startswith(("http://", "https://")):
                                continue
                            raw_candidates.append(
                                {
                                    **dict(item),
                                    "canonical_url": candidate_url,
                                    "artifact_refs": artifact_refs,
                                }
                            )
                    candidates.extend(
                        normalize_candidates(
                            raw_candidates,
                            run_id=task.run_id,
                            task_id=task.task_id,
                            step_id=task.step_id,
                            attempt_no=provider_index,
                        )
                    )
                errors = provider_result.get("errors") or []
                error = "; ".join(
                    str(item.get("message") or "") for item in errors if isinstance(item, Mapping)
                )
                attempts.append(
                    _public_attempt(
                        task=task,
                        capability="provider_research",
                        provider=str(provider_result.get("provider") or "provider"),
                        status=str(provider_result.get("status") or "failed"),
                        attempt_no=provider_index,
                        artifact_refs=artifact_refs,
                        started_at=str((provider_result.get("timestamps") or {}).get("started_at") or started),
                        completed_at=str((provider_result.get("timestamps") or {}).get("completed_at") or _utc_now()),
                        error=error,
                        usage=provider_result.get("usage") if isinstance(provider_result.get("usage"), Mapping) else {},
                        external_state=provider_result.get("external_job") if isinstance(provider_result.get("external_job"), Mapping) else {},
                        execution_kind="provider_research_agent",
                        tool=step.tool,
                    )
                )
                _trace_event(
                    trace,
                    run_id=task.run_id,
                    task_id=task.task_id,
                    step_id=task.step_id,
                    attempt_no=provider_index,
                    event_type="provider_research_completed",
                    artifact_refs=artifact_refs,
                    public_payload={
                        "provider": str(provider_result.get("provider") or ""),
                        "status": str(provider_result.get("status") or "failed"),
                        "candidate_count": len(provider_result.get("candidates") or []),
                    },
                )
            continue

        if step.tool in {
            "crawl",
            "extract",
            "batch",
            "deep-search",
            "jina-search",
            "rerank",
            "academic-search",
            "academic-read",
            "academic-related",
            "developer-search",
        }:
            for provider_index, provider_result in enumerate(result.get("attempts") or [], start=1):
                if not isinstance(provider_result, Mapping):
                    continue
                artifact = _register_json_result(
                    registry,
                    task=task,
                    attempt_no=provider_index,
                    result=provider_result,
                    artifact_kind="provider_capability_result",
                )
                raw_result = provider_result.get("result") if isinstance(provider_result.get("result"), Mapping) else {}
                sources = _result_sources(raw_result)
                candidates.extend(
                    normalize_candidates(
                        [
                            {
                                **item,
                                "source_type": str(provider_result.get("capability") or step.capability),
                                "discovery_path": [f"provider-capability:{provider_result.get('provider', '')}:{step.tool}"],
                                "artifact_refs": [artifact.artifact_id],
                            }
                            for item in sources
                        ],
                        run_id=task.run_id,
                        task_id=task.task_id,
                        step_id=task.step_id,
                        attempt_no=provider_index,
                    )
                )
                errors = provider_result.get("errors") or []
                error = "; ".join(
                    str(item.get("message") or "") for item in errors if isinstance(item, Mapping)
                )
                attempts.append(
                    _public_attempt(
                        task=task,
                        capability=step.capability,
                        provider=str(provider_result.get("provider") or "provider"),
                        status=str(provider_result.get("status") or "failed"),
                        attempt_no=provider_index,
                        artifact_refs=[artifact.artifact_id],
                        started_at=started,
                        completed_at=_utc_now(),
                        error=error,
                        execution_kind="tool",
                        tool=step.tool,
                    )
                )
                _trace_event(
                    trace,
                    run_id=task.run_id,
                    task_id=task.task_id,
                    step_id=task.step_id,
                    attempt_no=provider_index,
                    event_type="provider_capability_completed",
                    artifact_refs=[artifact.artifact_id],
                    public_payload={
                        "provider": str(provider_result.get("provider") or ""),
                        "tool": step.tool,
                        "status": str(provider_result.get("status") or "failed"),
                    },
                )
            continue

        artifact = _register_json_result(
            registry,
            task=task,
            attempt_no=attempt_no,
            result=result,
            artifact_kind="internal_discovery_result",
        )
        artifact_refs = [artifact.artifact_id]
        if step.tool == "fetch" and result.get("ok") and isinstance(result.get("content"), str) and result.get("content"):
            document_artifact = registry.register_snapshot(
                run_id=task.run_id,
                task_id=task.task_id,
                step_id=task.step_id,
                attempt_no=attempt_no,
                content=str(result["content"]),
                media_type="text/markdown",
                canonical_url=str(result.get("url") or _first_url(task)),
                artifact_kind="fetched_snapshot",
                metadata={
                    "parser": {"name": "smart-search-fetch", "version": "1"},
                    "provider": str(result.get("provider") or ""),
                    "untrusted_content": True,
                },
            )
            artifact_refs.append(document_artifact.artifact_id)
        raw_candidates = [
            {
                **item,
                "source_type": step.capability,
                "discovery_path": [f"smart-search:{step.tool}"],
                "artifact_refs": artifact_refs,
            }
            for item in _result_sources(result)
        ]
        candidates.extend(
            normalize_candidates(
                raw_candidates,
                run_id=task.run_id,
                task_id=task.task_id,
                step_id=task.step_id,
                attempt_no=attempt_no,
            )
        )
        ok = bool(result.get("ok", True))
        attempts.append(
            _public_attempt(
                task=task,
                capability=step.capability,
                provider=str(result.get("provider") or "smart-search"),
                status="success" if ok else str(result.get("error_type") or "failed"),
                attempt_no=attempt_no,
                artifact_refs=artifact_refs,
                started_at=started,
                completed_at=_utc_now(),
                error=str(result.get("error") or ""),
                usage={"elapsed_ms": result.get("elapsed_ms")} if result.get("elapsed_ms") is not None else {},
                tool=step.tool,
            )
        )
        _trace_event(
            trace,
            run_id=task.run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=attempt_no,
            event_type="internal_step_completed" if ok else "internal_step_degraded",
            artifact_refs=artifact_refs,
            public_payload={"capability": step.capability, "tool": step.tool, "candidate_count": len(raw_candidates)},
        )

    normalized = normalize_candidates(candidates)
    cards, summary = build_candidate_cards(normalized) if normalized else ([], {"schema_version": SCHEMA_VERSION, "count": 0, "estimated_context_size": 0, "grouping_suggestions": {}, "raw_index": {}})
    updated_run = dataclasses.replace(
        dossier.run,
        attempts=attempts,
        candidate_summary=summary,
    )
    return dataclasses.replace(
        dossier,
        run=updated_run,
        candidates=normalized,
        candidate_cards=cards,
    )


def import_delegated_result(
    dossier: ResearchDossier,
    *,
    result: Mapping[str, Any],
    artifact_root: str | Path,
) -> ResearchDossier:
    """Validate one child result; suggestions remain facts for Root to judge."""

    request_id = str(result.get("request_id") or "")
    request = next((item for item in dossier.delegate_requests if item.request_id == request_id), None)
    if request is None:
        raise ContractValidationError("DelegateResult has no originating DelegateRequest")
    task = _task_by_id(dossier, request.source_task_id)
    if request.target == "anysearch":
        imported = import_anysearch_result(
            result,
            dispatch={"delegate_request": request.to_dict(), "input": {"query": task.question}},
        )
    else:
        imported = import_delegate_result(result, request=request)
    contract = DelegateResult.from_dict(imported)
    if any(item.result_id == contract.result_id for item in dossier.delegate_results):
        return dossier

    registry = ArtifactRegistry(artifact_root, dossier.run.run_id)
    trace = JsonlTraceStore(artifact_root, dossier.run.run_id)
    registry.resolve_inputs(contract.artifact_refs)
    artifact = registry.register_snapshot(
        run_id=request.run_id,
        task_id=request.task_id,
        step_id=request.step_id,
        attempt_no=request.attempt_no,
        content=json.dumps(imported, ensure_ascii=False, sort_keys=True),
        media_type="application/json",
        canonical_url="",
        artifact_kind="delegate_result",
        metadata={"target": request.target, "untrusted_content": True},
    )
    candidates = list(dossier.candidates)
    proposals = list(dossier.key_source_proposals)
    evidence_items = list(dossier.evidence_items)
    payload = contract.payload
    if request.target in {"anysearch", "search_scout"}:
        source_values = payload.get("sources") if request.target == "anysearch" else payload.get("candidates")
        raw_candidates: list[dict[str, Any]] = []
        for item in source_values if isinstance(source_values, list) else []:
            if not isinstance(item, Mapping):
                continue
            url = item.get("canonical_url") or item.get("url")
            raw_candidates.append(
                {
                    **dict(item),
                    "canonical_url": url,
                    "summary": item.get("summary") or item.get("content") or "",
                    "source_type": request.target,
                    "discovery_path": [f"delegate:{request.target}"],
                    "artifact_refs": [artifact.artifact_id],
                }
            )
        candidates.extend(
            normalize_candidates(
                raw_candidates,
                run_id=request.run_id,
                task_id=request.task_id,
                step_id=request.step_id,
                attempt_no=request.attempt_no,
            )
        )
    elif request.target == "source_curator":
        value = payload.get("key_source_proposal")
        if not isinstance(value, Mapping):
            raise ContractValidationError("Source Curator result requires key_source_proposal")
        proposal_payload = dict(value)
        proposal_payload["artifact_refs"] = sorted(set(proposal_payload.get("artifact_refs", [])) | {artifact.artifact_id})
        proposal = KeySourceProposal.from_dict(proposal_payload)
        if (
            proposal.run_id != request.run_id
            or proposal.task_id != request.task_id
            or proposal.step_id != request.step_id
            or proposal.attempt_no != request.attempt_no
        ):
            raise ContractValidationError("KeySourceProposal does not match the originating Curator request")
        known_candidate_ids = {item.candidate_id for item in dossier.candidates}
        unknown_candidate_ids = sorted(set(proposal.input_candidate_ids) - known_candidate_ids)
        if unknown_candidate_ids:
            raise ContractValidationError("KeySourceProposal references candidates outside the run")
        requested_candidate_ids = task.user_constraints.get("candidate_ids")
        if isinstance(requested_candidate_ids, list) and set(proposal.input_candidate_ids) != {
            str(item) for item in requested_candidate_ids
        }:
            raise ContractValidationError("KeySourceProposal does not cover the Root-assigned candidate shard")
        proposals.append(proposal)
    elif request.target == "evidence_miner":
        values = payload.get("evidence_items")
        if not isinstance(values, list):
            raise ContractValidationError("Evidence Miner result requires evidence_items")
        for value in values:
            evidence = EvidenceItem.from_dict(value)
            if (
                evidence.run_id != request.run_id
                or evidence.task_id != request.task_id
                or evidence.step_id != request.step_id
                or evidence.attempt_no != request.attempt_no
            ):
                raise ContractValidationError("EvidenceItem does not match the originating Evidence Miner request")
            if not isinstance(task, EvidenceMiningTask) or evidence.claim_spec_id != task.claim_spec_id:
                raise ContractValidationError("EvidenceItem does not match its EvidenceMiningTask ClaimSpec")
            if evidence.artifact_id not in task.artifact_ids:
                raise ContractValidationError("EvidenceItem references a document outside the EvidenceMiningTask")
            resolved = registry.resolve_inputs(evidence.artifact_refs)
            source_artifact = next(
                (item for item in resolved if item.artifact_id == evidence.artifact_id),
                None,
            )
            if source_artifact is None:
                raise ContractValidationError("EvidenceItem artifact_id is not present in artifact_refs")
            if (
                evidence.snapshot_id != source_artifact.snapshot_id
                or evidence.canonical_url != source_artifact.canonical_url
            ):
                raise ContractValidationError("EvidenceItem source identity does not match the registered artifact")
            if evidence.evidence_id in {item.evidence_id for item in evidence_items}:
                raise ContractValidationError("EvidenceItem.evidence_id must be unique within a run")
            evidence_items.append(evidence)
    elif request.target == "mineru":
        if not request.input_artifact_ids:
            raise ContractValidationError("MinerU DelegateRequest requires a registered source artifact")
        source_refs = list(request.input_artifact_ids)
        if contract.status in {"success", "partial"}:
            allowed_fields = {"source_artifact_id", "markdown", "parser_version"}
            unexpected = sorted(set(payload) - allowed_fields)
            if unexpected:
                raise ContractValidationError(
                    f"MinerU payload has unsupported fields: {', '.join(unexpected)}"
                )
            source_artifact_id = str(payload.get("source_artifact_id") or "")
            if not source_artifact_id and len(source_refs) == 1:
                source_artifact_id = source_refs[0]
            if source_artifact_id not in source_refs:
                raise ContractValidationError(
                    "MinerU payload source_artifact_id is outside the originating request"
                )
            markdown = payload.get("markdown")
            parser_version = payload.get("parser_version")
            if not isinstance(markdown, str) or not markdown:
                raise ContractValidationError("successful MinerU payload requires non-empty markdown")
            if len(markdown.encode("utf-8")) > SIDECAR_MAX_ARTIFACT_BYTES:
                raise ContractValidationError("MinerU Markdown exceeds the document artifact size limit")
            if not isinstance(parser_version, str) or not parser_version.strip():
                raise ContractValidationError("successful MinerU payload requires parser_version")
            source_artifact = registry.get(source_artifact_id)
            if source_artifact.artifact_kind not in {
                "snapshot",
                "fetched_snapshot",
                "document_snapshot",
            }:
                raise ContractValidationError("MinerU source must be a registered document snapshot")
            derived = registry.register_snapshot(
                run_id=request.run_id,
                task_id=request.task_id,
                step_id=request.step_id,
                attempt_no=request.attempt_no,
                content=markdown,
                media_type="text/markdown",
                canonical_url=source_artifact.canonical_url,
                artifact_kind="document_snapshot",
                parent_artifact_id=source_artifact.artifact_id,
                metadata={
                    "parser": {"name": "mineru", "version": parser_version},
                    "delegate_request_id": request.request_id,
                    "delegate_result_id": contract.result_id,
                    "untrusted_content": True,
                },
            )
            contract = dataclasses.replace(
                contract,
                payload={
                    "source_artifact_id": source_artifact.artifact_id,
                    "artifact_ref": derived.artifact_id,
                    "parser_version": parser_version,
                },
                artifact_refs=list(
                    dict.fromkeys(
                        contract.artifact_refs
                        + source_refs
                        + [derived.artifact_id]
                    )
                ),
            )
            payload = contract.payload
        else:
            contract = dataclasses.replace(
                contract,
                artifact_refs=list(dict.fromkeys(contract.artifact_refs + source_refs)),
            )

    attempt = _public_attempt(
        task=task,
        capability=request.target,
        provider=request.target,
        status=contract.status,
        attempt_no=request.attempt_no,
        artifact_refs=list(dict.fromkeys(contract.artifact_refs + [artifact.artifact_id])),
        started_at="",
        completed_at=_utc_now(),
        usage=contract.usage,
        error=contract.termination_reason if contract.status in {"failed", "unavailable"} else "",
        execution_kind="skill" if request.target in {"anysearch", "mineru"} else "project_agent",
        tool=request.target,
    )
    attempts = list(dossier.run.attempts) + [attempt]
    normalized = normalize_candidates(candidates)
    cards, summary = build_candidate_cards(normalized) if normalized else ([], dossier.run.candidate_summary)
    gaps = list(dict.fromkeys(dossier.run.evidence_gaps + contract.gaps))
    updated_run = dataclasses.replace(dossier.run, attempts=attempts, candidate_summary=summary, evidence_gaps=gaps)
    _trace_event(
        trace,
        run_id=request.run_id,
        task_id=request.task_id,
        step_id=request.step_id,
        attempt_no=request.attempt_no,
        event_type="delegate_result_imported",
        artifact_refs=list(dict.fromkeys(contract.artifact_refs + [artifact.artifact_id])),
        public_payload={
            "target": request.target,
            "status": contract.status,
            "gap_count": len(contract.gaps),
            "suggestion_count": len(contract.suggestions),
        },
    )
    return dataclasses.replace(
        dossier,
        run=updated_run,
        delegate_results=dossier.delegate_results + [contract],
        candidates=normalized,
        candidate_cards=cards,
        key_source_proposals=proposals,
        evidence_items=evidence_items,
    )


def _mineru_results_from_dossier(
    dossier: ResearchDossier,
    *,
    task: EvidenceMiningTask,
    registry: ArtifactRegistry,
) -> dict[str, dict[str, Any]]:
    """Resolve only imported, registered MinerU artifacts for this mining task."""

    requests = {
        item.request_id: item
        for item in dossier.delegate_requests
        if item.target == "mineru"
    }
    resolved: dict[str, dict[str, Any]] = {}
    for result in dossier.delegate_results:
        request = requests.get(result.request_id)
        if request is None:
            continue
        source_ids = [
            artifact_id
            for artifact_id in request.input_artifact_ids
            if artifact_id in task.artifact_ids
        ]
        if not source_ids:
            continue
        if result.status in {"success", "partial"}:
            source_artifact_id = str(result.payload.get("source_artifact_id") or "")
            derived_artifact_id = str(result.payload.get("artifact_ref") or "")
            parser_version = str(result.payload.get("parser_version") or "")
            if source_artifact_id not in source_ids or not derived_artifact_id or not parser_version:
                raise ContractValidationError("stored MinerU result has an invalid artifact binding")
            source_artifact = registry.get(source_artifact_id)
            derived_artifact = registry.get(derived_artifact_id)
            if (
                derived_artifact.parent_artifact_id != source_artifact.artifact_id
                or derived_artifact.artifact_kind != "document_snapshot"
                or derived_artifact.media_type.split(";", 1)[0].strip().lower()
                != "text/markdown"
                or derived_artifact.canonical_url != source_artifact.canonical_url
            ):
                raise ContractValidationError("stored MinerU artifact does not match its source snapshot")
            markdown = (registry.run_dir / derived_artifact.raw_ref).read_text(
                encoding="utf-8"
            )
            resolved[source_artifact_id] = {
                "status": "success",
                "markdown": markdown,
                "artifact_ref": derived_artifact.artifact_id,
                "parser_version": parser_version,
            }
            continue
        status = "unavailable" if result.status == "unavailable" else "failed"
        error = result.termination_reason or "; ".join(result.gaps) or f"mineru {status}"
        for source_artifact_id in source_ids:
            resolved[source_artifact_id] = {"status": status, "error": error}
    return resolved


async def execute_document_task(
    dossier: ResearchDossier,
    *,
    task: EvidenceMiningTask,
    operations: Sequence[Mapping[str, Any]],
    artifact_root: str | Path,
    config: Config | None = None,
) -> dict[str, Any]:
    """Run controlled document tools and persist public attempts in the dossier."""

    if task.run_id != dossier.run.run_id or task.claim_spec_id not in {item.claim_spec_id for item in dossier.run.claims}:
        raise ContractValidationError("EvidenceMiningTask has a broken run or ClaimSpec reference")
    if task.task_id not in dossier.run.task_refs:
        raise ContractValidationError("EvidenceMiningTask must be added by Root before execution")
    requested_tools = {str(item.get("op") or "") for item in operations}
    if not requested_tools.issubset(task.allowed_tools):
        raise ContractValidationError("document operation exceeds EvidenceMiningTask.allowed_tools")
    registry = ArtifactRegistry(artifact_root, task.run_id)
    trace = JsonlTraceStore(artifact_root, task.run_id)
    mineru_results = _mineru_results_from_dossier(
        dossier,
        task=task,
        registry=registry,
    )
    started_at = _utc_now()
    existing_attempts = list(dossier.run.attempts)
    attempt_no = 1 + sum(item.task_id == task.task_id for item in existing_attempts)
    try:
        document_result = await run_document_operations(
            registry=registry,
            artifact_ids=task.artifact_ids,
            operations=operations,
            config=config or service.config,
            mineru_results=mineru_results,
        )
    except SidecarBridgeError as exc:
        status = (
            "timeout"
            if exc.code == "SIDECAR_TIMEOUT"
            else "unavailable"
            if exc.code == "SIDECAR_UNAVAILABLE"
            else "failed"
        )
        attempt = _public_attempt(
            task=task,
            capability="document_tool",
            provider="search-toolkit-sidecar",
            status=status,
            attempt_no=attempt_no,
            artifact_refs=task.artifact_ids,
            started_at=started_at,
            completed_at=_utc_now(),
            error=exc.message,
            external_state={"error_code": exc.code},
            execution_kind="tool",
            tool="search-toolkit-sidecar",
        )
        updated_run = dataclasses.replace(
            dossier.run,
            attempts=existing_attempts + [attempt],
            evidence_gaps=list(
                dict.fromkeys(
                    dossier.run.evidence_gaps
                    + [f"document sidecar unavailable for {task.task_id}: {exc.code}"]
                )
            ),
        )
        _trace_event(
            trace,
            run_id=task.run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=attempt_no,
            event_type="document_tool_failed",
            artifact_refs=task.artifact_ids,
            public_payload={"status": status, "error_code": exc.code},
        )
        updated = dataclasses.replace(dossier, run=updated_run)
        return {
            "ok": False,
            "error_type": status,
            "error": exc.message,
            "sidecar_error": exc.to_dict(),
            "document_result": {},
            "dossier": updated.to_dict(),
        }

    public_attempts: list[ExecutionAttempt] = []
    component_attempts = document_result.get("component_attempts") or []
    for offset, component in enumerate(component_attempts):
        if not isinstance(component, Mapping):
            continue
        component_status = str(component.get("status") or "failed")
        public_attempts.append(
            _public_attempt(
                task=task,
                capability="document_tool",
                provider=str(component.get("component") or "search-toolkit-sidecar"),
                status=component_status,
                attempt_no=attempt_no + offset,
                artifact_refs=list(component.get("artifact_refs") or task.artifact_ids),
                started_at=started_at,
                completed_at=str(component.get("observed_at") or _utc_now()),
                error=str(component.get("reason") or "") if component_status not in {"success", "succeeded"} else "",
                execution_kind=(
                    "parser"
                    if str(component.get("execution_kind") or "") == "parser"
                    else "tool"
                ),
                tool=str(component.get("component") or "search-toolkit-sidecar"),
            )
        )
    if not public_attempts:
        public_attempts.append(
            _public_attempt(
                task=task,
                capability="document_tool",
                provider="search-toolkit-sidecar",
                status="success",
                attempt_no=attempt_no,
                artifact_refs=task.artifact_ids,
                started_at=started_at,
                completed_at=_utc_now(),
                execution_kind="tool",
                tool="search-toolkit-sidecar",
            )
        )
    degraded = any(item.status not in {"success"} for item in public_attempts)
    updated_run = dataclasses.replace(
        dossier.run,
        attempts=existing_attempts + public_attempts,
    )
    _trace_event(
        trace,
        run_id=task.run_id,
        task_id=task.task_id,
        step_id=task.step_id,
        attempt_no=attempt_no,
        event_type="document_tool_degraded" if degraded else "document_tool_completed",
        artifact_refs=task.artifact_ids,
        public_payload={
            "operation_count": len(operations),
            "component_attempt_count": len(public_attempts),
            "degraded": degraded,
        },
    )
    updated = dataclasses.replace(dossier, run=updated_run)
    return {
        "ok": True,
        "document_result": document_result,
        "dossier": updated.to_dict(),
    }


def add_root_evidence_tasks(
    dossier: ResearchDossier,
    tasks: Sequence[EvidenceMiningTask],
) -> ResearchDossier:
    """Add only explicitly Root-authored mining tasks; no count policy is applied."""

    existing = {item.task_id for item in dossier.search_tasks + dossier.evidence_mining_tasks}
    claim_ids = {item.claim_spec_id for item in dossier.run.claims}
    for task in tasks:
        if task.run_id != dossier.run.run_id or task.task_id in existing:
            raise ContractValidationError("EvidenceMiningTask has a broken run or duplicate task_id")
        if task.claim_spec_id not in claim_ids:
            raise ContractValidationError("EvidenceMiningTask references an unknown ClaimSpec")
        existing.add(task.task_id)
    task_refs = dossier.run.task_refs + [item.task_id for item in tasks]
    requests = list(dossier.delegate_requests)
    for task in tasks:
        request = DelegateRequest(
            request_id=stable_id(
                "delegate",
                run_id=task.run_id,
                task_id=task.task_id,
                step_id=task.step_id,
                attempt_no=1,
                identity="evidence_miner",
            ),
            run_id=task.run_id,
            task_id=task.task_id,
            step_id=task.step_id,
            attempt_no=1,
            target="evidence_miner",
            source_task_id=task.task_id,
            input_artifact_ids=list(task.artifact_ids),
            permissions=list(dossier.run.frame.permissions),
            output_schema=task.expected_output,
            artifact_refs=list(task.artifact_refs),
        )
        requests.append(request)
    return dataclasses.replace(
        dossier,
        run=dataclasses.replace(
            dossier.run,
            task_refs=task_refs,
            delegate_refs=dossier.run.delegate_refs + [item.request_id for item in requests[len(dossier.delegate_requests):]],
        ),
        evidence_mining_tasks=dossier.evidence_mining_tasks + list(tasks),
        delegate_requests=requests,
    )


def add_root_search_tasks(
    dossier: ResearchDossier,
    tasks: Sequence[SearchTask],
) -> ResearchDossier:
    """Compile a Root-authored replan without interpreting child suggestions."""

    existing = {item.task_id for item in dossier.search_tasks + dossier.evidence_mining_tasks}
    for task in tasks:
        if task.run_id != dossier.run.run_id or task.task_id in existing:
            raise ContractValidationError("SearchTask has a broken run or duplicate task_id")
        existing.add(task.task_id)
    compiled = PlanCompiler().compile(
        dossier.run.frame,
        dossier.run.claims,
        list(tasks),
        dossier.run.capability_snapshot,
    )
    requests = dossier.delegate_requests + list(compiled.delegate_requests)
    return dataclasses.replace(
        dossier,
        run=dataclasses.replace(
            dossier.run,
            task_refs=dossier.run.task_refs + [item.task_id for item in tasks],
            delegate_refs=dossier.run.delegate_refs + [item.request_id for item in compiled.delegate_requests],
            root_next_decision="",
            stop_reason="",
        ),
        search_tasks=dossier.search_tasks + list(tasks),
        delegate_requests=requests,
    )


def derive_root_claim_records(
    dossier: ResearchDossier,
    *,
    decisions: Sequence[Mapping[str, Any]],
) -> ResearchDossier:
    """Apply Root's public gaps/conflicts while deriving status from evidence stances."""

    decision_by_claim: dict[str, Mapping[str, Any]] = {}
    for decision in decisions:
        claim_id = str(decision.get("claim_spec_id") or "")
        if not claim_id or claim_id in decision_by_claim:
            raise ContractValidationError("claim decisions require unique claim_spec_id")
        decision_by_claim[claim_id] = decision
    records: list[ClaimRecord] = []
    for claim in dossier.run.claims:
        decision = decision_by_claim.get(claim.claim_spec_id, {})
        gaps = decision.get("gaps", [])
        conflicts = decision.get("conflicts", [])
        citation_map = decision.get("citation_map", {})
        if not isinstance(gaps, list) or not isinstance(conflicts, list) or not isinstance(citation_map, Mapping):
            raise ContractValidationError("claim decision gaps/conflicts/citation_map have invalid types")
        evidence = [item for item in dossier.evidence_items if item.claim_spec_id == claim.claim_spec_id]
        records.append(
            derive_claim_record(
                claim,
                evidence,
                gaps=[str(item) for item in gaps],
                conflicts=[str(item) for item in conflicts],
                citation_map={str(key): str(value) for key, value in citation_map.items()},
            )
        )
    return dataclasses.replace(dossier, claim_records=records)


def update_root_decision(
    dossier: ResearchDossier,
    *,
    next_decision: str = "",
    stop_reason: str = "",
) -> ResearchDossier:
    """Record Root's public decision without interpreting or enforcing it."""

    if bool(next_decision) == bool(stop_reason):
        raise ContractValidationError("provide exactly one of next_decision or stop_reason")
    return dataclasses.replace(
        dossier,
        run=dataclasses.replace(
            dossier.run,
            root_next_decision=next_decision,
            stop_reason=stop_reason,
        ),
    )


def _normalize_final_citations(
    citations: Sequence[Mapping[str, str]],
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: dict[str, tuple[str, str]] = {}
    for index, citation in enumerate(citations):
        if not isinstance(citation, Mapping):
            raise ContractValidationError(f"citation mapping at index {index} must be an object")
        citation_id = str(citation.get("citation_id") or "")
        claim_record_id = str(citation.get("claim_record_id") or "")
        evidence_id = str(citation.get("evidence_id") or "")
        if not citation_id:
            raise ContractValidationError(f"citation mapping at index {index} requires citation_id")
        if not claim_record_id or not evidence_id:
            if citation.get("candidate_id") or citation.get("url") or citation.get("canonical_url"):
                raise ContractValidationError(
                    f"citation {citation_id} must reference a ClaimRecord and EvidenceItem; "
                    "CandidateCard or URL-only citations are discovery inputs, not report evidence"
                )
            raise ContractValidationError(
                f"citation {citation_id} requires claim_record_id and evidence_id"
            )
        target = (claim_record_id, evidence_id)
        previous = seen.get(citation_id)
        if previous is not None:
            if previous != target:
                raise ContractValidationError(
                    f"citation {citation_id} has conflicting duplicate mappings"
                )
            continue
        seen[citation_id] = target
        normalized.append(
            {
                "citation_id": citation_id,
                "claim_record_id": claim_record_id,
                "evidence_id": evidence_id,
            }
        )
    return normalized


def _metadata_value(metadata: Mapping[str, Any], *names: str) -> Any:
    bibliographic = metadata.get("bibliographic")
    sources = [bibliographic, metadata] if isinstance(bibliographic, Mapping) else [metadata]
    for source in sources:
        for name in names:
            value = source.get(name)
            if value not in (None, "", [], {}):
                return value
    return ""


def _bibliographic_metadata(artifact: ArtifactRecord) -> dict[str, Any]:
    metadata = artifact.metadata
    result: dict[str, Any] = {}
    title = _metadata_value(metadata, "title")
    authors = _metadata_value(metadata, "authors", "author")
    published = _metadata_value(
        metadata,
        "published_at",
        "publication_date",
        "published_date",
        "date",
    )
    venue = _metadata_value(metadata, "venue", "journal", "publisher")
    doi = _metadata_value(metadata, "doi")
    accessed = _metadata_value(metadata, "accessed_at", "access_date")
    if isinstance(title, str) and title.strip():
        result["title"] = title.strip()
    if isinstance(authors, str) and authors.strip():
        result["authors"] = [authors.strip()]
    elif isinstance(authors, list):
        cleaned = [item.strip() for item in authors if isinstance(item, str) and item.strip()]
        if cleaned:
            result["authors"] = cleaned
    for name, value in (
        ("published_at", published),
        ("venue", venue),
        ("doi", doi),
        ("accessed_at", accessed),
    ):
        if isinstance(value, str) and value.strip():
            result[name] = value.strip()
    return result


def _merge_bibliographic_metadata(
    current: dict[str, Any], artifact: ArtifactRecord
) -> None:
    for name, value in _bibliographic_metadata(artifact).items():
        if name not in current:
            current[name] = value


def _escape_reference_text(value: str) -> str:
    return re.sub(r"([\\`*_{}\[\]<>])", r"\\\1", value)


def _render_reference(reference: Mapping[str, Any]) -> str:
    source = reference.get("source")
    source = source if isinstance(source, Mapping) else {}
    bibliographic = source.get("bibliographic")
    bibliographic = bibliographic if isinstance(bibliographic, Mapping) else {}
    canonical_url = str(source.get("canonical_url") or "")
    title = str(bibliographic.get("title") or "")
    authors = bibliographic.get("authors")
    parts: list[str] = []
    if isinstance(authors, list) and authors:
        parts.append(", ".join(_escape_reference_text(str(item)) for item in authors))
    if title and canonical_url:
        parts.append(f"[{_escape_reference_text(title)}]({canonical_url})")
    elif title:
        parts.append(_escape_reference_text(title))
    elif canonical_url:
        parts.append(canonical_url)
    for name in ("venue", "published_at"):
        value = str(bibliographic.get(name) or "")
        if value:
            parts.append(_escape_reference_text(value))
    doi = str(bibliographic.get("doi") or "")
    if doi:
        parts.append(f"DOI: {_escape_reference_text(doi)}")
    accessed = str(bibliographic.get("accessed_at") or "")
    if accessed:
        parts.append(f"Accessed: {_escape_reference_text(accessed)}")
    return ". ".join(parts).rstrip(".") + "."


def _render_citation_report(
    draft_report: str,
    *,
    dossier: ResearchDossier,
    mapping: Mapping[str, Mapping[str, str]],
    artifacts: Sequence[ArtifactRecord],
) -> tuple[str, dict[str, Any]]:
    if not isinstance(draft_report, str) or not draft_report.strip():
        raise ContractValidationError("draft_report must be non-empty Markdown when supplied")
    if _REFERENCES_HEADING_RE.search(draft_report):
        raise ContractValidationError(
            "draft_report must not contain a References heading; Smart Search appends it after verification"
        )
    marker_ids = _CITATION_MARKER_RE.findall(draft_report)
    without_valid_markers = _CITATION_MARKER_RE.sub("", draft_report)
    if re.search(r"\[cite:", without_valid_markers, flags=re.IGNORECASE):
        raise ContractValidationError(
            "draft_report contains a malformed citation marker; use exact [cite:<citation_id>] syntax"
        )
    if mapping and not marker_ids:
        raise ContractValidationError(
            "draft_report must use supplied citation mappings with [cite:<citation_id>] markers"
        )
    for citation_id in marker_ids:
        if citation_id not in mapping:
            raise ContractValidationError(
                f"draft_report marker {citation_id} has no supplied citation mapping"
            )

    evidence_by_id = {item.evidence_id: item for item in dossier.evidence_items}
    artifacts_by_id = {item.artifact_id: item for item in artifacts}
    references: list[dict[str, Any]] = []
    by_source: dict[str, dict[str, Any]] = {}
    citation_numbers: dict[str, int] = {}

    for citation_id in marker_ids:
        backtrace = mapping[citation_id]
        evidence = evidence_by_id[backtrace["evidence_id"]]
        artifact = artifacts_by_id[backtrace["artifact_id"]]
        normalized_url = canonicalize_url(evidence.canonical_url)
        if not artifact.canonical_url or canonicalize_url(artifact.canonical_url) != normalized_url:
            raise ContractValidationError(
                f"citation {citation_id} canonical URL does not match its registered artifact snapshot"
            )
        reference = by_source.get(evidence.source_id)
        if reference is None:
            number = len(references) + 1
            reference = {
                "number": number,
                "source": {
                    "source_id": evidence.source_id,
                    "canonical_url": normalized_url,
                    "canonical_urls": [normalized_url],
                    "bibliographic": _bibliographic_metadata(artifact),
                },
                "citation_ids": [],
                "claim_records": [],
                "evidence_items": [],
                "artifacts": [],
            }
            by_source[evidence.source_id] = reference
            references.append(reference)
        source = reference["source"]
        if normalized_url not in source["canonical_urls"]:
            source["canonical_urls"].append(normalized_url)
        _merge_bibliographic_metadata(source["bibliographic"], artifact)
        if citation_id not in reference["citation_ids"]:
            reference["citation_ids"].append(citation_id)
        claim_projection = {
            "claim_record_id": backtrace["claim_record_id"],
            "claim_spec_id": backtrace["claim_spec_id"],
        }
        if claim_projection not in reference["claim_records"]:
            reference["claim_records"].append(claim_projection)
        if not any(
            item["evidence_id"] == evidence.evidence_id
            for item in reference["evidence_items"]
        ):
            reference["evidence_items"].append(
                {
                    "evidence_id": evidence.evidence_id,
                    "claim_record_id": backtrace["claim_record_id"],
                    "claim_spec_id": evidence.claim_spec_id,
                    "task_id": evidence.task_id,
                    "step_id": evidence.step_id,
                    "attempt_no": evidence.attempt_no,
                    "attempt_id": backtrace["attempt_id"],
                    "artifact_id": evidence.artifact_id,
                    "snapshot_id": evidence.snapshot_id,
                    "canonical_url": normalized_url,
                    "retrieved_at": evidence.retrieved_at,
                    "locator": dict(evidence.locator),
                }
            )
        if not any(
            item["artifact_id"] == artifact.artifact_id
            for item in reference["artifacts"]
        ):
            reference["artifacts"].append(
                {
                    "artifact_id": artifact.artifact_id,
                    "snapshot_id": artifact.snapshot_id,
                    "raw_ref": artifact.raw_ref,
                    "canonical_url": artifact.canonical_url,
                }
            )
        citation_numbers[citation_id] = reference["number"]

    rendered = _CITATION_MARKER_RE.sub(
        lambda match: f"[{citation_numbers[match.group(1)]}]",
        draft_report.rstrip(),
    )
    if references:
        rendered += "\n\n## References\n\n" + "\n".join(
            f"{reference['number']}. {_render_reference(reference)}"
            for reference in references
        )
    rendered += "\n"
    register = {
        "schema_version": "1",
        "run_id": dossier.run.run_id,
        "projection": "derived_audit_reference_register",
        "reference_count": len(references),
        "references": references,
    }
    return rendered, register


def verify_final_citations(
    dossier: ResearchDossier,
    *,
    citations: Sequence[Mapping[str, str]],
    artifact_root: str | Path,
    draft_report: str | None = None,
) -> dict[str, Any]:
    registry = ArtifactRegistry(artifact_root, dossier.run.run_id)
    trace = JsonlTraceStore(artifact_root, dossier.run.run_id)
    normalized_citations = _normalize_final_citations(citations)
    artifacts = registry.records()
    trace_events = trace.events()
    if normalized_citations and not trace_events:
        raise ContractValidationError(
            "citation verification requires artifact-linked Trace events for the complete reverse trace"
        )
    mapping = validate_citation_backtrace(
        normalized_citations,
        claim_records=dossier.claim_records,
        evidence_items=dossier.evidence_items,
        tasks=dossier.search_tasks + dossier.evidence_mining_tasks,
        attempts=dossier.run.attempts,
        artifacts=artifacts,
        trace_events=trace_events,
    )
    citations_by_evidence: dict[str, list[str]] = {}
    for citation_id, backtrace in mapping.items():
        citations_by_evidence.setdefault(backtrace["evidence_id"], []).append(citation_id)
    locator_checks: dict[str, dict[str, Any]] = {}
    for evidence in dossier.evidence_items:
        try:
            locator_checks[evidence.evidence_id] = validate_evidence_locator(registry, evidence)
        except ContractValidationError as exc:
            citation_ids = citations_by_evidence.get(evidence.evidence_id, [])
            if citation_ids:
                raise ContractValidationError(
                    f"citation {citation_ids[0]} has an invalid EvidenceItem locator: {exc}"
                ) from exc
            raise
    result: dict[str, Any] = {
        "ok": True,
        "citation_count": len(mapping),
        "backtrace": mapping,
        "locator_checks": locator_checks,
        "trace_ref": dossier.run.trace_ref,
        "artifact_index_ref": dossier.run.artifact_index_ref,
    }
    if draft_report is not None:
        rendered_report, reference_register = _render_citation_report(
            draft_report,
            dossier=dossier,
            mapping=mapping,
            artifacts=artifacts,
        )
        result["rendered_report"] = rendered_report
        result["reference_register"] = reference_register
    return result
