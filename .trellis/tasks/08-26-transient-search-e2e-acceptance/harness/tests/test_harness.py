from __future__ import annotations

import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import ClassVar
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))

import case_launcher
import finalize_run
from cleanup_run import cleanup
from fault_gateway import HEALTH_PATH, GatewayState, make_handler
from preflight import _prompt_check
from prepare_run import prepare
from runtime import PYTHON, SOURCE_PYTHONPATH, assert_source_runtime
from schema import (
    GATEWAY_SCHEMA,
    INVOCATION_SCHEMA,
    append_jsonl,
    decode_jsonl,
    redact,
    write_private_json,
)
from verify_run import _case_rules, _verified_source_is_projected


class SyntheticUpstream(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, object]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        type(self).requests.append(
            {
                "path": self.path,
                "headers": {key.lower(): value for key, value in self.headers.items()},
                "body": self.rfile.read(length),
            }
        )
        body = b'{"choices":[{"message":{"content":"synthetic success"}}]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        return


def _start_server(
    handler: type[BaseHTTPRequestHandler],
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _post(url: str, *, body: bytes = b"request-secret-body") -> tuple[int, bytes]:
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": "Bearer request-secret-token",
            "X-Trace": "preserved",
        },
    )
    try:
        with urlopen(request, timeout=3) as response:
            return response.status, response.read()
    except HTTPError as error:
        return error.code, error.read()


def test_gateway_injects_twice_then_forwards_without_logging_request_data(
    tmp_path: Path,
) -> None:
    SyntheticUpstream.requests = []
    upstream, upstream_thread = _start_server(SyntheticUpstream)
    active = tmp_path / "active"
    active.write_text("inv-0001", encoding="utf-8")
    manifest = {
        "case_id": "A1",
        "provider": "openai-compatible",
        "active_invocation_path": str(active),
        "policy": {
            "allowed_methods": ["POST"],
            "allowed_path_prefixes": ["/v1/"],
            "strip_prefix": "/v1",
            "upstream_base": f"http://127.0.0.1:{upstream.server_port}/v1",
            "inject": {
                "methods": ["POST"],
                "path": "/v1/chat/completions",
                "count": 2,
                "status": 429,
                "error_class": "rate_limited",
                "body": {"error": {"code": "concurrency_limit_exceeded"}},
            },
        },
    }
    events = tmp_path / "events.jsonl"
    gateway, gateway_thread = _start_server(
        make_handler(GatewayState(manifest, events))
    )
    try:
        with urlopen(
            f"http://127.0.0.1:{gateway.server_port}{HEALTH_PATH}", timeout=3
        ) as response:
            assert response.status == 200
        statuses = [
            _post(
                f"http://127.0.0.1:{gateway.server_port}/v1/chat/completions?hidden=query"
            )[0]
            for _ in range(3)
        ]
        assert statuses == [429, 429, 200]
        observed = decode_jsonl(events, schema=GATEWAY_SCHEMA)
        assert [item["outcome"] for item in observed] == [
            "injected",
            "injected",
            "forwarded",
        ]
        assert [item["matched_ordinal"] for item in observed] == [1, 2, 3]
        assert all(item["invocation_id"] == "inv-0001" for item in observed)
        assert len(SyntheticUpstream.requests) == 1
        forwarded = SyntheticUpstream.requests[0]
        assert forwarded["path"] == "/v1/chat/completions?hidden=query"
        assert forwarded["headers"]["authorization"] == "Bearer request-secret-token"
        assert forwarded["headers"]["x-trace"] == "preserved"
        assert forwarded["body"] == b"request-secret-body"
        event_text = events.read_text(encoding="utf-8")
        for forbidden in (
            "request-secret-body",
            "request-secret-token",
            "hidden=query",
            "chat/completions",
        ):
            assert forbidden not in event_text
    finally:
        gateway.shutdown()
        upstream.shutdown()
        gateway_thread.join(timeout=2)
        upstream_thread.join(timeout=2)


