import asyncio
import time

import httpx
import pytest

from smart_search.config import Config
from smart_search.providers.xai_responses import XAIResponsesSearchProvider
from smart_search.providers.xai_responses import XAIRequestHardTimeout
from smart_search.providers.xai_responses import XAIRequestOutcomeUnknown
from smart_search.sources import split_answer_and_sources


class DummyResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def json(self):
        return self._json_data


def output_text_response(text, annotations=None):
    return DummyResponse(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": text,
                            "annotations": annotations or [],
                        }
                    ],
                }
            ]
        }
    )


def test_xai_responses_search_payload_uses_responses_shape():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search", "x_search"])

    payload = provider._build_search_payload("What is new?", "X")

    assert payload["model"] == "test-model"
    assert payload["instructions"]
    assert payload["stream"] is False
    assert payload["tools"] == [{"type": "web_search"}, {"type": "x_search"}]
    assert payload["input"][0]["role"] == "user"
    assert "What is new?" in payload["input"][0]["content"]
    assert "X" in payload["input"][0]["content"]


@pytest.mark.asyncio
async def test_xai_responses_parse_output_text_and_url_citations():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])
    response = DummyResponse(
        {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "Answer [[1]](https://example.com/a).",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url": "https://example.com/a",
                                    "title": "1",
                                    "start_index": 7,
                                    "end_index": 10,
                                },
                                {
                                    "type": "url_citation",
                                    "url": "https://example.com/a",
                                    "title": "duplicate",
                                },
                            ],
                        }
                    ],
                }
            ]
        }
    )

    result = await provider._parse_response(response)

    assert "Answer [[1]](https://example.com/a)." in result
    assert "sources(" in result
    assert result.count("https://example.com/a") == 2


@pytest.mark.asyncio
async def test_xai_responses_structured_url_citations_win_over_inline_urls():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])
    response = output_text_response(
        "Use [the inline link](https://inline.example.com/ignored) for context.",
        [
            {
                "type": "url_citation",
                "url": "https://structured.example.com/authoritative",
                "title": "Structured source",
            }
        ],
    )

    result = await provider._parse_response(response)
    answer, sources = split_answer_and_sources(result)

    assert answer == "Use [the inline link](https://inline.example.com/ignored) for context."
    assert sources == [
        {
            "url": "https://structured.example.com/authoritative",
            "title": "Structured source",
        }
    ]


@pytest.mark.asyncio
async def test_xai_responses_extracts_ordered_unique_markdown_and_bare_urls():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])
    response = output_text_response(
        "Read [the docs](https://docs.example.com/guide), then "
        "HTTPS://news.example.com/latest; repeat https://docs.example.com/guide."
    )

    result = await provider._parse_response(response)
    answer, sources = split_answer_and_sources(result)

    assert answer == (
        "Read [the docs](https://docs.example.com/guide), then "
        "HTTPS://news.example.com/latest; repeat https://docs.example.com/guide."
    )
    assert sources == [
        {"url": "https://docs.example.com/guide"},
        {"url": "https://news.example.com/latest"},
    ]


@pytest.mark.asyncio
async def test_xai_responses_inline_url_fallback_trims_ascii_and_cjk_terminal_punctuation():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])
    response = output_text_response(
        "[ASCII](https://ascii.example.com/path). "
        "CJK https://cjk.example.com/path， "
        "closer https://closer.example.com/path） "
        "bracket https://bracket.example.com/path】 "
        "balanced https://wiki.example.com/Function_(mathematics)."
    )

    result = await provider._parse_response(response)
    _, sources = split_answer_and_sources(result)

    assert [source["url"] for source in sources] == [
        "https://ascii.example.com/path",
        "https://cjk.example.com/path",
        "https://closer.example.com/path",
        "https://bracket.example.com/path",
        "https://wiki.example.com/Function_(mathematics)",
    ]


