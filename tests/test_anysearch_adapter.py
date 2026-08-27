from __future__ import annotations

import importlib.util
import json
import threading
from collections import Counter
from collections.abc import Callable
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = (
    ROOT
    / "skills"
    / "smart-search-cli"
    / "bundled-skills"
    / "anysearch"
    / "scripts"
    / "smart_search_anysearch.py"
)
SPEC = importlib.util.spec_from_file_location("smart_search_anysearch_adapter", ADAPTER_PATH)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


PRIMARY = "primary-symbol"
FALLBACK = "fallback-symbol"
EXPLICIT = "explicit-symbol"
ENVIRONMENT = "environment-symbol"
IDENTITIES = {PRIMARY: "primary", FALLBACK: "fallback", EXPLICIT: "explicit", ENVIRONMENT: "environment"}


def _success_body() -> bytes:
    return json.dumps(
        {
            "code": 0,
            "data": {
                "results": [
                    {
                        "title": "Synthetic result",
                        "url": "https://example.test/source",
                        "content": "Synthetic content",
                    }
                ],
                "metadata": {"total_results": 1, "search_time_ms": 1},
            },
        }
    ).encode("utf-8")


@contextmanager
def _stub_server(
    plan: Callable[[str, int], tuple[int, bytes]],
):
    class Handler(BaseHTTPRequestHandler):
        def _handle(self) -> None:
            header = self.headers.get("Authorization", "")
            token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
            identity = IDENTITIES.get(token, "unknown")
            call = {
                "identity": identity,
                "has_bearer": header.startswith("Bearer ") and bool(token),
                "path": self.path,
            }
            self.server.calls.append(call)  # type: ignore[attr-defined]
            status, body = plan(identity, len(self.server.calls))  # type: ignore[attr-defined]
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            self._handle()

        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            self._handle()

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.calls = []  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def _write_config(root: Path, *, primary: Any = PRIMARY, fallback: Any = FALLBACK) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "config.json"
    path.write_text(
        json.dumps({"ANYSEARCH_API_KEY": primary, "ANYSEARCH_API_KEY_FALLBACK": fallback}),
        encoding="utf-8",
    )
    return path


def _configure(monkeypatch: pytest.MonkeyPatch, server: ThreadingHTTPServer, config_dir: Path) -> None:
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("ANYSEARCH_API_BASE_URL", f"http://127.0.0.1:{server.server_port}")


def test_config_resolution_matches_override_default_and_windows_legacy(tmp_path):
    home = tmp_path / "home"
    local_appdata = tmp_path / "local-appdata"
    override = tmp_path / "override"
    legacy = home / ".config" / "smart-search" / "config.json"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("{}", encoding="utf-8")

    assert adapter.resolve_config_file(
        platform="linux", home=home, environ={"SMART_SEARCH_CONFIG_DIR": str(override)}
    ) == override / "config.json"
    assert adapter.resolve_config_file(
        platform="linux", home=home, environ={}
    ) == legacy
    assert adapter.resolve_config_file(
        platform="win32", home=home, environ={"LOCALAPPDATA": str(local_appdata)}
    ) == legacy

    preferred = local_appdata / "smart-search" / "config.json"
    preferred.parent.mkdir(parents=True)
    preferred.write_text("{}", encoding="utf-8")
    assert adapter.resolve_config_file(
        platform="win32", home=home, environ={"LOCALAPPDATA": str(local_appdata)}
    ) == preferred


@pytest.mark.parametrize(
    "primary, fallback",
    [
        (None, FALLBACK),
        (PRIMARY, None),
        (123, FALLBACK),
        (PRIMARY, []),
        (" ", FALLBACK),
        (PRIMARY, PRIMARY),
    ],
)
def test_credentials_require_distinct_non_empty_strings(tmp_path, primary, fallback):
    config_file = _write_config(tmp_path / "config", primary=primary, fallback=fallback)
    with pytest.raises(adapter.AdapterError):
        adapter.load_credentials(config_file)


def test_primary_success_sends_one_non_empty_bearer_and_ignores_environment(monkeypatch, tmp_path, capsys):
    def plan(identity: str, _call_no: int) -> tuple[int, bytes]:
        assert identity == "primary"
        return 200, _success_body().replace(b"Synthetic content", PRIMARY.encode())

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        monkeypatch.setenv("ANYSEARCH_API_KEY", ENVIRONMENT)
        code = adapter.main(["search", "synthetic query"])

    assert code == 0
    assert [call["identity"] for call in server.calls] == ["primary"]
    assert all(call["has_bearer"] for call in server.calls)
    output = capsys.readouterr().out
    assert ENVIRONMENT not in output
    assert PRIMARY not in output


