"""Loopback-only deterministic fault gateway for one acceptance case."""

from __future__ import annotations

import argparse
import json
import threading
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

try:
    from .schema import (
        GATEWAY_SCHEMA,
        append_jsonl,
        load_json,
        monotonic_ns,
        public_path_category,
    )
except ImportError:
    from schema import (
        GATEWAY_SCHEMA,
        append_jsonl,
        load_json,
        monotonic_ns,
        public_path_category,
    )


HEALTH_PATH = "/__acceptance_health__"
HOP_BY_HOP = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}
RETURN_HEADERS = {"content-type", "retry-after"}


def _status_error_class(status: int) -> str | None:
    if status in {200, 201, 202, 204}:
        return None
    if status in {400, 422}:
        return "parameter_error"
    if status in {401, 403}:
        return "auth_error"
    if status == 408:
        return "timeout"
    if status == 429:
        return "rate_limited"
    if status == 499:
        return "request_cancelled"
    if 500 <= status <= 599:
        return "network_error"
    return "provider_error"


class GatewayState:
    def __init__(self, manifest: dict[str, Any], events_path: Path):
        self.manifest = manifest
        self.events_path = events_path
        self.lock = threading.Lock()
        self.sequence = 0
        self.request_ordinal = 0
        self.matched_ordinal = 0

    def _active_invocation_id(self) -> str:
        active_path = Path(self.manifest["active_invocation_path"])
        try:
            return active_path.read_text(encoding="utf-8").strip()
        except OSError:
            return "unattributed"

    def _next_ordinals(self, matched: bool) -> tuple[int, int | None]:
        with self.lock:
            self.request_ordinal += 1
            match_ordinal: int | None = None
            if matched:
                self.matched_ordinal += 1
                match_ordinal = self.matched_ordinal
            return self.request_ordinal, match_ordinal

    def _matches(self, method: str, path: str) -> bool:
        inject = self.manifest["policy"]["inject"]
        methods = {item.upper() for item in inject.get("methods", ["GET", "POST"])}
        if method not in methods:
            return False
        exact = inject.get("path")
        prefix = inject.get("path_prefix")
        return bool((exact and path == exact) or (prefix and path.startswith(prefix)))

    def _allowed(self, method: str, path: str) -> bool:
        policy = self.manifest["policy"]
        methods = {
            item.upper() for item in policy.get("allowed_methods", ["GET", "POST"])
        }
        if method not in methods:
            return False
        exact = set(policy.get("allowed_paths", []))
        prefixes = tuple(policy.get("allowed_path_prefixes", []))
        return path in exact or any(path.startswith(prefix) for prefix in prefixes)

    def _injected_response(self) -> tuple[int, dict[str, str], bytes]:
        inject = self.manifest["policy"]["inject"]
        status = int(inject["status"])
        content_type = str(inject.get("content_type") or "application/json")
        body = inject.get(
            "body", {"error": {"type": inject.get("error_class", "provider_error")}}
        )
        payload = (
            body.encode("utf-8")
            if isinstance(body, str)
            else json.dumps(body, ensure_ascii=False).encode("utf-8")
        )
        headers = {"Content-Type": content_type}
        if inject.get("retry_after") is not None:
            headers["Retry-After"] = str(inject["retry_after"])
        return status, headers, payload

    def _forward_target(self, raw_path: str) -> str:
        policy = self.manifest["policy"]
        upstream = str(policy.get("upstream_base") or "").rstrip("/")
        if not upstream:
            raise ValueError("forwarding requested without upstream")
        parsed = urlsplit(raw_path)
        forwarded_path = parsed.path
        strip_prefix = str(policy.get("strip_prefix") or "")
        if strip_prefix and forwarded_path.startswith(strip_prefix):
            forwarded_path = forwarded_path[len(strip_prefix) :] or "/"
        return urlunsplit(
            ("", "", upstream + "/" + forwarded_path.lstrip("/"), parsed.query, "")
        )

    def _forward(
        self,
        method: str,
        raw_path: str,
        request_headers: Mapping[str, str],
        request_body: bytes,
    ) -> tuple[int, dict[str, str], bytes, str]:
        try:
            target = self._forward_target(raw_path)
            forwarded_headers = {
                key: value
                for key, value in request_headers.items()
                if key.lower() not in HOP_BY_HOP
            }
            request = Request(
                target,
                data=request_body if method not in {"GET", "HEAD"} else None,
                headers=forwarded_headers,
                method=method,
            )
            with urlopen(
                request,
                timeout=float(self.manifest["policy"].get("upstream_timeout", 120)),
            ) as response:
                headers = {
                    key: value
                    for key, value in response.headers.items()
                    if key.lower() in RETURN_HEADERS
                }
                return response.status, headers, response.read(), "forwarded"
        except HTTPError as error:
            headers = {
                key: value
                for key, value in error.headers.items()
                if key.lower() in RETURN_HEADERS
            }
            return error.code, headers, error.read(), "forwarded"
        except (URLError, TimeoutError, OSError, ValueError):
            return (
                502,
                {"Content-Type": "application/json"},
                b'{"error":{"type":"upstream_unavailable"}}',
                "suppressed",
            )

    def handle(
        self,
        method: str,
        raw_path: str,
        request_headers: Mapping[str, str],
        request_body: bytes,
    ) -> tuple[int, dict[str, str], bytes, str, int, int | None]:
        parsed_path = urlsplit(raw_path).path
        matched = self._matches(method, parsed_path)
        request_ordinal, matched_ordinal = self._next_ordinals(matched)
        if not self._allowed(method, parsed_path):
            return (
                404,
                {"Content-Type": "application/json"},
                b'{"error":{"type":"route_not_allowed"}}',
                "rejected",
                request_ordinal,
                matched_ordinal,
            )
        inject_count = int(self.manifest["policy"]["inject"].get("count", 0))
        if matched_ordinal is not None and matched_ordinal <= inject_count:
            status, headers, body = self._injected_response()
            return status, headers, body, "injected", request_ordinal, matched_ordinal
        status, headers, body, outcome = self._forward(
            method, raw_path, request_headers, request_body
        )
        return status, headers, body, outcome, request_ordinal, matched_ordinal

    def record(
        self,
        *,
        method: str,
        status: int,
        outcome: str,
        request_ordinal: int,
        matched_ordinal: int | None,
        started_ns: int,
    ) -> None:
        with self.lock:
            self.sequence += 1
            sequence = self.sequence
        append_jsonl(
            self.events_path,
            {
                "schema": GATEWAY_SCHEMA,
                "case_id": self.manifest["case_id"],
                "seq": sequence,
                "monotonic_ns": monotonic_ns(),
                "invocation_id": self._active_invocation_id(),
                "provider": self.manifest["provider"],
                "channel": public_path_category(self.manifest["provider"]),
                "method": method,
                "request_ordinal": request_ordinal,
                "matched_ordinal": matched_ordinal,
                "outcome": outcome,
                "http_status": status,
                "error_class": (
                    self.manifest["policy"]["inject"].get("error_class")
                    if outcome == "injected"
                    else _status_error_class(status)
                ),
                "duration_ms": round((monotonic_ns() - started_ns) / 1_000_000, 3),
            },
        )