@pytest.mark.asyncio
async def test_xai_responses_inline_url_fallback_rejects_malformed_and_non_http_urls():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])
    response = output_text_response(
        "Ignore ftp://files.example.com/archive, mailto:person@example.com, "
        "https:///missing-host, https://?missing-host, http://[bad, and "
        "https://port.example.com:not-a-port, xhttps://prefixed.example.com/path, and "
        "https://backslash.example.com/path\\tail. Keep https://valid.example.com/path."
    )

    result = await provider._parse_response(response)
    _, sources = split_answer_and_sources(result)

    assert sources == [{"url": "https://valid.example.com/path"}]


@pytest.mark.asyncio
async def test_xai_responses_inline_url_fallback_keeps_answers_without_urls_unchanged():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])

    result = await provider._parse_response(output_text_response("No citation URLs were returned."))

    assert result == "No citation URLs were returned."


@pytest.mark.asyncio
async def test_xai_responses_inline_url_fallback_preserves_existing_sources_block():
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", ["web_search"])
    response = output_text_response('Answer.\n\nsources([{"url": "https://already.example.com"}])')

    result = await provider._parse_response(response)
    answer, sources = split_answer_and_sources(result)

    assert answer == "Answer."
    assert sources == [{"url": "https://already.example.com"}]


