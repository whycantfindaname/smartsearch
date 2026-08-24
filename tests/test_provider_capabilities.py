import asyncio
import json
from collections.abc import Mapping
from typing import Any

import httpx
import pytest

from smart_search.provider_capabilities import (
    CapabilityCall,
    ExaDeepSearchAdapter,
    FirecrawlV2Adapter,
    JinaCapabilityAdapter,
    TavilyCapabilityAdapter,
    gather_capability_calls,
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
            {
                "method": method,
                "url": url,
                "headers": dict(headers),
                "json": json,
                "timeout": timeout,
            }
        )
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


@pytest.mark.asyncio
async def test_firecrawl_v2_scrape_crawl_and_batch_scrape_request_shapes():
    transport = FakeTransport(
        FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "markdown": "Extracted",
                    "metadata": {"url": "https://extract.test"},
                },
            },
        ),
        FakeResponse(
            200, {"success": True, "id": "crawl-1", "url": "https://example.test"}
        ),
        FakeResponse(
            200,
            {
                "status": "completed",
                "total": 1,
                "completed": 1,
                "data": [{"markdown": "A"}],
            },
        ),
        FakeResponse(
            200,
            {"success": True, "id": "batch-1", "url": "https://api.firecrawl.dev/job"},
        ),
        FakeResponse(
            200, {"status": "completed", "total": 2, "completed": 2, "data": [{}, {}]}
        ),
    )
    adapter = FirecrawlV2Adapter("fc-secret", transport=transport, poll_interval=0)

    scrape = await adapter.scrape(
        "https://extract.test", options={"formats": ["markdown"]}
    )
    crawl = await adapter.crawl("https://example.test", options={"limit": 25})
    batch = await adapter.batch_scrape(
        ["https://a.test", "https://b.test"], options={"formats": ["markdown"]}
    )

    assert scrape["status"] == crawl["status"] == batch["status"] == "succeeded"
    assert transport.calls[0]["url"] == "https://api.firecrawl.dev/v2/scrape"
    assert transport.calls[0]["json"] == {
        "formats": ["markdown"],
        "url": "https://extract.test",
    }
    assert transport.calls[1] == {
        "method": "POST",
        "url": "https://api.firecrawl.dev/v2/crawl",
        "headers": {
            "Authorization": "Bearer fc-secret",
            "Content-Type": "application/json",
        },
        "json": {"limit": 25, "url": "https://example.test"},
        "timeout": 30.0,
    }
    assert transport.calls[2]["method"] == "GET"
    assert transport.calls[2]["url"] == "https://api.firecrawl.dev/v2/crawl/crawl-1"
    assert transport.calls[3]["url"] == "https://api.firecrawl.dev/v2/batch/scrape"
    assert transport.calls[3]["json"] == {
        "formats": ["markdown"],
        "urls": ["https://a.test", "https://b.test"],
    }
    assert (
        transport.calls[4]["url"] == "https://api.firecrawl.dev/v2/batch/scrape/batch-1"
    )
    assert crawl["request"]["submit"]["headers"]["Authorization"] == "[REDACTED]"
    assert crawl["result"]["terminal"]["data"] == [{"markdown": "A"}]