@pytest.mark.parametrize("status", [401, 403, 429])
def test_auth_permission_or_rate_limit_uses_fallback_once(monkeypatch, tmp_path, status):
    def plan(identity: str, _call_no: int) -> tuple[int, bytes]:
        if identity == "primary":
            return status, json.dumps({"code": status, "message": "try another key"}).encode()
        assert identity == "fallback"
        return 200, _success_body()

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        assert adapter.main(["search", "synthetic query"]) == 0

    assert [call["identity"] for call in server.calls] == ["primary", "fallback"]
    assert all(call["has_bearer"] for call in server.calls)


def test_batch_fallback_is_bounded_per_item(monkeypatch, tmp_path):
    primary_calls = 0

    def plan(identity: str, _call_no: int) -> tuple[int, bytes]:
        nonlocal primary_calls
        if identity == "primary":
            primary_calls += 1
            if primary_calls == 1:
                return 401, json.dumps({"code": 401, "message": "try fallback"}).encode()
            return 200, _success_body()
        assert identity == "fallback"
        return 200, _success_body()

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        assert adapter.main(["batch_search", "--query", "first", "--query", "second"]) == 0

    assert Counter(call["identity"] for call in server.calls) == Counter({"primary": 2, "fallback": 1})
    assert all(call["has_bearer"] for call in server.calls)


def test_batch_local_error_does_not_inherit_another_item_response_status(monkeypatch, tmp_path):
    remote_completed = threading.Event()
    _write_config(tmp_path / "config")

    def plan(identity: str, _call_no: int) -> tuple[int, bytes]:
        if identity == "primary":
            return 401, json.dumps({"code": 401, "message": "try fallback"}).encode()
        assert identity == "fallback"
        return 200, _success_body()

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        upstream = adapter._load_upstream_cli()
        original_request = upstream.requests.request
        original_rest = upstream._call_rest

        def rest(
            method: str,
            path: str,
            api_key: str,
            *,
            payload: Any = None,
            params: Any = None,
        ) -> Any:
            query = (payload or {}).get("query")
            try:
                return original_rest(method, path, api_key, payload=payload, params=params)
            finally:
                if query == "remote":
                    remote_completed.set()

        def request(method: str, url: str, **kwargs: Any) -> Any:
            query = (kwargs.get("json") or {}).get("query")
            if query == "local-error":
                assert remote_completed.wait(timeout=5)
                raise upstream.ApiError("local failure", status=401)
            response = original_request(method, url, **kwargs)
            remote_completed.set()
            return response

        monkeypatch.setattr(upstream.requests, "request", request)
        monkeypatch.setattr(upstream, "_call_rest", rest)
        monkeypatch.setattr(adapter, "_load_upstream_cli", lambda: upstream)
        assert adapter.main(
            [
                "batch_search",
                "--queries",
                json.dumps([{"query": "remote"}, {"query": "local-error"}]),
            ]
        ) == 0

    assert Counter(call["identity"] for call in server.calls) == Counter({"primary": 1, "fallback": 1})
    assert all(call["has_bearer"] for call in server.calls)


@pytest.mark.parametrize("status", [408, 500])
def test_timeout_like_http_status_does_not_use_fallback(monkeypatch, tmp_path, status):
    def plan(_identity: str, _call_no: int) -> tuple[int, bytes]:
        return status, json.dumps({"code": status, "message": "temporary"}).encode()

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        assert adapter.main(["search", "synthetic query"]) == 1

    assert [call["identity"] for call in server.calls] == ["primary"]


@pytest.mark.parametrize("exception_name", ["Timeout", "ConnectionError"])
def test_transport_failures_do_not_use_fallback(monkeypatch, tmp_path, exception_name):
    _write_config(tmp_path / "config")
    upstream = adapter._load_upstream_cli()

    def fail_request(*_args: Any, **_kwargs: Any) -> Any:
        raise getattr(upstream.requests.exceptions, exception_name)()

    monkeypatch.setattr(upstream.requests, "request", fail_request)
    monkeypatch.setattr(adapter, "_load_upstream_cli", lambda: upstream)
    monkeypatch.setenv("SMART_SEARCH_CONFIG_DIR", str(tmp_path / "config"))
    assert adapter.main(["search", "synthetic query"]) == 1


@pytest.mark.parametrize(
    "body, status",
    [
        (b"not-json", 401),
        (json.dumps(["not", "an", "object"]).encode(), 429),
        (json.dumps({"code": None, "message": "bad schema"}).encode(), 401),
    ],
)
def test_malformed_or_schema_response_does_not_use_fallback(monkeypatch, tmp_path, body, status):
    def plan(_identity: str, _call_no: int) -> tuple[int, bytes]:
        return status, body

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        assert adapter.main(["search", "synthetic query"]) == 1

    assert [call["identity"] for call in server.calls] == ["primary"]


