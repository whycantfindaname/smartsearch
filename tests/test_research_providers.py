import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from smart_search.research_providers import (
    ExaResearchAdapter,
    FirecrawlResearchAdapter,
    JinaDeepSearchAdapter,
    ResearchProviderAdapter,
    TavilyResearchAdapter,
    build_research_provider_adapters,
    capability_inventory,
    run_deep_provider_agents,
)


class FakeResponse:
    def __init__(self, status_code: int, data: Any):
        self.status_code = status_code
        self.data = data
        self.text = data if isinstance(data, str) else json.dumps(data)

    def json(self) -> Any:
        if isinstance(self.data, BaseException):
            raise self.data
        if isinstance(self.data, str):
            return json.loads(self.data)
        return self.data


class FakeTransport:
    def __init__(self, *responses: FakeResponse | BaseException):
        self.responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str],
        json: Mapping[str, Any] | None = None,
        timeout: float | None = None,
    ) -> FakeResponse:
        self.calls.append(
            {"method": method, "url": url, "headers": dict(headers), "json": json, "timeout": timeout}
        )
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class FakeClock:
    def __init__(self, value: float = 1_700_000_000.0):
        self.value = value

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.value += seconds
        await asyncio.sleep(0)


@pytest.mark.asyncio
async def test_missing_key_still_yields_independent_attempt_without_network():
    transport = FakeTransport()
    adapter = FirecrawlResearchAdapter("", transport=transport)

    result = await adapter.run("question")

    assert result["status"] == "not_configured"
    assert result["configured"] is False
    assert result["reachable"] is None
    assert result["entitled"] is None
    assert result["external_job"] == {"id": "", "cursor": None}
    assert result["errors"][0]["error_type"] == "missing_key"
    assert transport.calls == []


@pytest.mark.asyncio
async def test_firecrawl_success_polls_and_normalizes_candidate_layer():
    clock = FakeClock()
    transport = FakeTransport(
        FakeResponse(200, {"success": True, "id": "fc-job"}),
        FakeResponse(200, {"status": "processing"}),
        FakeResponse(
            200,
            {
                "status": "completed",
                "data": {
                    "finalAnalysis": "Firecrawl report",
                    "sources": [{"title": "Primary", "url": "https://example.test/firecrawl"}],
                },
                "creditsUsed": 7,
            },
        ),
    )
    adapter = FirecrawlResearchAdapter(
        "fc-test", transport=transport, clock=clock, sleep=clock.sleep, poll_interval=1
    )

    result = await adapter.run("research this", timeout_seconds=10, run_id="run-1")

    assert result["status"] == "succeeded"
    assert result["external_job"] == {"id": "fc-job", "cursor": None}
    assert result["report"] == "Firecrawl report"
    assert result["usage"] == {"credits_used": 7}
    assert result["candidates"][0]["candidate_layer"] == "discovery"
    assert result["candidates"][0]["evidence_status"] == "pending_source_reread"
    assert [call["method"] for call in transport.calls] == ["POST", "GET", "GET"]


@pytest.mark.asyncio
async def test_tavily_success_shape():
    transport = FakeTransport(
        FakeResponse(201, {"request_id": "tv-job", "status": "pending"}),
        FakeResponse(
            200,
            {
                "request_id": "tv-job",
                "status": "completed",
                "content": "Tavily report",
                "sources": [{"title": "Source", "url": "https://example.test/tavily"}],
                "response_time": 4.5,
            },
        ),
    )
    adapter = TavilyResearchAdapter("tvly-test", transport=transport, poll_interval=0)

    result = await adapter.run("question")

    assert result["status"] == "succeeded"
    assert result["report"] == "Tavily report"
    assert result["usage"]["response_time_seconds"] == 4.5
    assert transport.calls[0]["json"] == {"input": "question", "stream": False}
    assert transport.calls[1]["url"].endswith("/research/tv-job")


