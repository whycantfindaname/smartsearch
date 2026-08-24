"""Deterministic Milestone A/B kernel for Root-led research.

This module compiles already-authored tasks, stores append-only public facts,
and provides pure evidence lifecycle helpers.  It intentionally contains no
semantic planner, synthesis model, fixed task count, or research budget.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

try:  # pragma: no cover - exercised on POSIX; fallback keeps imports portable.
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

from .research_contracts import (
    SCHEMA_VERSION,
    ArtifactRecord,
    CandidateCard,
    ClaimRecord,
    ClaimSpec,
    ContractValidationError,
    DelegateRequest,
    DiscoveryCandidate,
    EvidenceItem,
    EvidenceMiningTask,
    ExecutionAttempt,
    ResearchFrame,
    SearchTask,
    TraceEvent,
    stable_id,
    validate_artifact_id,
)


SUPPORTED_INTERNAL_TOOLS = frozenset(
    {
        "search",
        "exa-search",
        "exa-similar",
        "zhipu-search",
        "context7-library",
        "context7-docs",
        "fetch",
        "map",
        "crawl",
        "extract",
        "batch",
        "provider-research",
        "deep-search",
        "jina-search",
        "rerank",
        "academic-search",
        "academic-read",
        "academic-related",
        "developer-search",
    }
)

_TRACKING_QUERY_KEYS = frozenset(
    {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src"}
)
_SENSITIVE_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "access_token",
        "refresh_token",
        "id_token",
        "private_key",
    }
)
_HIDDEN_REASONING_KEYS = frozenset(
    {"chain_of_thought", "hidden_reasoning", "private_reasoning", "system_prompt", "developer_prompt"}
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _json_line(value: Mapping[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _assert_public_payload(value: Any, *, path: str = "payload") -> None:
    """Fail closed on fields intended to carry secrets or hidden reasoning."""
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_KEYS or normalized.endswith("_api_key"):
                raise ContractValidationError(f"{path}.{key} may not store secrets")
            if normalized in _HIDDEN_REASONING_KEYS:
                raise ContractValidationError(f"{path}.{key} may not store hidden reasoning or prompts")
            _assert_public_payload(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_public_payload(child, path=f"{path}[{index}]")


def canonicalize_url(url: str) -> str:
    """Return a stable HTTP(S) URL identity without fragments or trackers."""
    if not isinstance(url, str):
        raise ContractValidationError("url must be a string")
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise ContractValidationError("url must be an absolute http(s) URL")
    hostname = parsed.hostname.lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ContractValidationError(f"invalid URL port: {exc}") from exc
    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = hostname
    if parsed.username or parsed.password:
        raise ContractValidationError("URLs containing credentials are not allowed")
    if port and not default_port:
        netloc = f"{hostname}:{port}"
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_QUERY_KEYS
    ]
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, urlencode(sorted(query)), ""))


class _AppendOnlyJsonl:
    """Single-record atomic JSONL appends with process and thread locking."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line_no, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ContractValidationError(f"corrupt JSONL at {self.path}:{line_no}") from exc
                if not isinstance(value, dict):
                    raise ContractValidationError(f"JSONL record at {self.path}:{line_no} is not an object")
                records.append(value)
        return records

    def append(self, value: Mapping[str, Any]) -> None:
        _assert_public_payload(value)
        data = _json_line(value)
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        with self._lock:
            descriptor = os.open(self.path, flags, 0o600)
            try:
                if fcntl is not None:
                    fcntl.flock(descriptor, fcntl.LOCK_EX)
                view = memoryview(data)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("atomic JSONL append made no progress")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                if fcntl is not None:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)


def _run_dir(base_dir: str | os.PathLike[str], run_id: str) -> Path:
    validate_artifact_id(run_id)
    base = Path(base_dir).expanduser().resolve()
    target = (base / run_id).resolve()
    if target.parent != base:
        raise ContractValidationError("run_id must resolve to one run-local directory")
    target.mkdir(parents=True, exist_ok=True)
    return target


