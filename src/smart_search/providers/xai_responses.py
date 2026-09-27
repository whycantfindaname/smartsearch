from ..i18n import source_message
import asyncio
import json
import logging
import re
import uuid
from contextlib import suppress
import time
from typing import Any
from urllib.parse import quote, urlsplit

import httpx
from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt

from .base import BaseSearchProvider
from .openai_compatible import _StopAtDeadline, _WaitWithRetryAfter, _is_retryable_exception, get_local_time_info
from ..config import config
from ..logger import log_info
from ..utils import search_prompt


_logger = logging.getLogger(__name__)
_ssl_warning_emitted = False
_INLINE_URL_PATTERN = re.compile(r"(?<![A-Za-z0-9+.\-])https?://[^\s<>'\"\x60]+", re.IGNORECASE)
_SERIALIZED_SOURCES_PATTERN = re.compile(r"(?ims)(?:^|\n)\s*sources\s*\(\s*\[.*\]\s*\)\s*\Z")
_INLINE_URL_TRAILING_PUNCTUATION = ".,;:!?，。；：！？、…．"
_INLINE_URL_BRACKET_PAIRS = (
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("（", "）"),
    ("【", "】"),
    ("《", "》"),
    ("〈", "〉"),
    ("「", "」"),
    ("『", "』"),
)


class XAIRequestHardTimeout(TimeoutError):
    pass


class XAIRequestOutcomeUnknown(httpx.RemoteProtocolError):
    pass


def _is_pre_submission_connection_failure(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout))


