"""Read-only preflight for source identity, prompts, capabilities, and gateways."""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
from pathlib import Path
from typing import Any

try:
    from .fault_gateway import HEALTH_PATH
    from .runtime import assert_source_runtime, config_values
    from .schema import dump_public_json, load_json
except ImportError:
    from fault_gateway import HEALTH_PATH
    from runtime import assert_source_runtime, config_values
    from schema import dump_public_json, load_json


CONFIG_KEYS = (
    "OPENAI_COMPATIBLE_API_URL",
    "OPENAI_COMPATIBLE_API_KEY",
    "XAI_API_KEY",
    "EXA_API_KEY",
    "SCIVERSE_API_TOKEN",
    "ZHIPU_MCP_API_KEY",
    "FIRECRAWL_API_KEY",
    "JINA_API_KEY",
    "TAVILY_API_KEY",
)

FAULT_LEAK_PATTERNS = {
    "A1": (
        r"concurrency_limit_exceeded",
        r"HTTP\s+429",
        r"logical_attempts\s*=\s*3",
        r"exactly two",
    ),
    "A2": (r"request_cancelled", r"HTTP\s+499", r"safe_to_replay\s*=\s*false"),
    "A3": (r"\bContext7\b", r"HTTP\s+503", r"exactly three"),
    "A4": (r"\bExa\b", r"HTTP\s+402", r"payment_required"),
    "A5": (r"TAVILY_ENABLED", r"\bJina\b", r"\bCloudflare\b", r"quality_error"),
}


def _gateway_healthy(endpoint: str) -> bool:
    port = int(endpoint.rsplit(":", 1)[1])
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", HEALTH_PATH)
        response = connection.getresponse()
        response.read()
        return response.status == 200
    except OSError:
        return False
    finally:
        connection.close()


def _prompt_check(case_id: str, prompt_path: Path) -> tuple[bool, list[str]]:
    text = prompt_path.read_text(encoding="utf-8")
    violations = [
        pattern
        for pattern in FAULT_LEAK_PATTERNS[case_id]
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]
    unresolved = [
        token
        for token in (
            "{{COMMON}}",
            "{{LAUNCHER}}",
            "{{OUTPUT_DIR}}",
            "{{LANGUAGE_SYSTEM_SKILL}}",
            "{{SMART_SEARCH_SKILL}}",
        )
        if token in text
    ]
    violations.extend(unresolved)
    return not violations, violations


def inspect(runtime_root: Path) -> dict[str, Any]:
    run_manifest = load_json(runtime_root / "private" / "run-manifest.json")
    runtime = assert_source_runtime()
    values = config_values(CONFIG_KEYS)
    main_configured = bool(
        values["XAI_API_KEY"]
        or (values["OPENAI_COMPATIBLE_API_URL"] and values["OPENAI_COMPATIBLE_API_KEY"])
    )
    fetch_fallback = bool(values["ZHIPU_MCP_API_KEY"] or values["FIRECRAWL_API_KEY"])
    academic_fallback = bool(values["SCIVERSE_API_TOKEN"] or main_configured)
    cases: dict[str, Any] = {}
    for case_id, case in run_manifest["cases"].items():
        prompt_ok, prompt_violations = _prompt_check(case_id, Path(case["prompt"]))
        process_alive = True
        try:
            os.kill(int(case["gateway_pid"]), 0)
        except OSError:
            process_alive = False
        capability_ok = {
            "A1": bool(
                values["OPENAI_COMPATIBLE_API_URL"]
                and values["OPENAI_COMPATIBLE_API_KEY"]
            ),
            "A2": bool(
                values["OPENAI_COMPATIBLE_API_URL"]
                and values["OPENAI_COMPATIBLE_API_KEY"]
            ),
            "A3": bool(values["EXA_API_KEY"]),
            "A4": academic_fallback,
            "A5": bool(main_configured and fetch_fallback),
        }[case_id]
        case_ok = (
            prompt_ok
            and process_alive
            and _gateway_healthy(case["gateway_endpoint"])
            and capability_ok
        )
        cases[case_id] = {
            "ok": case_ok,
            "prompt_ok": prompt_ok,
            "prompt_violations": prompt_violations,
            "gateway_process_alive": process_alive,
            "gateway_health_ok": _gateway_healthy(case["gateway_endpoint"]),
            "required_unaffected_capability_present": capability_ok,
        }
    overall = runtime == run_manifest["runtime"] and all(
        case["ok"] for case in cases.values()
    )
    return {
        "schema": "transient-search-preflight.v1",
        "ok": overall,
        "doctor_calls": 0,
        "source_runtime_matches_run": runtime == run_manifest["runtime"],
        "source_commit": runtime["source_commit"],
        "configured_capabilities": {
            "main_search": main_configured,
            "docs_fallback_for_A3": bool(values["EXA_API_KEY"]),
            "academic_fallback_for_A4": academic_fallback,
            "non_tavily_fetch_fallback_for_A5": fetch_fallback,
        },
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = inspect(arguments.runtime_root)
    destination = arguments.output or arguments.runtime_root / "preflight.json"
    dump_public_json(destination, result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