class ArtifactRegistry:
    """Append-only artifact facts and content-addressed run-local raw bytes."""

    def __init__(self, base_dir: str | os.PathLike[str], run_id: str):
        self.run_id = run_id
        self.run_dir = _run_dir(base_dir, run_id)
        self.index_path = self.run_dir / "artifacts.jsonl"
        self.raw_dir = self.run_dir / "raw"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self._store = _AppendOnlyJsonl(self.index_path)
        self._lock = threading.Lock()

    def records(self) -> list[ArtifactRecord]:
        return [ArtifactRecord.from_dict(item) for item in self._store.read()]

    def get(self, artifact_id: str) -> ArtifactRecord:
        validate_artifact_id(artifact_id)
        for record in self.records():
            if record.artifact_id == artifact_id:
                return record
        raise ContractValidationError(f"unknown artifact_id: {artifact_id}")

    def contains(self, artifact_id: str) -> bool:
        try:
            self.get(artifact_id)
        except ContractValidationError:
            return False
        return True

    def resolve_inputs(self, artifact_ids: Sequence[str]) -> list[ArtifactRecord]:
        """Resolve agent-facing IDs without accepting paths, URLs, or unknown IDs."""
        resolved: list[ArtifactRecord] = []
        for artifact_id in artifact_ids:
            validate_artifact_id(artifact_id)
            resolved.append(self.get(artifact_id))
        return resolved

    def append(self, record: ArtifactRecord) -> ArtifactRecord:
        if record.run_id != self.run_id:
            raise ContractValidationError("ArtifactRecord belongs to a different run")
        _assert_public_payload(record.metadata, path="ArtifactRecord.metadata")
        with self._lock:
            existing = {item.artifact_id: item for item in self.records()}
            if record.artifact_id in existing:
                raise ContractValidationError(f"artifact registry is append-only; duplicate artifact_id: {record.artifact_id}")
            if record.parent_artifact_id and record.parent_artifact_id not in existing:
                raise ContractValidationError("parent_artifact_id is not registered in this run")
            raw_path = (self.run_dir / record.raw_ref).resolve()
            if self.run_dir not in raw_path.parents or not raw_path.is_file():
                raise ContractValidationError("raw_ref does not resolve to an existing run-local artifact")
            self._store.append(record.to_dict())
        return record

    def register_snapshot(
        self,
        *,
        run_id: str,
        task_id: str,
        step_id: str,
        attempt_no: int,
        content: bytes | str,
        media_type: str,
        canonical_url: str,
        artifact_kind: str = "fetched_snapshot",
        metadata: Mapping[str, Any] | None = None,
        parent_artifact_id: str = "",
        created_at: str | None = None,
    ) -> ArtifactRecord:
        if run_id != self.run_id:
            raise ContractValidationError("snapshot run_id does not match registry")
        raw = content.encode("utf-8") if isinstance(content, str) else content
        if not isinstance(raw, bytes):
            raise ContractValidationError("content must be bytes or string")
        safe_metadata = dict(metadata or {})
        _assert_public_payload(safe_metadata, path="ArtifactRecord.metadata")
        snapshot_digest = hashlib.sha256(raw).hexdigest()
        snapshot_id = f"snap_{snapshot_digest}"
        normalized_url = canonicalize_url(canonical_url) if canonical_url else ""
        artifact_id = stable_id(
            "art",
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
            attempt_no=attempt_no,
            identity={"snapshot_id": snapshot_id, "kind": artifact_kind, "url": normalized_url},
        )
        raw_ref = f"raw/{snapshot_id}.bin"
        raw_path = self.run_dir / raw_ref
        try:
            descriptor = os.open(raw_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            if raw_path.read_bytes() != raw:
                raise ContractValidationError("snapshot identity collision")
        else:
            try:
                view = memoryview(raw)
                while view:
                    written = os.write(descriptor, view)
                    if written <= 0:
                        raise OSError("snapshot write made no progress")
                    view = view[written:]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        record = ArtifactRecord(
            artifact_id=artifact_id,
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
            attempt_no=attempt_no,
            artifact_kind=artifact_kind,
            media_type=media_type,
            snapshot_id=snapshot_id,
            raw_ref=raw_ref,
            created_at=created_at or _utc_now(),
            canonical_url=normalized_url,
            parent_artifact_id=parent_artifact_id,
            metadata=safe_metadata,
        )
        return self.append(record)


class JsonlTraceStore:
    """Run-local append-only store for auditable public TraceEvent facts."""

    def __init__(self, base_dir: str | os.PathLike[str], run_id: str):
        self.run_id = run_id
        self.run_dir = _run_dir(base_dir, run_id)
        self.path = self.run_dir / "trace.jsonl"
        self._store = _AppendOnlyJsonl(self.path)
        self._lock = threading.Lock()

    def events(self) -> list[TraceEvent]:
        return [TraceEvent.from_dict(item) for item in self._store.read()]

    def append(self, event: TraceEvent) -> TraceEvent:
        if event.run_id != self.run_id:
            raise ContractValidationError("TraceEvent belongs to a different run")
        _assert_public_payload(event.public_payload, path="TraceEvent.public_payload")
        with self._lock:
            existing = {item.event_id: item for item in self.events()}
            if event.event_id in existing:
                raise ContractValidationError(f"trace is append-only; duplicate event_id: {event.event_id}")
            if event.parent_event_id and event.parent_event_id not in existing:
                raise ContractValidationError("parent_event_id is not present in this run trace")
            self._store.append(event.to_dict())
        return event


TraceStore = JsonlTraceStore


@dataclass(frozen=True)
class CompiledInternalStep:
    run_id: str
    task_id: str
    step_id: str
    capability: str
    tool: str
    providers: tuple[str, ...]
    permissions: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "capability": self.capability,
            "tool": self.tool,
            "providers": list(self.providers),
            "permissions": list(self.permissions),
        }


