"""Deterministic filesystem projections for one caller-held research dossier.

The dossier, Trace, artifact registry, EvidenceItem, and ClaimRecord contracts
remain authoritative.  This module writes a public-agent-skills-compatible
workspace for people and later visualizers without copying artifact bytes or
turning Markdown into a second source of truth.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .research_contracts import SCHEMA_VERSION, ContractValidationError
from .research_kernel import canonicalize_url
from .research_runtime import ResearchDossier


WORKSPACE_SCHEMA_VERSION = "1"

_CHECKPOINT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_TASK_COMPONENT_RE = re.compile(r"[^A-Za-z0-9_-]+")
_REFERENCES_HEADING_RE = re.compile(r"(?im)^#{1,6}\s+references\s*$")
_NUMBERED_CITATION_RE = re.compile(r"\[([1-9][0-9]*)\]")
_FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "authorization",
        "chain_of_thought",
        "credential",
        "credentials",
        "developer_prompt",
        "hidden_reasoning",
        "id_token",
        "password",
        "private_key",
        "private_reasoning",
        "refresh_token",
        "secret",
        "system_prompt",
    }
)
_DELEGATE_PRIVATE_REASONING_KEYS = frozenset({"analysis", "reasoning", "scratchpad", "thoughts"})
_NONTERMINAL_ATTEMPT_STATUSES = frozenset({"pending", "running"})
_PUBLIC_TRACE_FIELDS = (
    "event_id",
    "run_id",
    "task_id",
    "step_id",
    "attempt_no",
    "parent_event_id",
    "event_type",
    "timestamp",
    "artifact_refs",
)


class ResearchWorkspaceError(ContractValidationError):
    """Raised when a workspace projection would be unsafe or inconsistent."""


def _normalize_key(value: Any) -> str:
    return str(value).strip().lower().replace("-", "_")


def _assert_public(value: Any, *, path: str) -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = _normalize_key(key)
            if (
                normalized in _FORBIDDEN_PUBLIC_KEYS
                or normalized.endswith("_api_key")
                or normalized.endswith("_secret")
                or normalized.endswith("_password")
                or normalized.endswith("_token")
                or (
                    ".delegate_results[" in path
                    and ".payload" in path
                    and normalized in _DELEGATE_PRIVATE_REASONING_KEYS
                )
            ):
                raise ResearchWorkspaceError(
                    f"{path}.{key} may not be projected into a public research workspace"
                )
            _assert_public(child, path=f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _assert_public(child, path=f"{path}[{index}]")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _canonical_jsonl(values: Sequence[Mapping[str, Any]]) -> str:
    return "".join(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for value in values
    )


def _markdown_json(value: Any) -> str:
    return "```json\n" + json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n```"


def _task_directory_name(task_id: str) -> str:
    component = _TASK_COMPONENT_RE.sub("_", task_id).strip("_") or "task"
    component = component[:64]
    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:8]
    return f"task_{component}_{digest}"


def _locator_summary(locator: Mapping[str, Any]) -> str:
    locator_type = str(locator.get("type") or "unknown")
    if locator_type in {"character_range", "page_character_range"}:
        prefix = f"page {locator.get('page')}, " if "page" in locator else ""
        return f"{locator_type}: {prefix}characters {locator.get('start')}–{locator.get('end')}"
    if locator_type == "section":
        return f"section: {locator.get('section')}"
    if locator_type == "chunk":
        identity = locator.get("chunk_id", locator.get("index"))
        return f"chunk: {identity}"
    if locator_type == "repository_line_range":
        return (
            f"repository lines: {locator.get('repository')}@{locator.get('commit')} "
            f"{locator.get('file')}:{locator.get('line_start')}–{locator.get('line_end')}"
        )
    return locator_type


def _validate_reference_register(
    dossier: ResearchDossier,
    *,
    final_synthesis: str | None,
    citation_verification: Mapping[str, Any] | None,
    reference_register: Mapping[str, Any] | None,
) -> None:
    if reference_register is None:
        return
    if final_synthesis is None:
        raise ResearchWorkspaceError(
            "reference_register requires the rendered final_synthesis in the same materialization"
        )
    if citation_verification is None or citation_verification.get("ok") is not True:
        raise ResearchWorkspaceError(
            "reference_register requires a successful citation_verification projection"
        )
    if reference_register.get("schema_version") != "1":
        raise ResearchWorkspaceError("reference_register.schema_version must be 1")
    if reference_register.get("run_id") != dossier.run.run_id:
        raise ResearchWorkspaceError("reference_register belongs to a different research run")
    if reference_register.get("projection") != "derived_audit_reference_register":
        raise ResearchWorkspaceError(
            "reference_register.projection must identify the derived audit projection"
        )
    references = reference_register.get("references")
    if not isinstance(references, list):
        raise ResearchWorkspaceError("reference_register.references must be a list")
    if reference_register.get("reference_count") != len(references):
        raise ResearchWorkspaceError(
            "reference_register.reference_count must match the references list"
        )
    backtrace = citation_verification.get("backtrace")
    if not isinstance(backtrace, Mapping):
        raise ResearchWorkspaceError(
            "citation_verification.backtrace is required for reference_register validation"
        )
    heading_matches = list(_REFERENCES_HEADING_RE.finditer(final_synthesis))
    if references and len(heading_matches) != 1:
        raise ResearchWorkspaceError(
            "a rendered report with references must contain exactly one References section"
        )
    if not references and heading_matches:
        raise ResearchWorkspaceError(
            "a rendered report may not contain References when reference_register is empty"
        )
    report_body = final_synthesis[: heading_matches[0].start()] if heading_matches else final_synthesis
    displayed_numbers = {int(value) for value in _NUMBERED_CITATION_RE.findall(report_body)}
    expected_numbers = list(range(1, len(references) + 1))
    unexpected_numbers = displayed_numbers - set(expected_numbers)
    if unexpected_numbers:
        raise ResearchWorkspaceError(
            "rendered report contains an in-text reference number absent from reference_register"
        )
    known_internal_ids: set[str] = {
        item.candidate_id for item in dossier.candidate_cards
    }
    known_internal_ids.update(item.evidence_id for item in dossier.evidence_items)
    known_internal_ids.update(item.claim_record_id for item in dossier.claim_records)
    seen_citation_ids: set[str] = set()
    seen_source_ids: set[str] = set()
    authoritative_evidence = {
        item.evidence_id: item for item in dossier.evidence_items
    }
    authoritative_claims = {
        item.claim_record_id: item for item in dossier.claim_records
    }
    authoritative_attempts = {
        (item.run_id, item.task_id, item.step_id, item.attempt_no): item
        for item in dossier.run.attempts
    }

    def normalized_url(value: Any, *, label: str) -> str:
        try:
            return canonicalize_url(str(value or ""))
        except ContractValidationError as exc:
            raise ResearchWorkspaceError(f"{label} is not a valid canonical URL") from exc

    for expected_number, reference in zip(expected_numbers, references):
        if not isinstance(reference, Mapping) or reference.get("number") != expected_number:
            raise ResearchWorkspaceError(
                "reference_register reference numbers must be consecutive in display order"
            )
        if expected_number not in displayed_numbers:
            raise ResearchWorkspaceError(
                f"reference {expected_number} is not used by an in-text citation"
            )
        source = reference.get("source")
        citation_ids = reference.get("citation_ids")
        claim_records = reference.get("claim_records")
        evidence_items = reference.get("evidence_items")
        artifacts = reference.get("artifacts")
        if (
            not isinstance(source, Mapping)
            or not isinstance(source.get("canonical_url"), str)
            or not source.get("canonical_url")
            or not str(source.get("canonical_url")).startswith(("http://", "https://"))
        ):
            raise ResearchWorkspaceError(
                f"reference {expected_number} requires canonical source metadata"
            )
        canonical_urls = source.get("canonical_urls")
        bibliographic = source.get("bibliographic")
        if (
            not isinstance(canonical_urls, list)
            or not canonical_urls
            or any(not isinstance(item, str) or not item for item in canonical_urls)
            or not isinstance(bibliographic, Mapping)
        ):
            raise ResearchWorkspaceError(
                f"reference {expected_number} requires canonical URL aliases and bibliographic metadata"
            )
        normalized_source_urls = [
            normalized_url(
                item,
                label=f"reference {expected_number} source canonical URL",
            )
            for item in canonical_urls
        ]
        primary_source_url = normalized_url(
            source.get("canonical_url"),
            label=f"reference {expected_number} primary source URL",
        )
        if (
            primary_source_url not in normalized_source_urls
            or len(normalized_source_urls) != len(set(normalized_source_urls))
        ):
            raise ResearchWorkspaceError(
                f"reference {expected_number} canonical source aliases are inconsistent"
            )
        if not isinstance(citation_ids, list) or not citation_ids:
            raise ResearchWorkspaceError(
                f"reference {expected_number} requires at least one citation_id"
            )
        if any(not isinstance(item, str) or not item for item in citation_ids):
            raise ResearchWorkspaceError(
                f"reference {expected_number} citation_ids must be non-empty strings"
            )
        duplicate_citations = seen_citation_ids.intersection(citation_ids)
        if duplicate_citations:
            raise ResearchWorkspaceError(
                "a citation_id may map to only one displayed reference number"
            )
        seen_citation_ids.update(citation_ids)
        source_id = str(source.get("source_id") or "")
        if not source_id or source_id in seen_source_ids:
            raise ResearchWorkspaceError(
                "reference_register requires one unique stable source_id per displayed reference"
            )
        seen_source_ids.add(source_id)
        if not isinstance(claim_records, list) or not isinstance(evidence_items, list):
            raise ResearchWorkspaceError(
                f"reference {expected_number} requires ClaimRecord and EvidenceItem mappings"
            )
        if not isinstance(artifacts, list) or not artifacts:
            raise ResearchWorkspaceError(
                f"reference {expected_number} requires registered artifact snapshots"
            )
        evidence_by_id = {
            str(item.get("evidence_id") or ""): item
            for item in evidence_items
            if isinstance(item, Mapping)
        }
        artifacts_by_id = {
            str(item.get("artifact_id") or ""): item
            for item in artifacts
            if isinstance(item, Mapping)
        }
        claims_by_id = {
            str(item.get("claim_record_id") or ""): item
            for item in claim_records
            if isinstance(item, Mapping)
        }
        for citation_id in citation_ids:
            verified = backtrace.get(citation_id)
            if not isinstance(verified, Mapping):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} is absent from citation_verification"
                )
            evidence_id = str(verified.get("evidence_id") or "")
            artifact_id = str(verified.get("artifact_id") or "")
            claim_record_id = str(verified.get("claim_record_id") or "")
            evidence_projection = evidence_by_id.get(evidence_id)
            artifact_projection = artifacts_by_id.get(artifact_id)
            claim_projection = claims_by_id.get(claim_record_id)
            evidence_authority = authoritative_evidence.get(evidence_id)
            claim_authority = authoritative_claims.get(claim_record_id)
            if (
                evidence_projection is None
                or artifact_projection is None
                or claim_projection is None
                or evidence_authority is None
                or claim_authority is None
            ):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} has an incomplete claim/evidence/artifact mapping"
                )
            linked_evidence = set(
                claim_authority.support_evidence_ids
                + claim_authority.contradict_evidence_ids
                + claim_authority.qualify_evidence_ids
            )
            if (
                evidence_id not in linked_evidence
                or evidence_authority.claim_spec_id != claim_authority.claim_spec_id
                or evidence_authority.source_id != source_id
            ):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} conflicts with authoritative source or claim identity"
                )
            attempt_authority = authoritative_attempts.get(
                (
                    evidence_authority.run_id,
                    evidence_authority.task_id,
                    evidence_authority.step_id,
                    evidence_authority.attempt_no,
                )
            )
            if attempt_authority is None:
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} has no authoritative attempt"
                )
            authoritative_fields = {
                "claim_record_id": claim_authority.claim_record_id,
                "claim_spec_id": claim_authority.claim_spec_id,
                "evidence_id": evidence_authority.evidence_id,
                "task_id": evidence_authority.task_id,
                "attempt_id": attempt_authority.attempt_id,
                "artifact_id": evidence_authority.artifact_id,
                "snapshot_id": evidence_authority.snapshot_id,
            }
            for field, value in authoritative_fields.items():
                if str(verified.get(field) or "") != str(value):
                    raise ResearchWorkspaceError(
                        f"reference {expected_number} citation {citation_id} conflicts with authoritative {field}"
                    )
            if not isinstance(evidence_projection.get("locator"), Mapping):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} requires a typed locator"
                )
            if claim_projection.get("claim_spec_id") != verified.get("claim_spec_id"):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} conflicts on claim_spec_id"
                )
            for field in ("claim_record_id", "claim_spec_id", "artifact_id", "snapshot_id"):
                if str(evidence_projection.get(field) or verified.get(field) or "") != str(
                    verified.get(field) or ""
                ):
                    raise ResearchWorkspaceError(
                        f"reference {expected_number} citation {citation_id} conflicts on {field}"
                    )
            if artifact_projection.get("snapshot_id") != verified.get("snapshot_id"):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} conflicts on snapshot_id"
                )
            if artifact_projection.get("raw_ref") != verified.get("raw_ref"):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} conflicts on raw_ref"
                )
            projected_evidence_fields = {
                "claim_record_id": claim_authority.claim_record_id,
                "claim_spec_id": evidence_authority.claim_spec_id,
                "task_id": evidence_authority.task_id,
                "step_id": evidence_authority.step_id,
                "attempt_no": evidence_authority.attempt_no,
                "attempt_id": attempt_authority.attempt_id,
                "artifact_id": evidence_authority.artifact_id,
                "snapshot_id": evidence_authority.snapshot_id,
                "retrieved_at": evidence_authority.retrieved_at,
            }
            for field, value in projected_evidence_fields.items():
                if evidence_projection.get(field) != value:
                    raise ResearchWorkspaceError(
                        f"reference {expected_number} citation {citation_id} conflicts on projected {field}"
                    )
            if dict(evidence_projection["locator"]) != dict(evidence_authority.locator):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} conflicts on projected locator"
                )
            evidence_url = normalized_url(
                evidence_authority.canonical_url,
                label=f"reference {expected_number} evidence canonical URL",
            )
            if (
                evidence_url not in normalized_source_urls
                or normalized_url(
                    evidence_projection.get("canonical_url"),
                    label=f"reference {expected_number} projected evidence URL",
                )
                != evidence_url
                or normalized_url(
                    artifact_projection.get("canonical_url"),
                    label=f"reference {expected_number} projected artifact URL",
                )
                != evidence_url
            ):
                raise ResearchWorkspaceError(
                    f"reference {expected_number} citation {citation_id} conflicts on canonical source URL"
                )
        known_internal_ids.update(str(item) for item in citation_ids)
        for collection, fields in (
            (claim_records, ("claim_record_id", "claim_spec_id")),
            (evidence_items, ("evidence_id", "claim_record_id", "claim_spec_id", "artifact_id", "snapshot_id")),
            (artifacts, ("artifact_id", "snapshot_id")),
        ):
            for item in collection:
                if isinstance(item, Mapping):
                    known_internal_ids.update(
                        str(item[field]) for field in fields if item.get(field)
                    )

    if heading_matches:
        human_references = final_synthesis[heading_matches[0].start() :]
        leaked = next(
            (identity for identity in sorted(known_internal_ids) if identity in human_references),
            "",
        )
        if leaked:
            raise ResearchWorkspaceError(
                "the reader-facing References section may not contain internal audit identifiers"
            )


class ResearchWorkspace:
    """Materialize one ResearchDossier into a deterministic run workspace.

    ``artifact_root`` follows the runtime API: it is the parent directory that
    contains the run-id directory.  Artifact bytes are never copied.
    """

    def __init__(
        self,
        workspace_root: str | os.PathLike[str],
        *,
        artifact_root: str | os.PathLike[str] | None = None,
    ) -> None:
        self.root = self._resolve_input_path(workspace_root, label="workspace_root")
        self.artifact_root = (
            self._resolve_input_path(artifact_root, label="artifact_root")
            if artifact_root is not None
            else None
        )

    @staticmethod
    def _resolve_input_path(value: str | os.PathLike[str], *, label: str) -> Path:
        path = Path(value).expanduser()
        if ".." in path.parts:
            raise ResearchWorkspaceError(f"{label} may not contain parent traversal")
        return path.resolve()

    def _destination(self, relative: str | Path) -> Path:
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise ResearchWorkspaceError("workspace output path escapes the workspace root")
        destination = self.root / relative_path
        if destination == self.root:
            return destination
        parent = destination.parent.resolve()
        if parent != self.root and self.root not in parent.parents:
            raise ResearchWorkspaceError("workspace output path escapes the workspace root")
        return destination

    def _mkdir(self, relative: str | Path = ".") -> Path:
        destination = self._destination(relative)
        if destination.exists() and not destination.is_dir():
            raise ResearchWorkspaceError(f"workspace directory path is not a directory: {destination}")
        destination.mkdir(parents=True, exist_ok=True)
        resolved = destination.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ResearchWorkspaceError("workspace directory resolves outside the workspace root")
        return destination

    def _atomic_write(self, relative: str | Path, content: str) -> Path:
        destination = self._destination(relative)
        self._mkdir(destination.parent.relative_to(self.root))
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return destination

    def _remove_generated_file(self, relative: str | Path) -> None:
        destination = self._destination(relative)
        if destination.is_symlink() or destination.is_file():
            destination.unlink()

    def _assert_workspace_identity(self, dossier: ResearchDossier) -> None:
        manifest_path = self._destination("project_manifest.json")
        if not manifest_path.exists():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ResearchWorkspaceError("existing project_manifest.json is unreadable") from exc
        if not isinstance(manifest, Mapping) or manifest.get("run_id") != dossier.run.run_id:
            raise ResearchWorkspaceError("workspace already belongs to a different research run")

    def _artifact_refs(self, dossier: ResearchDossier) -> dict[str, str]:
        if self.artifact_root is None:
            return {}
        run_directory = (self.artifact_root / dossier.run.run_id).resolve()
        try:
            run_reference = run_directory.relative_to(self.root).as_posix()
        except ValueError:
            run_reference = str(run_directory)

        def resolve_run_ref(value: str) -> str:
            return str(Path(run_reference) / value) if value else ""

        return {
            "artifact_run_directory": run_reference,
            "artifact_registry": resolve_run_ref(dossier.run.artifact_index_ref),
            "trace": resolve_run_ref(dossier.run.trace_ref),
        }

    def _project_public_trace(self, dossier: ResearchDossier) -> bool:
        """Copy only public Trace identity metadata into the visible workspace."""
        if self.artifact_root is None or not dossier.run.trace_ref:
            return False
        source = (self.artifact_root / dossier.run.run_id / dossier.run.trace_ref).resolve()
        run_root = (self.artifact_root / dossier.run.run_id).resolve()
        if source != run_root and run_root not in source.parents:
            raise ResearchWorkspaceError("Trace reference escapes the run artifact directory")
        if not source.is_file():
            return False

        projected: list[dict[str, Any]] = []
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ResearchWorkspaceError(
                    f"Trace line {line_number} is not valid JSON"
                ) from exc
            if not isinstance(event, Mapping):
                raise ResearchWorkspaceError(f"Trace line {line_number} is not an object")
            projected.append(
                {key: event[key] for key in _PUBLIC_TRACE_FIELDS if key in event}
            )
        self._atomic_write("public_trace.jsonl", _canonical_jsonl(projected))
        return True

    @staticmethod
    def _phase(dossier: ResearchDossier) -> tuple[str, str]:
        if dossier.run.stop_reason:
            return "completed", "root_decision"
        if dossier.run.root_next_decision:
            return "in_progress", "root_decision"
        if dossier.claim_records:
            return "in_progress", "claim_assessment"
        if dossier.evidence_items or dossier.evidence_mining_tasks:
            return "in_progress", "evidence_mining"
        if dossier.key_source_proposals:
            return "in_progress", "source_curation"
        if dossier.candidates or dossier.run.attempts:
            return "in_progress", "discovery"
        return "in_progress", "initialization"

    @staticmethod
    def _observed_timestamps(dossier: ResearchDossier) -> list[str]:
        values = [dossier.run.capability_observed_at]
        for attempt in dossier.run.attempts:
            values.extend((attempt.started_at, attempt.deadline_at, attempt.completed_at))
        return sorted({value for value in values if value})

    def _task_layout(self, dossier: ResearchDossier) -> list[tuple[Any, str]]:
        tasks = dossier.search_tasks + dossier.evidence_mining_tasks
        names: dict[str, str] = {}
        layout: list[tuple[Any, str]] = []
        for task in tasks:
            name = _task_directory_name(task.task_id)
            other = names.get(name)
            if other is not None and other != task.task_id:
                raise ResearchWorkspaceError("task directory identity collision")
            names[name] = task.task_id
            layout.append((task, name))
        return layout

    def _manifest(
        self,
        dossier: ResearchDossier,
        task_layout: Sequence[tuple[Any, str]],
        *,
        citation_verification_available: bool,
        reference_register_available: bool,
        public_trace_available: bool,
    ) -> dict[str, Any]:
        status, phase = self._phase(dossier)
        entrypoints: dict[str, Any] = {
            "initial_context": "initial_context.md",
            "domain_methodology": "domain_methodology.md",
            "main_log": "main_log.md",
            "latest_dossier": "latest_dossier.json",
            "checkpoints": "checkpoints/",
            "evidence": "evidence/",
            "tasks": {task.task_id: f"{directory}/" for task, directory in task_layout},
        }
        if self._destination("final_synthesis.md").is_file():
            entrypoints["final_synthesis"] = "final_synthesis.md"
        if citation_verification_available:
            entrypoints["citation_verification"] = "evidence/citation_verification.json"
        if reference_register_available:
            entrypoints["reference_register"] = "evidence/reference_register.json"
        if public_trace_available:
            entrypoints["public_trace"] = "public_trace.jsonl"
        entrypoints.update(self._artifact_refs(dossier))
        observed_timestamps = self._observed_timestamps(dossier)
        return {
            "schema_version": WORKSPACE_SCHEMA_VERSION,
            "dossier_schema_version": dossier.schema_version,
            "project_name": dossier.run.frame.question,
            "run_id": dossier.run.run_id,
            "goal": dossier.run.frame.question,
            "question": dossier.run.frame.question,
            "mode": dossier.run.frame.mode,
            "status": status,
            "current_phase": phase,
            "observed_timestamps": observed_timestamps,
            "updated_at": observed_timestamps[-1] if observed_timestamps else "",
            "public_trace_path": "public_trace.jsonl" if public_trace_available else "",
            "counts": {
                "search_tasks": len(dossier.search_tasks),
                "evidence_mining_tasks": len(dossier.evidence_mining_tasks),
                "execution_attempts": len(dossier.run.attempts),
                "delegate_requests": len(dossier.delegate_requests),
                "delegate_results": len(dossier.delegate_results),
                "candidates": len(dossier.candidates),
                "candidate_cards": len(dossier.candidate_cards),
                "key_source_proposals": len(dossier.key_source_proposals),
                "evidence_items": len(dossier.evidence_items),
                "claim_records": len(dossier.claim_records),
            },
            "entrypoints": entrypoints,
        }

    @staticmethod
    def _initial_context(dossier: ResearchDossier) -> str:
        frame = dossier.run.frame
        claims = [
            {
                "claim_spec_id": claim.claim_spec_id,
                "statement": claim.statement,
                "terms_scope": claim.terms_scope,
                "time_boundary": claim.time_boundary,
                "decision_criteria": claim.decision_criteria,
            }
            for claim in dossier.run.claims
        ]
        return (
            "# Initial Context\n\n"
            "## User Question\n\n"
            f"{frame.question}\n\n"
            "## Scope and Constraints\n\n"
            + _markdown_json(
                {
                    "scope": frame.scope,
                    "time_boundary": frame.time_boundary,
                    "source_preferences": frame.source_preferences,
                    "user_constraints": frame.user_constraints,
                    "permissions": frame.permissions,
                    "untrusted_content_policy": frame.untrusted_content_policy,
                }
            )
            + "\n\n## Initial Claim Frame\n\n"
            + (_markdown_json(claims) if claims else "No initial claims were supplied.")
            + "\n"
        )

    @staticmethod
    def _domain_methodology(dossier: ResearchDossier) -> str:
        return (
            "# Domain Methodology\n\n"
            "This workspace follows the supplied ResearchDossier contract; it does not require "
            "or imply a separate methodology agent.\n\n"
            "## Evidence Method\n\n"
            "- DiscoveryCandidate and CandidateCard records are discovery inputs, not proof.\n"
            "- KeySourceProposal records preserve retain, defer, and reject recommendations; Root "
            "remains responsible for source selection.\n"
            "- EvidenceItem records bind a ClaimSpec to a canonical source URL, immutable artifact "
            "snapshot, typed locator, stance, and qualitative evidence dimensions.\n"
            "- ClaimRecord status is derived from linked support, contradiction, qualification, "
            "conflicts, and explicit gaps; no synthetic evidence score is introduced here.\n\n"
            "## Citation and Source Handling\n\n"
            "- Final citations must reverse-trace through ClaimRecord and EvidenceItem to the task, "
            "attempt, artifact, snapshot, and raw reference.\n"
            "- Trace records observable execution facts and public decisions; it is separate from "
            "evidence provenance and does not prove source truth.\n"
            "- Provider response bodies and artifact bytes are not copied into these Markdown "
            "projections. Direct source URLs and bounded EvidenceItem text remain available for review.\n\n"
            f"Current dossier declares {len(dossier.run.claims)} ClaimSpec records and "
            f"{len(dossier.evidence_items)} EvidenceItem records.\n"
        )

    @staticmethod
    def _main_log(
        dossier: ResearchDossier,
        *,
        citation_verification: Mapping[str, Any] | None,
    ) -> str:
        lines = [
            f"# Research Log: {dossier.run.frame.question}",
            "",
            "## Phase 1: Initialization",
            "",
            f"- Run `{dossier.run.run_id}` initialized in `{dossier.run.frame.mode}` mode.",
            f"- Root supplied {len(dossier.run.claims)} claims and "
            f"{len(dossier.search_tasks)} initial/current search tasks.",
        ]
        if dossier.run.capability_observed_at:
            lines.append(f"- Capability snapshot observed at `{dossier.run.capability_observed_at}`.")

        lines.extend(["", "## Phase 2: Discovery", ""])
        lines.append(
            f"- Observed {len(dossier.run.attempts)} execution attempts and retained "
            f"{len(dossier.candidates)} normalized candidates."
        )
        for attempt in dossier.run.attempts:
            provider = f" via `{attempt.provider}`" if attempt.provider else ""
            lines.append(
                f"- Task `{attempt.task_id}` / `{attempt.capability}`{provider}: `{attempt.status}`."
            )
            if attempt.error:
                lines.append(f"  - Public error: {attempt.error}")
            if attempt.degraded_reason:
                lines.append(f"  - Degraded reason: {attempt.degraded_reason}")

        if dossier.key_source_proposals:
            lines.extend(["", "## Phase 3: Source Curation", ""])
            for proposal in dossier.key_source_proposals:
                lines.append(
                    f"- Proposal `{proposal.proposal_id}` retained {len(proposal.keep_candidate_ids)}, "
                    f"deferred {len(proposal.defer_candidate_ids)}, and rejected "
                    f"{len(proposal.reject_candidate_ids)} candidates."
                )

        if dossier.evidence_mining_tasks or dossier.evidence_items:
            lines.extend(["", "## Phase 4: Evidence Mining", ""])
            lines.append(
                f"- Root assigned {len(dossier.evidence_mining_tasks)} evidence tasks; "
                f"{len(dossier.evidence_items)} EvidenceItem records are present."
            )
            for gap in dossier.run.evidence_gaps:
                lines.append(f"- Evidence gap: {gap}")

        if dossier.claim_records:
            lines.extend(["", "## Phase 5: Claim Assessment", ""])
            for claim in dossier.claim_records:
                lines.append(
                    f"- Claim `{claim.claim_spec_id}` is `{claim.status}` with "
                    f"{len(claim.support_evidence_ids)} support, "
                    f"{len(claim.contradict_evidence_ids)} contradiction, and "
                    f"{len(claim.qualify_evidence_ids)} qualification records."
                )

        if dossier.run.root_next_decision or dossier.run.stop_reason:
            lines.extend(["", "## Phase 6: Root Decision", ""])
            if dossier.run.root_next_decision:
                lines.append(f"- Next decision: {dossier.run.root_next_decision}")
            if dossier.run.stop_reason:
                lines.append(f"- Stop reason: {dossier.run.stop_reason}")

        if citation_verification is not None:
            lines.extend(["", "## Phase 7: Citation Verification", ""])
            lines.append(
                f"- Supplied verification status: `{citation_verification.get('ok')}`; "
                f"citation count: `{citation_verification.get('citation_count', 'unknown')}`."
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _task_role(task: Any, requests: Sequence[Any]) -> str:
        targets = sorted({request.target for request in requests})
        if targets:
            return ",".join(targets)
        if hasattr(task, "artifact_ids"):
            return "evidence_miner"
        return "internal_search"

    @staticmethod
    def _task_status(attempts: Sequence[Any], requests: Sequence[Any], results: Sequence[Any]) -> str:
        if requests:
            completed_request_ids = {result.request_id for result in results}
            if all(request.request_id in completed_request_ids for request in requests):
                return "completed"
        if attempts:
            if any(attempt.status == "running" for attempt in attempts):
                return "running"
            if all(attempt.status not in _NONTERMINAL_ATTEMPT_STATUSES for attempt in attempts):
                return "completed"
        return "pending"

    @staticmethod
    def _candidate_fragment(candidate: Any) -> list[str]:
        lines = [
            f"## Candidate: {candidate.title}",
            "",
            f"- Candidate ID: `{candidate.candidate_id}`",
            f"- Source URL: {candidate.canonical_url}",
            f"- Source type: `{candidate.source_type}`",
        ]
        if candidate.summary:
            lines.extend([f"- Summary: {candidate.summary}"])
        if candidate.discovery_path:
            lines.append(f"- Discovery path: {', '.join(candidate.discovery_path)}")
        return lines

    def _knowledge_fragments(
        self,
        task: Any,
        *,
        candidates: Sequence[Any],
        proposals: Sequence[Any],
        evidence_items: Sequence[Any],
        attempts: Sequence[Any],
        results: Sequence[Any],
        candidate_by_id: Mapping[str, Any],
    ) -> str:
        lines = [f"# Knowledge Fragments: {task.task_id}"]
        for candidate in candidates:
            lines.extend(["", ""] + self._candidate_fragment(candidate))

        for proposal in proposals:
            lines.extend(["", "", f"## Source Proposal: {proposal.proposal_id}", ""])
            dispositions = (
                ("Retained", proposal.keep_candidate_ids),
                ("Deferred", proposal.defer_candidate_ids),
                ("Rejected", proposal.reject_candidate_ids),
            )
            for label, candidate_ids in dispositions:
                for candidate_id in candidate_ids:
                    candidate = candidate_by_id.get(candidate_id)
                    url = f" — {candidate.canonical_url}" if candidate is not None else ""
                    reason = proposal.reasons.get(candidate_id, "No reason supplied")
                    lines.append(f"- {label} `{candidate_id}`{url}: {reason}")
            for gap in proposal.coverage_gaps:
                lines.append(f"- Coverage gap: {gap}")
            for uncertainty in proposal.uncertainties:
                lines.append(f"- Uncertainty: {uncertainty}")

        for evidence in evidence_items:
            lines.extend(
                [
                    "",
                    "",
                    f"## EvidenceItem: {evidence.evidence_id}",
                    "",
                    f"- Claim: `{evidence.claim_spec_id}`",
                    f"- Stance: `{evidence.stance}`",
                    f"- Source URL: {evidence.canonical_url}",
                    f"- Locator: {_locator_summary(evidence.locator)}",
                    f"- Evidence: {evidence.text}",
                    "- Qualitative dimensions:",
                ]
            )
            for name, value in sorted(evidence.quality.items()):
                lines.append(f"  - {name}: {value}")

        for attempt in attempts:
            lines.extend(
                [
                    "",
                    "",
                    f"## Attempt Outcome: {attempt.attempt_id}",
                    "",
                    f"- Capability: `{attempt.capability}`",
                    f"- Provider: `{attempt.provider or 'not supplied'}`",
                    f"- Status: `{attempt.status}`",
                ]
            )
            if attempt.error:
                lines.append(f"- Public error: {attempt.error}")
            if attempt.degraded_reason:
                lines.append(f"- Degraded reason: {attempt.degraded_reason}")

        for result in results:
            for gap in result.gaps:
                lines.extend(["", "", "## Reported Gap", "", f"- {gap}"])
            if result.termination_reason:
                lines.extend(
                    ["", "", "## Termination Outcome", "", f"- {result.termination_reason}"]
                )
        if len(lines) == 1:
            lines.extend(["", "No public results have been recorded for this task."])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _public_delegate_result(result: Any) -> dict[str, Any]:
        return {
            "schema_version": result.schema_version,
            "result_id": result.result_id,
            "request_id": result.request_id,
            "run_id": result.run_id,
            "task_id": result.task_id,
            "step_id": result.step_id,
            "attempt_no": result.attempt_no,
            "status": result.status,
            "elapsed_ms": result.elapsed_ms,
            "gaps": result.gaps,
            "suggestions": result.suggestions,
            "termination_reason": result.termination_reason,
            "artifact_refs": result.artifact_refs,
        }

    def _write_task(self, dossier: ResearchDossier, task: Any, directory: str) -> None:
        attempts = [item for item in dossier.run.attempts if item.task_id == task.task_id]
        requests = [item for item in dossier.delegate_requests if item.task_id == task.task_id]
        request_ids = {item.request_id for item in requests}
        results = [item for item in dossier.delegate_results if item.request_id in request_ids]
        candidates = [item for item in dossier.candidates if item.task_id == task.task_id]
        proposals = [item for item in dossier.key_source_proposals if item.task_id == task.task_id]
        evidence_items = [item for item in dossier.evidence_items if item.task_id == task.task_id]
        candidate_by_id = {item.candidate_id: item for item in dossier.candidates}
        status = self._task_status(attempts, requests, results)

        self._mkdir(directory)
        self._atomic_write(f"{directory}/task_spec.json", _canonical_json(task.to_dict()))
        self._atomic_write(
            f"{directory}/task_state.json",
            _canonical_json(
                {
                    "schema_version": WORKSPACE_SCHEMA_VERSION,
                    "run_id": dossier.run.run_id,
                    "task_id": task.task_id,
                    "role": self._task_role(task, requests),
                    "status": status,
                    "attempt_count": len(attempts),
                    "attempt_statuses": [item.status for item in attempts],
                    "delegate_request_ids": [item.request_id for item in requests],
                    "delegate_result_ids": [item.result_id for item in results],
                    "result_counts": {
                        "candidates": len(candidates),
                        "key_source_proposals": len(proposals),
                        "evidence_items": len(evidence_items),
                    },
                }
            ),
        )
        self._atomic_write(
            f"{directory}/knowledge_fragments.md",
            self._knowledge_fragments(
                task,
                candidates=candidates,
                proposals=proposals,
                evidence_items=evidence_items,
                attempts=attempts,
                results=results,
                candidate_by_id=candidate_by_id,
            ),
        )
        if status == "completed":
            self._atomic_write(f"{directory}/status.txt", "Completed")
        else:
            self._remove_generated_file(f"{directory}/status.txt")

        has_results = bool(attempts or results or candidates or proposals or evidence_items)
        if has_results:
            self._atomic_write(
                f"{directory}/result.json",
                _canonical_json(
                    {
                        "schema_version": WORKSPACE_SCHEMA_VERSION,
                        "run_id": dossier.run.run_id,
                        "task_id": task.task_id,
                        "attempts": [item.to_dict() for item in attempts],
                        "delegate_results": [self._public_delegate_result(item) for item in results],
                        "candidates": [item.to_dict() for item in candidates],
                        "key_source_proposals": [item.to_dict() for item in proposals],
                        "evidence_items": [item.to_dict() for item in evidence_items],
                    }
                ),
            )
        else:
            self._remove_generated_file(f"{directory}/result.json")

    def write_checkpoint(self, dossier: ResearchDossier, label: str) -> Path:
        """Write one immutable named dossier snapshot, or accept an exact replay."""
        if not isinstance(label, str) or not _CHECKPOINT_RE.fullmatch(label) or label in {".", ".."}:
            raise ResearchWorkspaceError("checkpoint label must be a safe filesystem label")
        dossier_payload = dossier.to_dict()
        _assert_public(dossier_payload, path="ResearchDossier")
        self._mkdir("checkpoints")
        destination = self._destination(f"checkpoints/{label}.json")
        if destination.exists():
            try:
                existing = json.loads(destination.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ResearchWorkspaceError(f"checkpoint {label!r} is unreadable") from exc
            if existing != dossier_payload:
                raise ResearchWorkspaceError(
                    f"checkpoint {label!r} already contains a different dossier snapshot"
                )
            return destination
        return self._atomic_write(f"checkpoints/{label}.json", _canonical_json(dossier_payload))

    def materialize(
        self,
        dossier: ResearchDossier,
        *,
        checkpoint_labels: Sequence[str] = (),
        final_synthesis: str | None = None,
        citation_verification: Mapping[str, Any] | None = None,
        reference_register: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Write deterministic projections and return the manifest payload."""
        if not isinstance(dossier, ResearchDossier):
            raise ResearchWorkspaceError("dossier must be a ResearchDossier")
        if isinstance(checkpoint_labels, (str, bytes)):
            raise ResearchWorkspaceError("checkpoint_labels must be a sequence of labels")
        for label in checkpoint_labels:
            if not isinstance(label, str) or not _CHECKPOINT_RE.fullmatch(label) or label in {".", ".."}:
                raise ResearchWorkspaceError("checkpoint label must be a safe filesystem label")
        if final_synthesis is not None and (
            not isinstance(final_synthesis, str) or not final_synthesis.strip()
        ):
            raise ResearchWorkspaceError("final_synthesis must be non-empty text when supplied")
        if citation_verification is not None and not isinstance(citation_verification, Mapping):
            raise ResearchWorkspaceError("citation_verification must be an object when supplied")
        if reference_register is not None and not isinstance(reference_register, Mapping):
            raise ResearchWorkspaceError("reference_register must be an object when supplied")

        dossier_payload = dossier.to_dict()
        _assert_public(dossier_payload, path="ResearchDossier")
        if citation_verification is not None:
            _assert_public(citation_verification, path="citation_verification")
        if reference_register is not None:
            _assert_public(reference_register, path="reference_register")
        _validate_reference_register(
            dossier,
            final_synthesis=final_synthesis,
            citation_verification=citation_verification,
            reference_register=reference_register,
        )

        self._mkdir()
        self._assert_workspace_identity(dossier)
        task_layout = self._task_layout(dossier)
        public_trace_available = self._project_public_trace(dossier)
        for label in checkpoint_labels:
            self.write_checkpoint(dossier, label)

        self._mkdir("evidence")
        self._atomic_write(
            "evidence/candidates.jsonl",
            _canonical_jsonl([item.to_dict() for item in dossier.candidates]),
        )
        self._atomic_write(
            "evidence/candidate_cards.jsonl",
            _canonical_jsonl([item.to_dict() for item in dossier.candidate_cards]),
        )
        self._atomic_write(
            "evidence/key_source_proposals.jsonl",
            _canonical_jsonl([item.to_dict() for item in dossier.key_source_proposals]),
        )
        self._atomic_write(
            "evidence/evidence_items.jsonl",
            _canonical_jsonl([item.to_dict() for item in dossier.evidence_items]),
        )
        self._atomic_write(
            "evidence/claim_records.json",
            _canonical_json(
                {
                    "schema_version": SCHEMA_VERSION,
                    "claim_records": [item.to_dict() for item in dossier.claim_records],
                }
            ),
        )
        if citation_verification is not None:
            self._atomic_write(
                "evidence/citation_verification.json",
                _canonical_json(dict(citation_verification)),
            )
        if reference_register is not None:
            self._atomic_write(
                "evidence/reference_register.json",
                _canonical_json(dict(reference_register)),
            )
        if final_synthesis is not None:
            # A caller-supplied legacy report is a new report projection.  Do
            # not leave an audit register from an earlier finalized report
            # attached to it after all run-identity checks have passed.
            if reference_register is None:
                self._remove_generated_file("evidence/reference_register.json")
            self._atomic_write("final_synthesis.md", final_synthesis)

        for task, directory in task_layout:
            self._write_task(dossier, task, directory)

        citation_available = (
            citation_verification is not None
            or self._destination("evidence/citation_verification.json").is_file()
        )
        reference_register_available = (
            reference_register is not None
            or self._destination("evidence/reference_register.json").is_file()
        )
        manifest = self._manifest(
            dossier,
            task_layout,
            citation_verification_available=citation_available,
            reference_register_available=reference_register_available,
            public_trace_available=public_trace_available,
        )
        self._atomic_write("latest_dossier.json", _canonical_json(dossier_payload))
        self._atomic_write("initial_context.md", self._initial_context(dossier))
        self._atomic_write("domain_methodology.md", self._domain_methodology(dossier))
        self._atomic_write(
            "main_log.md",
            self._main_log(dossier, citation_verification=citation_verification),
        )
        self._atomic_write("project_manifest.json", _canonical_json(manifest))
        return manifest


__all__ = [
    "WORKSPACE_SCHEMA_VERSION",
    "ResearchWorkspace",
    "ResearchWorkspaceError",
]