@pytest.mark.asyncio
async def test_firecrawl_v2_research_and_developer_index_request_shapes():
    transport = FakeTransport(
        FakeResponse(200, {"success": True, "results": [{"id": "paper-1"}]}),
        FakeResponse(
            200, {"success": True, "paper": {"id": "paper/1", "title": "Paper"}}
        ),
        FakeResponse(
            200,
            {
                "success": True,
                "results": [{"id": "paper-2"}],
                "poolSize": 8,
                "truncated": False,
            },
        ),
        FakeResponse(
            200,
            {
                "success": True,
                "results": [{"repository": "acme/sdk"}],
                "coverage": {"repositories": 1, "sources": ["github"]},
                "reranked": True,
                "query": "stream parser",
                "k": 5,
            },
        ),
    )
    adapter = FirecrawlV2Adapter("fc-secret", transport=transport)

    search = await adapter.research_search(
        "multimodal quality",
        options={
            "k": 25,
            "authors": ["Liao Wenjie", "Ada Lovelace"],
            "categories": ["cs.CV", "cs.AI"],
            "from": "2024-01-01",
            "to": "2026-08-24",
        },
    )
    read = await adapter.research_read("paper/1?#", options={"query": "IQA", "k": 4})
    related = await adapter.research_related(
        "paper/1",
        "find references & citers",
        options={"mode": "references", "k": 7, "rerank": True, "anchor": ["a", "b"]},
    )
    developer = await adapter.developer_search(
        "stream parser",
        options={
            "k": 5,
            "types": ["issue", "pull_request"],
            "repos": ["acme/sdk", "acme/cli"],
            "sources": ["github", "npm"],
            "skills": "only",
            "passages": 3,
            "language": "python",
            "topic": "search",
            "license": "MIT",
            "min_stars": 10,
            "max_stars": 5000,
            "archived": False,
            "fork": False,
        },
    )

    assert [
        search["status"],
        read["status"],
        related["status"],
        developer["status"],
    ] == [
        "succeeded",
        "succeeded",
        "succeeded",
        "succeeded",
    ]
    assert [
        search["capability"],
        read["capability"],
        related["capability"],
        developer["capability"],
    ] == [
        "academic_search",
        "academic_read",
        "academic_related",
        "developer_search",
    ]
    assert transport.calls[0] == {
        "method": "GET",
        "url": (
            "https://api.firecrawl.dev/v2/search/research/papers?"
            "query=multimodal+quality&k=25&authors=Liao+Wenjie&authors=Ada+Lovelace&"
            "categories=cs.CV&categories=cs.AI&from=2024-01-01&to=2026-08-24"
        ),
        "headers": {"Authorization": "Bearer fc-secret"},
        "json": None,
        "timeout": 30.0,
    }
    assert transport.calls[1]["url"] == (
        "https://api.firecrawl.dev/v2/search/research/papers/paper%2F1%3F%23?query=IQA&k=4"
    )
    assert transport.calls[2]["url"] == (
        "https://api.firecrawl.dev/v2/search/research/papers/paper%2F1/similar?"
        "intent=find+references+%26+citers&mode=references&k=7&rerank=true&anchor=a&anchor=b"
    )
    assert transport.calls[3]["url"] == (
        "https://api.firecrawl.dev/v2/search/developer?query=stream+parser&k=5&"
        "types=issue&types=pull_request&repos=acme%2Fsdk&repos=acme%2Fcli&"
        "sources=github&sources=npm&skills=only&passages=3&language=python&"
        "topic=search&license=MIT&min_stars=10&max_stars=5000&archived=false&fork=false"
    )
    assert developer["result"]["coverage"] == {"repositories": 1, "sources": ["github"]}
    assert developer["result"]["query"] == "stream parser"
    assert all(call["json"] is None for call in transport.calls)
    assert all(
        call["headers"] == {"Authorization": "Bearer fc-secret"}
        for call in transport.calls
    )
    assert "fc-secret" not in json.dumps([search, read, related, developer])


@pytest.mark.asyncio
async def test_firecrawl_v2_research_related_truncated_is_partial():
    transport = FakeTransport(
        FakeResponse(
            200,
            {
                "success": True,
                "results": [{"id": "kept"}],
                "poolSize": 501,
                "truncated": True,
            },
        )
    )

    result = await FirecrawlV2Adapter("fc-key", transport=transport).research_related(
        "paper-1", "similar work"
    )

    assert result["status"] == "partial"
    assert result["result"]["truncated"] is True
    assert result["errors"] == [
        {
            "error_type": "provider_partial",
            "message": "provider returned partial results",
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "response"),
    [
        ("research_search", {"success": True, "results": {}}),
        ("research_read", {"success": True, "paper": []}),
        (
            "research_related",
            {"success": True, "results": [], "poolSize": 0, "truncated": "false"},
        ),
        (
            "developer_search",
            {"success": True, "results": [], "coverage": [], "reranked": False},
        ),
    ],
)
async def test_firecrawl_v2_index_malformed_success_shapes_are_attempt_facts(
    operation: str, response: Mapping[str, Any]
):
    transport = FakeTransport(FakeResponse(200, response))
    adapter = FirecrawlV2Adapter("fc-key", transport=transport)
    arguments = {
        "research_search": {"query": "q", "options": {}},
        "research_read": {"paper_id": "paper", "options": {}},
        "research_related": {"paper_id": "paper", "intent": "similar", "options": {}},
        "developer_search": {"query": "q", "options": {}},
    }[operation]

    result = await adapter.execute(operation, arguments)

    assert result["status"] == "failed"
    assert result["reachable"] is True
    assert result["entitled"] is True
    assert result["errors"][0]["error_type"] == "malformed_response"
    assert len(transport.calls) == 1