@dataclass(frozen=True)
class CompiledPlan:
    internal_steps: tuple[CompiledInternalStep, ...]
    delegate_requests: tuple[DelegateRequest, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "internal_steps": [item.to_dict() for item in self.internal_steps],
            "delegate_requests": [item.to_dict() for item in self.delegate_requests],
        }


def _state_is_true(value: Any, provider: str = "") -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"available", "ok", "true", "reachable", "entitled", "configured"}
    if isinstance(value, (list, tuple, set)):
        return provider in value if provider else bool(value)
    return False


def _eligible_providers(entry: Mapping[str, Any]) -> tuple[str, ...]:
    providers = entry.get("providers")
    eligible: list[str] = []
    if isinstance(providers, list):
        for provider_entry in providers:
            if isinstance(provider_entry, str):
                name = provider_entry
                configured = _state_is_true(entry.get("configured"), name)
                reachable = _state_is_true(entry.get("reachable"), name)
                entitled = _state_is_true(entry.get("entitled"), name)
            elif isinstance(provider_entry, Mapping):
                name = str(provider_entry.get("name") or "")
                configured = _state_is_true(provider_entry.get("configured"))
                reachable = _state_is_true(provider_entry.get("reachable"))
                entitled = _state_is_true(provider_entry.get("entitled"))
            else:
                continue
            if name and configured and reachable and entitled:
                eligible.append(name)
    elif all(_state_is_true(entry.get(key)) for key in ("configured", "reachable", "entitled")):
        provider = entry.get("provider")
        eligible.append(str(provider) if provider else "internal")
    return tuple(dict.fromkeys(eligible))


def _capability_tools(entry: Mapping[str, Any]) -> tuple[str, ...]:
    tools = entry.get("tools")
    if isinstance(tools, str):
        return (tools,)
    if isinstance(tools, list) and all(isinstance(item, str) for item in tools):
        return tuple(dict.fromkeys(tools))
    default_tool = entry.get("default_tool") or entry.get("tool")
    return (str(default_tool),) if default_tool else ()


