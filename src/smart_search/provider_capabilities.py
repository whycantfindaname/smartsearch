"""Bounded adapters for provider capabilities outside Provider Research Agents.

The request contracts were checked against the providers' official references
on 2026-08-24.  "Current" means the unversioned contract published at that
date; it is not promoted to a locally invented API version.

* Firecrawl REST API v2 scrape, crawl, batch scrape, Research Index, and
  Developer Index:
  https://docs.firecrawl.dev/api-reference/endpoint/scrape
  https://docs.firecrawl.dev/api-reference/endpoint/crawl-post
  https://docs.firecrawl.dev/api-reference/endpoint/crawl-get
  https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape
  https://docs.firecrawl.dev/api-reference/endpoint/batch-scrape-get
  https://docs.firecrawl.dev/api-reference/endpoint/research-search-papers
  https://docs.firecrawl.dev/api-reference/endpoint/research-paper
  https://docs.firecrawl.dev/api-reference/endpoint/research-related-papers
  https://docs.firecrawl.dev/api-reference/endpoint/developer-search
* Tavily current REST crawl and extract:
  https://docs.tavily.com/documentation/api-reference/endpoint/crawl
  https://docs.tavily.com/documentation/api-reference/endpoint/extract
* Exa current Search API, including ``deep`` and ``deep-reasoning``:
  https://exa.ai/docs/reference/search
* Jina Search and Search Foundation Reranker APIs:
  https://jina.ai/reader/ (``https://s.jina.ai/?q=...``)
  https://api.jina.ai/redoc (``POST /v1/rerank``)

Each call returns one self-contained attempt fact.  A configured credential is
not evidence that a provider is reachable or entitled; those fields remain
unknown until the transport produces relevant evidence.  The adapters perform
one bounded request each, apply no provider/task count cap or research budget,
and never retry implicitly.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Mapping, Protocol, Sequence
from urllib.parse import quote, urlencode

import httpx


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
    """Minimum response surface needed by the adapters."""

    status_code: int
    text: str

    def json(self) -> Any: ...


class AsyncTransport(Protocol):
    """Injectable transport used by all provider capability adapters."""

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
    """Default network transport; offline tests inject a fake implementation."""

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            return await client.request(method, url, headers=dict(headers), json=json)


@dataclass(frozen=True)
class OperationSpec:
    method: str
    url: str
    headers: Mapping[str, str]
    payload: Mapping[str, Any] | None


@dataclass(frozen=True)
class CapabilityCall:
    """One independently executable operation for :func:`gather_capability_calls`."""

    adapter: "ProviderCapabilityAdapter"
    operation: str
    arguments: Mapping[str, Any]
    timeout_seconds: float = 30.0


class ResponseShapeError(ValueError):
    """Raised internally when a successful HTTP response violates its contract."""


def _redact_text(value: str, secret: str) -> str:
    if not secret:
        return value
    redacted = value.replace(secret, "[REDACTED]")
    return redacted.replace(quote(secret, safe=""), "[REDACTED]")


def _sanitize(value: Any, secret: str) -> Any:
    if isinstance(value, Mapping):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized in {
                "api_key",
                "apikey",
                "authorization",
                "x_api_key",
                "token",
                "access_token",
                "secret",
                "password",
            }:
                safe[str(key)] = "[REDACTED]"
            else:
                safe[str(key)] = _sanitize(item, secret)
        return safe
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, secret) for item in value]
    if isinstance(value, str):
        return _redact_text(value, secret)
    return value


def _message(value: Any, secret: str, *, limit: int = 500) -> str:
    safe = _sanitize(value, secret)
    if not isinstance(safe, str):
        try:
            safe = json.dumps(safe, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError):
            safe = str(safe)
    return " ".join(safe.split())[:limit]


def _base_attempt(
    adapter: "ProviderCapabilityAdapter",
    operation: str,
    timeout_seconds: float,
) -> dict[str, Any]:
    return {
        "schema_version": ATTEMPT_SCHEMA_VERSION,
        "provider": adapter.provider,
        "provider_api_version": adapter.provider_api_version,
        "capability": adapter.capabilities.get(operation, "unknown"),
        "operation": operation,
        "status": "failed",
        "configured": bool(adapter.api_key),
        "reachable": None,
        "entitled": None,
        "timeout_seconds": timeout_seconds,
        "request": {},
        "result": {},
        "errors": [],
    }


class ProviderCapabilityAdapter:
    """Base for one-request capability adapters with explicit fact states."""

    provider = "provider"
    provider_api_version = "unknown"
    capabilities: Mapping[str, str] = {}

    def __init__(
        self,
        api_key: str,
        *,
        transport: AsyncTransport | None = None,
    ) -> None:
        self.api_key = api_key or ""
        self.transport = transport or HTTPXTransport()

    def build_operation(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> OperationSpec:
        raise NotImplementedError

    def normalize(
        self, operation: str, response: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        raise NotImplementedError

    async def execute(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        *,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        if operation not in self.capabilities:
            raise ValueError(f"unsupported {self.provider} operation: {operation}")
        timeout_seconds = max(0.0, float(timeout_seconds))
        attempt = _base_attempt(self, operation, timeout_seconds)
        if not self.api_key:
            attempt["status"] = "not_configured"
            attempt["errors"] = [
                {
                    "error_type": "missing_key",
                    "message": f"{self.provider} API key is not configured",
                }
            ]
            return attempt

        try:
            spec = self.build_operation(operation, arguments)
            attempt["request"] = _sanitize(
                {
                    "method": spec.method,
                    "url": spec.url,
                    "headers": dict(spec.headers),
                    "json": spec.payload,
                },
                self.api_key,
            )
            response = await self.transport.request(
                spec.method,
                spec.url,
                headers=spec.headers,
                json=spec.payload,
                timeout=max(0.001, timeout_seconds),
            )
            attempt["reachable"] = True
            if response.status_code in {401, 402, 403}:
                attempt["status"] = "entitlement_denied"
                attempt["entitled"] = False
                attempt["errors"] = [self._http_error(response, "auth_or_entitlement")]
                return attempt
            if response.status_code == 408:
                attempt["status"] = "timeout"
                attempt["errors"] = [self._http_error(response, "upstream_timeout")]
                return attempt
            if response.status_code == 429:
                attempt["status"] = "failed"
                attempt["errors"] = [self._http_error(response, "rate_limited")]
                return attempt
            if 500 <= response.status_code <= 599:
                attempt["status"] = "unreachable"
                attempt["reachable"] = False
                attempt["errors"] = [self._http_error(response, "upstream_unavailable")]
                return attempt
            if not 200 <= response.status_code <= 299:
                attempt["status"] = "failed"
                attempt["errors"] = [self._http_error(response, "http_error")]
                return attempt

            attempt["entitled"] = True
            raw = self._json_object(response)
            attempt["result"] = _sanitize(raw, self.api_key)
            status, normalized = self.normalize(operation, raw)
            if status not in ATTEMPT_STATUSES:
                raise ResponseShapeError(
                    f"normalizer returned invalid status: {status}"
                )
            attempt["status"] = status
            attempt["result"] = _sanitize(normalized, self.api_key)
            if status == "partial":
                attempt["errors"] = [
                    {
                        "error_type": "provider_partial",
                        "message": "provider returned partial results",
                    }
                ]
            elif status == "failed":
                attempt["errors"] = [
                    {
                        "error_type": "provider_failed",
                        "message": "provider reported operation failure",
                    }
                ]
            return attempt
        except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError) as exc:
            attempt["status"] = "timeout"
            attempt["errors"] = [
                {
                    "error_type": "timeout",
                    "message": _message(exc or "timeout", self.api_key),
                }
            ]
        except httpx.RequestError as exc:
            attempt["status"] = "unreachable"
            attempt["reachable"] = False
            attempt["errors"] = [
                {"error_type": "network_error", "message": _message(exc, self.api_key)}
            ]
        except ResponseShapeError as exc:
            attempt["status"] = "failed"
            attempt["errors"] = [
                {
                    "error_type": "malformed_response",
                    "message": _message(exc, self.api_key),
                }
            ]
        except Exception as exc:  # one provider must not escape an aggregate
            attempt["status"] = "failed"
            attempt["errors"] = [
                {"error_type": "runtime_error", "message": _message(exc, self.api_key)}
            ]
        return attempt

    def unexpected_failure(
        self,
        operation: str,
        timeout_seconds: float,
        exc: BaseException,
    ) -> dict[str, Any]:
        attempt = _base_attempt(self, operation, timeout_seconds)
        attempt["errors"] = [
            {"error_type": "runtime_error", "message": _message(exc, self.api_key)}
        ]
        return attempt

    def _json_object(self, response: HTTPResponse) -> Mapping[str, Any]:
        try:
            value = response.json()
        except Exception as exc:
            raise ResponseShapeError(
                f"provider returned invalid JSON: {_message(exc, self.api_key)}"
            ) from exc
        if not isinstance(value, Mapping):
            raise ResponseShapeError("provider response must be a JSON object")
        return value

    def _http_error(self, response: HTTPResponse, error_type: str) -> dict[str, Any]:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        return {
            "error_type": error_type,
            "http_status": response.status_code,
            "message": f"HTTP {response.status_code}: {_message(detail, self.api_key)}",
        }

    def _record_http_failure(
        self, attempt: dict[str, Any], response: HTTPResponse
    ) -> bool:
        """Record a non-2xx response and return whether execution must stop."""
        attempt["reachable"] = True
        if response.status_code in {401, 402, 403}:
            attempt["status"] = "entitlement_denied"
            attempt["entitled"] = False
            attempt["errors"] = [self._http_error(response, "auth_or_entitlement")]
        elif response.status_code == 408:
            attempt["status"] = "timeout"
            attempt["errors"] = [self._http_error(response, "upstream_timeout")]
        elif response.status_code == 429:
            attempt["status"] = "failed"
            attempt["errors"] = [self._http_error(response, "rate_limited")]
        elif 500 <= response.status_code <= 599:
            attempt["status"] = "unreachable"
            attempt["reachable"] = False
            attempt["errors"] = [self._http_error(response, "upstream_unavailable")]
        elif not 200 <= response.status_code <= 299:
            attempt["status"] = "failed"
            attempt["errors"] = [self._http_error(response, "http_error")]
        else:
            return False
        return True


class FirecrawlV2Adapter(ProviderCapabilityAdapter):
    provider = "firecrawl"
    provider_api_version = "v2"
    capabilities = {
        "scrape": "extract",
        "crawl": "crawl",
        "batch_scrape": "batch_scrape",
        "research_search": "academic_search",
        "research_read": "academic_read",
        "research_related": "academic_related",
        "developer_search": "developer_search",
    }

    _GET_OPERATIONS = frozenset(
        {"research_search", "research_read", "research_related", "developer_search"}
    )
    _RESEARCH_SEARCH_OPTIONS = ("k", "authors", "categories", "from", "to")
    _RESEARCH_READ_OPTIONS = ("query", "k")
    _RESEARCH_RELATED_OPTIONS = ("intent", "mode", "k", "rerank", "anchor")
    _DEVELOPER_SEARCH_OPTIONS = (
        "k",
        "types",
        "repos",
        "sources",
        "skills",
        "passages",
        "language",
        "topic",
        "license",
        "min_stars",
        "max_stars",
        "archived",
        "fork",
    )

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.firecrawl.dev/v2",
        transport: AsyncTransport | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        poll_interval: float = 0.5,
    ) -> None:
        super().__init__(api_key, transport=transport)
        self.base_url = base_url.rstrip("/")
        self.clock = clock
        self.sleep = sleep
        self.poll_interval = max(0.0, poll_interval)

    def build_operation(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> OperationSpec:
        if operation in self._GET_OPERATIONS:
            return self._build_index_operation(operation, arguments)
        options = dict(arguments.get("options") or {})
        if operation == "scrape":
            payload = {**options, "url": arguments["url"]}
            endpoint = "scrape"
        elif operation == "crawl":
            payload = {**options, "url": arguments["url"]}
            endpoint = "crawl"
        else:
            payload = {**options, "urls": list(arguments["urls"])}
            endpoint = "batch/scrape"
        return OperationSpec(
            "POST",
            f"{self.base_url}/{endpoint}",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            payload,
        )

    def _build_index_operation(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> OperationSpec:
        options = dict(arguments.get("options") or {})
        headers = {"Authorization": f"Bearer {self.api_key}"}
        if operation == "research_search":
            query = self._required_text(arguments.get("query"), "query")
            self._reject_unknown_options(options, self._RESEARCH_SEARCH_OPTIONS)
            params = {
                "query": query,
                **self._ordered_options(options, self._RESEARCH_SEARCH_OPTIONS),
            }
            endpoint = "search/research/papers"
            self._validate_k(params.get("k"), maximum=500)
        elif operation == "research_read":
            paper_id = self._required_text(arguments.get("paper_id"), "paper_id")
            self._reject_unknown_options(options, self._RESEARCH_READ_OPTIONS)
            params = self._ordered_options(options, self._RESEARCH_READ_OPTIONS)
            endpoint = f"search/research/papers/{quote(paper_id, safe='')}"
            self._validate_optional_text(params.get("query"), "query")
            self._validate_k(params.get("k"), maximum=50)
        elif operation == "research_related":
            paper_id = self._required_text(arguments.get("paper_id"), "paper_id")
            intent = self._required_text(arguments.get("intent"), "intent")
            self._reject_unknown_options(options, self._RESEARCH_RELATED_OPTIONS)
            params = {
                "intent": intent,
                **self._ordered_options(
                    options, self._RESEARCH_RELATED_OPTIONS, exclude={"intent"}
                ),
            }
            endpoint = f"search/research/papers/{quote(paper_id, safe='')}/similar"
            if params.get("mode") not in {None, "similar", "citers", "references"}:
                raise ValueError("mode must be similar, citers, or references")
            self._validate_k(params.get("k"), maximum=500)
            self._validate_optional_bool(params.get("rerank"), "rerank")
        else:
            query = self._required_text(arguments.get("query"), "query")
            self._reject_unknown_options(options, self._DEVELOPER_SEARCH_OPTIONS)
            params = {
                "query": query,
                **self._ordered_options(options, self._DEVELOPER_SEARCH_OPTIONS),
            }
            endpoint = "search/developer"
            self._validate_k(params.get("k"), maximum=100)
            result_types = params.get("types")
            if result_types is not None:
                if isinstance(result_types, str):
                    result_types = [result_types]
                if (
                    not isinstance(result_types, (list, tuple))
                    or not result_types
                    or any(
                        item not in {"doc", "issue", "pull_request", "readme"}
                        for item in result_types
                    )
                ):
                    raise ValueError(
                        "types must contain only doc, issue, pull_request, or readme"
                    )
            if params.get("skills") not in {None, "only"}:
                raise ValueError("skills must be 'only' when provided")
            passages = params.get("passages")
            if passages is not None and (
                isinstance(passages, bool)
                or not isinstance(passages, int)
                or not 1 <= passages <= 5
            ):
                raise ValueError("passages must be an integer from 1 to 5")
            for name in ("archived", "fork"):
                self._validate_optional_bool(params.get(name), name)
            for name in ("min_stars", "max_stars"):
                value = params.get(name)
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, int) or value < 0
                ):
                    raise ValueError(f"{name} must be a non-negative integer")

        encoded = urlencode(self._query_items(params), doseq=True)
        suffix = f"?{encoded}" if encoded else ""
        return OperationSpec("GET", f"{self.base_url}/{endpoint}{suffix}", headers, None)

    @staticmethod
    def _ordered_options(
        options: Mapping[str, Any],
        order: Sequence[str],
        *,
        exclude: set[str] | None = None,
    ) -> dict[str, Any]:
        excluded = exclude or set()
        return {
            name: options[name]
            for name in order
            if name in options and name not in excluded
        }

    @staticmethod
    def _query_items(params: Mapping[str, Any]) -> list[tuple[str, Any]]:
        items: list[tuple[str, Any]] = []
        for name, value in params.items():
            if value is None:
                continue
            if isinstance(value, bool):
                value = str(value).lower()
            elif isinstance(value, (list, tuple)):
                value = [
                    str(item).lower() if isinstance(item, bool) else item
                    for item in value
                ]
            items.append((name, value))
        return items

    @staticmethod
    def _required_text(value: Any, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value

    @staticmethod
    def _validate_optional_text(value: Any, name: str) -> None:
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{name} must be a non-empty string when provided")

    @staticmethod
    def _validate_optional_bool(value: Any, name: str) -> None:
        if value is not None and not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean")

    @staticmethod
    def _validate_k(value: Any, *, maximum: int) -> None:
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= maximum
        ):
            raise ValueError(f"k must be an integer from 1 to {maximum}")

    @staticmethod
    def _reject_unknown_options(
        options: Mapping[str, Any], allowed: Sequence[str]
    ) -> None:
        unknown = sorted(set(options) - set(allowed))
        if unknown:
            raise ValueError(f"unsupported options: {', '.join(unknown)}")

    def normalize(
        self, operation: str, response: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        if response.get("success") is False:
            return "failed", dict(response)
        if operation in {"research_search", "research_related", "developer_search"}:
            if response.get("success") is not True or not isinstance(
                response.get("results"), list
            ):
                raise ResponseShapeError(
                    f"Firecrawl {operation} response requires success=true and a results list"
                )
            if operation == "research_related":
                if not isinstance(response.get("poolSize"), int) or not isinstance(
                    response.get("truncated"), bool
                ):
                    raise ResponseShapeError(
                        "Firecrawl research_related response requires integer poolSize and boolean truncated"
                    )
                return ("partial" if response["truncated"] else "succeeded"), dict(
                    response
                )
            if operation == "developer_search":
                coverage = response.get("coverage")
                reranked = response.get("reranked")
                if coverage is not None and not isinstance(coverage, Mapping):
                    raise ResponseShapeError(
                        "Firecrawl developer_search coverage must be an object when present"
                    )
                if reranked is not None and not isinstance(reranked, bool):
                    raise ResponseShapeError(
                        "Firecrawl developer_search reranked must be boolean when present"
                    )
            return "succeeded", dict(response)
        if operation == "research_read":
            if response.get("success") is not True or not isinstance(
                response.get("paper"), Mapping
            ):
                raise ResponseShapeError(
                    "Firecrawl research_read response requires success=true and object paper"
                )
            return "succeeded", dict(response)
        if operation == "scrape":
            if response.get("success") is not True or not isinstance(
                response.get("data"), Mapping
            ):
                raise ResponseShapeError(
                    "Firecrawl scrape response requires success=true and object data"
                )
            return "succeeded", dict(response)
        if response.get("success") is not True or not isinstance(
            response.get("id"), str
        ):
            raise ResponseShapeError(
                f"Firecrawl {operation} response requires success=true and string id"
            )
        return "succeeded", dict(response)

    async def execute(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        *,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        if operation not in {"crawl", "batch_scrape"}:
            return await super().execute(
                operation, arguments, timeout_seconds=timeout_seconds
            )
        return await self._run_job(
            operation, arguments, timeout_seconds=timeout_seconds
        )

    async def scrape(
        self,
        url: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await super().execute(
            "scrape",
            {"url": url, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def crawl(
        self,
        url: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await self._run_job(
            "crawl",
            {"url": url, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def batch_scrape(
        self,
        urls: Sequence[str],
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await self._run_job(
            "batch_scrape",
            {"urls": list(urls), "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def research_search(
        self,
        query: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await super().execute(
            "research_search",
            {"query": query, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def research_read(
        self,
        paper_id: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await super().execute(
            "research_read",
            {"paper_id": paper_id, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def research_related(
        self,
        paper_id: str,
        intent: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await super().execute(
            "research_related",
            {"paper_id": paper_id, "intent": intent, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def developer_search(
        self,
        query: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await super().execute(
            "developer_search",
            {"query": query, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def _run_job(
        self,
        operation: str,
        arguments: Mapping[str, Any],
        *,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        started = self.clock()
        attempt = await super().execute(
            operation, arguments, timeout_seconds=timeout_seconds
        )
        if attempt["status"] != "succeeded":
            return attempt

        submission = dict(attempt["result"])
        job_id = submission["id"]
        status_path = "crawl" if operation == "crawl" else "batch/scrape"
        status_url = f"{self.base_url}/{status_path}/{job_id}"
        attempt["request"] = {
            "submit": attempt["request"],
            "status_endpoint": status_url,
            "poll_count": 0,
        }
        deadline = started + max(0.0, float(timeout_seconds))
        headers = {"Authorization": f"Bearer {self.api_key}"}
        latest: Mapping[str, Any] = {}

        while True:
            remaining = deadline - self.clock()
            if remaining <= 0:
                attempt["status"] = "timeout"
                attempt["result"] = {
                    "submission": submission,
                    "latest": _sanitize(latest, self.api_key),
                }
                attempt["errors"] = [
                    {
                        "error_type": "deadline_exceeded",
                        "message": "Firecrawl job polling deadline exceeded",
                    }
                ]
                return attempt
            try:
                response = await self.transport.request(
                    "GET",
                    status_url,
                    headers=headers,
                    json=None,
                    timeout=max(0.001, remaining),
                )
                attempt["request"]["poll_count"] += 1
                if self._record_http_failure(attempt, response):
                    return attempt
                attempt["entitled"] = True
                latest = self._json_object(response)
                attempt["result"] = {
                    "submission": submission,
                    "terminal": _sanitize(latest, self.api_key),
                }
                provider_status = latest.get("status")
                if provider_status == "completed":
                    if not isinstance(latest.get("data"), list):
                        raise ResponseShapeError(
                            "Firecrawl completed response requires a data list"
                        )
                    if latest.get("next"):
                        attempt["status"] = "partial"
                        attempt["errors"] = [
                            {
                                "error_type": "provider_partial",
                                "message": "Firecrawl returned a next page URL; current result is incomplete",
                            }
                        ]
                    else:
                        attempt["status"] = "succeeded"
                        attempt["errors"] = []
                    return attempt
                if provider_status == "failed":
                    data = latest.get("data", [])
                    completed = latest.get("completed", 0)
                    has_output = isinstance(data, list) and bool(data)
                    attempt["status"] = (
                        "partial" if has_output or completed else "failed"
                    )
                    attempt["errors"] = [
                        {
                            "error_type": "provider_partial"
                            if attempt["status"] == "partial"
                            else "provider_failed",
                            "message": "Firecrawl job reported failure",
                        }
                    ]
                    return attempt
                if provider_status != "scraping":
                    raise ResponseShapeError(
                        "Firecrawl status must be scraping, completed, or failed"
                    )
                if self.poll_interval:
                    await self.sleep(
                        min(self.poll_interval, max(0.0, deadline - self.clock()))
                    )
            except (httpx.TimeoutException, asyncio.TimeoutError, TimeoutError) as exc:
                attempt["status"] = "timeout"
                attempt["errors"] = [
                    {
                        "error_type": "timeout",
                        "message": _message(exc or "timeout", self.api_key),
                    }
                ]
                return attempt
            except httpx.RequestError as exc:
                attempt["status"] = "unreachable"
                attempt["reachable"] = False
                attempt["errors"] = [
                    {
                        "error_type": "network_error",
                        "message": _message(exc, self.api_key),
                    }
                ]
                return attempt
            except ResponseShapeError as exc:
                attempt["status"] = "failed"
                attempt["errors"] = [
                    {
                        "error_type": "malformed_response",
                        "message": _message(exc, self.api_key),
                    }
                ]
                return attempt
            except Exception as exc:
                attempt["status"] = "failed"
                attempt["errors"] = [
                    {
                        "error_type": "runtime_error",
                        "message": _message(exc, self.api_key),
                    }
                ]
                return attempt


class TavilyCapabilityAdapter(ProviderCapabilityAdapter):
    provider = "tavily"
    provider_api_version = "current"
    capabilities = {"crawl": "crawl", "extract": "extract"}

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.tavily.com",
        transport: AsyncTransport | None = None,
    ) -> None:
        super().__init__(api_key, transport=transport)
        self.base_url = base_url.rstrip("/")

    def build_operation(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> OperationSpec:
        options = dict(arguments.get("options") or {})
        key = "url" if operation == "crawl" else "urls"
        value: Any = arguments[key] if operation == "crawl" else list(arguments[key])
        return OperationSpec(
            "POST",
            f"{self.base_url}/{operation}",
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            {**options, key: value},
        )

    def normalize(
        self, operation: str, response: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        results = response.get("results")
        if not isinstance(results, list):
            raise ResponseShapeError(
                f"Tavily {operation} response requires a results list"
            )
        failed = response.get("failed_results", [])
        if not isinstance(failed, list):
            raise ResponseShapeError("Tavily failed_results must be a list")
        status = (
            "partial"
            if results and failed
            else "failed"
            if failed and not results
            else "succeeded"
        )
        return status, dict(response)

    async def crawl(
        self,
        url: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 150.0,
    ) -> dict[str, Any]:
        return await self.execute(
            "crawl",
            {"url": url, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def extract(
        self,
        urls: Sequence[str],
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        return await self.execute(
            "extract",
            {"urls": list(urls), "options": options or {}},
            timeout_seconds=timeout_seconds,
        )


class ExaDeepSearchAdapter(ProviderCapabilityAdapter):
    provider = "exa"
    provider_api_version = "current-search"
    capabilities = {"deep": "deep_search", "deep-reasoning": "deep_reasoning_search"}

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.exa.ai",
        transport: AsyncTransport | None = None,
    ) -> None:
        super().__init__(api_key, transport=transport)
        self.endpoint = f"{base_url.rstrip('/')}/search"

    def build_operation(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> OperationSpec:
        options = dict(arguments.get("options") or {})
        payload = {**options, "query": arguments["query"], "type": operation}
        return OperationSpec(
            "POST",
            self.endpoint,
            {"x-api-key": self.api_key, "Content-Type": "application/json"},
            payload,
        )

    def normalize(
        self, operation: str, response: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        if not isinstance(response.get("results"), list):
            raise ResponseShapeError(
                f"Exa {operation} response requires a results list"
            )
        return "succeeded", dict(response)

    async def search(
        self,
        query: str,
        *,
        search_type: str = "deep",
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 60.0,
    ) -> dict[str, Any]:
        return await self.execute(
            search_type,
            {"query": query, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )


class JinaCapabilityAdapter(ProviderCapabilityAdapter):
    provider = "jina"
    provider_api_version = "current-search-foundation"
    capabilities = {"search": "web_search", "rerank": "rerank"}

    def __init__(
        self,
        api_key: str,
        *,
        search_base_url: str = "https://s.jina.ai",
        rerank_base_url: str = "https://api.jina.ai",
        transport: AsyncTransport | None = None,
    ) -> None:
        super().__init__(api_key, transport=transport)
        self.search_base_url = search_base_url.rstrip("/")
        self.rerank_base_url = rerank_base_url.rstrip("/")

    def build_operation(
        self, operation: str, arguments: Mapping[str, Any]
    ) -> OperationSpec:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        if operation == "search":
            options = dict(arguments.get("options") or {})
            query = urlencode({"q": arguments["query"], **options})
            return OperationSpec(
                "GET", f"{self.search_base_url}/?{query}", headers, None
            )
        options = dict(arguments.get("options") or {})
        payload = {
            **options,
            "model": arguments["model"],
            "query": arguments["query"],
            "documents": list(arguments["documents"]),
        }
        headers["Content-Type"] = "application/json"
        return OperationSpec(
            "POST", f"{self.rerank_base_url}/v1/rerank", headers, payload
        )

    def normalize(
        self, operation: str, response: Mapping[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        field = "data" if operation == "search" else "results"
        if not isinstance(response.get(field), list):
            raise ResponseShapeError(
                f"Jina {operation} response requires a {field} list"
            )
        return "succeeded", dict(response)

    async def search(
        self,
        query: str,
        *,
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await self.execute(
            "search",
            {"query": query, "options": options or {}},
            timeout_seconds=timeout_seconds,
        )

    async def rerank(
        self,
        query: str,
        documents: Sequence[str | Mapping[str, Any]],
        *,
        model: str = "jina-reranker-v3.5",
        options: Mapping[str, Any] | None = None,
        timeout_seconds: float = 30.0,
    ) -> dict[str, Any]:
        return await self.execute(
            "rerank",
            {
                "query": query,
                "documents": list(documents),
                "model": model,
                "options": options or {},
            },
            timeout_seconds=timeout_seconds,
        )


async def gather_capability_calls(
    calls: Sequence[CapabilityCall],
) -> list[dict[str, Any]]:
    """Run every supplied operation independently, preserving input order.

    The sequence is intentionally unbounded by a fixed provider/task count.
    Callers own concurrency policy and overall research budgets.
    """

    async def run(call: CapabilityCall) -> dict[str, Any]:
        try:
            return await call.adapter.execute(
                call.operation,
                call.arguments,
                timeout_seconds=call.timeout_seconds,
            )
        except Exception as exc:
            return call.adapter.unexpected_failure(
                call.operation, call.timeout_seconds, exc
            )

    return list(await asyncio.gather(*(run(call) for call in calls)))