@pytest.mark.asyncio
async def test_exa_agent_success_shape_and_beta_header():
    transport = FakeTransport(
        FakeResponse(200, {"id": "agent_run_1", "status": "queued"}),
        FakeResponse(
            200,
            {
                "id": "agent_run_1",
                "status": "completed",
                "output": {
                    "text": "Exa report",
                    "structured": None,
                    "grounding": [
                        {
                            "field": "text",
                            "citations": [{"title": "Paper", "url": "https://example.test/exa"}],
                        }
                    ],
                },
                "usage": {"searches": 3, "agentComputeUnits": 1.5},
                "costDollars": {"total": 0.04},
            },
        ),
    )
    adapter = ExaResearchAdapter("exa-test", transport=transport, poll_interval=0)

    result = await adapter.run("question")

    assert result["status"] == "succeeded"
    assert result["report"] == "Exa report"
    assert result["candidates"][0]["url"] == "https://example.test/exa"
    assert result["usage"]["searches"] == 3
    assert result["usage"]["cost_dollars"] == {"total": 0.04}
    assert transport.calls[0]["headers"]["Exa-Beta"] == "agent-2026-05-07"


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["deep", "deep-reasoning"])
async def test_exa_deep_search_success_shapes(operation: str):
    transport = FakeTransport(
        FakeResponse(
            200,
            {
                "requestId": "search-1",
                "results": [
                    {
                        "title": "Deep result",
                        "url": "https://example.test/deep",
                        "summary": "summary",
                    }
                ],
                "costDollars": {"total": 0.01},
            },
        )
    )
    adapter = ExaResearchAdapter("exa-test", operation=operation, transport=transport)

    result = await adapter.run("question")

    assert result["status"] == "succeeded"
    assert result["candidates"][0]["url"] == "https://example.test/deep"
    assert transport.calls[0]["json"]["type"] == operation
    assert "Exa-Beta" not in transport.calls[0]["headers"]


@pytest.mark.asyncio
async def test_jina_success_shape():
    transport = FakeTransport(
        FakeResponse(
            200,
            {
                "id": "chat-1",
                "choices": [
                    {
                        "message": {
                            "content": "Jina report",
                            "citations": [{"title": "Doc", "url": "https://example.test/jina"}],
                        }
                    }
                ],
                "usage": {"total_tokens": 99},
            },
        )
    )
    adapter = JinaDeepSearchAdapter("jina-test", transport=transport)

    result = await adapter.run("question")

    assert result["status"] == "succeeded"
    assert result["report"] == "Jina report"
    assert result["usage"] == {"total_tokens": 99}
    assert transport.calls[0]["url"] == "https://deepsearch.jina.ai/v1/chat/completions"
    assert transport.calls[0]["json"]["model"] == "jina-deepsearch-v1"


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 402, 403])
async def test_auth_or_entitlement_denied_is_distinct(status_code: int):
    transport = FakeTransport(FakeResponse(status_code, {"error": "plan does not include research"}))
    adapter = TavilyResearchAdapter("tvly-test", transport=transport)

    result = await adapter.run("question")

    assert result["status"] == "entitlement_denied"
    assert result["reachable"] is True
    assert result["entitled"] is False
    assert result["errors"][0]["http_status"] == status_code


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_status", "error_type"),
    [
        (408, "timeout", "upstream_timeout"),
        (429, "failed", "rate_limited"),
        (503, "unreachable", "upstream_unavailable"),
    ],
)
async def test_retryable_http_failures_are_terminal_without_adapter_retries(
    status_code: int, expected_status: str, error_type: str
):
    transport = FakeTransport(FakeResponse(status_code, {"error": "temporary failure"}))
    adapter = FirecrawlResearchAdapter("fc-test", transport=transport)

    result = await adapter.run("question")

    assert result["status"] == expected_status
    assert result["errors"][0]["error_type"] == error_type
    assert len(transport.calls) == 1