@pytest.mark.asyncio
async def test_firecrawl_v2_index_provider_failure_and_invalid_arguments_are_bounded_facts():
    provider_failure_transport = FakeTransport(
        FakeResponse(200, {"success": False, "error": "index unavailable"})
    )
    invalid_transport = FakeTransport()

    provider_failure = await FirecrawlV2Adapter(
        "fc-key", transport=provider_failure_transport
    ).developer_search("query")
    invalid = await FirecrawlV2Adapter(
        "fc-key", transport=invalid_transport
    ).research_search("query", options={"k": 501})
    invalid_read = await FirecrawlV2Adapter(
        "fc-key", transport=invalid_transport
    ).research_read("paper", options={"query": "question", "k": 51})
    invalid_developer = await FirecrawlV2Adapter(
        "fc-key", transport=invalid_transport
    ).developer_search(
        "query", options={"types": ["repository"], "passages": True}
    )

    assert provider_failure["status"] == "failed"
    assert provider_failure["errors"][0]["error_type"] == "provider_failed"
    assert invalid["status"] == "failed"
    assert invalid["errors"][0]["error_type"] == "runtime_error"
    assert invalid_read["status"] == "failed"
    assert invalid_read["errors"][0]["error_type"] == "runtime_error"
    assert invalid_developer["status"] == "failed"
    assert invalid_developer["errors"][0]["error_type"] == "runtime_error"
    assert invalid_transport.calls == []


@pytest.mark.asyncio
async def test_firecrawl_developer_search_accepts_omitted_optional_metadata():
    transport = FakeTransport(
        FakeResponse(
            200,
            {
                "success": True,
                "results": [
                    {
                        "id": "readme:acme/search-agent",
                        "title": "acme/search-agent",
                        "url": "https://github.com/acme/search-agent",
                        "passages": [{"text": "Agentic search benchmark"}],
                    }
                ],
            },
        )
    )

    result = await FirecrawlV2Adapter("fc-key", transport=transport).developer_search(
        "agentic search", options={"types": ["readme"], "passages": 3}
    )

    assert result["status"] == "succeeded"
    assert result["result"]["results"][0]["id"] == "readme:acme/search-agent"