def make_handler(state: GatewayState):
    class Handler(BaseHTTPRequestHandler):
        def _respond(self, method: str) -> None:
            if urlsplit(self.path).path == HEALTH_PATH:
                body = b"ok"
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                if method != "HEAD":
                    self.wfile.write(body)
                return
            length = int(self.headers.get("Content-Length", "0"))
            request_body = self.rfile.read(length) if length else b""
            started_ns = monotonic_ns()
            status, headers, body, outcome, request_ordinal, matched_ordinal = (
                state.handle(
                    method, self.path, dict(self.headers.items()), request_body
                )
            )
            state.record(
                method=method,
                status=status,
                outcome=outcome,
                request_ordinal=request_ordinal,
                matched_ordinal=matched_ordinal,
                started_ns=started_ns,
            )
            self.send_response(status)
            for key, value in headers.items():
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(body)

        def do_GET(self) -> None:
            self._respond("GET")

        def do_POST(self) -> None:
            self._respond("POST")

        def do_HEAD(self) -> None:
            self._respond("HEAD")

        def log_message(self, *_args: Any) -> None:
            return

    return Handler


def serve(
    manifest_path: Path, events_path: Path, ready_path: Path, port: int = 0
) -> None:
    manifest = load_json(manifest_path)
    server = ThreadingHTTPServer(
        ("127.0.0.1", port), make_handler(GatewayState(manifest, events_path))
    )
    ready_path.write_text(
        json.dumps({"host": "127.0.0.1", "port": server.server_port}), encoding="utf-8"
    )
    ready_path.chmod(0o600)
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--ready", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    arguments = parser.parse_args()
    serve(arguments.manifest, arguments.events, arguments.ready, arguments.port)