@pytest.mark.asyncio
async def test_safe_polling_deadline_has_no_unbounded_retry():
    clock = FakeClock()
    transport = FakeTransport(
        FakeResponse(200, {"id": "fc-job"}),
        FakeResponse(200, {"status": "processing"}),
        FakeResponse(200, {"status": "processing"}),
    )
    adapter = FirecrawlResearchAdapter(
        "fc-test", transport=transport, clock=clock, sleep=clock.sleep, poll_interval=1
    )

    result = await adapter.run("question", timeout_seconds=2)

    assert result["status"] == "timeout"
    assert result["reachable"] is True
    assert result["entitled"] is True
    assert result["errors"][0]["error_type"] == "deadline_exceeded"
    assert len(transport.calls) == 3


@pytest.mark.asyncio
async def test_partial_terminal_response_preserves_report_and_candidate():
    transport = FakeTransport(
        FakeResponse(201, {"request_id": "tv-job", "status": "pending"}),
        FakeResponse(
            200,
            {
                "request_id": "tv-job",
                "status": "failed",
                "content": "Report before failure",
                "sources": [{"url": "https://example.test/partial"}],
                "detail": "upstream source failed",
            },
        ),
    )
    adapter = TavilyResearchAdapter("tvly-test", transport=transport, poll_interval=0)

    result = await adapter.run("question")

    assert result["status"] == "partial"
    assert result["report"] == "Report before failure"
    assert result["candidates"][0]["evidence_status"] == "pending_source_reread"
    assert result["errors"][0]["error_type"] == "provider_partial"


@pytest.mark.asyncio
async def test_exa_budget_reached_and_jina_nested_url_citation_are_partial_candidates():
    exa_transport = FakeTransport(
        FakeResponse(200, {"id": "agent_run_1", "status": "queued"}),
        FakeResponse(
            200,
            {
                "id": "agent_run_1",
                "status": "completed",
                "stopReason": "budget_reached",
                "output": {"text": "bounded report", "structured": None, "grounding": []},
            },
        ),
    )
    jina_transport = FakeTransport(
        FakeResponse(
            200,
            {
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {
                            "content": "truncated report",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url_citation": {
                                        "title": "Nested citation",
                                        "url": "https://example.test/nested",
                                    },
                                }
                            ],
                        },
                    }
                ]
            },
        )
    )

    exa_result, jina_result = await asyncio.gather(
        ExaResearchAdapter("exa-test", transport=exa_transport, poll_interval=0).run("question"),
        JinaDeepSearchAdapter("jina-test", transport=jina_transport).run("question"),
    )

    assert exa_result["status"] == "partial"
    assert jina_result["status"] == "partial"
    assert jina_result["candidates"][0]["url"] == "https://example.test/nested"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "adapter",
    [
        FirecrawlResearchAdapter("fc-test", transport=FakeTransport(FakeResponse(200, {"success": True}))),
        JinaDeepSearchAdapter("jina-test", transport=FakeTransport(FakeResponse(200, {"id": "chat-1"}))),
    ],
)
async def test_malformed_response_is_failed(adapter: ResearchProviderAdapter):
    result = await adapter.run("question")

    assert result["status"] == "failed"
    assert result["errors"][0]["error_type"] == "malformed_response"
    assert result["artifact"]["raw_response"]


class ConcurrentProbeAdapter(ResearchProviderAdapter):
    provider_api_version = "test"

    def __init__(self, provider: str, shared: dict[str, int], release: asyncio.Event):
        self.provider = provider
        self.shared = shared
        self.release = release
        super().__init__("test-key", "https://example.test")

    async def submit(self, query: str, *, timeout: float) -> Mapping[str, Any]:
        self.shared["active"] += 1
        self.shared["maximum"] = max(self.shared["maximum"], self.shared["active"])
        if self.shared["active"] == self.shared["expected"]:
            self.release.set()
        await asyncio.wait_for(self.release.wait(), timeout=1)
        self.shared["active"] -= 1
        return {"id": self.provider}

    async def poll_or_stream(
        self, submission: Mapping[str, Any], *, deadline: float
    ) -> Any:
        from smart_search.research_providers import LifecycleResult

        return LifecycleResult({"status": "completed"}, "succeeded")

    async def normalize(self, raw_response: Mapping[str, Any], *, artifact_ref: str) -> dict[str, Any]:
        return {"report": self.provider, "candidates": []}