@pytest.mark.asyncio
async def test_tavily_crawl_success_and_extract_partial_are_distinct():
    transport = FakeTransport(
        FakeResponse(
            200, {"base_url": "docs.test", "results": [{"url": "https://docs.test/a"}]}
        ),
        FakeResponse(
            200,
            {
                "results": [{"url": "https://a.test", "raw_content": "A"}],
                "failed_results": [{"url": "https://b.test", "error": "blocked"}],
                "request_id": "request-1",
            },
        ),
    )
    adapter = TavilyCapabilityAdapter("tvly-secret", transport=transport)

    crawl = await adapter.crawl("https://docs.test", options={"max_depth": 2})
    extract = await adapter.extract(
        ["https://a.test", "https://b.test"], options={"include_usage": True}
    )

    assert crawl["status"] == "succeeded"
    assert extract["status"] == "partial"
    assert extract["errors"][0]["error_type"] == "provider_partial"
    assert transport.calls[0]["url"] == "https://api.tavily.com/crawl"
    assert transport.calls[0]["json"] == {"max_depth": 2, "url": "https://docs.test"}
    assert transport.calls[1]["url"] == "https://api.tavily.com/extract"
    assert transport.calls[1]["json"] == {
        "include_usage": True,
        "urls": ["https://a.test", "https://b.test"],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("search_type", ["deep", "deep-reasoning"])
async def test_exa_deep_search_request_shape_and_success(search_type: str):
    transport = FakeTransport(
        FakeResponse(
            200, {"requestId": "exa-1", "results": [{"url": "https://example.test"}]}
        )
    )
    adapter = ExaDeepSearchAdapter("exa-secret", transport=transport)

    result = await adapter.search(
        "current contract",
        search_type=search_type,
        options={"numResults": 7, "contents": {"highlights": True}},
    )

    assert result["status"] == "succeeded"
    assert transport.calls[0]["url"] == "https://api.exa.ai/search"
    assert transport.calls[0]["headers"]["x-api-key"] == "exa-secret"
    assert transport.calls[0]["json"] == {
        "numResults": 7,
        "contents": {"highlights": True},
        "query": "current contract",
        "type": search_type,
    }


@pytest.mark.asyncio
async def test_jina_search_and_reranker_request_shapes():
    transport = FakeTransport(
        FakeResponse(
            200, {"data": [{"title": "Result", "url": "https://example.test"}]}
        ),
        FakeResponse(
            200,
            {
                "model": "jina-reranker-v3.5",
                "results": [{"index": 1, "relevance_score": 0.9}],
            },
        ),
    )
    adapter = JinaCapabilityAdapter("jina-secret", transport=transport)

    search = await adapter.search("API shape & auth")
    rerank = await adapter.rerank("best", ["first", "second"], options={"top_n": 1})

    assert search["status"] == rerank["status"] == "succeeded"
    assert transport.calls[0]["method"] == "GET"
    assert transport.calls[0]["url"] == "https://s.jina.ai/?q=API+shape+%26+auth"
    assert transport.calls[0]["headers"]["Accept"] == "application/json"
    assert transport.calls[0]["json"] is None
    assert transport.calls[1]["url"] == "https://api.jina.ai/v1/rerank"
    assert transport.calls[1]["json"] == {
        "top_n": 1,
        "model": "jina-reranker-v3.5",
        "query": "best",
        "documents": ["first", "second"],
    }


@pytest.mark.asyncio
async def test_missing_key_is_not_configured_without_transport_call():
    transport = FakeTransport()

    result = await FirecrawlV2Adapter("", transport=transport, poll_interval=0).crawl(
        "https://example.test"
    )

    assert result["status"] == "not_configured"
    assert result["configured"] is False
    assert result["reachable"] is None
    assert result["entitled"] is None
    assert result["errors"][0]["error_type"] == "missing_key"
    assert transport.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 402, 403])
async def test_auth_or_entitlement_is_separate_from_reachability_and_sanitized(
    status_code: int,
):
    secret = "tvly-private-key"
    transport = FakeTransport(
        FakeResponse(status_code, {"error": f"Bearer {secret}", "api_key": secret})
    )

    result = await TavilyCapabilityAdapter(secret, transport=transport).crawl(
        "https://example.test"
    )

    assert result["status"] == "entitlement_denied"
    assert result["configured"] is True
    assert result["reachable"] is True
    assert result["entitled"] is False
    assert secret not in json.dumps(result)
    assert "[REDACTED]" in json.dumps(result)


@pytest.mark.asyncio
async def test_timeout_and_malformed_response_have_independent_failure_facts():
    timeout_transport = FakeTransport(asyncio.TimeoutError("slow provider"))
    malformed_transport = FakeTransport(FakeResponse(200, {"unexpected": []}))

    timeout_result = await ExaDeepSearchAdapter(
        "exa-key", transport=timeout_transport
    ).search("q")
    malformed_result = await JinaCapabilityAdapter(
        "jina-key", transport=malformed_transport
    ).rerank("q", ["document"])

    assert timeout_result["status"] == "timeout"
    assert timeout_result["errors"][0]["error_type"] == "timeout"
    assert malformed_result["status"] == "failed"
    assert malformed_result["reachable"] is True
    assert malformed_result["entitled"] is True
    assert malformed_result["result"] == {"unexpected": []}
    assert malformed_result["errors"][0]["error_type"] == "malformed_response"