class PlanCompiler:
    """Validate and mechanically compile Root-authored tasks against live facts."""

    def __init__(self, supported_tools: Iterable[str] = SUPPORTED_INTERNAL_TOOLS):
        self.supported_tools = frozenset(supported_tools)

    def compile(
        self,
        frame: ResearchFrame,
        claims: Sequence[ClaimSpec],
        tasks: Sequence[SearchTask],
        capability_snapshot: Mapping[str, Any],
    ) -> CompiledPlan:
        if not isinstance(frame, ResearchFrame):
            raise ContractValidationError("frame must be a ResearchFrame")
        if not isinstance(capability_snapshot, Mapping):
            raise ContractValidationError("capability_snapshot must be an object")
        claim_ids: set[str] = set()
        for claim in claims:
            if not isinstance(claim, ClaimSpec) or claim.run_id != frame.run_id:
                raise ContractValidationError("claim has a broken run reference")
            if claim.claim_spec_id in claim_ids:
                raise ContractValidationError("duplicate claim_spec_id")
            claim_ids.add(claim.claim_spec_id)

        internal_steps: list[CompiledInternalStep] = []
        delegate_requests: list[DelegateRequest] = []
        task_ids: set[str] = set()
        for task in tasks:
            if not isinstance(task, SearchTask) or task.run_id != frame.run_id:
                raise ContractValidationError("task has a broken run reference")
            if task.task_id in task_ids:
                raise ContractValidationError("duplicate task_id")
            task_ids.add(task.task_id)
            if task.claim_spec_id and task.claim_spec_id not in claim_ids:
                raise ContractValidationError(f"task references unknown claim_spec_id: {task.claim_spec_id}")
            if not set(task.permissions).issubset(frame.permissions):
                raise ContractValidationError("task permissions exceed ResearchFrame permissions")

            if task.delegate_target:
                request_id = stable_id(
                    "delegate",
                    run_id=task.run_id,
                    task_id=task.task_id,
                    step_id=task.step_id,
                    attempt_no=1,
                    identity=task.delegate_target,
                )
                delegate_requests.append(
                    DelegateRequest(
                        request_id=request_id,
                        run_id=task.run_id,
                        task_id=task.task_id,
                        step_id=task.step_id,
                        attempt_no=1,
                        target=task.delegate_target,
                        source_task_id=task.task_id,
                        input_artifact_ids=list(task.artifact_refs),
                        permissions=list(task.permissions),
                        output_schema=task.expected_output,
                        artifact_refs=list(task.artifact_refs),
                    )
                )
                continue

            if not task.allowed_capabilities:
                raise ContractValidationError("internal SearchTask must declare allowed_capabilities")
            for capability in task.allowed_capabilities:
                entry = capability_snapshot.get(capability)
                if not isinstance(entry, Mapping):
                    raise ContractValidationError(f"capability is absent from snapshot: {capability}")
                providers = _eligible_providers(entry)
                if not providers:
                    raise ContractValidationError(
                        f"capability is not configured, reachable, and entitled: {capability}"
                    )
                snapshot_tools = _capability_tools(entry)
                requested_tools = tuple(task.allowed_tools) if task.allowed_tools else snapshot_tools
                if not requested_tools and capability in self.supported_tools:
                    requested_tools = (capability,)
                if not requested_tools:
                    raise ContractValidationError(f"no Root-authorized tool for capability: {capability}")
                for tool in requested_tools:
                    if tool not in self.supported_tools:
                        raise ContractValidationError(f"unsupported internal tool: {tool}")
                    if snapshot_tools and tool not in snapshot_tools:
                        continue
                    internal_steps.append(
                        CompiledInternalStep(
                            run_id=task.run_id,
                            task_id=task.task_id,
                            step_id=task.step_id,
                            capability=capability,
                            tool=tool,
                            providers=providers,
                            permissions=tuple(task.permissions),
                        )
                    )
            if not any(item.task_id == task.task_id for item in internal_steps):
                raise ContractValidationError(f"task has no allowed tool in capability snapshot: {task.task_id}")
        return CompiledPlan(tuple(internal_steps), tuple(delegate_requests))