@pytest.mark.parametrize(
    ("case_id", "provider", "status", "count_requested"),
    [
        ("A2", "openai-compatible", 499, 1),
        ("A3", "context7", 503, 3),
        ("A4", "exa", 402, 1),
        ("A5", "jina", 200, 2),
    ],
)
def test_fault_gateway_records_exact_synthetic_policy(
    tmp_path: Path,
    case_id: str,
    provider: str,
    status: int,
    count_requested: int,
) -> None:
    active = tmp_path / "active"
    active.write_text("inv-test", encoding="utf-8")
    manifest = {
        "case_id": case_id,
        "provider": provider,
        "active_invocation_path": str(active),
        "policy": {
            "allowed_methods": ["POST"],
            "allowed_path_prefixes": ["/fault"],
            "inject": {
                "methods": ["POST"],
                "path_prefix": "/fault",
                "count": 1_000,
                "status": status,
                "error_class": "quality_error" if status == 200 else "provider_error",
                "body": "Title: Just a moment..."
                if status == 200
                else {"error": {"type": "synthetic"}},
            },
        },
    }
    events = tmp_path / "events.jsonl"
    gateway, thread = _start_server(make_handler(GatewayState(manifest, events)))
    try:
        statuses = [
            _post(f"http://127.0.0.1:{gateway.server_port}/fault")[0]
            for _ in range(count_requested)
        ]
        assert statuses == [status] * count_requested
        observed = decode_jsonl(events, schema=GATEWAY_SCHEMA)
        assert len(observed) == count_requested
        assert all(item["outcome"] == "injected" for item in observed)
    finally:
        gateway.shutdown()
        thread.join(timeout=2)


def test_redaction_masks_exact_values_and_preserves_public_sources() -> None:
    value = {
        "authorization": "Bearer hidden",
        "message": "secret-value private-endpoint https://www.apple.com/mac-mini/",
    }
    public = redact(
        value, secrets=["secret-value"], private_values=["private-endpoint"]
    )
    assert public["authorization"] == "[REDACTED_SECRET]"
    assert "secret-value" not in public["message"]
    assert "private-endpoint" not in public["message"]
    assert "https://www.apple.com/mac-mini/" in public["message"]


def test_redaction_masks_local_paths_but_preserves_public_urls() -> None:
    public = redact(
        {
            "message": "/Users/example/.config/smart-search/config.json https://www.apple.com/mac-mini/"
        }
    )
    assert "/Users/example" not in public["message"]
    assert "[REDACTED_LOCAL_PATH]" in public["message"]
    assert "https://www.apple.com/mac-mini/" in public["message"]


def test_source_runtime_is_explicit_and_has_resilient_help() -> None:
    identity = assert_source_runtime()
    assert identity["python"] == str(PYTHON)
    assert identity["pythonpath"] == str(SOURCE_PYTHONPATH)
    assert identity["source_commit"]


def test_prepare_creates_opaque_owner_only_case_and_clean_health_log(
    tmp_path: Path,
) -> None:
    manifest = prepare(["A3"], "syntheticprepare", tmp_path)
    runtime_root = Path(manifest["runtime_root"])
    try:
        case = manifest["cases"]["A3"]
        case_dir = Path(case["case_dir"])
        assert case_dir.name.startswith("work-") and "A3" not in case_dir.name
        assert case_dir.stat().st_mode & 0o777 == 0o700
        assert Path(case["launcher"]).stat().st_mode & 0o777 == 0o700
        assert Path(case["output_dir"]).stat().st_mode & 0o777 == 0o700
        assert (
            decode_jsonl(case_dir / "gateway-events.jsonl", schema=GATEWAY_SCHEMA) == []
        )
        prompt_ok, violations = _prompt_check("A3", Path(case["prompt"]))
        assert prompt_ok, violations
    finally:
        cleanup(runtime_root)