@pytest.mark.asyncio
async def test_deep_runner_starts_all_providers_concurrently_without_count_cap():
    provider_count = 6
    shared = {"active": 0, "maximum": 0, "expected": provider_count}
    release = asyncio.Event()
    adapters = [ConcurrentProbeAdapter(f"provider-{index}", shared, release) for index in range(provider_count)]

    result = await run_deep_provider_agents("question", adapters)

    assert len(result["attempts"]) == provider_count
    assert shared["maximum"] == provider_count
    assert {attempt["status"] for attempt in result["attempts"]} == {"succeeded"}


class ExplodingAdapter(ConcurrentProbeAdapter):
    async def run(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("independent explosion")


@pytest.mark.asyncio
async def test_one_provider_exception_does_not_fail_aggregate():
    shared = {"active": 0, "maximum": 0, "expected": 1}
    release = asyncio.Event()
    good = ConcurrentProbeAdapter("good", shared, release)
    bad = ExplodingAdapter("bad", shared, release)

    result = await run_deep_provider_agents("question", [bad, good])

    assert [attempt["status"] for attempt in result["attempts"]] == ["failed", "succeeded"]
    assert result["degraded"] is True


@pytest.mark.asyncio
async def test_transport_failure_is_unreachable_and_independent():
    request = httpx.Request("POST", "https://api.firecrawl.dev/v2/agent")
    transport = FakeTransport(httpx.ConnectError("offline", request=request))
    adapter = FirecrawlResearchAdapter("fc-test", transport=transport)

    result = await adapter.run("question")

    assert result["status"] == "unreachable"
    assert result["reachable"] is False


@pytest.mark.asyncio
async def test_secret_is_redacted_from_errors_raw_artifact_and_request_summary():
    secret = "super-secret-provider-key"
    transport = FakeTransport(
        FakeResponse(
            403,
            {
                "error": f"Authorization: Bearer {secret}",
                "api_key": secret,
                "nested": {"token": secret},
            },
        )
    )
    adapter = FirecrawlResearchAdapter(secret, transport=transport)

    result = await adapter.run(f"do not echo {secret}")
    serialized = json.dumps(result)

    assert secret not in serialized
    assert "[REDACTED]" in serialized
    assert result["request_summary"]["query_preview"] == "do not echo [REDACTED]"


def test_inventory_separates_configured_reachable_and_entitled():
    clock = FakeClock()
    adapters = build_research_provider_adapters(
        {"firecrawl": "configured", "exa": "configured"}, clock=clock, sleep=clock.sleep
    )
    attempts = [
        {
            "provider": "firecrawl",
            "status": "entitlement_denied",
            "reachable": True,
            "entitled": False,
            "observed_at": "2026-08-24T00:00:00Z",
        }
    ]

    inventory = capability_inventory(adapters, attempts, clock=clock)

    assert set(inventory["capability_pool"]) == {
        "general_current",
        "docs_api",
        "academic",
        "code_developer",
        "known_url",
        "crawl_extract_batch",
    }
    assert inventory["providers"]["firecrawl"]["configured"] is True
    assert inventory["providers"]["firecrawl"]["reachable"] is True
    assert inventory["providers"]["firecrawl"]["entitled"] is False
    assert inventory["providers"]["exa"]["configured"] is True
    assert inventory["providers"]["exa"]["reachable"] is None
    assert inventory["providers"]["exa"]["entitled"] is None
    assert inventory["providers"]["jina"]["status"] == "not_configured"
    assert "search:deep-reasoning" in inventory["providers"]["exa"]["operations"]