def normalize_candidates(
    candidates: Iterable[DiscoveryCandidate | Mapping[str, Any]],
    *,
    run_id: str = "",
    task_id: str = "",
    step_id: str = "",
    attempt_no: int = 1,
) -> list[DiscoveryCandidate]:
    """Canonicalize and exactly deduplicate candidates without merging clusters."""
    normalized: list[DiscoveryCandidate] = []
    for item in candidates:
        if isinstance(item, DiscoveryCandidate):
            payload = item.to_dict()
        elif isinstance(item, Mapping):
            payload = dict(item)
        else:
            raise ContractValidationError("candidate input must be DiscoveryCandidate or object")
        item_run_id = str(payload.get("run_id") or run_id)
        item_task_id = str(payload.get("task_id") or task_id)
        item_step_id = str(payload.get("step_id") or step_id)
        item_attempt = payload.get("attempt_no", attempt_no)
        url = canonicalize_url(str(payload.get("canonical_url") or payload.get("url") or ""))
        stable_entity = str(payload.get("stable_entity_id") or "")
        identity = stable_entity or url
        candidate_id = stable_id(
            "cand",
            run_id=item_run_id,
            task_id=item_task_id,
            step_id=item_step_id,
            attempt_no=item_attempt,
            identity=identity,
        )
        raw_discovery_path = payload.get("discovery_path", [])
        if isinstance(raw_discovery_path, str):
            raw_discovery_path = [raw_discovery_path]
        raw_refs = payload.get("artifact_refs", [])
        if isinstance(raw_refs, str):
            raw_refs = [raw_refs]
        normalized.append(
            DiscoveryCandidate(
                schema_version=str(payload.get("schema_version") or SCHEMA_VERSION),
                candidate_id=candidate_id,
                run_id=item_run_id,
                task_id=item_task_id,
                step_id=item_step_id,
                attempt_no=item_attempt,
                title=str(payload.get("title") or url),
                canonical_url=url,
                summary=str(payload.get("summary") or payload.get("content") or ""),
                published_at=str(payload.get("published_at") or ""),
                source_type=str(payload.get("source_type") or "web"),
                stable_entity_id=stable_entity,
                discovery_path=list(raw_discovery_path),
                raw_rank=payload.get("raw_rank"),
                related_cluster_id=str(payload.get("related_cluster_id") or ""),
                independence=str(payload.get("independence") or "unknown"),
                artifact_refs=list(raw_refs),
            )
        )

    grouped: dict[tuple[str, str], list[DiscoveryCandidate]] = {}
    for candidate in normalized:
        key = (
            candidate.run_id,
            candidate.stable_entity_id or candidate.canonical_url,
        )
        grouped.setdefault(key, []).append(candidate)

    deduplicated: list[DiscoveryCandidate] = []
    for group in grouped.values():
        chosen = min(group, key=lambda item: json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True))
        paths = sorted({path for item in group for path in item.discovery_path})
        refs = sorted({ref for item in group for ref in item.artifact_refs})
        ranks = [item.raw_rank for item in group if item.raw_rank is not None]
        clusters = {item.related_cluster_id for item in group if item.related_cluster_id}
        independence_values = {item.independence for item in group}
        deduplicated.append(
            DiscoveryCandidate(
                candidate_id=chosen.candidate_id,
                run_id=chosen.run_id,
                task_id=chosen.task_id,
                step_id=chosen.step_id,
                attempt_no=chosen.attempt_no,
                title=chosen.title,
                canonical_url=chosen.canonical_url,
                summary=chosen.summary,
                published_at=chosen.published_at,
                source_type=chosen.source_type,
                stable_entity_id=chosen.stable_entity_id,
                discovery_path=paths,
                raw_rank=min(ranks) if ranks else None,
                related_cluster_id=next(iter(clusters)) if len(clusters) == 1 else "",
                independence=next(iter(independence_values)) if len(independence_values) == 1 else "unknown",
                artifact_refs=refs,
            )
        )
    return sorted(deduplicated, key=lambda item: item.candidate_id)