def _launcher_case(tmp_path: Path, case_id: str = "A1") -> Path:
    for directory in (
        tmp_path / "private",
        tmp_path / "output",
        tmp_path / "output" / "commands",
    ):
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    (tmp_path / "invocations.jsonl").touch(mode=0o600)
    manifest = {
        "case_id": case_id,
        "runtime": {
            "source_commit": "abc123",
            "python": "/source/python",
            "pythonpath": "/source/src",
        },
        "environment": {},
        "force_search_provider": "openai-compatible" if case_id in {"A1", "A2"} else "",
        "gateway_endpoint": "http://127.0.0.1:43210",
    }
    write_private_json(tmp_path / "private" / "case-manifest.json", manifest)
    return tmp_path


def test_launcher_does_not_append_timeout_or_max_try(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    case_dir = _launcher_case(tmp_path)
    captured: dict[str, object] = {}

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        return subprocess.CompletedProcess(
            command, 0, stdout='{"ok":true}', stderr="secret-value"
        )

    monkeypatch.setattr(case_launcher.subprocess, "run", fake_run)
    monkeypatch.setattr(
        case_launcher, "private_redaction_values", lambda: (["secret-value"], [])
    )
    monkeypatch.setattr(
        case_launcher,
        "source_environment",
        lambda overrides=None: {**(overrides or {})},
    )
    output = case_dir / "output" / "commands" / "search.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "smart-search",
            "search",
            "topic",
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )
    assert case_launcher.main(case_dir=case_dir) == 0
    command = captured["command"]
    assert "--providers" in command and "openai-compatible" in command
    assert "--timeout" not in command and "--max-try" not in command
    invocations = decode_jsonl(case_dir / "invocations.jsonl", schema=INVOCATION_SCHEMA)
    assert invocations[0]["search_contract"]["explicit_timeout_120"] is False
    assert invocations[0]["search_contract"]["explicit_max_try_5"] is False
    stderr = (case_dir / invocations[0]["stderr_relative"]).read_text(encoding="utf-8")
    assert "secret-value" not in stderr


