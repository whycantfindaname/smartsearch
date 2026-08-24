"""Versioned public contracts for Root-led deterministic research.

The contracts deliberately use only the Python standard library.  They are
plain JSON envelopes owned by the caller; this module validates identity and
reference facts, but never makes semantic planning decisions.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field, fields
from typing import Any, ClassVar, Mapping, TypeVar
from urllib.parse import urlsplit


SCHEMA_VERSION = "1"


class ContractValidationError(ValueError):
    """Raised when a public research contract is malformed."""


_T = TypeVar("_T", bound="Contract")
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_ARTIFACT_ID_RE = _ID_RE


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def stable_id(
    kind: str,
    *,
    run_id: str,
    task_id: str = "",
    step_id: str = "",
    attempt_no: int = 0,
    identity: Any = None,
) -> str:
    """Return a deterministic identifier bound to its execution scope."""
    _require_identifier("kind", kind)
    _require_identifier("run_id", run_id)
    if task_id:
        _require_identifier("task_id", task_id)
    if step_id:
        _require_identifier("step_id", step_id)
    if not isinstance(attempt_no, int) or isinstance(attempt_no, bool) or attempt_no < 0:
        raise ContractValidationError("attempt_no must be a non-negative integer")
    digest = hashlib.sha256(
        _canonical_json(
            {
                "kind": kind,
                "run_id": run_id,
                "task_id": task_id,
                "step_id": step_id,
                "attempt_no": attempt_no,
                "identity": identity,
            }
        ).encode("utf-8")
    ).hexdigest()[:24]
    prefix = re.sub(r"[^A-Za-z0-9]", "_", kind).strip("_") or "id"
    return f"{prefix}_{digest}"


make_stable_id = stable_id


def _require_string(name: str, value: Any, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        suffix = "a string" if allow_empty else "a non-empty string"
        raise ContractValidationError(f"{name} must be {suffix}")
    return value


def _require_identifier(name: str, value: Any, *, allow_empty: bool = False) -> str:
    if allow_empty and value == "":
        return value
    _require_string(name, value)
    if not _ID_RE.fullmatch(value):
        raise ContractValidationError(f"{name} is not a valid stable identifier")
    return value


def _require_attempt(value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ContractValidationError("attempt_no must be a positive integer")
    return value


def _require_string_list(name: str, value: Any) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ContractValidationError(f"{name} must be a list of non-empty strings")


def _require_mapping(name: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise ContractValidationError(f"{name} must be an object")


def _require_http_url(name: str, value: Any, *, allow_empty: bool = False) -> None:
    if allow_empty and value == "":
        return
    _require_string(name, value)
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ContractValidationError(f"{name} must be an absolute http(s) URL")


def validate_artifact_id(value: Any) -> str:
    """Reject path/URL-shaped agent inputs; registration is checked by the kernel."""
    _require_string("artifact_id", value)
    lowered = value.lower()
    if (
        "://" in lowered
        or lowered.startswith(("file:", "/", "\\", "./", "../", "~"))
        or "/" in value
        or "\\" in value
        or not _ARTIFACT_ID_RE.fullmatch(value)
    ):
        raise ContractValidationError("agent-facing artifact input must be a registered artifact_id, not a path or URL")
    return value


def _validate_artifact_refs(values: Any) -> None:
    _require_string_list("artifact_refs", values)
    for value in values:
        validate_artifact_id(value)


def _validate_scope(run_id: str, task_id: str = "", step_id: str = "", attempt_no: int | None = None) -> None:
    _require_identifier("run_id", run_id)
    if task_id:
        _require_identifier("task_id", task_id)
    if step_id:
        _require_identifier("step_id", step_id)
    if attempt_no is not None:
        _require_attempt(attempt_no)


@dataclass(frozen=True)
class Contract:
    """Base class with strict, explicit JSON conversion."""

    schema_version: str = field(default=SCHEMA_VERSION, kw_only=True)
    _nested_fields: ClassVar[dict[str, type[Contract] | tuple[type[Contract], bool]]] = {}

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ContractValidationError(f"unsupported schema_version: {self.schema_version!r}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls: type[_T], value: Mapping[str, Any]) -> _T:
        if not isinstance(value, Mapping):
            raise ContractValidationError(f"{cls.__name__} must be an object")
        if "schema_version" not in value:
            raise ContractValidationError(f"{cls.__name__}.schema_version is required")
        known = {item.name for item in fields(cls)}
        unknown = sorted(set(value) - known)
        if unknown:
            raise ContractValidationError(f"{cls.__name__} has unknown fields: {', '.join(unknown)}")
        payload = dict(value)
        for name, specification in cls._nested_fields.items():
            if name not in payload:
                continue
            nested_type: type[Contract]
            is_list = False
            if isinstance(specification, tuple):
                nested_type, is_list = specification
            else:
                nested_type = specification
            if is_list:
                if not isinstance(payload[name], list):
                    raise ContractValidationError(f"{cls.__name__}.{name} must be a list")
                payload[name] = [
                    item if isinstance(item, nested_type) else nested_type.from_dict(item) for item in payload[name]
                ]
            elif not isinstance(payload[name], nested_type):
                payload[name] = nested_type.from_dict(payload[name])
        try:
            return cls(**payload)
        except ContractValidationError:
            raise
        except (TypeError, ValueError) as exc:
            raise ContractValidationError(f"invalid {cls.__name__}: {exc}") from exc


@dataclass(frozen=True)
class ResearchFrame(Contract):
    run_id: str
    question: str
    mode: str = "standard"
    scope: dict[str, Any] = field(default_factory=dict)
    time_boundary: dict[str, Any] = field(default_factory=dict)
    source_preferences: list[str] = field(default_factory=list)
    user_constraints: dict[str, Any] = field(default_factory=dict)
    permissions: list[str] = field(default_factory=list)
    untrusted_content_policy: str = "treat_as_data"

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id)
        _require_string("question", self.question)
        if self.mode not in {"quick", "standard", "deep"}:
            raise ContractValidationError("mode must be quick, standard, or deep")
        _require_mapping("scope", self.scope)
        _require_mapping("time_boundary", self.time_boundary)
        _require_mapping("user_constraints", self.user_constraints)
        _require_string_list("source_preferences", self.source_preferences)
        _require_string_list("permissions", self.permissions)
        if self.untrusted_content_policy != "treat_as_data":
            raise ContractValidationError("untrusted_content_policy must be treat_as_data")


@dataclass(frozen=True)
class ClaimSpec(Contract):
    run_id: str
    claim_spec_id: str
    statement: str
    terms_scope: dict[str, Any] = field(default_factory=dict)
    time_boundary: dict[str, Any] = field(default_factory=dict)
    decision_criteria: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id)
        _require_identifier("claim_spec_id", self.claim_spec_id)
        _require_string("statement", self.statement)
        _require_mapping("terms_scope", self.terms_scope)
        _require_mapping("time_boundary", self.time_boundary)
        _require_string_list("decision_criteria", self.decision_criteria)


@dataclass(frozen=True)
class SearchTask(Contract):
    run_id: str
    task_id: str
    step_id: str
    question: str
    claim_spec_id: str = ""
    time_range: dict[str, Any] = field(default_factory=dict)
    source_preferences: list[str] = field(default_factory=list)
    allowed_capabilities: list[str] = field(default_factory=list)
    allowed_tools: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    user_constraints: dict[str, Any] = field(default_factory=dict)
    expected_output: str = "discovery_candidates"
    delegate_target: str = ""
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id)
        _require_string("question", self.question)
        if self.claim_spec_id:
            _require_identifier("claim_spec_id", self.claim_spec_id)
        _require_mapping("time_range", self.time_range)
        _require_mapping("user_constraints", self.user_constraints)
        for name in ("source_preferences", "allowed_capabilities", "allowed_tools", "permissions"):
            _require_string_list(name, getattr(self, name))
        _require_string("expected_output", self.expected_output)
        if self.delegate_target:
            _require_identifier("delegate_target", self.delegate_target)
        _validate_artifact_refs(self.artifact_refs)


EVIDENCE_MINING_TOOLS = frozenset({"search", "open", "navigate", "read", "grep"})


@dataclass(frozen=True)
class EvidenceMiningTask(Contract):
    run_id: str
    task_id: str
    step_id: str
    claim_spec_id: str
    artifact_ids: list[str]
    allowed_tools: list[str] = field(default_factory=lambda: sorted(EVIDENCE_MINING_TOOLS))
    read_locators: list[dict[str, Any]] = field(default_factory=list)
    user_constraints: dict[str, Any] = field(default_factory=dict)
    platform_constraints: dict[str, Any] = field(default_factory=dict)
    expected_output: str = "evidence_items"
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id)
        _require_identifier("claim_spec_id", self.claim_spec_id)
        _require_string_list("artifact_ids", self.artifact_ids)
        if not self.artifact_ids:
            raise ContractValidationError("artifact_ids must not be empty")
        for artifact_id in self.artifact_ids:
            validate_artifact_id(artifact_id)
        _require_string_list("allowed_tools", self.allowed_tools)
        unsupported = sorted(set(self.allowed_tools) - EVIDENCE_MINING_TOOLS)
        if unsupported:
            raise ContractValidationError(f"unsupported evidence mining tools: {', '.join(unsupported)}")
        if "delete" in self.allowed_tools:
            raise ContractValidationError("delete is not available to Evidence Miner")
        if not isinstance(self.read_locators, list) or any(not isinstance(item, dict) for item in self.read_locators):
            raise ContractValidationError("read_locators must be a list of objects")
        _require_mapping("user_constraints", self.user_constraints)
        _require_mapping("platform_constraints", self.platform_constraints)
        _require_string("expected_output", self.expected_output)
        _validate_artifact_refs(self.artifact_refs)


DELEGATE_TARGETS = frozenset(
    {"search_scout", "source_curator", "evidence_miner", "anysearch", "mineru"}
)


@dataclass(frozen=True)
class DelegateRequest(Contract):
    request_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    target: str
    source_task_id: str
    input_artifact_ids: list[str] = field(default_factory=list)
    permissions: list[str] = field(default_factory=list)
    output_schema: str = ""
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("request_id", self.request_id)
        _require_identifier("source_task_id", self.source_task_id)
        if self.target not in DELEGATE_TARGETS:
            raise ContractValidationError(f"unsupported delegate target: {self.target}")
        _require_string_list("input_artifact_ids", self.input_artifact_ids)
        for artifact_id in self.input_artifact_ids:
            validate_artifact_id(artifact_id)
        _require_string_list("permissions", self.permissions)
        _require_string("output_schema", self.output_schema)
        _validate_artifact_refs(self.artifact_refs)


DELEGATE_STATUSES = frozenset({"success", "partial", "failed", "unavailable", "cancelled"})


@dataclass(frozen=True)
class DelegateResult(Contract):
    result_id: str
    request_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    status: str
    payload: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: int | None = None
    gaps: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    termination_reason: str = ""
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("result_id", self.result_id)
        _require_identifier("request_id", self.request_id)
        if self.status not in DELEGATE_STATUSES:
            raise ContractValidationError(f"unsupported delegate status: {self.status}")
        _require_mapping("payload", self.payload)
        _require_mapping("usage", self.usage)
        if self.elapsed_ms is not None and (
            not isinstance(self.elapsed_ms, int) or isinstance(self.elapsed_ms, bool) or self.elapsed_ms < 0
        ):
            raise ContractValidationError("elapsed_ms must be a non-negative integer or null")
        _require_string_list("gaps", self.gaps)
        _require_string_list("suggestions", self.suggestions)
        _require_string("termination_reason", self.termination_reason, allow_empty=True)
        _validate_artifact_refs(self.artifact_refs)


ATTEMPT_STATUSES = frozenset(
    {
        "pending",
        "running",
        "success",
        "partial",
        "failed",
        "timeout",
        "unavailable",
        "missing_key",
        "entitlement_failure",
        "cancelled",
        "degraded",
    }
)
EXECUTION_KINDS = frozenset(
    {"internal", "provider_agent", "provider_research_agent", "skill", "project_agent", "parser", "tool"}
)


@dataclass(frozen=True)
class ExecutionAttempt(Contract):
    attempt_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    execution_kind: str
    capability: str
    status: str
    provider: str = ""
    external_state: dict[str, Any] = field(default_factory=dict)
    started_at: str = ""
    deadline_at: str = ""
    completed_at: str = ""
    request_summary: dict[str, Any] = field(default_factory=dict)
    usage: dict[str, Any] = field(default_factory=dict)
    retry_safe: bool = False
    error: str = ""
    degraded_reason: str = ""
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("attempt_id", self.attempt_id)
        if self.execution_kind not in EXECUTION_KINDS:
            raise ContractValidationError(f"unsupported execution_kind: {self.execution_kind}")
        _require_identifier("capability", self.capability)
        if self.status not in ATTEMPT_STATUSES:
            raise ContractValidationError(f"unsupported attempt status: {self.status}")
        if self.provider:
            _require_identifier("provider", self.provider)
        _require_mapping("external_state", self.external_state)
        _require_mapping("request_summary", self.request_summary)
        _require_mapping("usage", self.usage)
        if not isinstance(self.retry_safe, bool):
            raise ContractValidationError("retry_safe must be boolean")
        for name in ("started_at", "deadline_at", "completed_at", "error", "degraded_reason"):
            _require_string(name, getattr(self, name), allow_empty=True)
        _validate_artifact_refs(self.artifact_refs)


INDEPENDENCE_VALUES = frozenset({"independent", "related", "syndicated", "unknown"})


@dataclass(frozen=True)
class DiscoveryCandidate(Contract):
    candidate_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    title: str
    canonical_url: str
    summary: str = ""
    published_at: str = ""
    source_type: str = "web"
    stable_entity_id: str = ""
    discovery_path: list[str] = field(default_factory=list)
    raw_rank: int | None = None
    related_cluster_id: str = ""
    independence: str = "unknown"
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("candidate_id", self.candidate_id)
        _require_string("title", self.title)
        _require_http_url("canonical_url", self.canonical_url)
        _require_string("summary", self.summary, allow_empty=True)
        _require_string("published_at", self.published_at, allow_empty=True)
        _require_identifier("source_type", self.source_type)
        if self.stable_entity_id:
            _require_string("stable_entity_id", self.stable_entity_id)
        _require_string_list("discovery_path", self.discovery_path)
        if self.raw_rank is not None and (
            not isinstance(self.raw_rank, int) or isinstance(self.raw_rank, bool) or self.raw_rank < 0
        ):
            raise ContractValidationError("raw_rank must be a non-negative integer or null")
        if self.related_cluster_id:
            _require_identifier("related_cluster_id", self.related_cluster_id)
        if self.independence not in INDEPENDENCE_VALUES:
            raise ContractValidationError(f"unsupported independence value: {self.independence}")
        _validate_artifact_refs(self.artifact_refs)


@dataclass(frozen=True)
class CandidateCard(Contract):
    candidate_id: str
    run_id: str
    title: str
    canonical_url: str
    summary: str
    source_type: str
    raw_record_ref: str
    published_at: str = ""
    related_cluster_id: str = ""
    independence: str = "unknown"

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id)
        _require_identifier("candidate_id", self.candidate_id)
        _require_string("title", self.title)
        _require_http_url("canonical_url", self.canonical_url)
        _require_string("summary", self.summary, allow_empty=True)
        _require_identifier("source_type", self.source_type)
        validate_artifact_id(self.raw_record_ref)
        _require_string("published_at", self.published_at, allow_empty=True)
        if self.related_cluster_id:
            _require_identifier("related_cluster_id", self.related_cluster_id)
        if self.independence not in INDEPENDENCE_VALUES:
            raise ContractValidationError(f"unsupported independence value: {self.independence}")


@dataclass(frozen=True)
class KeySourceProposal(Contract):
    proposal_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    input_candidate_ids: list[str]
    keep_candidate_ids: list[str] = field(default_factory=list)
    defer_candidate_ids: list[str] = field(default_factory=list)
    reject_candidate_ids: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    coverage_gaps: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("proposal_id", self.proposal_id)
        for name in (
            "input_candidate_ids",
            "keep_candidate_ids",
            "defer_candidate_ids",
            "reject_candidate_ids",
            "coverage_gaps",
            "uncertainties",
        ):
            _require_string_list(name, getattr(self, name))
        selected = self.keep_candidate_ids + self.defer_candidate_ids + self.reject_candidate_ids
        if len(selected) != len(set(selected)):
            raise ContractValidationError("a candidate may appear in only one proposal disposition")
        if not set(selected).issubset(self.input_candidate_ids):
            raise ContractValidationError("proposal dispositions must reference input_candidate_ids")
        if not isinstance(self.reasons, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in self.reasons.items()
        ):
            raise ContractValidationError("reasons must be a string-to-string object")
        _validate_artifact_refs(self.artifact_refs)


@dataclass(frozen=True)
class ArtifactRecord(Contract):
    artifact_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    artifact_kind: str
    media_type: str
    snapshot_id: str
    raw_ref: str
    created_at: str
    canonical_url: str = ""
    parent_artifact_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        validate_artifact_id(self.artifact_id)
        _require_identifier("artifact_kind", self.artifact_kind)
        _require_string("media_type", self.media_type)
        _require_identifier("snapshot_id", self.snapshot_id)
        _require_string("raw_ref", self.raw_ref)
        if urlsplit(self.raw_ref).scheme or self.raw_ref.startswith(("/", "~")) or ".." in self.raw_ref.split("/"):
            raise ContractValidationError("raw_ref must be a run-local relative reference")
        _require_string("created_at", self.created_at)
        _require_http_url("canonical_url", self.canonical_url, allow_empty=True)
        if self.parent_artifact_id:
            validate_artifact_id(self.parent_artifact_id)
        _require_mapping("metadata", self.metadata)


EVIDENCE_STANCES = frozenset({"support", "contradict", "qualify"})
LOCATOR_TYPES = frozenset(
    {"page_character_range", "character_range", "section", "chunk", "repository_line_range"}
)
EVIDENCE_DIMENSIONS = (
    "authority",
    "directness",
    "freshness",
    "methodological_fit",
    "independence",
    "locator_quality",
)


def _require_non_negative_locator_int(locator: Mapping[str, Any], name: str) -> int:
    value = locator.get(name)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ContractValidationError(f"locator.{name} must be a non-negative integer")
    return value


def _validate_locator(locator: Mapping[str, Any]) -> None:
    locator_type = locator["type"]
    if locator_type in {"character_range", "page_character_range"}:
        start = _require_non_negative_locator_int(locator, "start")
        end = _require_non_negative_locator_int(locator, "end")
        if end <= start:
            raise ContractValidationError("locator.end must be greater than locator.start")
        if locator_type == "page_character_range":
            page = locator.get("page")
            if not isinstance(page, int) or isinstance(page, bool) or page < 1:
                raise ContractValidationError("locator.page must be a positive integer")
    elif locator_type == "section":
        _require_string("locator.section", locator.get("section"))
    elif locator_type == "chunk":
        if "chunk_id" not in locator and "index" not in locator:
            raise ContractValidationError("chunk locator requires chunk_id or index")
        if "chunk_id" in locator:
            _require_string("locator.chunk_id", locator["chunk_id"])
        if "index" in locator:
            _require_non_negative_locator_int(locator, "index")
    elif locator_type == "repository_line_range":
        for name in ("repository", "commit", "file"):
            _require_string(f"locator.{name}", locator.get(name))
        line_start = _require_non_negative_locator_int(locator, "line_start")
        line_end = _require_non_negative_locator_int(locator, "line_end")
        if line_start < 1 or line_end < line_start:
            raise ContractValidationError("repository locator lines must be positive and ordered")


@dataclass(frozen=True)
class EvidenceItem(Contract):
    evidence_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    claim_spec_id: str
    source_id: str
    canonical_url: str
    artifact_id: str
    snapshot_id: str
    retrieved_at: str
    content_type: str
    locator: dict[str, Any]
    text: str
    stance: str
    quality: dict[str, str]
    parser_id: str = ""
    parser_version: str = ""
    chunker_id: str = ""
    chunker_version: str = ""
    artifact_refs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("evidence_id", self.evidence_id)
        _require_identifier("claim_spec_id", self.claim_spec_id)
        _require_identifier("source_id", self.source_id)
        _require_http_url("canonical_url", self.canonical_url)
        validate_artifact_id(self.artifact_id)
        _require_identifier("snapshot_id", self.snapshot_id)
        _require_string("retrieved_at", self.retrieved_at)
        _require_string("content_type", self.content_type)
        _require_mapping("locator", self.locator)
        locator_type = self.locator.get("type")
        if locator_type not in LOCATOR_TYPES:
            raise ContractValidationError(f"unsupported locator type: {locator_type}")
        _validate_locator(self.locator)
        _require_string("text", self.text)
        if self.stance not in EVIDENCE_STANCES:
            raise ContractValidationError(f"unsupported evidence stance: {self.stance}")
        if not isinstance(self.quality, dict):
            raise ContractValidationError("quality must be an object")
        missing = [name for name in EVIDENCE_DIMENSIONS if not isinstance(self.quality.get(name), str)]
        if missing:
            raise ContractValidationError(f"quality is missing qualitative dimensions: {', '.join(missing)}")
        for name in ("parser_id", "parser_version", "chunker_id", "chunker_version"):
            _require_string(name, getattr(self, name), allow_empty=True)
        _validate_artifact_refs(self.artifact_refs)
        if self.artifact_id not in self.artifact_refs:
            raise ContractValidationError("artifact_refs must include artifact_id")


CLAIM_STATUSES = frozenset({"supported", "contested", "weakly_supported", "unsupported", "unresolved"})


@dataclass(frozen=True)
class ClaimRecord(Contract):
    claim_record_id: str
    run_id: str
    claim_spec_id: str
    statement: str
    status: str
    support_evidence_ids: list[str] = field(default_factory=list)
    contradict_evidence_ids: list[str] = field(default_factory=list)
    qualify_evidence_ids: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    citation_map: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id)
        _require_identifier("claim_record_id", self.claim_record_id)
        _require_identifier("claim_spec_id", self.claim_spec_id)
        _require_string("statement", self.statement)
        if self.status not in CLAIM_STATUSES:
            raise ContractValidationError(f"unsupported claim status: {self.status}")
        for name in (
            "support_evidence_ids",
            "contradict_evidence_ids",
            "qualify_evidence_ids",
            "conflicts",
            "gaps",
        ):
            _require_string_list(name, getattr(self, name))
        evidence_ids = self.support_evidence_ids + self.contradict_evidence_ids + self.qualify_evidence_ids
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ContractValidationError("an EvidenceItem may have only one stance in a ClaimRecord")
        if not isinstance(self.citation_map, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in self.citation_map.items()
        ):
            raise ContractValidationError("citation_map must be a string-to-string object")
        if not set(self.citation_map.values()).issubset(evidence_ids):
            raise ContractValidationError("citation_map contains evidence not linked to this ClaimRecord")


@dataclass(frozen=True)
class TraceEvent(Contract):
    event_id: str
    run_id: str
    task_id: str
    step_id: str
    attempt_no: int
    event_type: str
    timestamp: str
    parent_event_id: str = ""
    artifact_refs: list[str] = field(default_factory=list)
    public_payload: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id, self.task_id, self.step_id, self.attempt_no)
        _require_identifier("event_id", self.event_id)
        _require_identifier("event_type", self.event_type)
        _require_string("timestamp", self.timestamp)
        if self.parent_event_id:
            _require_identifier("parent_event_id", self.parent_event_id)
            if self.parent_event_id == self.event_id:
                raise ContractValidationError("TraceEvent cannot be its own parent")
        _validate_artifact_refs(self.artifact_refs)
        _require_mapping("public_payload", self.public_payload)


@dataclass(frozen=True)
class ResearchRun(Contract):
    run_id: str
    frame: ResearchFrame
    claims: list[ClaimSpec] = field(default_factory=list)
    task_refs: list[str] = field(default_factory=list)
    capability_snapshot: dict[str, Any] = field(default_factory=dict)
    capability_observed_at: str = ""
    attempts: list[ExecutionAttempt] = field(default_factory=list)
    delegate_refs: list[str] = field(default_factory=list)
    candidate_summary: dict[str, Any] = field(default_factory=dict)
    evidence_gaps: list[str] = field(default_factory=list)
    root_next_decision: str = ""
    stop_reason: str = ""
    trace_ref: str = ""
    artifact_index_ref: str = ""

    _nested_fields: ClassVar[dict[str, type[Contract] | tuple[type[Contract], bool]]] = {
        "frame": ResearchFrame,
        "claims": (ClaimSpec, True),
        "attempts": (ExecutionAttempt, True),
    }

    def __post_init__(self) -> None:
        super().__post_init__()
        _validate_scope(self.run_id)
        if not isinstance(self.frame, ResearchFrame) or self.frame.run_id != self.run_id:
            raise ContractValidationError("ResearchRun.frame must reference the same run_id")
        claim_ids: set[str] = set()
        for claim in self.claims:
            if not isinstance(claim, ClaimSpec) or claim.run_id != self.run_id:
                raise ContractValidationError("ResearchRun.claims contain a broken run reference")
            if claim.claim_spec_id in claim_ids:
                raise ContractValidationError("ResearchRun.claims contain duplicate claim_spec_id")
            claim_ids.add(claim.claim_spec_id)
        for attempt in self.attempts:
            if not isinstance(attempt, ExecutionAttempt) or attempt.run_id != self.run_id:
                raise ContractValidationError("ResearchRun.attempts contain a broken run reference")
        for name in ("task_refs", "delegate_refs", "evidence_gaps"):
            _require_string_list(name, getattr(self, name))
        _require_mapping("capability_snapshot", self.capability_snapshot)
        _require_mapping("candidate_summary", self.candidate_summary)
        for name in (
            "capability_observed_at",
            "root_next_decision",
            "stop_reason",
            "trace_ref",
            "artifact_index_ref",
        ):
            _require_string(name, getattr(self, name), allow_empty=True)


PUBLIC_CONTRACTS = {
    cls.__name__: cls
    for cls in (
        ResearchFrame,
        ResearchRun,
        ClaimSpec,
        SearchTask,
        EvidenceMiningTask,
        DelegateRequest,
        DelegateResult,
        ExecutionAttempt,
        DiscoveryCandidate,
        CandidateCard,
        KeySourceProposal,
        ArtifactRecord,
        EvidenceItem,
        ClaimRecord,
        TraceEvent,
    )
}


def contract_from_dict(contract_name: str, value: Mapping[str, Any]) -> Contract:
    """Deserialize one named public contract with strict version validation."""
    contract_type = PUBLIC_CONTRACTS.get(contract_name)
    if contract_type is None:
        raise ContractValidationError(f"unsupported contract type: {contract_name}")
    return contract_type.from_dict(value)


__all__ = [
    "SCHEMA_VERSION",
    "ContractValidationError",
    "stable_id",
    "make_stable_id",
    "validate_artifact_id",
    "ResearchFrame",
    "ResearchRun",
    "ClaimSpec",
    "SearchTask",
    "EvidenceMiningTask",
    "DelegateRequest",
    "DelegateResult",
    "ExecutionAttempt",
    "DiscoveryCandidate",
    "CandidateCard",
    "KeySourceProposal",
    "ArtifactRecord",
    "EvidenceItem",
    "ClaimRecord",
    "TraceEvent",
    "contract_from_dict",
]