def build_candidate_cards(
    candidates: Sequence[DiscoveryCandidate],
    raw_index: Mapping[str, str] | None = None,
) -> tuple[list[CandidateCard], dict[str, Any]]:
    """Build compact cards plus a stable expandable raw index."""
    index = dict(raw_index or {})
    cards: list[CandidateCard] = []
    for candidate in candidates:
        if not isinstance(candidate, DiscoveryCandidate):
            raise ContractValidationError("candidates must contain DiscoveryCandidate objects")
        raw_ref = index.get(candidate.candidate_id) or next(iter(candidate.artifact_refs), "")
        if not raw_ref:
            raise ContractValidationError(f"candidate has no raw artifact reference: {candidate.candidate_id}")
        validate_artifact_id(raw_ref)
        index[candidate.candidate_id] = raw_ref
        cards.append(
            CandidateCard(
                candidate_id=candidate.candidate_id,
                run_id=candidate.run_id,
                title=candidate.title,
                canonical_url=candidate.canonical_url,
                summary=candidate.summary,
                source_type=candidate.source_type,
                raw_record_ref=raw_ref,
                published_at=candidate.published_at,
                related_cluster_id=candidate.related_cluster_id,
                independence=candidate.independence,
            )
        )
    clusters: dict[str, list[str]] = {}
    source_types: dict[str, list[str]] = {}
    for candidate in candidates:
        if candidate.related_cluster_id:
            clusters.setdefault(candidate.related_cluster_id, []).append(candidate.candidate_id)
        source_types.setdefault(candidate.source_type, []).append(candidate.candidate_id)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "count": len(cards),
        "estimated_context_size": sum(len(card.title) + len(card.summary) + len(card.canonical_url) for card in cards),
        "grouping_suggestions": {
            "related_clusters": {key: sorted(value) for key, value in sorted(clusters.items())},
            "source_types": {key: sorted(value) for key, value in sorted(source_types.items())},
        },
        "raw_index": {key: index[key] for key in sorted(index)},
    }
    return cards, summary


candidate_cards = build_candidate_cards


def register_fetched_snapshot(registry: ArtifactRegistry, **kwargs: Any) -> ArtifactRecord:
    """Small compatibility seam for later service/fetch integration."""
    return registry.register_snapshot(**kwargs)


def create_evidence_item(
    *,
    claim: ClaimSpec,
    artifact: ArtifactRecord,
    source_id: str,
    task_id: str,
    step_id: str,
    attempt_no: int,
    locator: Mapping[str, Any],
    text: str,
    stance: str,
    quality: Mapping[str, str],
    retrieved_at: str | None = None,
    parser_id: str = "",
    parser_version: str = "",
    chunker_id: str = "",
    chunker_version: str = "",
) -> EvidenceItem:
    """Create evidence bound to one immutable snapshot and typed locator."""
    if claim.run_id != artifact.run_id:
        raise ContractValidationError("claim and artifact belong to different runs")
    identity = {
        "claim_spec_id": claim.claim_spec_id,
        "artifact_id": artifact.artifact_id,
        "snapshot_id": artifact.snapshot_id,
        "locator": dict(locator),
        "stance": stance,
    }
    evidence_id = stable_id(
        "evidence",
        run_id=claim.run_id,
        task_id=task_id,
        step_id=step_id,
        attempt_no=attempt_no,
        identity=identity,
    )
    return EvidenceItem(
        evidence_id=evidence_id,
        run_id=claim.run_id,
        task_id=task_id,
        step_id=step_id,
        attempt_no=attempt_no,
        claim_spec_id=claim.claim_spec_id,
        source_id=source_id,
        canonical_url=artifact.canonical_url,
        artifact_id=artifact.artifact_id,
        snapshot_id=artifact.snapshot_id,
        retrieved_at=retrieved_at or artifact.created_at,
        content_type=artifact.media_type,
        parser_id=parser_id,
        parser_version=parser_version,
        chunker_id=chunker_id,
        chunker_version=chunker_version,
        locator=dict(locator),
        text=text,
        stance=stance,
        quality=dict(quality),
        artifact_refs=[artifact.artifact_id],
    )