def test_launcher_rejects_output_outside_case(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    case_dir = _launcher_case(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["smart-search", "search", "topic", "--output", "/tmp/not-owned.json"],
    )
    with pytest.raises(SystemExit, match="assigned output directory"):
        case_launcher.main(case_dir=case_dir)


def test_verdict_rules_do_not_pass_an_observed_fault_without_recovery() -> None:
    events = [
        {"outcome": "injected", "http_status": 429, "invocation_id": "inv-1"},
        {"outcome": "injected", "http_status": 429, "invocation_id": "inv-1"},
    ]
    invocation = {
        "command": "search",
        "invocation_id": "inv-1",
        "search_contract": {
            "explicit_timeout_120": True,
            "explicit_max_try_5": True,
            "explicit_json_format": True,
            "explicit_output": True,
        },
    }
    valid_fault, _checks, violations = _case_rules(
        "A1", events, [invocation], {"inv-1": {"ok": False, "logical_attempts": 2}}
    )
    assert valid_fault is True
    assert violations


def test_a5_accepts_explicit_anysearch_extract_only_after_observed_jina_quality_error() -> (
    None
):
    events = [
        {
            "provider": "jina",
            "outcome": "injected",
            "http_status": 200,
            "invocation_id": "fetch-1",
        }
    ]
    invocations = [
        {"command": "fetch", "invocation_id": "fetch-1"},
        {"command": "anysearch-extract", "invocation_id": "extract-1"},
    ]
    results = {
        "fetch-1": {
            "ok": False,
            "provider_attempts": [
                {"provider": "jina", "status": "error", "error_type": "quality_error"},
                {"provider": "firecrawl", "status": "empty", "error_type": ""},
            ],
        },
        "extract-1": {"ok": True, "provider": "anysearch", "tool": "extract"},
    }
    valid_fault, _checks, violations = _case_rules("A5", events, invocations, results)
    assert valid_fault is True
    assert violations == []


def test_a4_rejects_a_composite_route_that_reaches_exa_again() -> None:
    events = [
        {
            "provider": "exa",
            "outcome": "injected",
            "http_status": 402,
            "invocation_id": "exa-1",
        },
        {
            "provider": "exa",
            "outcome": "injected",
            "http_status": 402,
            "invocation_id": "research-1",
        },
    ]
    invocations = [
        {"command": "exa-search", "invocation_id": "exa-1"},
        {"command": "research", "invocation_id": "research-1"},
    ]
    results = {"exa-1": {"error_type": "provider_error"}, "research-1": {"ok": True}}
    valid_fault, _checks, violations = _case_rules("A4", events, invocations, results)
    assert valid_fault is True
    assert "A4 reached Exa more than once after the non-retryable 402" in violations


def test_a4_ignores_local_parser_and_help_invocations_before_provider_request() -> None:
    events = [
        {
            "provider": "exa",
            "outcome": "injected",
            "http_status": 402,
            "invocation_id": "exa-provider",
        }
    ]
    invocations = [
        {"command": "exa-search", "invocation_id": "exa-parser"},
        {"command": "exa-search", "invocation_id": "exa-help"},
        {"command": "exa-search", "invocation_id": "exa-provider"},
    ]
    results = {
        "exa-parser": {},
        "exa-help": {},
        "exa-provider": {"error_type": "provider_error"},
    }
    valid_fault, _checks, violations = _case_rules("A4", events, invocations, results)
    assert valid_fault is True
    assert violations == []


def test_durable_copy_redacts_assigned_case_path(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    assigned_case_path = "/tmp/suite/work-0123456789ab"
    (source / "report.md").write_text(
        f"Evidence directory: {assigned_case_path}/output/evidence\n", encoding="utf-8"
    )
    destination = tmp_path / "destination"
    finalize_run._copy_tree(source, destination, private_values=[assigned_case_path])
    copied = (destination / "report.md").read_text(encoding="utf-8")
    assert assigned_case_path not in copied
    assert "[REDACTED_PRIVATE_VALUE]" in copied


def test_append_only_decoder_rejects_mixed_schema(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    append_jsonl(path, {"schema": GATEWAY_SCHEMA, "case_id": "A1"})
    append_jsonl(path, {"schema": "wrong", "case_id": "A1"})
    with pytest.raises(ValueError, match="unsupported schema"):
        decode_jsonl(path, schema=GATEWAY_SCHEMA)


def test_arxiv_batch_evidence_accepts_reader_facing_canonical_projection() -> None:
    source = {
        "url": "https://export.arxiv.org/api/query?id_list=2606.03005,2509.26006",
        "locator": "arXiv Atom entries: canonical id, published, title",
    }
    report = "[MUSE](https://arxiv.org/abs/2606.03005) [AgenticIQA](https://arxiv.org/abs/2509.26006)"
    assert _verified_source_is_projected(source, report) is True

    partial_report = "[MUSE](https://arxiv.org/abs/2606.03005)"
    assert _verified_source_is_projected(source, partial_report) is False


def test_selected_suite_accepts_split_runs_and_enforces_global_doctor_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    case_dirs = {
        case_id: tmp_path / f"opaque-{case_id.lower()}"
        for case_id in ("A1", "A2", "A3", "A4", "A5")
    }

    def fake_inspect(path: Path, *, sibling_names: list[str]) -> dict[str, object]:
        case_id = path.name[-2:].upper()
        assert path.name not in sibling_names
        return {
            "case_id": case_id,
            "verdict": "PASS",
            "source_commit": "fixed" if case_id != "A3" else "baseline",
            "observed": {"doctor_calls": 1 if case_id == "A2" else 0},
        }

    monkeypatch.setattr(finalize_run, "inspect", fake_inspect)
    suite = finalize_run.inspect_selected(case_dirs)
    assert suite["verdict"] == "PASS"
    assert suite["doctor_calls"] == 1
    assert suite["source_commits"] == ["baseline", "fixed"]
