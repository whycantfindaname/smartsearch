"""Read-only HTTP visualizer for a Smart Search Research Workspace.

The interaction model is adapted from github/cafe3310/public-agent-skills'
MIT-licensed Deep Research visualizer. See NOTICE.md in this directory.

Only fixed, public workspace projections are exposed. Runtime files, raw
artifacts, configuration, environment files, and caller-selected paths are
never served.
"""

from __future__ import annotations

import argparse
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urlsplit


MAX_JSON_BYTES = 8 * 1024 * 1024
MAX_MARKDOWN_BYTES = 2 * 1024 * 1024
MAX_TRACE_EVENTS = 2_000
TASK_ID_RE = re.compile(r"^task_[A-Za-z0-9][A-Za-z0-9_.-]*$")
REFERENCES_HEADING_RE = re.compile(r"(?im)^#{1,6}\s+references\s*$")

FIXED_MARKDOWN = {
    "initial_context": "initial_context.md",
    "domain_methodology": "domain_methodology.md",
    "main_log": "main_log.md",
    "final_synthesis": "final_synthesis.md",
}
FORBIDDEN_PARTS = frozenset(
    {
        "runtime",
        "raw",
        "raw_artifacts",
        "artifacts",
        ".env",
        "config",
        "configs",
        "secrets",
        "credentials",
    }
)
ATTEMPT_FAILURES = frozenset(
    {
        "failed",
        "timeout",
        "unavailable",
        "missing_key",
        "entitlement_failure",
        "cancelled",
        "degraded",
        "error",
    }
)
SUCCESS_STATUSES = frozenset({"success", "succeeded", "completed", "complete", "verified"})
AGENT_ROLES = frozenset({"search_scout", "source_curator", "evidence_miner", "anysearch", "mineru"})
PUBLIC_TRACE_FIELDS = (
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


class WorkspaceError(ValueError):
    """Raised when a workspace or requested identifier violates the contract."""


def validate_workspace(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise WorkspaceError("workspace must be a directory")
    return root


def _within(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _fixed_path(root: Path, relative: str, *, must_exist: bool = False) -> Path:
    candidate = root.joinpath(relative).resolve(strict=must_exist)
    if not _within(root, candidate):
        raise WorkspaceError("workspace path escapes the workspace root")
    return candidate


def _validate_task_id(task_id: str) -> str:
    if not TASK_ID_RE.fullmatch(task_id) or task_id in {"task_..", "task_."}:
        raise WorkspaceError("invalid task identifier")
    return task_id


def _read_text(path: Path, *, limit: int) -> str:
    if not path.is_file():
        return ""
    if path.stat().st_size > limit:
        raise WorkspaceError(f"public file exceeds {limit} bytes")
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path, default: Any) -> Any:
    text = _read_text(path, limit=MAX_JSON_BYTES)
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    text = _read_text(path, limit=MAX_JSON_BYTES)
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _collection(root: Path, relative: str, keys: Iterable[str]) -> list[dict[str, Any]]:
    path = _fixed_path(root, relative)
    if path.suffix == ".jsonl":
        return _read_jsonl(path)
    value = _read_json(path, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for key in keys:
            items = value.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        if value and all(isinstance(item, dict) for item in value.values()):
            return list(value.values())
    return []


def _dossier(root: Path) -> dict[str, Any]:
    value = _read_json(_fixed_path(root, "latest_dossier.json"), {})
    return value if isinstance(value, dict) else {}


def _run_data(dossier: dict[str, Any]) -> dict[str, Any]:
    run = dossier.get("run")
    return run if isinstance(run, dict) else dossier


def _attempts(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    values = _run_data(dossier).get("attempts", [])
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def _task_dirs(root: Path) -> list[Path]:
    tasks = []
    for path in root.iterdir():
        if path.is_symlink():
            continue
        if path.is_dir() and TASK_ID_RE.fullmatch(path.name):
            tasks.append(path)
    return sorted(tasks, key=lambda item: item.name)


def _pick(mapping: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        value = mapping.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _string_list(value: Any, *, limit: int = 40) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item)[:500] for item in value[:limit] if isinstance(item, (str, int, float))]


def _task_summary(path: Path) -> dict[str, Any]:
    spec = _read_json(path / "task_spec.json", {})
    state = _read_json(path / "task_state.json", {})
    result = _read_json(path / "result.json", {})
    spec = spec if isinstance(spec, dict) else {}
    state = state if isinstance(state, dict) else {}
    result = result if isinstance(result, dict) else {}
    status_text = _read_text(path / "status.txt", limit=4_096).strip()
    status = str(_pick(state, "status", "state", default="")).lower()
    if not status:
        status = str(_pick(result, "status", default=status_text or "pending")).lower()
    role = str(
        _pick(
            state,
            "role",
            default=_pick(spec, "role", "agent_role", "delegate_target", "task_type", default=""),
        )
    )
    name = str(_pick(spec, "question", "task_name", "name", "title", default=path.name))
    return {
        "task_id": path.name,
        "source_task_id": str(_pick(state, "task_id", default=spec.get("task_id", "")))[:160],
        "name": name[:240],
        "role": role[:80],
        "status": status[:80],
        "claim_spec_id": str(_pick(spec, "claim_spec_id", default=""))[:160],
        "has_fragments": (path / "knowledge_fragments.md").is_file(),
        "has_result": (path / "result.json").is_file(),
    }


def _task_is_agent(task: dict[str, Any]) -> bool:
    role = task["role"].lower().replace("-", "_").replace(" ", "_")
    if role in AGENT_ROLES or any(agent in role for agent in AGENT_ROLES):
        return True
    name = task["name"].lower().replace("-", "_").replace(" ", "_")
    return any(agent in name for agent in AGENT_ROLES)


def _citation_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if not isinstance(value, dict):
        return 0
    for key in ("backtrace", "citations", "citation_map", "verified_citations", "results"):
        items = value.get(key)
        if isinstance(items, (list, dict)):
            return len(items)
    for key in ("verified_count", "citation_count", "total"):
        count = value.get(key)
        if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
            return count
    return 0


def _locator_summary(locator: Any) -> str:
    if not isinstance(locator, dict):
        return "No locator"
    kind = str(locator.get("type", "locator"))
    if kind in {"character_range", "page_character_range"}:
        prefix = f"page {locator.get('page')} · " if locator.get("page") else ""
        return f"{prefix}chars {locator.get('start', '?')}–{locator.get('end', '?')}"
    if kind == "repository_line_range":
        return f"{locator.get('file', '?')}:{locator.get('line_start', '?')}–{locator.get('line_end', '?')}"
    if kind == "section":
        return f"section · {locator.get('section', '?')}"
    if kind == "chunk":
        return f"chunk · {locator.get('chunk_id', locator.get('index', '?'))}"
    return kind.replace("_", " ")


def _public_evidence(item: dict[str, Any]) -> dict[str, Any]:
    text = str(_pick(item, "text", "summary", "excerpt", default=""))
    return {
        "evidence_id": str(item.get("evidence_id", ""))[:160],
        "source_id": str(item.get("source_id", ""))[:160],
        "url": str(_pick(item, "canonical_url", "url", default=""))[:2_048],
        "stance": str(item.get("stance", "unknown"))[:40],
        "role": str(_pick(item, "role", "source_role", default=item.get("stance", "evidence")))[:80],
        "locator": _locator_summary(item.get("locator")),
        "task_id": str(item.get("task_id", ""))[:160],
        "claim_spec_id": str(item.get("claim_spec_id", ""))[:160],
        "summary": text[:360],
        "retrieved_at": str(item.get("retrieved_at", ""))[:80],
    }


def _public_failure(item: dict[str, Any]) -> dict[str, Any]:
    status = str(item.get("status", "unknown")).lower()
    return {
        "attempt_id": str(item.get("attempt_id", ""))[:160],
        "provider": str(_pick(item, "provider", "capability", default="unknown"))[:120],
        "capability": str(item.get("capability", ""))[:120],
        "task_id": str(item.get("task_id", ""))[:160],
        "status": status[:80],
        "reason": str(_pick(item, "degraded_reason", "error", "termination_reason", default=status))[:500],
    }


def _public_trace_path(root: Path, manifest: dict[str, Any]) -> Path | None:
    declared = _pick(manifest, "public_trace_path", "safe_trace_path", default="")
    if not isinstance(declared, str) or not declared:
        return None
    relative = Path(declared)
    if relative.is_absolute() or relative.suffix.lower() not in {".json", ".jsonl"}:
        raise WorkspaceError("public trace must be a relative JSON or JSONL path")
    lowered = {part.lower() for part in relative.parts}
    if ".." in relative.parts or lowered & FORBIDDEN_PARTS:
        raise WorkspaceError("public trace path targets a forbidden workspace area")
    path = _fixed_path(root, declared)
    return path if path.is_file() else None


def gather_public_trace(root: Path, manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    manifest = manifest or _read_json(_fixed_path(root, "project_manifest.json"), {})
    if not isinstance(manifest, dict):
        manifest = {}
    path = _public_trace_path(root, manifest)
    if path is None:
        return []
    if path.suffix.lower() == ".jsonl":
        events = _read_jsonl(path)
    else:
        value = _read_json(path, [])
        events = value if isinstance(value, list) else value.get("events", []) if isinstance(value, dict) else []
    projected = []
    for event in events[-MAX_TRACE_EVENTS:]:
        if not isinstance(event, dict):
            continue
        projected.append({key: event[key] for key in PUBLIC_TRACE_FIELDS if key in event})
    return projected


def _parse_main_log(root: Path) -> list[dict[str, Any]]:
    text = _read_text(_fixed_path(root, "main_log.md"), limit=MAX_MARKDOWN_BYTES)
    entries: list[dict[str, Any]] = []
    section = "Run initialized"
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()[:240]
        elif line.startswith(("- ", "* ")):
            entries.append({"source": "main_log", "stage": section, "detail": line[2:].strip()[:600]})
    return entries[-300:]


def gather_activity(root: Path) -> dict[str, Any]:
    manifest = _read_json(_fixed_path(root, "project_manifest.json"), {})
    manifest = manifest if isinstance(manifest, dict) else {}
    log_entries = _parse_main_log(root)
    trace_entries = [
        {
            "source": "public_trace",
            "stage": str(event.get("event_type", "trace event")),
            "detail": " · ".join(
                str(event[key]) for key in ("task_id", "step_id", "event_id") if event.get(key)
            ),
            "timestamp": str(event.get("timestamp", "")),
            "status": str(event.get("event_type", "")),
        }
        for event in gather_public_trace(root, manifest)
    ]
    return {"log": log_entries, "trace": trace_entries, "trace_declared": bool(_pick(manifest, "public_trace_path", "safe_trace_path", default=""))}


def _node_status(has_data: bool, has_active: bool, has_failures: bool) -> str:
    if has_active:
        return "active"
    if has_data and has_failures:
        return "degraded"
    if has_data:
        return "complete"
    return "waiting"


def gather_summary(root: Path) -> dict[str, Any]:
    manifest = _read_json(_fixed_path(root, "project_manifest.json"), {})
    manifest = manifest if isinstance(manifest, dict) else {}
    dossier = _dossier(root)
    run = _run_data(dossier)
    attempts = _attempts(dossier)
    tasks = [_task_summary(path) for path in _task_dirs(root)]
    candidates = _collection(root, "evidence/candidates.jsonl", ("candidates", "items"))
    cards = _collection(root, "evidence/candidate_cards.jsonl", ("candidate_cards", "cards", "items"))
    proposals = _collection(root, "evidence/key_source_proposals.jsonl", ("key_source_proposals", "proposals"))
    evidence = _collection(root, "evidence/evidence_items.jsonl", ("evidence_items", "evidence"))
    claims = _collection(root, "evidence/claim_records.json", ("claim_records", "claims"))
    verification = _read_json(_fixed_path(root, "evidence/citation_verification.json"), {})
    reference_register = _read_json(_fixed_path(root, "evidence/reference_register.json"), {})
    reference_register = reference_register if isinstance(reference_register, dict) else {}
    provider_attempts = [
        item
        for item in attempts
        if item.get("execution_kind") in {"provider_agent", "provider_research_agent"}
    ]
    failures = [_public_failure(item) for item in attempts if str(item.get("status", "")).lower() in ATTEMPT_FAILURES]
    active_statuses = {"pending", "running", "active", "in_progress", "ongoing"}
    has_active = any(task["status"] in active_statuses for task in tasks) or any(
        str(item.get("status", "")).lower() in active_statuses for item in attempts
    )
    citation_count = _citation_count(verification)
    report_path = _fixed_path(root, "final_synthesis.md")
    has_report = report_path.is_file()
    report_text = _read_text(report_path, limit=MAX_MARKDOWN_BYTES) if has_report else ""
    has_report_references = bool(REFERENCES_HEADING_RE.search(report_text))
    registered_references = reference_register.get("references")
    registered_references = registered_references if isinstance(registered_references, list) else []
    entrypoints = manifest.get("entrypoints")
    entrypoints = entrypoints if isinstance(entrypoints, dict) else {}
    counts = {
        "tasks": len(tasks),
        "provider_attempts": len(provider_attempts),
        "agents": sum(1 for task in tasks if _task_is_agent(task)),
        "candidates": len(candidates),
        "candidate_cards": len(cards),
        "proposals": len(proposals),
        "evidence": len(evidence),
        "claims": len(claims),
        "citations": citation_count,
        "references": len(registered_references),
    }
    claim_statuses = Counter(str(item.get("status", "unknown")) for item in claims)
    attempt_statuses = Counter(str(item.get("status", "unknown")) for item in attempts)
    planning_present = bool(run.get("frame") or run.get("claims") or tasks or manifest)
    nodes = [
        {
            "id": "root-plan",
            "index": "01",
            "label": "Root Plan",
            "status": _node_status(planning_present, has_active and not candidates, False),
            "metrics": [{"label": "tasks", "value": counts["tasks"]}, {"label": "claims scoped", "value": len(run.get("claims", [])) if isinstance(run.get("claims"), list) else 0}],
            "description": "Root owns decomposition, ClaimSpecs, constraints, replanning, and stop decisions.",
        },
        {
            "id": "discovery",
            "index": "02",
            "label": "Multi-source Discovery",
            "status": _node_status(bool(candidates or provider_attempts), has_active and not proposals, bool(failures)),
            "metrics": [{"label": "candidates", "value": counts["candidates"]}, {"label": "provider attempts", "value": counts["provider_attempts"]}, {"label": "agents", "value": counts["agents"]}],
            "description": "Independent provider and delegated paths add candidates; one timeout or entitlement failure does not cancel siblings.",
        },
        {
            "id": "curation",
            "index": "03",
            "label": "Source Curation",
            "status": _node_status(bool(proposals), has_active and bool(candidates) and not proposals, False),
            "metrics": [{"label": "candidate cards", "value": counts["candidate_cards"]}, {"label": "proposals", "value": counts["proposals"]}],
            "description": "Curators propose keep, defer, and reject sets. Root retains the source-selection decision.",
        },
        {
            "id": "mining",
            "index": "04",
            "label": "Evidence Mining",
            "status": _node_status(bool(evidence), has_active and bool(proposals) and not evidence, False),
            "metrics": [{"label": "evidence", "value": counts["evidence"]}, {"label": "located", "value": sum(1 for item in evidence if isinstance(item.get("locator"), dict))}],
            "description": "Evidence Miners inspect registered snapshots and return typed locators, stance, and qualitative dimensions.",
        },
        {
            "id": "claims",
            "index": "05",
            "label": "Claims / Citations",
            "status": _node_status(bool(claims or citation_count), has_active and bool(evidence) and not claims, bool(verification) and verification.get("ok") is False),
            "metrics": [{"label": "claims", "value": counts["claims"]}, {"label": "citations verified", "value": counts["citations"]}],
            "description": "ClaimRecords preserve support, contradiction, qualification, gaps, and citation backtraces.",
        },
        {
            "id": "synthesis",
            "index": "06",
            "label": "Final Report / References",
            "status": "complete" if has_report else "active" if has_active and claims else "waiting",
            "metrics": [{"label": "report", "value": "ready" if has_report else "not available"}, {"label": "audit references", "value": counts["references"]}],
            "description": "Reader-facing References live in the final report; the audit reference register preserves internal mappings, while the manifest entrypoints are only a Workspace document index.",
        },
    ]
    return {
        "workspace": {
            "project_name": str(_pick(manifest, "project_name", "name", "title", default="Smart Search Research Run"))[:240],
            "run_id": str(_pick(run, "run_id", default=manifest.get("run_id", "")))[:160],
            "mode": str(_pick(run.get("frame", {}) if isinstance(run.get("frame"), dict) else {}, "mode", "budget", default=manifest.get("mode", "")))[:80],
            "status": str(_pick(manifest, "status", default="active" if has_active else "complete" if has_report else "partial"))[:80],
            "has_final_report": has_report,
            "has_report_references": has_report_references,
            "has_reference_register": bool(reference_register),
            "has_document_index": bool(entrypoints),
            "updated_at": str(_pick(manifest, "updated_at", "last_updated", default=""))[:80],
        },
        "counts": counts,
        "pipeline": nodes,
        "tasks": tasks,
        "failures": failures,
        "evidence": [_public_evidence(item) for item in evidence],
        "claim_statuses": dict(claim_statuses),
        "attempt_statuses": dict(attempt_statuses),
        "gaps": _string_list(run.get("evidence_gaps", [])),
        "root_decision": str(run.get("root_next_decision", ""))[:1_000],
        "stop_reason": str(run.get("stop_reason", ""))[:1_000],
        "citation_verification": {
            "present": bool(verification),
            "ok": verification.get("ok") if isinstance(verification, dict) else None,
            "count": citation_count,
        },
        "projections": {
            "report_references": {
                "present": has_report_references,
                "kind": "reader_projection",
            },
            "reference_register": {
                "present": bool(reference_register),
                "count": len(registered_references),
                "kind": "audit_projection",
            },
            "document_index": {
                "present": bool(entrypoints),
                "count": len(entrypoints),
                "kind": "workspace_navigation",
            },
        },
    }


def gather_task_detail(root: Path, task_id: str) -> dict[str, Any]:
    task_id = _validate_task_id(task_id)
    task_dir = _fixed_path(root, task_id)
    if not task_dir.is_dir():
        raise WorkspaceError("unknown task identifier")
    summary = _task_summary(task_dir)
    spec = _read_json(task_dir / "task_spec.json", {})
    state = _read_json(task_dir / "task_state.json", {})
    result = _read_json(task_dir / "result.json", {})
    spec = spec if isinstance(spec, dict) else {}
    state = state if isinstance(state, dict) else {}
    result = result if isinstance(result, dict) else {}
    source_task_id = summary.get("source_task_id") or task_id
    attempts = [
        item for item in _attempts(_dossier(root)) if item.get("task_id") == source_task_id
    ]
    evidence = [
        _public_evidence(item)
        for item in _collection(root, "evidence/evidence_items.jsonl", ("evidence_items", "evidence"))
        if item.get("task_id") == source_task_id
    ]
    return {
        **summary,
        "objective": str(_pick(spec, "objective", "question", "query", "brief", default=""))[:2_000],
        "scope": _pick(spec, "scope", "constraints", "user_constraints", default={}),
        "allowed_capabilities": _string_list(_pick(spec, "allowed_capabilities", "capabilities", default=[])),
        "expected_output": str(_pick(spec, "expected_output", "output_contract", default=""))[:1_000],
        "started_at": str(_pick(state, "started_at", "created_at", default=""))[:80],
        "completed_at": str(_pick(state, "completed_at", "updated_at", default=""))[:80],
        "gaps": _string_list(_pick(result, "gaps", "coverage_gaps", default=[])),
        "suggestions": _string_list(result.get("suggestions", [])),
        "termination_reason": str(result.get("termination_reason", ""))[:500],
        "usage": result.get("usage", {}) if isinstance(result.get("usage"), dict) else {},
        "attempts": [
            {
                "attempt_id": str(item.get("attempt_id", ""))[:160],
                "provider": str(item.get("provider", ""))[:120],
                "capability": str(item.get("capability", ""))[:120],
                "execution_kind": str(item.get("execution_kind", ""))[:80],
                "status": str(item.get("status", ""))[:80],
                "started_at": str(item.get("started_at", ""))[:80],
                "completed_at": str(item.get("completed_at", ""))[:80],
                "reason": str(_pick(item, "degraded_reason", "error", default=""))[:500],
            }
            for item in attempts
        ],
        "evidence": evidence,
    }


def get_markdown_source(root: Path, document_id: str, *, task_id: str = "") -> str:
    if document_id == "task_knowledge":
        task_id = _validate_task_id(task_id)
        path = _fixed_path(root, f"{task_id}/knowledge_fragments.md")
    elif document_id in FIXED_MARKDOWN:
        path = _fixed_path(root, FIXED_MARKDOWN[document_id])
    else:
        raise WorkspaceError("unknown public document identifier")
    return _read_text(path, limit=MAX_MARKDOWN_BYTES)


class ResearchVisualizerHandler(BaseHTTPRequestHandler):
    server_version = "SmartSearchResearchVisualizer/1"

    @property
    def workspace(self) -> Path:
        return self.server.workspace  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _headers(self, content_type: str, length: int, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()

    def _send(self, body: bytes, content_type: str, status: int = 200) -> None:
        self._headers(content_type, len(body), status)
        self.wfile.write(body)

    def _json(self, value: Any, status: int = 200) -> None:
        body = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        self._send(body, "application/json; charset=utf-8", status)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        parsed = urlsplit(self.path)
        path = unquote(parsed.path)
        try:
            if path in {"/", "/index.html"}:
                body = Path(__file__).with_name("index.html").read_bytes()
                self._send(body, "text/html; charset=utf-8")
            elif path == "/api/summary":
                self._json(gather_summary(self.workspace))
            elif path == "/api/activity":
                self._json(gather_activity(self.workspace))
            elif path.startswith("/api/tasks/"):
                task_id = path.removeprefix("/api/tasks/")
                self._json(gather_task_detail(self.workspace, task_id))
            elif path.startswith("/api/documents/"):
                document_id = path.removeprefix("/api/documents/")
                task_id = parse_qs(parsed.query).get("task", [""])[0]
                body = get_markdown_source(self.workspace, document_id, task_id=task_id).encode("utf-8")
                self._send(body, "text/markdown; charset=utf-8")
            else:
                self._json({"error": "not_found"}, 404)
        except WorkspaceError as exc:
            self._json({"error": "invalid_request", "message": str(exc)}, 400)
        except (OSError, ValueError):
            self._json({"error": "workspace_unavailable"}, 500)


class ResearchVisualizerServer(ThreadingHTTPServer):
    def __init__(self, workspace: Path, port: int) -> None:
        self.workspace = workspace
        super().__init__(("127.0.0.1", port), ResearchVisualizerHandler)


def serve(workspace: str | Path, port: int = 8080) -> None:
    """Serve one validated workspace on the loopback interface."""
    if not 1 <= port <= 65_535:
        raise WorkspaceError("port must be between 1 and 65535")
    root = validate_workspace(workspace)
    with ResearchVisualizerServer(root, port) as server:
        print(f"Smart Search Research Workspace: http://127.0.0.1:{port}")
        server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="View a Smart Search Research Workspace")
    parser.add_argument("workspace", help="Research workspace directory")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65_535:
        parser.error("--port must be between 1 and 65535")
    try:
        workspace = validate_workspace(args.workspace)
    except (OSError, WorkspaceError) as exc:
        parser.error(str(exc))
    serve(workspace, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