class ExplodingAdapter(FirecrawlV2Adapter):
    async def execute(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        raise RuntimeError("one operation exploded")


class BarrierTransport(FakeTransport):
    def __init__(
        self, *responses: FakeResponse, shared: dict[str, int], release: asyncio.Event
    ):
        super().__init__(*responses)
        self.shared = shared
        self.release = release

    async def request(self, *args: Any, **kwargs: Any) -> FakeResponse:
        self.shared["active"] += 1
        self.shared["maximum"] = max(self.shared["maximum"], self.shared["active"])
        if self.shared["active"] == self.shared["expected"]:
            self.release.set()
        await asyncio.wait_for(self.release.wait(), timeout=1)
        self.shared["active"] -= 1
        return await super().request(*args, **kwargs)


@pytest.mark.asyncio
async def test_gather_is_concurrent_unbounded_and_one_failure_never_raises():
    good_count = 5
    shared = {"active": 0, "maximum": 0, "expected": good_count}
    release = asyncio.Event()
    calls = [
        CapabilityCall(
            FirecrawlV2Adapter(
                f"key-{index}",
                transport=BarrierTransport(
                    FakeResponse(200, {"success": True, "id": f"job-{index}"}),
                    FakeResponse(200, {"status": "completed", "data": []}),
                    shared=shared,
                    release=release,
                ),
                poll_interval=0,
            ),
            "crawl",
            {"url": f"https://example{index}.test", "options": {}},
        )
        for index in range(good_count)
    ]
    calls.insert(
        2,
        CapabilityCall(
            ExplodingAdapter("bad-key", transport=FakeTransport()),
            "crawl",
            {"url": "https://bad.test", "options": {}},
        ),
    )
    calls.append(
        CapabilityCall(
            FirecrawlV2Adapter("invalid-key", transport=FakeTransport()),
            "unknown",
            {},
        )
    )

    results = await gather_capability_calls(calls)

    assert len(results) == good_count + 2
    assert shared["maximum"] == good_count
    assert [result["status"] for result in results].count("succeeded") == good_count
    assert results[2]["status"] == "failed"
    assert results[2]["errors"][0]["error_type"] == "runtime_error"
    assert results[-1]["status"] == "failed"
    assert results[-1]["capability"] == "unknown"


@pytest.mark.asyncio
async def test_transport_network_failure_is_unreachable():
    request = httpx.Request("POST", "https://api.firecrawl.dev/v2/crawl")
    transport = FakeTransport(httpx.ConnectError("offline", request=request))

    result = await FirecrawlV2Adapter("fc-key", transport=transport).crawl(
        "https://example.test"
    )

    assert result["status"] == "unreachable"
    assert result["reachable"] is False
    assert result["entitled"] is None
    assert result["errors"][0]["error_type"] == "network_error"


class AdvancingClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    async def sleep(self, seconds: float) -> None:
        self.value += seconds


@pytest.mark.asyncio
async def test_firecrawl_polling_timeout_and_partial_terminal_result():
    timeout_clock = AdvancingClock()
    timeout_transport = FakeTransport(
        FakeResponse(200, {"success": True, "id": "slow-job"}),
        FakeResponse(200, {"status": "scraping", "data": []}),
        FakeResponse(200, {"status": "scraping", "data": []}),
    )
    partial_transport = FakeTransport(
        FakeResponse(200, {"success": True, "id": "partial-job"}),
        FakeResponse(
            200,
            {
                "status": "completed",
                "completed": 1,
                "data": [{"markdown": "kept"}],
                "next": "https://api.firecrawl.dev/v2/batch/scrape/partial-job?skip=1",
            },
        ),
    )

    timeout_result = await FirecrawlV2Adapter(
        "fc-key",
        transport=timeout_transport,
        clock=timeout_clock,
        sleep=timeout_clock.sleep,
        poll_interval=1,
    ).crawl("https://slow.test", timeout_seconds=2)
    partial_result = await FirecrawlV2Adapter(
        "fc-key", transport=partial_transport, poll_interval=0
    ).batch_scrape(["https://a.test", "https://b.test"])

    assert timeout_result["status"] == "timeout"
    assert timeout_result["errors"][0]["error_type"] == "deadline_exceeded"
    assert partial_result["status"] == "partial"
    assert partial_result["result"]["terminal"]["data"] == [{"markdown": "kept"}]