def validate_evidence_locator(
    registry: ArtifactRegistry,
    evidence: EvidenceItem,
) -> dict[str, Any]:
    """Re-open the immutable snapshot and verify one typed locator.

    Character and repository-line locators are checked at their exact offsets.
    Section, chunk, and page locators are accepted only when the quoted text can
    still be found in the registered snapshot; parser-specific position facts
    remain available in the locator and artifact metadata for later adapters.
    """

    artifact = registry.get(evidence.artifact_id)
    if artifact.snapshot_id != evidence.snapshot_id:
        raise ContractValidationError("EvidenceItem snapshot_id does not match its registered artifact")
    raw_path = (registry.run_dir / artifact.raw_ref).resolve()
    if registry.run_dir not in raw_path.parents:
        raise ContractValidationError("EvidenceItem raw_ref escapes the run directory")
    try:
        content = raw_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ContractValidationError("EvidenceItem locator validation requires a UTF-8 text snapshot") from exc

    locator = evidence.locator
    locator_type = str(locator.get("type") or "")
    located = ""
    if locator_type in {"character_range", "page_character_range"}:
        start = int(locator["start"])
        end = int(locator["end"])
        if end > len(content):
            raise ContractValidationError("EvidenceItem locator exceeds its artifact snapshot")
        located = content[start:end]
    elif locator_type == "repository_line_range":
        lines = content.splitlines(keepends=True)
        line_start = int(locator["line_start"])
        line_end = int(locator["line_end"])
        if line_end > len(lines):
            raise ContractValidationError("EvidenceItem repository locator exceeds its artifact snapshot")
        located = "".join(lines[line_start - 1 : line_end]).rstrip("\r\n")
    elif locator_type in {"section", "chunk"}:
        located = evidence.text if evidence.text in content else ""
    else:  # EvidenceItem validation should already reject unsupported types.
        raise ContractValidationError(f"unsupported locator type: {locator_type}")

    if located != evidence.text:
        raise ContractValidationError("EvidenceItem locator does not reproduce its quoted text")
    return {
        "artifact_id": artifact.artifact_id,
        "snapshot_id": artifact.snapshot_id,
        "locator_type": locator_type,
        "text_length": len(evidence.text),
    }


def derive_claim_record(
    claim: ClaimSpec,
    evidence_items: Sequence[EvidenceItem],
    *,
    gaps: Sequence[str] = (),
    conflicts: Sequence[str] = (),
    citation_map: Mapping[str, str] | None = None,
) -> ClaimRecord:
    """Derive a qualitative ClaimRecord without a synthetic numeric score."""
    seen: set[str] = set()
    by_stance: dict[str, list[str]] = {"support": [], "contradict": [], "qualify": []}
    for evidence in evidence_items:
        if evidence.run_id != claim.run_id or evidence.claim_spec_id != claim.claim_spec_id:
            raise ContractValidationError("EvidenceItem has a broken ClaimSpec reference")
        if evidence.evidence_id in seen:
            continue
        seen.add(evidence.evidence_id)
        by_stance[evidence.stance].append(evidence.evidence_id)
    support = bool(by_stance["support"])
    contradict = bool(by_stance["contradict"])
    qualify = bool(by_stance["qualify"])
    if support and contradict:
        status = "contested"
    elif support and (qualify or gaps):
        status = "weakly_supported"
    elif support:
        status = "supported"
    elif contradict:
        status = "unsupported"
    elif qualify:
        status = "weakly_supported"
    else:
        status = "unresolved"
    record_id = stable_id(
        "claim_record",
        run_id=claim.run_id,
        identity={
            "claim_spec_id": claim.claim_spec_id,
            "evidence_ids": sorted(seen),
            "gaps": list(gaps),
            "conflicts": list(conflicts),
        },
    )
    return ClaimRecord(
        claim_record_id=record_id,
        run_id=claim.run_id,
        claim_spec_id=claim.claim_spec_id,
        statement=claim.statement,
        status=status,
        support_evidence_ids=sorted(by_stance["support"]),
        contradict_evidence_ids=sorted(by_stance["contradict"]),
        qualify_evidence_ids=sorted(by_stance["qualify"]),
        conflicts=list(conflicts),
        gaps=list(gaps),
        citation_map=dict(citation_map or {}),
    )