class XAIResponsesSearchProvider(BaseSearchProvider):
    def __init__(self, api_url: str, api_key: str, model: str = "grok-4-fast", tools: list[str] | None = None):
        super().__init__(api_url.rstrip("/"), api_key)
        self.model = model
        self.tools = tools or []
        self._search_deadline_monotonic: float | None = None

    def set_search_deadline(self, deadline_monotonic: float | None) -> None:
        """Set by the service for one main-search candidate; standalone calls stay unchanged."""
        self._search_deadline_monotonic = deadline_monotonic

    def _request_timeout(self) -> httpx.Timeout:
        if self._search_deadline_monotonic is None:
            return httpx.Timeout(connect=6.0, read=config.search_timeout_or_default(), write=10.0, pool=None)
        remaining = self._search_deadline_monotonic - time.monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError(source_message('main_search deadline exhausted'))
        bounded = max(0.001, remaining)
        return httpx.Timeout(
            connect=min(6.0, bounded),
            read=bounded,
            write=min(10.0, bounded),
            pool=bounded,
        )

    def _retry_stop(self):
        stop = stop_after_attempt(config.retry_max_attempts + 1)
        if self._search_deadline_monotonic is not None:
            return stop | _StopAtDeadline(self._search_deadline_monotonic)
        return stop

    def get_provider_name(self) -> str:
        return "xAI Responses"

    def _build_api_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "smart-search/0.1.0",
        }

    def _get_ssl_verify(self) -> bool:
        global _ssl_warning_emitted
        verify = config.ssl_verify_enabled
        if not verify and not _ssl_warning_emitted:
            _ssl_warning_emitted = True
            _logger.warning("SSL_VERIFY=false: xAI Responses API 请求已禁用 SSL 证书验证，存在安全风险")
        return verify

    def _build_search_payload(self, query: str, platform: str = "") -> dict[str, Any]:
        platform_prompt = ""
        if platform:
            platform_prompt = "\n\nYou should search the web for the information you need, and focus on these platform: " + platform + "\n"
        time_context = get_local_time_info() + "\n"
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": search_prompt,
            "input": [{"role": "user", "content": time_context + query + platform_prompt}],
            "stream": False,
            "tools": [{"type": tool} for tool in self.tools],
        }
        return payload

    async def search(self, query: str, platform: str = "", ctx=None, soft_timeout_seconds: float | None = None) -> str:
        payload = self._build_search_payload(query, platform)
        await log_info(ctx, f"platform_prompt: {query}", config.debug_enabled)
        return await self._execute_response_with_retry(
            self._build_api_headers(),
            payload,
            ctx,
            soft_timeout_seconds=soft_timeout_seconds,
        )

    async def _execute_response_with_retry(
        self,
        headers: dict,
        payload: dict,
        ctx=None,
        *,
        soft_timeout_seconds: float | None = None,
    ) -> str:
        hard_timeout = config.xai_hard_timeout
        loop = asyncio.get_running_loop()
        now = loop.time()
        if self._search_deadline_monotonic is not None:
            remaining = self._search_deadline_monotonic - now
            if remaining <= 0:
                raise asyncio.TimeoutError(source_message('main_search deadline exhausted'))
            hard_timeout = min(hard_timeout, remaining)
        hard_deadline = now + hard_timeout
        execution_task = asyncio.create_task(
            self._execute_response_attempts(
                headers,
                payload,
                ctx,
                soft_timeout_seconds=soft_timeout_seconds,
                hard_deadline=hard_deadline,
            )
        )
        try:
            done, _ = await asyncio.wait({execution_task}, timeout=hard_timeout)
        except BaseException:
            await self._cancel_request_task(execution_task)
            raise
        if done:
            return execution_task.result()
        await self._cancel_request_task(execution_task)
        raise XAIRequestHardTimeout(
            f"xAI Responses logical request exceeded hard timeout of {hard_timeout:g} seconds"
        )

    async def _execute_response_attempts(
        self,
        headers: dict,
        payload: dict,
        ctx=None,
        *,
        soft_timeout_seconds: float | None,
        hard_deadline: float,
    ) -> str:
        timeout = httpx.Timeout(connect=6.0, read=None, write=10.0, pool=None)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, verify=self._get_ssl_verify()) as client:
            async for attempt in AsyncRetrying(
                stop=self._retry_stop(),
                wait=_WaitWithRetryAfter(
                    config.retry_multiplier,
                    config.retry_max_wait,
                    deadline_monotonic=hard_deadline,
                ),
                retry=retry_if_exception(
                    lambda exc: not isinstance(exc, (XAIRequestOutcomeUnknown, XAIRequestHardTimeout))
                    and (_is_pre_submission_connection_failure(exc) or _is_retryable_exception(exc))
                ),
                reraise=True,
            ):
                with attempt:
                    response = await self._post_with_status_monitor(
                        client,
                        headers,
                        payload,
                        soft_timeout_seconds=soft_timeout_seconds,
                        hard_deadline=hard_deadline,
                    )
                    response.raise_for_status()
                    return await self._parse_response(response, ctx)
        return ""

    async def _post_with_status_monitor(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        payload: dict,
        *,
        soft_timeout_seconds: float | None,
        hard_deadline: float | None = None,
    ) -> httpx.Response:
        request_id = uuid.uuid4().hex
        request_headers = {**headers, "X-Request-ID": request_id}
        request_task = asyncio.create_task(
            client.post(f"{self.api_url}/responses", headers=request_headers, json=payload)
        )
        loop = asyncio.get_running_loop()
        started_at = loop.time()
        soft_timeout = soft_timeout_seconds or config.xai_soft_timeout
        hard_timeout = config.xai_hard_timeout
        if hard_deadline is None:
            hard_deadline = started_at + hard_timeout
        wait_seconds = min(soft_timeout, hard_timeout)
        try:
            while True:
                remaining = hard_deadline - loop.time()
                if remaining <= 0:
                    await self._cancel_request_task(request_task)
                    raise XAIRequestHardTimeout(
                        f"xAI Responses request {request_id} exceeded hard timeout of {hard_timeout:g} seconds"
                    )
                done, _ = await asyncio.wait({request_task}, timeout=min(wait_seconds, remaining))
                if done:
                    return self._completed_response(request_task, request_id)

                state = await self._request_status(client, request_headers, request_id)
                if state in {"completed", "failed"}:
                    done, _ = await asyncio.wait(
                        {request_task},
                        timeout=min(2.0, config.xai_status_poll, remaining),
                    )
                    if done:
                        return self._completed_response(request_task, request_id)
                    await self._cancel_request_task(request_task)
                    raise XAIRequestOutcomeUnknown(
                        f"request {request_id} reached terminal state {state} before the response connection completed"
                    )
                wait_seconds = config.xai_status_poll
        except BaseException:
            await self._cancel_request_task(request_task)
            raise

    @staticmethod
    def _completed_response(request_task: asyncio.Task, request_id: str) -> httpx.Response:
        try:
            return request_task.result()
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise
        except httpx.RequestError as exc:
            raise XAIRequestOutcomeUnknown(
                f"request {request_id} may have been submitted before the response connection failed: {exc}"
            ) from exc

    async def _request_status(
        self,
        client: httpx.AsyncClient,
        headers: dict,
        request_id: str,
    ) -> str:
        try:
            response = await client.get(
                f"{self.api_url}/request-status/{quote(request_id, safe='')}",
                headers=headers,
                timeout=min(10.0, config.xai_status_poll),
            )
            if response.status_code != 200:
                return "unknown"
            data = response.json()
            state = data.get("state") if isinstance(data, dict) else None
            return state if state in {"running", "completed", "failed"} else "unknown"
        except (httpx.HTTPError, ValueError, TypeError):
            return "unknown"

    @staticmethod
    async def _cancel_request_task(request_task: asyncio.Task) -> None:
        if request_task.done():
            return
        request_task.cancel()
        with suppress(asyncio.CancelledError):
            await request_task

    async def _parse_response(self, response: httpx.Response, ctx=None) -> str:
        data = response.json()
        text_parts: list[str] = []
        sources: list[dict[str, str]] = []
        seen: set[str] = set()

        for item in data.get("output", []) if isinstance(data, dict) else []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") != "output_text":
                    continue
                text = content.get("text")
                if isinstance(text, str) and text:
                    text_parts.append(text)
                for annotation in content.get("annotations", []) or []:
                    if not isinstance(annotation, dict) or annotation.get("type") != "url_citation":
                        continue
                    url = annotation.get("url")
                    if not isinstance(url, str) or not url.startswith(("http://", "https://")) or url in seen:
                        continue
                    seen.add(url)
                    source: dict[str, str] = {"url": url}
                    title = annotation.get("title")
                    if isinstance(title, str) and title.strip():
                        source["title"] = title.strip()
                    sources.append(source)

        answer = "\n\n".join(part.strip() for part in text_parts if part.strip()).strip()
        if not sources and answer and not _SERIALIZED_SOURCES_PATTERN.search(answer):
            sources = self._extract_inline_urls(answer)
        if sources:
            answer = f"{answer}\n\nsources({json.dumps(sources, ensure_ascii=False)})".strip()

        await log_info(ctx, f"content: {answer}", config.debug_enabled)
        return answer

    @staticmethod
    def _extract_inline_urls(text: str) -> list[dict[str, str]]:
        sources: list[dict[str, str]] = []
        seen: set[str] = set()

        for match in _INLINE_URL_PATTERN.finditer(text):
            url = XAIResponsesSearchProvider._trim_inline_url_terminal_punctuation(match.group())
            if not XAIResponsesSearchProvider._is_valid_inline_http_url(url):
                continue
            scheme, separator, remainder = url.partition(":")
            url = f"{scheme.lower()}{separator}{remainder}"
            if url in seen:
                continue
            seen.add(url)
            sources.append({"url": url})

        return sources

    @staticmethod
    def _trim_inline_url_terminal_punctuation(url: str) -> str:
        trimmed = url
        while trimmed:
            candidate = trimmed.rstrip(_INLINE_URL_TRAILING_PUNCTUATION)
            for opening, closing in _INLINE_URL_BRACKET_PAIRS:
                while candidate.endswith(closing) and candidate.count(closing) > candidate.count(opening):
                    candidate = candidate[:-1]
            if candidate == trimmed:
                return candidate
            trimmed = candidate
        return trimmed

    @staticmethod
    def _is_valid_inline_http_url(url: str) -> bool:
        try:
            parsed = urlsplit(url)
            hostname = parsed.hostname
            _ = parsed.port
        except ValueError:
            return False

        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.netloc)
            and bool(hostname)
            and not any(char.isspace() for char in url)
            and "\\" not in url
        )
