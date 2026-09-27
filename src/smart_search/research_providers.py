"""Isolated lifecycle adapters for Provider Research Agents.

The adapters in this module deliberately stop at the discovery-candidate layer.
Provider reports and citations are useful research artifacts, but cited sources
must be read again before they can become claim evidence.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Mapping, Protocol, Sequence

import httpx

from .config import config


ATTEMPT_SCHEMA_VERSION = "1"
ATTEMPT_STATUSES = frozenset(
    {
        "not_configured",
        "unreachable",
        "entitlement_denied",
        "timeout",
        "partial",
        "succeeded",
        "failed",
    }
)


class HTTPResponse(Protocol):
    status_code: int
    text: str

    def json(self) -> Any: ...


class AsyncHTTPTransport(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> HTTPResponse: ...


class HTTPXTransport:
    """Small default transport; tests can inject an in-memory implementation."""

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=config.ssl_verify_enabled) as client:
            return await client.request(method, url, headers=dict(headers), json=json)


@dataclass(frozen=True)
class LifecycleResult:
    raw_response: Mapping[str, Any]
    status: str


@dataclass
class ExecutionAttempt:
    provider: str
    provider_api_version: str
    attempt_no: int
    configured: bool
    started_at: str
    deadline_at: str
    observed_at: str
    request_summary: dict[str, Any]
    run_id: str = ""
    task_id: str = ""
    step_id: str = ""
    schema_version: str = ATTEMPT_SCHEMA_VERSION
    execution_kind: str = "provider_research_agent"
    capability: str = "provider_research"
    status: str = "failed"
    reachable: bool | None = None
    entitled: bool | None = None
    completed_at: str = ""
    external_job: dict[str, Any] = field(default_factory=lambda: {"id": "", "cursor": None})
    usage: dict[str, Any] = field(default_factory=dict)
    artifact_refs: list[str] = field(default_factory=list)
    artifact: dict[str, Any] = field(default_factory=dict)
    report: Any = ""
    candidates: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        if self.status not in ATTEMPT_STATUSES:
            raise ValueError(f"invalid research provider status: {self.status}")
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "step_id": self.step_id,
            "attempt_no": self.attempt_no,
            "execution_kind": self.execution_kind,
            "provider": self.provider,
            "provider_api_version": self.provider_api_version,
            "capability": self.capability,
            "status": self.status,
            "configured": self.configured,
            "reachable": self.reachable,
            "entitled": self.entitled,
            "observed_at": self.observed_at,
            "external_job": self.external_job,
            "timestamps": {
                "started_at": self.started_at,
                "deadline_at": self.deadline_at,
                "completed_at": self.completed_at,
            },
            "request_summary": self.request_summary,
            "usage": self.usage,
            "artifact_refs": self.artifact_refs,
            "artifact": self.artifact,
            "report": self.report,
            "candidates": self.candidates,
            "errors": self.errors,
        }


class AdapterFailure(RuntimeError):
    def __init__(
        self,
        status: str,
        error_type: str,
        message: str,
        *,
        http_status: int | None = None,
        raw_response: Any = None,
    ):
        super().__init__(message)
        self.status = status
        self.error_type = error_type
        self.message = message
        self.http_status = http_status
        self.raw_response = raw_response


Clock = Callable[[], float]
Sleep = Callable[[float], Awaitable[None]]


def _iso_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _safe_value(value: Any, *, secret: str) -> Any:
    """Recursively remove credential fields and redact the configured key."""
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in {
                "api_key",
                "apikey",
                "x_api_key",
                "authorization",
                "access_token",
                "refresh_token",
                "token",
                "secret",
                "password",
            }:
                safe[str(key)] = "[REDACTED]"
            else:
                safe[str(key)] = _safe_value(item, secret=secret)
        return safe
    if isinstance(value, (list, tuple)):
        return [_safe_value(item, secret=secret) for item in value]
    if isinstance(value, str) and secret:
        return value.replace(secret, "[REDACTED]")
    return value


def _compact_message(value: Any, *, secret: str, limit: int = 500) -> str:
    safe = _safe_value(value, secret=secret)
    if isinstance(safe, str):
        text = safe
    else:
        try:
            text = json.dumps(safe, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(safe)
    return " ".join(text.split())[:limit]


def _response_json(response: HTTPResponse, *, secret: str) -> Mapping[str, Any]:
    try:
        data = response.json()
    except Exception as exc:
        raise AdapterFailure(
            "failed",
            "malformed_response",
            f"provider returned invalid JSON: {_compact_message(exc, secret=secret)}",
            http_status=response.status_code,
            raw_response=response.text,
        ) from exc
    if not isinstance(data, Mapping):
        raise AdapterFailure(
            "failed",
            "malformed_response",
            "provider response must be a JSON object",
            http_status=response.status_code,
            raw_response=data,
        )
    return data


def _http_failure(response: HTTPResponse, *, secret: str) -> AdapterFailure:
    status_code = response.status_code
    try:
        raw: Any = response.json()
    except Exception:
        raw = response.text
    message = f"HTTP {status_code}: {_compact_message(raw, secret=secret)}"
    if status_code in {401, 402, 403}:
        return AdapterFailure(
            "entitlement_denied", "auth_or_entitlement", message, http_status=status_code, raw_response=raw
        )
    if status_code == 408:
        return AdapterFailure("timeout", "upstream_timeout", message, http_status=status_code, raw_response=raw)
    if status_code == 429:
        return AdapterFailure("failed", "rate_limited", message, http_status=status_code, raw_response=raw)
    if 500 <= status_code <= 599:
        return AdapterFailure("unreachable", "upstream_unavailable", message, http_status=status_code, raw_response=raw)
    return AdapterFailure("failed", "http_error", message, http_status=status_code, raw_response=raw)


def _candidate_id(provider: str, url: str, title: str, rank: int) -> str:
    identity = f"{provider}\n{url}\n{title}\n{rank}".encode("utf-8")
    return f"candidate_{hashlib.sha256(identity).hexdigest()[:20]}"


def _candidate_from_source(
    provider: str,
    source: Any,
    rank: int,
    artifact_ref: str,
) -> dict[str, Any] | None:
    if isinstance(source, str):
        url = source if source.startswith(("http://", "https://")) else ""
        title = ""
        summary = "" if url else source
        published_at = None
    elif isinstance(source, Mapping):
        nested_citation = source.get("url_citation")
        if isinstance(nested_citation, Mapping):
            source = nested_citation
        url = str(source.get("url") or source.get("link") or source.get("id") or "")
        title = str(source.get("title") or source.get("name") or "")
        summary = str(
            source.get("summary")
            or source.get("snippet")
            or source.get("description")
            or source.get("text")
            or ""
        )
        published_at = source.get("published_at") or source.get("publishedDate") or source.get("published_date")
    else:
        return None
    if not url and not title and not summary:
        return None
    return {
        "schema_version": "1",
        "candidate_id": _candidate_id(provider, url, title, rank),
        "candidate_layer": "discovery",
        "evidence_status": "pending_source_reread",
        "provider": provider,
        "title": title,
        "url": url,
        "summary": summary,
        "published_at": published_at,
        "source_type": "provider_citation",
        "discovery_path": f"provider_research_agent:{provider}",
        "raw_rank": rank,
        "artifact_refs": [artifact_ref],
    }


def _flatten_citations(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, (str, Mapping)):
        return [value]
    if isinstance(value, Sequence):
        return list(value)
    return []


class ResearchProviderAdapter:
    provider = "provider"
    provider_api_version = "unknown"
    operation = "research"

    def __init__(
        self,
        api_key: str,
        base_url: str,
        *,
        transport: AsyncHTTPTransport | None = None,
        clock: Clock = time.time,
        sleep: Sleep = asyncio.sleep,
        poll_interval: float = 2.0,
    ):
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")
        self.transport = transport or HTTPXTransport()
        self.clock = clock
        self.sleep = sleep
        self.poll_interval = max(0.0, poll_interval)

    async def submit(self, query: str, *, timeout: float) -> Mapping[str, Any]:
        raise NotImplementedError

    async def poll_or_stream(
        self,
        submission: Mapping[str, Any],
        *,
        deadline: float,
    ) -> LifecycleResult:
        raise NotImplementedError

    async def normalize(
        self,
        raw_response: Mapping[str, Any],
        *,
        artifact_ref: str,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def external_job(self, submission: Mapping[str, Any]) -> dict[str, Any]:
        return {}

    def usage(self, raw_response: Mapping[str, Any]) -> dict[str, Any]:
        usage = raw_response.get("usage")
        return dict(usage) if isinstance(usage, Mapping) else {}

    def _artifact_ref(self, *, run_id: str, task_id: str, step_id: str, attempt_no: int) -> str:
        identity = f"{run_id}:{task_id}:{step_id}:{self.provider}:{attempt_no}".encode("utf-8")
        return f"artifact_provider_{hashlib.sha256(identity).hexdigest()[:20]}"

    def _new_attempt(
        self,
        query: str,
        *,
        timeout_seconds: float,
        attempt_no: int,
        run_id: str,
        task_id: str,
        step_id: str,
    ) -> ExecutionAttempt:
        started = self.clock()
        deadline = started + max(0.0, timeout_seconds)
        return ExecutionAttempt(
            provider=self.provider,
            provider_api_version=self.provider_api_version,
            attempt_no=attempt_no,
            configured=bool(self.api_key),
            started_at=_iso_timestamp(started),
            deadline_at=_iso_timestamp(deadline),
            observed_at=_iso_timestamp(started),
            request_summary={
                "operation": self.operation,
                "endpoint": self.base_url,
                "query_length": len(query),
                "query_preview": _compact_message(query[:200], secret=self.api_key),
            },
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
        )

    async def run(
        self,
        query: str,
        *,
        timeout_seconds: float = 120.0,
        attempt_no: int = 1,
        run_id: str = "",
        task_id: str = "",
        step_id: str = "",
    ) -> dict[str, Any]:
        attempt = self._new_attempt(
            query,
            timeout_seconds=timeout_seconds,
            attempt_no=attempt_no,
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
        )
        deadline = self.clock() + max(0.0, timeout_seconds)
        artifact_ref = self._artifact_ref(
            run_id=run_id, task_id=task_id, step_id=step_id, attempt_no=attempt_no
        )
        raw_artifact: dict[str, Any] = {}
        if not self.api_key:
            attempt.status = "not_configured"
            attempt.errors.append({"error_type": "missing_key", "message": f"{self.provider} API key is not configured"})
            attempt.completed_at = _iso_timestamp(self.clock())
            return attempt.to_dict()

        try:
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise AdapterFailure("timeout", "deadline_exceeded", "deadline elapsed before submission")
            submission = await self.submit(query, timeout=remaining)
            raw_artifact["submit"] = _safe_value(submission, secret=self.api_key)
            attempt.external_job = self.external_job(submission)
            attempt.reachable = True
            attempt.entitled = True
            result = await self.poll_or_stream(submission, deadline=deadline)
            raw_artifact["terminal"] = _safe_value(result.raw_response, secret=self.api_key)
            normalized = await self.normalize(result.raw_response, artifact_ref=artifact_ref)
            attempt.status = result.status
            attempt.entitled = True
            attempt.report = normalized.get("report", "")
            attempt.candidates = list(normalized.get("candidates", []))
            attempt.usage = self.usage(result.raw_response)
            attempt.artifact_refs = [artifact_ref]
            attempt.artifact = {
                "schema_version": "1",
                "artifact_id": artifact_ref,
                "media_type": "application/json",
                "provider": self.provider,
                "candidate_layer": "discovery",
                "evidence_status": "pending_source_reread",
                "raw_response": raw_artifact,
            }
            if result.status in {"partial", "failed"}:
                attempt.errors.append(
                    {
                        "error_type": "provider_partial" if result.status == "partial" else "provider_failed",
                        "message": _compact_message(
                            result.raw_response.get("error")
                            or result.raw_response.get("detail")
                            or result.raw_response.get("stopReason")
                            or "provider reported failure",
                            secret=self.api_key,
                        ),
                    }
                )
        except AdapterFailure as exc:
            attempt.status = exc.status
            if exc.status == "entitlement_denied":
                attempt.reachable = True
                attempt.entitled = False
            elif exc.status == "unreachable":
                attempt.reachable = False
            attempt.errors.append(
                {
                    "error_type": exc.error_type,
                    "message": _compact_message(exc.message, secret=self.api_key),
                    "http_status": exc.http_status,
                }
            )
            if exc.raw_response is not None:
                raw_artifact["error_response"] = _safe_value(exc.raw_response, secret=self.api_key)
        except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError) as exc:
            attempt.status = "timeout"
            attempt.errors.append(
                {"error_type": "timeout", "message": _compact_message(exc or "request timed out", secret=self.api_key)}
            )
        except httpx.RequestError as exc:
            attempt.status = "unreachable"
            attempt.reachable = False
            attempt.errors.append(
                {"error_type": "network_error", "message": _compact_message(exc, secret=self.api_key)}
            )
        except Exception as exc:  # keep provider failures independent in gather
            attempt.status = "failed"
            attempt.errors.append(
                {"error_type": "runtime_error", "message": _compact_message(exc, secret=self.api_key)}
            )

        if raw_artifact and not attempt.artifact:
            attempt.artifact_refs = [artifact_ref]
            attempt.artifact = {
                "schema_version": "1",
                "artifact_id": artifact_ref,
                "media_type": "application/json",
                "provider": self.provider,
                "candidate_layer": "discovery",
                "evidence_status": "pending_source_reread",
                "raw_response": raw_artifact,
            }
        attempt.completed_at = _iso_timestamp(self.clock())
        attempt.observed_at = attempt.completed_at
        return attempt.to_dict()

    def unexpected_failure(
        self,
        query: str,
        exc: BaseException,
        *,
        timeout_seconds: float,
        attempt_no: int,
        run_id: str,
        task_id: str,
        step_id: str,
    ) -> dict[str, Any]:
        attempt = self._new_attempt(
            query,
            timeout_seconds=timeout_seconds,
            attempt_no=attempt_no,
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
        )
        attempt.status = "failed"
        attempt.completed_at = _iso_timestamp(self.clock())
        attempt.errors.append(
            {"error_type": "runtime_error", "message": _compact_message(exc, secret=self.api_key)}
        )
        return attempt.to_dict()

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        payload: Mapping[str, Any] | None,
        timeout: float,
        accepted_statuses: set[int] | None = None,
    ) -> Mapping[str, Any]:
        response = await self.transport.request(
            method, url, headers=headers, json=payload, timeout=max(0.001, timeout)
        )
        accepted = accepted_statuses or {200}
        if response.status_code not in accepted:
            raise _http_failure(response, secret=self.api_key)
        return _response_json(response, secret=self.api_key)

    async def _poll_json(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        deadline: float,
        pending: set[str],
        succeeded: set[str],
        failed: set[str],
        partial: set[str] | None = None,
        accepted_statuses: set[int] | None = None,
    ) -> LifecycleResult:
        partial = partial or set()
        while True:
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise AdapterFailure("timeout", "deadline_exceeded", "provider polling deadline exceeded")
            raw = await self._request_json(
                "GET",
                url,
                headers=headers,
                payload=None,
                timeout=remaining,
                accepted_statuses=accepted_statuses,
            )
            provider_status = str(raw.get("status") or "").lower()
            if provider_status in succeeded:
                return LifecycleResult(raw, "succeeded")
            if provider_status in partial:
                return LifecycleResult(raw, "partial")
            if provider_status in failed:
                normalized = await self.normalize(raw, artifact_ref="")
                has_partial = bool(normalized.get("report") or normalized.get("candidates"))
                return LifecycleResult(raw, "partial" if has_partial else "failed")
            if provider_status not in pending:
                raise AdapterFailure(
                    "failed",
                    "malformed_response",
                    f"unknown provider status: {provider_status or '<missing>'}",
                    raw_response=raw,
                )
            remaining = deadline - self.clock()
            if remaining <= 0:
                raise AdapterFailure("timeout", "deadline_exceeded", "provider polling deadline exceeded")
            await self.sleep(min(self.poll_interval, remaining))


class FirecrawlResearchAdapter(ResearchProviderAdapter):
    provider = "firecrawl"
    provider_api_version = "v2-agent"
    operation = "agent"

    def __init__(self, api_key: str, base_url: str = "https://api.firecrawl.dev/v2", **kwargs: Any):
        super().__init__(api_key, base_url, **kwargs)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def submit(self, query: str, *, timeout: float) -> Mapping[str, Any]:
        raw = await self._request_json(
            "POST", f"{self.base_url}/agent", headers=self.headers, payload={"prompt": query}, timeout=timeout
        )
        if not raw.get("id"):
            raise AdapterFailure("failed", "malformed_response", "Firecrawl Agent response is missing id", raw_response=raw)
        return raw

    def external_job(self, submission: Mapping[str, Any]) -> dict[str, Any]:
        return {"id": str(submission.get("id") or ""), "cursor": None}

    async def poll_or_stream(self, submission: Mapping[str, Any], *, deadline: float) -> LifecycleResult:
        return await self._poll_json(
            f"{self.base_url}/agent/{submission['id']}",
            headers=self.headers,
            deadline=deadline,
            pending={"processing", "pending", "queued", "running"},
            succeeded={"completed", "succeeded"},
            failed={"failed", "cancelled", "canceled"},
            partial={"partial", "incomplete"},
        )

    async def normalize(self, raw_response: Mapping[str, Any], *, artifact_ref: str) -> dict[str, Any]:
        data = raw_response.get("data")
        report: Any = data if data is not None else ""
        sources: list[Any] = []
        if isinstance(data, Mapping):
            report = data.get("report") or data.get("finalAnalysis") or data.get("content") or data
            sources = _flatten_citations(data.get("sources") or data.get("citations"))
        sources.extend(_flatten_citations(raw_response.get("sources") or raw_response.get("citations")))
        candidates = [
            candidate
            for rank, source in enumerate(sources, start=1)
            if (candidate := _candidate_from_source(self.provider, source, rank, artifact_ref)) is not None
        ]
        return {"report": _safe_value(report, secret=self.api_key), "candidates": candidates}

    def usage(self, raw_response: Mapping[str, Any]) -> dict[str, Any]:
        usage = super().usage(raw_response)
        if raw_response.get("creditsUsed") is not None:
            usage["credits_used"] = raw_response.get("creditsUsed")
        return usage


class TavilyResearchAdapter(ResearchProviderAdapter):
    provider = "tavily"
    provider_api_version = "research-v1"
    operation = "research"

    def __init__(self, api_key: str, base_url: str = "https://api.tavily.com", **kwargs: Any):
        super().__init__(api_key, base_url, **kwargs)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def submit(self, query: str, *, timeout: float) -> Mapping[str, Any]:
        raw = await self._request_json(
            "POST",
            f"{self.base_url}/research",
            headers=self.headers,
            payload={"input": query, "stream": False},
            timeout=timeout,
            accepted_statuses={200, 201, 202},
        )
        if not raw.get("request_id"):
            raise AdapterFailure("failed", "malformed_response", "Tavily Research response is missing request_id", raw_response=raw)
        return raw

    def external_job(self, submission: Mapping[str, Any]) -> dict[str, Any]:
        return {"id": str(submission.get("request_id") or ""), "cursor": None}

    async def poll_or_stream(self, submission: Mapping[str, Any], *, deadline: float) -> LifecycleResult:
        return await self._poll_json(
            f"{self.base_url}/research/{submission['request_id']}",
            headers=self.headers,
            deadline=deadline,
            pending={"pending", "in_progress", "processing", "queued", "running"},
            succeeded={"completed", "succeeded"},
            failed={"failed", "cancelled", "canceled"},
            partial={"partial", "incomplete"},
            accepted_statuses={200, 202},
        )

    async def normalize(self, raw_response: Mapping[str, Any], *, artifact_ref: str) -> dict[str, Any]:
        report = raw_response.get("content") or raw_response.get("report") or ""
        sources = _flatten_citations(raw_response.get("sources") or raw_response.get("citations"))
        candidates = [
            candidate
            for rank, source in enumerate(sources, start=1)
            if (candidate := _candidate_from_source(self.provider, source, rank, artifact_ref)) is not None
        ]
        return {"report": _safe_value(report, secret=self.api_key), "candidates": candidates}

    def usage(self, raw_response: Mapping[str, Any]) -> dict[str, Any]:
        usage = super().usage(raw_response)
        if raw_response.get("response_time") is not None:
            usage["response_time_seconds"] = raw_response.get("response_time")
        return usage


class ExaResearchAdapter(ResearchProviderAdapter):
    provider = "exa"
    provider_api_version = "agent-2026-05-07"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.exa.ai",
        *,
        operation: str = "agent",
        **kwargs: Any,
    ):
        if operation not in {"agent", "deep", "deep-reasoning"}:
            raise ValueError("Exa operation must be agent, deep, or deep-reasoning")
        self.operation = operation
        super().__init__(api_key, base_url, **kwargs)

    @property
    def headers(self) -> dict[str, str]:
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        if self.operation == "agent":
            headers["Exa-Beta"] = "agent-2026-05-07"
        return headers

    async def submit(self, query: str, *, timeout: float) -> Mapping[str, Any]:
        if self.operation in {"deep", "deep-reasoning"}:
            return await self._request_json(
                "POST",
                f"{self.base_url}/search",
                headers=self.headers,
                payload={"query": query, "type": self.operation},
                timeout=timeout,
            )
        raw = await self._request_json(
            "POST", f"{self.base_url}/agent/runs", headers=self.headers, payload={"query": query}, timeout=timeout
        )
        if not raw.get("id"):
            raise AdapterFailure("failed", "malformed_response", "Exa Agent response is missing id", raw_response=raw)
        return raw

    def external_job(self, submission: Mapping[str, Any]) -> dict[str, Any]:
        if self.operation == "agent":
            return {"id": str(submission.get("id") or ""), "cursor": None}
        return {"id": str(submission.get("requestId") or ""), "cursor": None}

    async def poll_or_stream(self, submission: Mapping[str, Any], *, deadline: float) -> LifecycleResult:
        if self.operation in {"deep", "deep-reasoning"}:
            return LifecycleResult(submission, "succeeded")
        result = await self._poll_json(
            f"{self.base_url}/agent/runs/{submission['id']}",
            headers=self.headers,
            deadline=deadline,
            pending={"queued", "running"},
            succeeded={"completed"},
            failed={"failed", "cancelled", "canceled"},
            partial={"partial", "incomplete"},
        )
        if result.status == "succeeded" and str(result.raw_response.get("stopReason") or "").lower() == "budget_reached":
            return LifecycleResult(result.raw_response, "partial")
        return result

    async def normalize(self, raw_response: Mapping[str, Any], *, artifact_ref: str) -> dict[str, Any]:
        if self.operation in {"deep", "deep-reasoning"}:
            sources = _flatten_citations(raw_response.get("results"))
            report: Any = raw_response.get("context") or raw_response.get("answer") or ""
        else:
            output = raw_response.get("output")
            report = ""
            sources = []
            if isinstance(output, Mapping):
                report = output.get("structured") if output.get("structured") is not None else output.get("text") or ""
                for grounding in _flatten_citations(output.get("grounding")):
                    if isinstance(grounding, Mapping):
                        sources.extend(_flatten_citations(grounding.get("citations")))
            sources.extend(_flatten_citations(raw_response.get("citations")))
        candidates = [
            candidate
            for rank, source in enumerate(sources, start=1)
            if (candidate := _candidate_from_source(self.provider, source, rank, artifact_ref)) is not None
        ]
        return {"report": _safe_value(report, secret=self.api_key), "candidates": candidates}

    def usage(self, raw_response: Mapping[str, Any]) -> dict[str, Any]:
        usage = super().usage(raw_response)
        if isinstance(raw_response.get("costDollars"), Mapping):
            usage["cost_dollars"] = _safe_value(raw_response["costDollars"], secret=self.api_key)
        return usage


class JinaDeepSearchAdapter(ResearchProviderAdapter):
    provider = "jina"
    provider_api_version = "jina-deepsearch-v1"
    operation = "deepsearch"

    def __init__(self, api_key: str, base_url: str = "https://deepsearch.jina.ai/v1", **kwargs: Any):
        super().__init__(api_key, base_url, **kwargs)

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    async def submit(self, query: str, *, timeout: float) -> Mapping[str, Any]:
        return await self._request_json(
            "POST",
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            payload={
                "model": "jina-deepsearch-v1",
                "messages": [{"role": "user", "content": query}],
                "stream": False,
            },
            timeout=timeout,
        )

    def external_job(self, submission: Mapping[str, Any]) -> dict[str, Any]:
        return {"id": str(submission.get("id") or ""), "cursor": None}

    async def poll_or_stream(self, submission: Mapping[str, Any], *, deadline: float) -> LifecycleResult:
        choices = submission.get("choices")
        if not isinstance(choices, list) or not choices:
            raise AdapterFailure("failed", "malformed_response", "Jina DeepSearch response is missing choices", raw_response=submission)
        first_choice = choices[0]
        finish_reason = str(first_choice.get("finish_reason") or "") if isinstance(first_choice, Mapping) else ""
        return LifecycleResult(submission, "partial" if finish_reason in {"length", "content_filter"} else "succeeded")

    async def normalize(self, raw_response: Mapping[str, Any], *, artifact_ref: str) -> dict[str, Any]:
        choices = raw_response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
            raise AdapterFailure("failed", "malformed_response", "Jina DeepSearch response is missing a message", raw_response=raw_response)
        message = choices[0].get("message")
        if not isinstance(message, Mapping):
            raise AdapterFailure("failed", "malformed_response", "Jina DeepSearch response is missing message content", raw_response=raw_response)
        report = message.get("content") or ""
        sources: list[Any] = []
        for container in (message, raw_response):
            sources.extend(
                _flatten_citations(
                    container.get("citations")
                    or container.get("sources")
                    or container.get("annotations")
                )
            )
        candidates = [
            candidate
            for rank, source in enumerate(sources, start=1)
            if (candidate := _candidate_from_source(self.provider, source, rank, artifact_ref)) is not None
        ]
        return {"report": _safe_value(report, secret=self.api_key), "candidates": candidates}


PROVIDER_CAPABILITY_PROFILES: dict[str, dict[str, Any]] = {
    "firecrawl": {
        "capabilities": ["general_current", "known_url", "crawl_extract_batch"],
        "operations": ["agent", "search", "scrape", "crawl", "extract", "batch_scrape"],
    },
    "tavily": {
        "capabilities": ["general_current", "known_url", "crawl_extract_batch"],
        "operations": ["research", "search", "extract", "crawl", "map"],
    },
    "exa": {
        "capabilities": ["general_current", "docs_api", "academic", "code_developer", "known_url"],
        "operations": ["agent", "search:deep", "search:deep-reasoning", "contents", "find_similar"],
    },
    "jina": {
        "capabilities": ["general_current", "docs_api", "academic", "code_developer", "known_url"],
        "operations": ["deepsearch", "search", "reader", "reranker"],
    },
}


def capability_inventory(
    adapters: Sequence[ResearchProviderAdapter],
    attempts: Sequence[Mapping[str, Any]] = (),
    *,
    clock: Clock = time.time,
) -> dict[str, Any]:
    """Return declared capability coverage plus separately observed live state."""
    latest_attempt = {str(item.get("provider")): item for item in attempts}
    providers: dict[str, Any] = {}
    for adapter in adapters:
        observed = latest_attempt.get(adapter.provider)
        configured = bool(adapter.api_key)
        reachable: bool | None = None
        entitled: bool | None = None
        observed_at = _iso_timestamp(clock()) if attempts else ""
        status = "not_configured" if not configured else "configured_unobserved"
        if observed:
            status = str(observed.get("status") or status)
            reachable = observed.get("reachable")
            entitled = observed.get("entitled")
            observed_at = str(observed.get("observed_at") or observed_at)
        profile = PROVIDER_CAPABILITY_PROFILES.get(adapter.provider, {"capabilities": [], "operations": []})
        providers[adapter.provider] = {
            "configured": configured,
            "reachable": reachable,
            "entitled": entitled,
            "observed_at": observed_at,
            "status": status,
            "capabilities": list(profile["capabilities"]),
            "operations": list(profile["operations"]),
        }
    capability_names = [
        "general_current",
        "docs_api",
        "academic",
        "code_developer",
        "known_url",
        "crawl_extract_batch",
    ]
    return {
        "schema_version": "1",
        "observed_at": _iso_timestamp(clock()) if attempts else "",
        "capability_pool": {
            name: [provider for provider, item in providers.items() if name in item["capabilities"]]
            for name in capability_names
        },
        "providers": providers,
    }


def build_research_provider_adapters(
    api_keys: Mapping[str, str],
    *,
    transports: Mapping[str, AsyncHTTPTransport] | None = None,
    clock: Clock = time.time,
    sleep: Sleep = asyncio.sleep,
    poll_interval: float = 2.0,
) -> list[ResearchProviderAdapter]:
    transports = transports or {}
    shared = {"clock": clock, "sleep": sleep, "poll_interval": poll_interval}
    return [
        FirecrawlResearchAdapter(api_keys.get("firecrawl", ""), transport=transports.get("firecrawl"), **shared),
        TavilyResearchAdapter(api_keys.get("tavily", ""), transport=transports.get("tavily"), **shared),
        ExaResearchAdapter(api_keys.get("exa", ""), transport=transports.get("exa"), **shared),
        JinaDeepSearchAdapter(api_keys.get("jina", ""), transport=transports.get("jina"), **shared),
    ]


async def run_deep_provider_agents(
    query: str,
    adapters: Sequence[ResearchProviderAdapter],
    *,
    timeout_seconds: float = 120.0,
    attempt_no: int = 1,
    run_id: str = "",
    task_id: str = "",
    step_id: str = "",
) -> dict[str, Any]:
    """Run every supplied adapter concurrently without truncating the provider list."""
    coroutines = [
        adapter.run(
            query,
            timeout_seconds=timeout_seconds,
            attempt_no=attempt_no,
            run_id=run_id,
            task_id=task_id,
            step_id=step_id,
        )
        for adapter in adapters
    ]
    gathered = await asyncio.gather(*coroutines, return_exceptions=True)
    attempts: list[dict[str, Any]] = []
    for adapter, result in zip(adapters, gathered):
        if isinstance(result, BaseException):
            attempts.append(
                adapter.unexpected_failure(
                    query,
                    result,
                    timeout_seconds=timeout_seconds,
                    attempt_no=attempt_no,
                    run_id=run_id,
                    task_id=task_id,
                    step_id=step_id,
                )
            )
        else:
            attempts.append(result)
    return {
        "schema_version": "1",
        "mode": "deep",
        "attempts": attempts,
        "capability_inventory": capability_inventory(adapters, attempts),
        "degraded": any(item["status"] != "succeeded" for item in attempts),
    }


__all__ = [
    "AsyncHTTPTransport",
    "ExecutionAttempt",
    "ExaResearchAdapter",
    "FirecrawlResearchAdapter",
    "HTTPXTransport",
    "JinaDeepSearchAdapter",
    "ResearchProviderAdapter",
    "TavilyResearchAdapter",
    "build_research_provider_adapters",
    "capability_inventory",
    "run_deep_provider_agents",
]