@pytest.mark.asyncio
async def test_xai_responses_execute_posts_to_responses(monkeypatch):
    provider = XAIResponsesSearchProvider("https://api.x.ai/v1", "test-key", "test-model", [])
    calls = []

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects, verify):
            self.timeout = timeout
            self.follow_redirects = follow_redirects
            self.verify = verify

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            calls.append((url, headers, json))
            return httpx.Response(
                200,
                json={"output": [{"content": [{"type": "output_text", "text": "ok", "annotations": []}]}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr("smart_search.providers.xai_responses.httpx.AsyncClient", FakeAsyncClient)

    result = await provider.search("query")

    assert result == "ok"
    assert calls[0][0] == "https://api.x.ai/v1/responses"
    assert calls[0][1]["X-Request-ID"]
    assert calls[0][2]["tools"] == []


@pytest.mark.asyncio
async def test_xai_responses_running_status_extends_soft_timeout(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    response = httpx.Response(200, json={"output": []}, request=httpx.Request("POST", "https://gateway.example.com/v1/responses"))

    class FakeClient:
        async def post(self, url, headers, json):
            await asyncio.sleep(0.03)
            return response

    status_calls = 0

    async def running_status(client, headers, request_id):
        nonlocal status_calls
        status_calls += 1
        return "running"

    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 0.2))
    monkeypatch.setattr(Config, "xai_status_poll", property(lambda self: 0.005))
    monkeypatch.setattr(provider, "_request_status", running_status)

    result = await provider._post_with_status_monitor(
        FakeClient(),
        provider._build_api_headers(),
        {},
        soft_timeout_seconds=0.005,
    )

    assert result is response
    assert status_calls >= 1


@pytest.mark.asyncio
async def test_xai_responses_queries_compatible_gateway_status_endpoint(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    captured = {}

    class FakeClient:
        async def get(self, url, headers, timeout):
            captured.update(url=url, headers=headers, timeout=timeout)
            return httpx.Response(
                200,
                json={"request_id": "request:1", "state": "running"},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr(Config, "xai_status_poll", property(lambda self: 3.0))

    state = await provider._request_status(
        FakeClient(),
        {"Authorization": "Bearer test-key", "X-Request-ID": "request:1"},
        "request:1",
    )

    assert state == "running"
    assert captured["url"] == "https://gateway.example.com/v1/request-status/request%3A1"
    assert captured["headers"]["X-Request-ID"] == "request:1"
    assert captured["timeout"] == 3.0


@pytest.mark.asyncio
async def test_xai_responses_unknown_status_waits_until_hard_timeout(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    cancelled = asyncio.Event()

    class FakeClient:
        async def post(self, url, headers, json):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    async def unknown_status(client, headers, request_id):
        return "unknown"

    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 0.03))
    monkeypatch.setattr(Config, "xai_status_poll", property(lambda self: 0.005))
    monkeypatch.setattr(provider, "_request_status", unknown_status)

    with pytest.raises(XAIRequestHardTimeout):
        await provider._post_with_status_monitor(
            FakeClient(),
            provider._build_api_headers(),
            {},
            soft_timeout_seconds=0.005,
        )

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_xai_responses_terminal_status_cancels_stuck_response_connection(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    cancelled = asyncio.Event()

    class FakeClient:
        async def post(self, url, headers, json):
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()

    async def failed_status(client, headers, request_id):
        return "failed"

    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 0.2))
    monkeypatch.setattr(Config, "xai_status_poll", property(lambda self: 0.005))
    monkeypatch.setattr(provider, "_request_status", failed_status)

    with pytest.raises(XAIRequestOutcomeUnknown, match="terminal state failed"):
        await provider._post_with_status_monitor(
            FakeClient(),
            provider._build_api_headers(),
            {},
            soft_timeout_seconds=0.005,
        )

    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_xai_responses_terminal_status_is_not_replayed_by_outer_retry(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    post_calls = 0

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects, verify):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            nonlocal post_calls
            post_calls += 1
            await asyncio.Event().wait()

    async def failed_status(client, headers, request_id):
        return "failed"

    monkeypatch.setattr("smart_search.providers.xai_responses.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 0.2))
    monkeypatch.setattr(Config, "xai_status_poll", property(lambda self: 0.005))
    monkeypatch.setattr(Config, "retry_max_attempts", property(lambda self: 3))
    monkeypatch.setattr(Config, "retry_multiplier", property(lambda self: 0.0))
    monkeypatch.setattr(provider, "_request_status", failed_status)

    with pytest.raises(XAIRequestOutcomeUnknown, match="terminal state failed"):
        await provider._execute_response_with_retry(
            provider._build_api_headers(),
            {},
            soft_timeout_seconds=0.005,
        )

    assert post_calls == 1


@pytest.mark.asyncio
async def test_xai_responses_retries_clear_pre_submission_connect_failure(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    post_calls = 0

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects, verify):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            nonlocal post_calls
            post_calls += 1
            if post_calls == 1:
                raise httpx.ConnectError("connect failed", request=httpx.Request("POST", url))
            return httpx.Response(
                200,
                json={"output": [{"content": [{"type": "output_text", "text": "ok", "annotations": []}]}]},
                request=httpx.Request("POST", url),
            )

    monkeypatch.setattr("smart_search.providers.xai_responses.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 0.2))
    monkeypatch.setattr(Config, "retry_max_attempts", property(lambda self: 3))
    monkeypatch.setattr(Config, "retry_multiplier", property(lambda self: 0.0))

    result = await provider._execute_response_with_retry(provider._build_api_headers(), {})

    assert result == "ok"
    assert post_calls == 2


@pytest.mark.asyncio
async def test_xai_responses_hard_deadline_includes_retry_waits(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    post_calls = 0

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects, verify):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            nonlocal post_calls
            post_calls += 1
            raise httpx.ConnectError("connect failed", request=httpx.Request("POST", url))

    monkeypatch.setattr("smart_search.providers.xai_responses.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 0.03))
    monkeypatch.setattr(Config, "retry_max_attempts", property(lambda self: 10))
    monkeypatch.setattr(Config, "retry_multiplier", property(lambda self: 1.0))
    monkeypatch.setattr(Config, "retry_max_wait", property(lambda self: 10))

    started_at = time.monotonic()
    with pytest.raises(XAIRequestHardTimeout, match="hard timeout"):
        await provider._execute_response_with_retry(provider._build_api_headers(), {})

    assert time.monotonic() - started_at < 0.5
    assert post_calls >= 1


@pytest.mark.asyncio
async def test_xai_responses_outer_cancellation_stops_inflight_post(monkeypatch):
    provider = XAIResponsesSearchProvider("https://gateway.example.com/v1", "test-key")
    post_started = asyncio.Event()
    post_cancelled = asyncio.Event()

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects, verify):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            post_started.set()
            try:
                await asyncio.Event().wait()
            finally:
                post_cancelled.set()

    monkeypatch.setattr("smart_search.providers.xai_responses.httpx.AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(Config, "xai_hard_timeout", property(lambda self: 1.0))

    search_task = asyncio.create_task(
        provider._execute_response_with_retry(provider._build_api_headers(), {})
    )
    await post_started.wait()
    search_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await search_task
    assert post_cancelled.is_set()
