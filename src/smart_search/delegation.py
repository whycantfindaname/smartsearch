"""Harness-neutral adapters for Root-led research delegation.

Public object shapes are owned by :mod:`smart_search.research_contracts`.  This
module accepts and returns plain mappings, and duck-types those contract objects
without defining another set of public schemas.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
import re
from typing import Any


SCHEMA_VERSION = "1"
ROOT_OWNER = "root"
DELEGATE_TARGETS = frozenset(
    {"search_scout", "source_curator", "evidence_miner", "anysearch", "mineru"}
)
TERMINAL_STATUSES = frozenset(
    {"success", "partial", "failed", "unavailable", "cancelled"}
)
_ARTIFACT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_FORBIDDEN_CHILD_OUTPUT_KEYS = frozenset(
    {
        "tasks",
        "new_tasks",
        "follow_up_tasks",
        "followup_tasks",
        "delegate_requests",
        "child_tasks",
        "children",
        "descendants",
        "spawn",
        "spawn_requests",
    }
)


class DelegationValidationError(ValueError):
    """Raised when adapter input violates a public contract or ownership rule."""


def _plain_mapping(value: Any, *, label: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="python")
        if isinstance(dumped, Mapping):
            return dict(dumped)
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        dumped = to_dict()
        if isinstance(dumped, Mapping):
            return dict(dumped)
    if is_dataclass(value) and not isinstance(value, type):
        dumped = asdict(value)
        if isinstance(dumped, Mapping):
            return dict(dumped)
    raise DelegationValidationError(f"{label} must be a mapping or mapping-like contract")


def _required_text(mapping: Mapping[str, Any], key: str, *, label: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise DelegationValidationError(f"{label}.{key} must be a non-empty string")
    return value.strip()


def _string_list(value: Any, *, label: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DelegationValidationError(f"{label} must be a list of strings")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise DelegationValidationError(f"{label} must contain non-empty strings")
        result.append(item.strip())
    return result


def _mapping_list(value: Any, *, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise DelegationValidationError(f"{label} must be a list of mappings")
    return [_plain_mapping(item, label=f"{label}[{index}]") for index, item in enumerate(value)]


def _artifact_id_list(value: Any, *, label: str) -> list[str]:
    result = _string_list(value, label=label)
    for artifact_id in result:
        lowered = artifact_id.lower()
        if (
            "://" in lowered
            or lowered.startswith(("file:", "/", "\\", "./", "../", "~"))
            or "/" in artifact_id
            or "\\" in artifact_id
            or not _ARTIFACT_ID_RE.fullmatch(artifact_id)
        ):
            raise DelegationValidationError(
                f"{label} must contain registered artifact_id values, not paths or URLs"
            )
    return result


def _reject_child_control_fields(mapping: Mapping[str, Any], *, label: str) -> None:
    forbidden = sorted(key for key in _FORBIDDEN_CHILD_OUTPUT_KEYS if key in mapping)
    if forbidden:
        raise DelegationValidationError(
            f"{label} contains executable child control fields: {', '.join(forbidden)}; "
            "only Root creates tasks"
        )


def create_delegate_request(
    *,
    request_id: str,
    task: Mapping[str, Any] | Any,
    attempt_no: int = 1,
    target: str = "",
    source_task_id: str = "",
    input_artifact_ids: Sequence[str] | None = None,
    permissions: Sequence[str] | None = None,
    output_schema: str = "",
    artifact_refs: Sequence[str] | None = None,
    created_by: str = ROOT_OWNER,
) -> dict[str, Any]:
    """Create the canonical DelegateRequest mapping from a Root-authored task."""

    if created_by != ROOT_OWNER:
        raise DelegationValidationError("only Root may create DelegateRequest objects")
    task_mapping = _plain_mapping(task, label="task")
    request = {
        "schema_version": SCHEMA_VERSION,
        "request_id": request_id,
        "run_id": task_mapping.get("run_id"),
        "task_id": task_mapping.get("task_id"),
        "step_id": task_mapping.get("step_id"),
        "attempt_no": attempt_no,
        "target": target or task_mapping.get("delegate_target"),
        "source_task_id": source_task_id or task_mapping.get("task_id"),
        "input_artifact_ids": list(
            input_artifact_ids
            if input_artifact_ids is not None
            else task_mapping.get("artifact_refs", [])
        ),
        "permissions": list(
            permissions if permissions is not None else task_mapping.get("permissions", [])
        ),
        "output_schema": output_schema or task_mapping.get("expected_output", ""),
        "artifact_refs": list(
            artifact_refs if artifact_refs is not None else task_mapping.get("artifact_refs", [])
        ),
    }
    return validate_delegate_request(request)


def validate_delegate_request(value: Mapping[str, Any] | Any) -> dict[str, Any]:
    """Validate the current public DelegateRequest using only plain mappings."""

    request = _plain_mapping(value, label="DelegateRequest")
    expected_fields = {
        "schema_version",
        "request_id",
        "run_id",
        "task_id",
        "step_id",
        "attempt_no",
        "target",
        "source_task_id",
        "input_artifact_ids",
        "permissions",
        "output_schema",
        "artifact_refs",
    }
    unknown = sorted(set(request) - expected_fields)
    if unknown:
        raise DelegationValidationError(
            "DelegateRequest has fields outside the public contract: " + ", ".join(unknown)
        )
    for key in (
        "schema_version",
        "request_id",
        "run_id",
        "task_id",
        "step_id",
        "target",
        "source_task_id",
        "output_schema",
    ):
        request[key] = _required_text(request, key, label="DelegateRequest")
    if request["schema_version"] != SCHEMA_VERSION:
        raise DelegationValidationError("DelegateRequest.schema_version is unsupported")
    if request["target"] not in DELEGATE_TARGETS:
        raise DelegationValidationError(
            f"unsupported DelegateRequest.target: {request['target']}"
        )
    attempt_no = request.get("attempt_no")
    if isinstance(attempt_no, bool) or not isinstance(attempt_no, int) or attempt_no < 1:
        raise DelegationValidationError("DelegateRequest.attempt_no must be a positive integer")
    request["input_artifact_ids"] = _artifact_id_list(
        request.get("input_artifact_ids"), label="DelegateRequest.input_artifact_ids"
    )
    request["permissions"] = _string_list(
        request.get("permissions"), label="DelegateRequest.permissions"
    )
    request["artifact_refs"] = _artifact_id_list(
        request.get("artifact_refs"), label="DelegateRequest.artifact_refs"
    )
    return request


def import_delegate_result(
    value: Mapping[str, Any] | Any,
    *,
    request: Mapping[str, Any] | Any,
) -> dict[str, Any]:
    """Import the canonical DelegateResult while keeping suggestions inert."""

    origin = validate_delegate_request(request)
    result = _plain_mapping(value, label="DelegateResult")
    _reject_child_control_fields(result, label="DelegateResult")
    expected_fields = {
        "schema_version",
        "result_id",
        "request_id",
        "run_id",
        "task_id",
        "step_id",
        "attempt_no",
        "status",
        "payload",
        "usage",
        "elapsed_ms",
        "gaps",
        "suggestions",
        "termination_reason",
        "artifact_refs",
    }
    unknown = sorted(set(result) - expected_fields)
    if unknown:
        raise DelegationValidationError(
            "DelegateResult has fields outside the public contract: " + ", ".join(unknown)
        )
    for key in ("schema_version", "request_id", "run_id", "task_id", "step_id"):
        result[key] = _required_text(result, key, label="DelegateResult")
        if result[key] != origin[key]:
            raise DelegationValidationError(
                f"DelegateResult.{key} does not match the originating request"
            )
    if result.get("attempt_no") != origin["attempt_no"]:
        raise DelegationValidationError(
            "DelegateResult.attempt_no does not match the originating request"
        )
    result["result_id"] = _required_text(result, "result_id", label="DelegateResult")
    status = _required_text(result, "status", label="DelegateResult")
    if status not in TERMINAL_STATUSES:
        raise DelegationValidationError(f"unsupported DelegateResult.status: {status}")
    result["payload"] = _plain_mapping(
        result.get("payload", {}), label="DelegateResult.payload"
    )
    _reject_child_control_fields(result["payload"], label="DelegateResult.payload")
    result["usage"] = _plain_mapping(result.get("usage", {}), label="DelegateResult.usage")
    elapsed_ms = result.get("elapsed_ms")
    if elapsed_ms is not None and (
        isinstance(elapsed_ms, bool) or not isinstance(elapsed_ms, int) or elapsed_ms < 0
    ):
        raise DelegationValidationError(
            "DelegateResult.elapsed_ms must be a non-negative integer or null"
        )
    result["gaps"] = _string_list(result.get("gaps"), label="DelegateResult.gaps")
    result["suggestions"] = _string_list(
        result.get("suggestions"), label="DelegateResult.suggestions"
    )
    result["termination_reason"] = result.get("termination_reason", "")
    if not isinstance(result["termination_reason"], str):
        raise DelegationValidationError("DelegateResult.termination_reason must be a string")
    result["artifact_refs"] = _artifact_id_list(
        result.get("artifact_refs"), label="DelegateResult.artifact_refs"
    )
    return result


def create_anysearch_dispatch(
    *,
    request_id: str,
    task: Mapping[str, Any] | Any,
    query: str,
    attempt_no: int = 1,
    created_by: str = ROOT_OWNER,
) -> dict[str, Any]:
    """Prepare a harness launch using bundled AnySearch before global fallback."""

    if not isinstance(query, str) or not query.strip():
        raise DelegationValidationError("AnySearch input.query must be a non-empty string")
    request = create_delegate_request(
        request_id=request_id,
        task=task,
        attempt_no=attempt_no,
        target="anysearch",
        output_schema="DelegateResult:anysearch_sources",
        created_by=created_by,
    )
    return {
        "delegate_request": request,
        "input": {"query": query.strip()},
        "skill_resolution": [
            {
                "kind": "bundled_snapshot",
                "path": "bundled-skills/anysearch/SKILL.md",
            },
            {"kind": "global_fallback", "skill": "anysearch"},
        ],
    }


def import_anysearch_result(
    value: Mapping[str, Any] | Any,
    *,
    dispatch: Mapping[str, Any] | Any,
) -> dict[str, Any]:
    """Validate AnySearch query/sources or return an explicit availability gap."""

    launch = _plain_mapping(dispatch, label="AnySearchDispatch")
    request = validate_delegate_request(launch.get("delegate_request"))
    if request["target"] != "anysearch":
        raise DelegationValidationError("dispatch is not an AnySearch delegation")
    input_mapping = _plain_mapping(launch.get("input"), label="AnySearchDispatch.input")
    expected_query = _required_text(input_mapping, "query", label="AnySearchDispatch.input")
    result = import_delegate_result(value, request=request)
    if result["status"] == "unavailable":
        if not result["gaps"]:
            result["gaps"] = [
                "bundled and global AnySearch Skills were unavailable; vertical search coverage is missing"
            ]
        result["payload"] = {"query": expected_query, "sources": []}
        return result

    payload = result["payload"]
    query = _required_text(payload, "query", label="DelegateResult.payload")
    if query != expected_query:
        raise DelegationValidationError("AnySearch result query does not match the dispatch")
    sources = _mapping_list(payload.get("sources"), label="DelegateResult.payload.sources")
    normalized_sources: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        label = f"DelegateResult.payload.sources[{index}]"
        normalized = {
            "title": _required_text(source, "title", label=label),
            "url": _required_text(source, "url", label=label),
            "content": _required_text(source, "content", label=label),
        }
        published_at = source.get("published_at")
        if published_at is not None:
            if not isinstance(published_at, str) or not published_at.strip():
                raise DelegationValidationError(
                    f"{label}.published_at must be a non-empty string"
                )
            normalized["published_at"] = published_at.strip()
        normalized_sources.append(normalized)
    result["payload"] = {"query": query, "sources": normalized_sources}
    return result


def summarize_candidates(
    candidates: Sequence[Mapping[str, Any] | Any],
    *,
    grouping_suggestions: Sequence[Mapping[str, Any] | Any] = (),
) -> dict[str, Any]:
    """Estimate context and preserve Root-supplied grouping suggestions."""

    ids: set[str] = set()
    estimated_context_chars = 0
    raw_index: list[dict[str, Any]] = []
    for index, value in enumerate(candidates):
        candidate = _plain_mapping(value, label=f"candidates[{index}]")
        candidate_id = _required_text(candidate, "candidate_id", label=f"candidates[{index}]")
        if candidate_id in ids:
            raise DelegationValidationError(f"duplicate candidate_id: {candidate_id}")
        ids.add(candidate_id)
        fields = [
            candidate.get(key)
            for key in ("title", "canonical_url", "url", "summary", "content")
        ]
        context_chars = sum(len(item) for item in fields if isinstance(item, str))
        estimated_context_chars += context_chars
        raw_index.append(
            {
                "candidate_id": candidate_id,
                "context_chars": context_chars,
                "artifact_refs": _artifact_id_list(
                    candidate.get("artifact_refs"),
                    label=f"candidates[{index}].artifact_refs",
                ),
            }
        )
    groups = [
        _plain_mapping(item, label=f"grouping_suggestions[{index}]")
        for index, item in enumerate(grouping_suggestions)
    ]
    if any(group.get("created_by") != ROOT_OWNER for group in groups):
        raise DelegationValidationError("candidate grouping suggestions must be Root-authored")
    return {
        "count": len(candidates),
        "estimated_context_chars": estimated_context_chars,
        "estimated_context_tokens": (estimated_context_chars + 3) // 4,
        "grouping_suggestions": groups,
        "raw_index": raw_index,
    }


def validate_curator_shards(
    candidate_ids: Iterable[str],
    shard_assignments: Sequence[Mapping[str, Any] | Any],
) -> list[dict[str, Any]]:
    """Validate Root-authored shards without choosing or auto-triggering any."""

    known_ids = set(_string_list(list(candidate_ids), label="candidate_ids"))
    normalized: list[dict[str, Any]] = []
    shard_ids: set[str] = set()
    for index, value in enumerate(shard_assignments):
        shard = _plain_mapping(value, label=f"shard_assignments[{index}]")
        if shard.get("created_by") != ROOT_OWNER:
            raise DelegationValidationError("Curator shard assignments must be Root-authored")
        shard_id = _required_text(shard, "shard_id", label=f"shard_assignments[{index}]")
        if shard_id in shard_ids:
            raise DelegationValidationError(f"duplicate shard_id: {shard_id}")
        shard_ids.add(shard_id)
        assigned = _string_list(
            shard.get("candidate_ids"), label=f"shard_assignments[{index}].candidate_ids"
        )
        if not assigned:
            raise DelegationValidationError(f"Curator shard {shard_id} must not be empty")
        if len(set(assigned)) != len(assigned):
            raise DelegationValidationError(f"Curator shard {shard_id} repeats candidate IDs")
        unknown = sorted(set(assigned) - known_ids)
        if unknown:
            raise DelegationValidationError(
                f"Curator shard {shard_id} contains unknown candidate IDs: {', '.join(unknown)}"
            )
        normalized.append({**shard, "candidate_ids": assigned})
    return normalized


def validate_key_source_proposal(
    value: Mapping[str, Any] | Any,
    *,
    originals: Mapping[str, Mapping[str, Any] | Any],
) -> dict[str, Any]:
    """Validate the canonical proposal and prove every disposition is reversible."""

    proposal = _plain_mapping(value, label="KeySourceProposal")
    _reject_child_control_fields(proposal, label="KeySourceProposal")
    expected_fields = {
        "schema_version",
        "proposal_id",
        "run_id",
        "task_id",
        "step_id",
        "attempt_no",
        "input_candidate_ids",
        "keep_candidate_ids",
        "defer_candidate_ids",
        "reject_candidate_ids",
        "reasons",
        "coverage_gaps",
        "uncertainties",
        "artifact_refs",
    }
    unknown = sorted(set(proposal) - expected_fields)
    if unknown:
        raise DelegationValidationError(
            "KeySourceProposal has fields outside the public contract: " + ", ".join(unknown)
        )
    for key in ("schema_version", "proposal_id", "run_id", "task_id", "step_id"):
        proposal[key] = _required_text(proposal, key, label="KeySourceProposal")
    if proposal["schema_version"] != SCHEMA_VERSION:
        raise DelegationValidationError("KeySourceProposal.schema_version is unsupported")
    attempt_no = proposal.get("attempt_no")
    if isinstance(attempt_no, bool) or not isinstance(attempt_no, int) or attempt_no < 1:
        raise DelegationValidationError("KeySourceProposal.attempt_no must be a positive integer")
    input_ids = _string_list(
        proposal.get("input_candidate_ids"), label="KeySourceProposal.input_candidate_ids"
    )
    if not input_ids or len(set(input_ids)) != len(input_ids):
        raise DelegationValidationError(
            "KeySourceProposal.input_candidate_ids must contain unique candidate IDs"
        )
    original_ids = set(originals)
    missing_originals = sorted(set(input_ids) - original_ids)
    if missing_originals:
        raise DelegationValidationError(
            "KeySourceProposal cannot expand missing originals: " + ", ".join(missing_originals)
        )
    dispositions: list[str] = []
    for field in ("keep_candidate_ids", "defer_candidate_ids", "reject_candidate_ids"):
        proposal[field] = _string_list(proposal.get(field), label=f"KeySourceProposal.{field}")
        dispositions.extend(proposal[field])
    if len(dispositions) != len(set(dispositions)):
        raise DelegationValidationError("a candidate may appear in only one proposal disposition")
    if set(dispositions) != set(input_ids):
        raise DelegationValidationError(
            "KeySourceProposal must preserve every input as kept, deferred, or rejected"
        )
    reasons = _plain_mapping(proposal.get("reasons", {}), label="KeySourceProposal.reasons")
    for candidate_id in dispositions:
        _required_text(reasons, candidate_id, label="KeySourceProposal.reasons")
    extra_reasons = sorted(set(reasons) - set(dispositions))
    if extra_reasons:
        raise DelegationValidationError(
            "KeySourceProposal.reasons contains IDs outside dispositions: "
            + ", ".join(extra_reasons)
        )
    proposal["reasons"] = reasons
    proposal["coverage_gaps"] = _string_list(
        proposal.get("coverage_gaps"), label="KeySourceProposal.coverage_gaps"
    )
    proposal["uncertainties"] = _string_list(
        proposal.get("uncertainties"), label="KeySourceProposal.uncertainties"
    )
    proposal["artifact_refs"] = _artifact_id_list(
        proposal.get("artifact_refs"), label="KeySourceProposal.artifact_refs"
    )
    proposal["input_candidate_ids"] = input_ids
    return proposal


def expand_key_source_proposal(
    value: Mapping[str, Any] | Any,
    *,
    originals: Mapping[str, Mapping[str, Any] | Any],
) -> dict[str, list[dict[str, Any]]]:
    """Expand canonical proposal IDs to original records without deleting data."""

    proposal = validate_key_source_proposal(value, originals=originals)
    original_map = {
        key: _plain_mapping(item, label=f"originals[{key}]") for key, item in originals.items()
    }
    expanded: dict[str, list[dict[str, Any]]] = {}
    for output_name, field in (
        ("retained", "keep_candidate_ids"),
        ("deferred", "defer_candidate_ids"),
        ("rejected", "reject_candidate_ids"),
    ):
        expanded[output_name] = [
            {
                "candidate_id": candidate_id,
                "reason": proposal["reasons"][candidate_id],
                "original": original_map[candidate_id],
            }
            for candidate_id in proposal[field]
        ]
    return expanded


__all__ = [
    "DelegationValidationError",
    "create_anysearch_dispatch",
    "create_delegate_request",
    "expand_key_source_proposal",
    "import_anysearch_result",
    "import_delegate_result",
    "summarize_candidates",
    "validate_curator_shards",
    "validate_delegate_request",
    "validate_key_source_proposal",
]