def test_explicit_api_key_is_single_key_override(monkeypatch, tmp_path):
    def plan(identity: str, _call_no: int) -> tuple[int, bytes]:
        assert identity == "explicit"
        return 401, json.dumps({"code": 401, "message": "denied"}).encode()

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config", primary=None, fallback=None)
        assert adapter.main(["search", "synthetic query", "--api_key", EXPLICIT]) == 1

    assert [call["identity"] for call in server.calls] == ["explicit"]


@pytest.mark.parametrize(
    "argv",
    [
        ["--api_key", EXPLICIT, "--api_key", EXPLICIT],
        ["--api_key=", "search", "q"],
    ],
)
def test_explicit_api_key_is_rejected_when_empty_or_repeated(monkeypatch, tmp_path, argv):
    with _stub_server(lambda _identity, _call_no: (200, _success_body())) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        assert adapter.main(argv) == 1
    assert server.calls == []


def test_missing_primary_fails_before_network_and_does_not_use_environment(monkeypatch, tmp_path, capsys):
    def plan(_identity: str, _call_no: int) -> tuple[int, bytes]:
        raise AssertionError("network must not be called")

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config", primary=None, fallback=FALLBACK)
        monkeypatch.setenv("ANYSEARCH_API_KEY", ENVIRONMENT)
        assert adapter.main(["search", "synthetic query"]) == 1
        error = capsys.readouterr().err

    assert server.calls == []
    assert ENVIRONMENT not in error
    assert FALLBACK not in error


def test_missing_fallback_fails_before_network(monkeypatch, tmp_path):
    def plan(_identity: str, _call_no: int) -> tuple[int, bytes]:
        raise AssertionError("network must not be called")

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config", fallback=None)
        assert adapter.main(["search", "synthetic query"]) == 1

    assert server.calls == []


def test_local_argument_error_fails_before_network(monkeypatch, tmp_path):
    def plan(_identity: str, _call_no: int) -> tuple[int, bytes]:
        raise AssertionError("network must not be called")

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        assert adapter.main(["search"]) != 0

    assert server.calls == []


def test_doc_is_offline_and_points_to_the_adapter(monkeypatch, capsys):
    monkeypatch.delenv("SMART_SEARCH_CONFIG_DIR", raising=False)
    assert adapter.main(["doc"]) == 0
    output = capsys.readouterr().out
    assert "scripts/smart_search_anysearch.py" in output
    assert "scripts/anysearch_cli.py" not in output
    assert "Authorization: Bearer [redacted]" in output
    assert "anonymous access is disabled" in output


def test_import_capture_stream_accepts_warning_writes():
    stream = adapter._Utf8ImportStream()

    assert stream.encoding == "utf-8"
    assert stream.write("import warning\n") == len("import warning\n")
    stream.flush()
    assert stream.getvalue() == "import warning\n"


def test_error_data_drops_auto_registered_and_sensitive_fields(monkeypatch, tmp_path, capsys):
    body = json.dumps(
        {
            "code": 401,
            "message": f"invalid {PRIMARY}",
            "data": {
                "auto_registered": {"api_key": "provider-generated-symbol"},
                "safe": "diagnostic",
            },
        }
    ).encode()

    def plan(_identity: str, _call_no: int) -> tuple[int, bytes]:
        return 401, body

    with _stub_server(plan) as server:
        _configure(monkeypatch, server, tmp_path / "config")
        _write_config(tmp_path / "config")
        assert adapter.main(["search", "synthetic query"]) == 1
        error = capsys.readouterr().err

    assert [call["identity"] for call in server.calls] == ["primary", "fallback"]
    assert "auto_registered" not in error
    assert "provider-generated-symbol" not in error
    assert PRIMARY not in error
    assert FALLBACK not in error
    assert "safe" in error


def test_public_and_packaged_adapters_are_byte_identical():
    packaged = (
        ROOT
        / "src"
        / "smart_search"
        / "assets"
        / "skills"
        / "smart-search-cli"
        / "bundled-skills"
        / "anysearch"
        / "scripts"
        / "smart_search_anysearch.py"
    )
    assert ADAPTER_PATH.read_bytes() == packaged.read_bytes()


def test_public_and_packaged_bundled_trees_are_byte_identical():
    public_root = ROOT / "skills" / "smart-search-cli" / "bundled-skills" / "anysearch"
    packaged_root = (
        ROOT
        / "src"
        / "smart_search"
        / "assets"
        / "skills"
        / "smart-search-cli"
        / "bundled-skills"
        / "anysearch"
    )
    public_files = {
        path.relative_to(public_root).as_posix()
        for path in public_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    packaged_files = {
        path.relative_to(packaged_root).as_posix()
        for path in packaged_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    assert public_files == packaged_files
    assert all((public_root / rel).read_bytes() == (packaged_root / rel).read_bytes() for rel in public_files)