def validate_citation_backtrace(
    citations: Sequence[Mapping[str, str]],
    *,
    claim_records: Sequence[ClaimRecord],
    evidence_items: Sequence[EvidenceItem],
    tasks: Sequence[SearchTask | EvidenceMiningTask],
    attempts: Sequence[ExecutionAttempt],
    artifacts: Sequence[ArtifactRecord],
    trace_events: Sequence[TraceEvent] = (),
) -> dict[str, dict[str, str]]:
    """Validate citation -> claim -> evidence -> task/attempt -> raw snapshot."""
    claims_by_id = {item.claim_record_id: item for item in claim_records}
    evidence_by_id = {item.evidence_id: item for item in evidence_items}
    tasks_by_id = {item.task_id: item for item in tasks}
    attempts_by_scope = {
        (item.run_id, item.task_id, item.step_id, item.attempt_no): item for item in attempts
    }
    artifacts_by_id = {item.artifact_id: item for item in artifacts}
    trace_by_scope: dict[tuple[str, str, str, int], list[TraceEvent]] = {}
    for event in trace_events:
        trace_by_scope.setdefault((event.run_id, event.task_id, event.step_id, event.attempt_no), []).append(event)

    result: dict[str, dict[str, str]] = {}
    for citation in citations:
        citation_id = str(citation.get("citation_id") or "")
        claim_record_id = str(citation.get("claim_record_id") or "")
        evidence_id = str(citation.get("evidence_id") or "")
        if not citation_id or citation_id in result:
            raise ContractValidationError("citations require unique non-empty citation_id")
        claim_record = claims_by_id.get(claim_record_id)
        evidence = evidence_by_id.get(evidence_id)
        if claim_record is None or evidence is None:
            raise ContractValidationError(f"citation {citation_id} has a broken claim/evidence reference")
        linked_ids = set(
            claim_record.support_evidence_ids
            + claim_record.contradict_evidence_ids
            + claim_record.qualify_evidence_ids
        )
        if evidence_id not in linked_ids or evidence.claim_spec_id != claim_record.claim_spec_id:
            raise ContractValidationError(f"citation {citation_id} evidence is not linked to its ClaimRecord")
        mapped_evidence = claim_record.citation_map.get(citation_id)
        if mapped_evidence is not None and mapped_evidence != evidence_id:
            raise ContractValidationError(f"citation {citation_id} conflicts with ClaimRecord.citation_map")
        task = tasks_by_id.get(evidence.task_id)
        if task is None or task.run_id != evidence.run_id or task.step_id != evidence.step_id or (
            task.claim_spec_id and task.claim_spec_id != evidence.claim_spec_id
        ):
            raise ContractValidationError(f"citation {citation_id} has a broken task backtrace")
        scope = (evidence.run_id, evidence.task_id, evidence.step_id, evidence.attempt_no)
        attempt = attempts_by_scope.get(scope)
        if attempt is None:
            raise ContractValidationError(f"citation {citation_id} has no matching ExecutionAttempt")
        artifact = artifacts_by_id.get(evidence.artifact_id)
        if artifact is None or artifact.run_id != evidence.run_id or artifact.snapshot_id != evidence.snapshot_id:
            raise ContractValidationError(f"citation {citation_id} has a broken artifact snapshot backtrace")
        if evidence.artifact_id not in attempt.artifact_refs:
            raise ContractValidationError(f"citation {citation_id} artifact is absent from ExecutionAttempt")
        artifact_scope = (artifact.run_id, artifact.task_id, artifact.step_id, artifact.attempt_no)
        if artifact_scope != scope and artifact_scope not in attempts_by_scope:
            raise ContractValidationError(f"citation {citation_id} has no artifact-producing ExecutionAttempt")
        if trace_events:
            scoped_events = trace_by_scope.get(scope, [])
            if not scoped_events or not any(evidence.artifact_id in event.artifact_refs for event in scoped_events):
                raise ContractValidationError(f"citation {citation_id} has no artifact-linked TraceEvent")
        result[citation_id] = {
            "claim_record_id": claim_record.claim_record_id,
            "claim_spec_id": claim_record.claim_spec_id,
            "evidence_id": evidence.evidence_id,
            "task_id": evidence.task_id,
            "attempt_id": attempt.attempt_id,
            "artifact_id": artifact.artifact_id,
            "snapshot_id": artifact.snapshot_id,
            "raw_ref": artifact.raw_ref,
        }
    return result


__all__ = [
    "SUPPORTED_INTERNAL_TOOLS",
    "canonicalize_url",
    "ArtifactRegistry",
    "JsonlTraceStore",
    "TraceStore",
    "CompiledInternalStep",
    "CompiledPlan",
    "PlanCompiler",
    "normalize_candidates",
    "build_candidate_cards",
    "candidate_cards",
    "register_fetched_snapshot",
    "create_evidence_item",
    "validate_evidence_locator",
    "derive_claim_record",
    "validate_citation_backtrace",
]
