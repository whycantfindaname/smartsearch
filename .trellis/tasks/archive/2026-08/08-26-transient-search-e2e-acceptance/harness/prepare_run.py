"""Create isolated case runtimes and start one loopback gateway per case."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import secrets
import signal
import subprocess
import time
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    from .fault_gateway import HEALTH_PATH
    from .runtime import (
        ACTIVE_LANGUAGE_SYSTEM,
        ACTIVE_SMART_SEARCH_SKILL,
        PYTHON,
        assert_source_runtime,
        config_values,
    )
    from .schema import write_private_json
except ImportError:
    from fault_gateway import HEALTH_PATH
    from runtime import (
        ACTIVE_LANGUAGE_SYSTEM,
        ACTIVE_SMART_SEARCH_SKILL,
        PYTHON,
        assert_source_runtime,
        config_values,
    )
    from schema import write_private_json


HERE = Path(__file__).resolve().parent
TASK_ROOT = HERE.parent

CASES: dict[str, dict[str, Any]] = {
    "A1": {
        "provider": "openai-compatible",
        "policy": {
            "allowed_methods": ["GET", "POST"],
            "allowed_path_prefixes": ["/v1/"],
            "strip_prefix": "/v1",
            "upstream_config_key": "OPENAI_COMPATIBLE_API_URL",
            "inject": {
                "methods": ["POST"],
                "path": "/v1/chat/completions",
                "count": 2,
                "status": 429,
                "error_class": "rate_limited",
                "retry_after": 0,
                "body": {
                    "error": {
                        "code": "concurrency_limit_exceeded",
                        "type": "concurrency_limit_exceeded",
                        "message": "concurrency_limit_exceeded",
                    }
                },
            },
        },
        "environment": {
            "XAI_API_KEY": "",
            "OPENAI_COMPATIBLE_STREAM": "false",
            "OPENAI_COMPATIBLE_FALLBACK_MODELS": "",
            "SMART_SEARCH_RETRY_MAX_ATTEMPTS": "0",
            "SMART_SEARCH_RETRY_MULTIPLIER": "0.01",
            "SMART_SEARCH_RETRY_MAX_WAIT": "1",
        },
        "force_search_provider": "openai-compatible",
    },
    "A2": {
        "provider": "openai-compatible",
        "policy": {
            "allowed_methods": ["GET", "POST"],
            "allowed_path_prefixes": ["/v1/"],
            "strip_prefix": "/v1",
            "upstream_config_key": "OPENAI_COMPATIBLE_API_URL",
            "inject": {
                "methods": ["POST"],
                "path": "/v1/chat/completions",
                "count": 1,
                "status": 499,
                "error_class": "request_cancelled",
                "body": {
                    "error": {
                        "code": "request_cancelled",
                        "type": "request_cancelled",
                        "message": "request_cancelled",
                    }
                },
            },
        },
        "environment": {
            "XAI_API_KEY": "",
            "OPENAI_COMPATIBLE_STREAM": "false",
            "OPENAI_COMPATIBLE_FALLBACK_MODELS": "",
            "SMART_SEARCH_RETRY_MAX_ATTEMPTS": "0",
            "SMART_SEARCH_RETRY_MULTIPLIER": "0.01",
            "SMART_SEARCH_RETRY_MAX_WAIT": "1",
        },
        "force_search_provider": "openai-compatible",
    },
    "A3": {
        "provider": "context7",
        "policy": {
            "allowed_methods": ["GET"],
            "allowed_path_prefixes": ["/api/v2/"],
            "inject": {
                "methods": ["GET"],
                "path_prefix": "/api/v2/",
                "count": 1_000_000,
                "status": 503,
                "error_class": "network_error",
                "body": {"error": {"type": "service_unavailable"}},
            },
        },
        "environment": {
            "CONTEXT7_API_KEY": "local-acceptance-placeholder",
            "SMART_SEARCH_RETRY_MAX_ATTEMPTS": "2",
            "SMART_SEARCH_RETRY_MULTIPLIER": "0.01",
            "SMART_SEARCH_RETRY_MAX_WAIT": "1",
        },
    },
    "A4": {
        "provider": "exa",
        "policy": {
            "allowed_methods": ["POST"],
            "allowed_paths": ["/search", "/findSimilar"],
            "inject": {
                "methods": ["POST"],
                "path_prefix": "/",
                "count": 1_000_000,
                "status": 402,
                "error_class": "provider_error",
                "body": {
                    "error": {"type": "payment_required", "message": "payment_required"}
                },
            },
        },
        "environment": {
            "EXA_API_KEY": "local-acceptance-placeholder",
            "SMART_SEARCH_RETRY_MAX_ATTEMPTS": "0",
            "SMART_SEARCH_RETRY_MULTIPLIER": "0.01",
            "SMART_SEARCH_RETRY_MAX_WAIT": "1",
        },
    },
    "A5": {
        "provider": "jina",
        "policy": {
            "allowed_methods": ["GET"],
            "allowed_path_prefixes": ["/http://", "/https://"],
            "inject": {
                "methods": ["GET"],
                "path_prefix": "/http",
                "count": 1_000_000,
                "status": 200,
                "error_class": "quality_error",
                "content_type": "text/plain; charset=utf-8",
                "body": "Title: Just a moment...\nChecking if the site connection is secure.\nacceptance-challenge-sentinel",
            },
        },
        "environment": {
            "JINA_API_KEY": "local-acceptance-placeholder",
            "JINA_RESPOND_WITH": "",
            "TAVILY_ENABLED": "false",
            "SMART_SEARCH_RETRY_MAX_ATTEMPTS": "0",
        },
    },
}


def _owner_directory(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(path, 0o700)


def _touch_private(path: Path) -> None:
    path.touch(mode=0o600, exist_ok=False)
    os.chmod(path, 0o600)


def _wait_ready(
    process: subprocess.Popen[bytes], ready_path: Path, timeout: float = 8.0
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"gateway exited before readiness: {process.returncode}")
        if ready_path.exists():
            ready = json.loads(ready_path.read_text(encoding="utf-8"))
            connection = http.client.HTTPConnection(
                "127.0.0.1", int(ready["port"]), timeout=2
            )
            try:
                connection.request("GET", HEALTH_PATH)
                response = connection.getresponse()
                response.read()
                if response.status == 200:
                    return ready
            finally:
                connection.close()
        time.sleep(0.05)
    raise RuntimeError("gateway readiness timeout")


def _launcher_source(case_dir: Path) -> str:
    return (
        f"#!{PYTHON}\n"
        "import sys\n"
        f"sys.path.insert(0, {str(HERE)!r})\n"
        "from case_launcher import main\n"
        f"raise SystemExit(main(case_dir={str(case_dir)!r}))\n"
    )


def _render_prompt(
    case_id: str, launcher: Path, output_dir: Path, destination: Path
) -> None:
    common = (TASK_ROOT / "prompts" / "common.md").read_text(encoding="utf-8")
    specific = (TASK_ROOT / "prompts" / f"case-{case_id.lower()}.md").read_text(
        encoding="utf-8"
    )
    rendered = specific.replace("{{COMMON}}", common)
    rendered = rendered.replace("{{LAUNCHER}}", str(launcher))
    rendered = rendered.replace("{{OUTPUT_DIR}}", str(output_dir))
    rendered = rendered.replace(
        "{{LANGUAGE_SYSTEM_SKILL}}", str(ACTIVE_LANGUAGE_SYSTEM)
    )
    rendered = rendered.replace(
        "{{SMART_SEARCH_SKILL}}", str(ACTIVE_SMART_SEARCH_SKILL)
    )
    destination.write_text(rendered, encoding="utf-8")
    os.chmod(destination, 0o600)


def _stop_processes(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass


def prepare(
    cases: list[str], run_id: str, runtime_parent: Path | None
) -> dict[str, Any]:
    runtime = assert_source_runtime()
    values = config_values(["OPENAI_COMPATIBLE_API_URL"])
    parent = runtime_parent or Path("/tmp")
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    root = parent / f"smart-search-e2e-acceptance-{run_id}"
    _owner_directory(root)
    private_root = root / "private"
    _owner_directory(private_root)
    processes: list[subprocess.Popen[bytes]] = []
    run_manifest: dict[str, Any] = {
        "schema": "transient-search-run-manifest.v1",
        "run_id": run_id,
        "runtime_root": str(root),
        "runtime": runtime,
        "cases": {},
    }
    try:
        for case_id in cases:
            if case_id not in CASES:
                raise ValueError(f"unknown case: {case_id}")
            case_spec = deepcopy(CASES[case_id])
            opaque_name = f"work-{secrets.token_hex(6)}"
            case_dir = root / opaque_name
            _owner_directory(case_dir)
            for directory in (
                case_dir / "private",
                case_dir / "bin",
                case_dir / "output",
                case_dir / "output" / "commands",
            ):
                _owner_directory(directory)
            events_path = case_dir / "gateway-events.jsonl"
            invocations_path = case_dir / "invocations.jsonl"
            _touch_private(events_path)
            _touch_private(invocations_path)
            active_invocation = case_dir / "private" / "active-invocation"
            ready_path = case_dir / "private" / "gateway-ready.json"
            gateway_log = case_dir / "private" / "gateway-process.log"
            manifest_path = case_dir / "private" / "case-manifest.json"
            policy = case_spec["policy"]
            upstream_key = policy.pop("upstream_config_key", "")
            if upstream_key:
                policy["upstream_base"] = values.get(upstream_key, "")
            manifest = {
                "schema": "transient-search-case-manifest.v1",
                "run_id": run_id,
                "case_id": case_id,
                "provider": case_spec["provider"],
                "case_dir": str(case_dir),
                "active_invocation_path": str(active_invocation),
                "runtime": runtime,
                "policy": policy,
                "environment": case_spec["environment"],
                "force_search_provider": case_spec.get("force_search_provider", ""),
            }
            write_private_json(manifest_path, manifest)
            with gateway_log.open("ab") as log_stream:
                process = subprocess.Popen(
                    [
                        str(PYTHON),
                        str(HERE / "fault_gateway.py"),
                        "--manifest",
                        str(manifest_path),
                        "--events",
                        str(events_path),
                        "--ready",
                        str(ready_path),
                    ],
                    stdout=log_stream,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                )
            processes.append(process)
            ready = _wait_ready(process, ready_path)
            endpoint = f"http://127.0.0.1:{ready['port']}"
            manifest["gateway_endpoint"] = endpoint
            if case_id in {"A1", "A2"}:
                manifest["environment"]["OPENAI_COMPATIBLE_API_URL"] = endpoint + "/v1"
            elif case_id == "A3":
                manifest["environment"]["CONTEXT7_BASE_URL"] = endpoint
            elif case_id == "A4":
                manifest["environment"]["EXA_BASE_URL"] = endpoint
            elif case_id == "A5":
                manifest["environment"]["JINA_READER_API_URL"] = endpoint
            write_private_json(manifest_path, manifest)
            launcher = case_dir / "bin" / "smart-search"
            launcher.write_text(_launcher_source(case_dir), encoding="utf-8")
            os.chmod(launcher, 0o700)
            prompt_path = case_dir / "worker-prompt.md"
            _render_prompt(case_id, launcher, case_dir / "output", prompt_path)
            run_manifest["cases"][case_id] = {
                "opaque_name": opaque_name,
                "case_dir": str(case_dir),
                "launcher": str(launcher),
                "output_dir": str(case_dir / "output"),
                "prompt": str(prompt_path),
                "gateway_pid": process.pid,
                "gateway_endpoint": endpoint,
            }
        write_private_json(private_root / "run-manifest.json", run_manifest)
        return run_manifest
    except Exception:
        _stop_processes(processes)
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=",".join(CASES))
    parser.add_argument("--run-id", default=uuid.uuid4().hex[:12])
    parser.add_argument("--runtime-parent", type=Path)
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Print only the runtime root, not private case metadata.",
    )
    arguments = parser.parse_args()
    selected = [
        item.strip().upper() for item in arguments.cases.split(",") if item.strip()
    ]
    manifest = prepare(selected, arguments.run_id, arguments.runtime_parent)
    print(
        manifest["runtime_root"]
        if arguments.quiet
        else json.dumps(manifest, ensure_ascii=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
