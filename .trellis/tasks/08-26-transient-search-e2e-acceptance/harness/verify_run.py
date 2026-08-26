"""Evidence-backed PASS/FAIL/HARNESS_INVALID verdict engine."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

try:
    from .runtime import private_redaction_values
    from .schema import (
        GATEWAY_SCHEMA,
        INVOCATION_SCHEMA,
        VERDICT_SCHEMA,
        count,
        decode_jsonl,
        dump_public_json,
        load_json,
    )
except ImportError:
    from runtime import private_redaction_values
    from schema import (
        GATEWAY_SCHEMA,
        INVOCATION_SCHEMA,
        VERDICT_SCHEMA,
        count,
        decode_jsonl,
        dump_public_json,
        load_json,
    )


REQUIRED_RESULT_FIELDS = {
    "status",
    "answer_complete",
    "observed_errors",
    "recovery_actions",
    "doctor_calls",
    "sources",
    "native_web_used",
    "security_incident",
}
LOG_SCHEMA_LEAK_RE = re.compile(
    r"(?i)(\"(?:authorization|proxy-authorization|cookie|set-cookie|request_body|response_body|headers)\"\s*:)"
)
OUTPUT_LEAK_RE = re.compile(
    r"(?i)(local-acceptance-placeholder|acceptance-challenge-sentinel|127\.0\.0\.1:\d+)"
)
LOCAL_PATH_LEAK_RE = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|home|tmp|private/var)/[^\s\"'<>]+"
)
PUBLIC_RUNTIME_IDENTITY = {
    "python": "<source-python>",
    "pythonpath": "<source-pythonpath>",
}


def _load_invocation_result(
    case_dir: Path, invocation: dict[str, Any]
) -> dict[str, Any]:
    relative = str(invocation.get("output_relative") or "")
    candidates: list[Path] = []
    if relative:
        candidates.append(case_dir / relative)
    stdout_relative = str(invocation.get("stdout_relative") or "")
    if stdout_relative:
        candidates.append(case_dir / stdout_relative)
    for path in candidates:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            continue
        if isinstance(value, dict):
            return value
    return {}


def _attempts(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item for item in result.get("provider_attempts") or [] if isinstance(item, dict)
    ]


def _contains_attempt(
    result: dict[str, Any],
    *,
    provider_fragment: str,
    error_type: str | None = None,
    status: str | None = None,
) -> bool:
    for attempt in _attempts(result):
        provider = str(attempt.get("provider") or attempt.get("tool") or "").lower()
        if provider_fragment.lower() not in provider:
            continue
        if error_type is not None and attempt.get("error_type") != error_type:
            continue
        if status is not None and attempt.get("status") != status:
            continue
        return True
    return False


def _verified_source_is_projected(source: dict[str, Any], report: str) -> bool:
    url = str(source.get("url") or "")
    if url in report:
        return True
    parsed = urlsplit(url)
    if parsed.netloc != "export.arxiv.org" or parsed.path != "/api/query":
        return False
    locator_ids = re.findall(r"\b\d{4}\.\d{5}\b", str(source.get("locator") or ""))
    query_ids = [
        item
        for value in parse_qs(parsed.query).get("id_list", [])
        for item in value.split(",")
    ]
    required_ids = locator_ids or query_ids
    return bool(required_ids) and all(
        identifier in report for identifier in required_ids
    )


def _source_checks(result: dict[str, Any], report: str, case_id: str) -> list[str]:
    violations: list[str] = []
    sources = result.get("sources")
    if not isinstance(sources, list):
        return ["run-result.sources must be a list"]
    verified = 0
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            violations.append(f"sources[{index}] is not an object")
            continue
        missing = [
            key
            for key in ("title", "url", "source_type", "evidence_status", "locator")
            if not source.get(key)
        ]
        if missing:
            violations.append(f"sources[{index}] missing {','.join(missing)}")
            continue
        if source.get("evidence_status") not in {"verified", "unverified", "missing"}:
            violations.append(f"sources[{index}] has invalid evidence_status")
        url = str(source.get("url") or "")
        if not url.startswith(("https://", "http://")):
            violations.append(f"sources[{index}] is not an HTTP(S) source")
        if source.get("evidence_status") == "verified":
            verified += 1
            if not _verified_source_is_projected(source, report):
                violations.append(f"verified source {index} is absent from report")
    minimum_verified = {"A1": 6, "A2": 1, "A3": 3, "A4": 1, "A5": 4}[case_id]
    if verified < minimum_verified:
        violations.append(
            f"verified source count {verified} is below {minimum_verified}"
        )
    if len(report.strip()) < 800:
        violations.append("research report is too short to answer the target")
    for required_heading in ("References", "Execution Summary"):
        if required_heading.lower() not in report.lower():
            violations.append(f"research report missing {required_heading}")
    if not any(status in report for status in ("verified", "unverified", "missing")):
        violations.append("research report does not expose evidence states")
    return violations


def _public_files(case_dir: Path) -> Iterable[Path]:
    for relative in ("gateway-events.jsonl", "invocations.jsonl"):
        path = case_dir / relative
        if path.exists():
            yield path
    for root_name in ("output", "cli-results"):
        root = case_dir / root_name
        if root.exists():
            yield from (path for path in root.rglob("*") if path.is_file())


def _leak_violations(case_dir: Path, *, sibling_names: Iterable[str] = ()) -> list[str]:
    secrets, private_values = private_redaction_values()
    manifest = load_json(case_dir / "private" / "case-manifest.json")
    private_values = [*private_values, str(manifest.get("gateway_endpoint") or "")]
    exact_values = [item for item in (*secrets, *private_values) if item]
    violations: list[str] = []
    for path in _public_files(case_dir):
        text = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(case_dir)
        if relative.as_posix() in {
            "gateway-events.jsonl",
            "invocations.jsonl",
        } and LOG_SCHEMA_LEAK_RE.search(text):
            violations.append(f"forbidden raw field in {relative}")
        if OUTPUT_LEAK_RE.search(text):
            violations.append(f"pattern leak in {path.relative_to(case_dir)}")
        if LOCAL_PATH_LEAK_RE.search(text):
            violations.append(f"local path leak in {path.relative_to(case_dir)}")
        if any(value in text for value in exact_values):
            violations.append(f"exact private value in {path.relative_to(case_dir)}")
        if any(name and name in text for name in sibling_names):
            violations.append(f"sibling case identity in {path.relative_to(case_dir)}")
    return sorted(set(violations))


def _case_rules(
    case_id: str,
    events: list[dict[str, Any]],
    invocations: list[dict[str, Any]],
    invocation_results: dict[str, dict[str, Any]],
) -> tuple[bool, list[str], list[str]]:
    checks: list[str] = []
    violations: list[str] = []
    search_invocations = [
        item for item in invocations if item.get("command") == "search"
    ]
    doctor_invocations = [
        item for item in invocations if item.get("command") == "doctor"
    ]
    if any(item.get("command") == "doctor" for item in invocations) and case_id != "A2":
        violations.append("doctor used outside A2")
    if case_id == "A1":
        valid_fault = count(events, outcome="injected", http_status=429) == 2
        if len(search_invocations) != 1:
            violations.append("A1 requires exactly one search invocation")
        if search_invocations:
            invocation = search_invocations[0]
            result = invocation_results.get(invocation["invocation_id"], {})
            contract = invocation.get("search_contract") or {}
            if not all(contract.values()):
                violations.append(
                    "A1 search did not explicitly satisfy timeout/max-try/json/output"
                )
            if result.get("ok") is not True:
                violations.append("A1 final search did not succeed")
            if (
                result.get("logical_attempts") != 3
                or result.get("logical_retry_max_attempts") != 5
            ):
                violations.append("A1 logical attempt accounting is not 3 within max 5")
            if not result.get("logical_retry_used"):
                violations.append("A1 did not report logical retry use")
            if (
                count(
                    events,
                    invocation_id=invocation["invocation_id"],
                    outcome="forwarded",
                )
                < 1
            ):
                violations.append(
                    "A1 did not reach the forwarding attempt after recovery"
                )
        if doctor_invocations:
            violations.append("A1 used doctor")
        checks.append("two exact injected 429 events tied to the single search")
    elif case_id == "A2":
        valid_fault = count(events, outcome="injected", http_status=499) == 1
        if not (1 <= len(search_invocations) <= 2):
            violations.append(
                "A2 requires one initial search and at most one fresh search"
            )
        if search_invocations:
            initial = search_invocations[0]
            result = invocation_results.get(initial["invocation_id"], {})
            contract = initial.get("search_contract") or {}
            if not all(contract.values()):
                violations.append(
                    "A2 initial search did not explicitly satisfy timeout/max-try/json/output"
                )
            if result.get("error_type") != "request_cancelled":
                violations.append("A2 initial result is not request_cancelled")
            if result.get("logical_attempts") != 1:
                violations.append(
                    "A2 initial result used more than one logical attempt"
                )
            recovery = result.get("recovery") or {}
            if (
                recovery.get("safe_to_replay") is not False
                or recovery.get("doctor_max_attempts") != 1
            ):
                violations.append(
                    "A2 recovery did not preserve safe_to_replay=false and one doctor probe"
                )
            if result.get("fallback_used") or result.get("model_fallback_used"):
                violations.append("A2 replayed through provider/model fallback")
            if count(events, invocation_id=initial["invocation_id"]) != 1:
                violations.append(
                    "A2 initial search did not remain a single HTTP request"
                )
        if len(doctor_invocations) > 1:
            violations.append("A2 exceeded its doctor budget")
        checks.append("one injected 499 with unsafe replay recovery")
    elif case_id == "A3":
        matching = [
            item
            for item in invocations
            if item.get("command") in {"context7-library", "context7-docs"}
        ]
        valid_fault = count(events, outcome="injected", http_status=503) >= 1
        if len(matching) != 1:
            violations.append("A3 requires exactly one Context7 command")
        if matching:
            invocation = matching[0]
            result = invocation_results.get(invocation["invocation_id"], {})
            if (
                count(
                    events,
                    invocation_id=invocation["invocation_id"],
                    outcome="injected",
                    http_status=503,
                )
                != 3
            ):
                violations.append(
                    "A3 transport budget did not produce exactly three requests"
                )
            if result.get("error_type") != "network_error":
                violations.append("A3 final Context7 error is not network_error")
        checks.append("persistent Context7 503 exercised inside one command")
    elif case_id == "A4":
        matching = [
            item
            for item in invocations
            if item.get("command") in {"exa-search", "exa-similar"}
        ]
        provider_requests = [
            item
            for item in matching
            if count(events, invocation_id=item["invocation_id"], provider="exa") >= 1
        ]
        valid_fault = count(events, outcome="injected", http_status=402) >= 1
        if count(events, provider="exa", outcome="injected", http_status=402) != 1:
            violations.append(
                "A4 reached Exa more than once after the non-retryable 402"
            )
        if len(provider_requests) != 1:
            violations.append("A4 requires exactly one Exa provider request")
        if provider_requests:
            invocation = provider_requests[0]
            result = invocation_results.get(invocation["invocation_id"], {})
            if (
                count(
                    events,
                    invocation_id=invocation["invocation_id"],
                    outcome="injected",
                    http_status=402,
                )
                != 1
            ):
                violations.append("A4 retried the non-retryable 402")
            if result.get("error_type") != "provider_error":
                violations.append("A4 final Exa error is not provider_error")
        checks.append("single non-retryable Exa 402 provider request")
    elif case_id == "A5":
        valid_fault = (
            count(events, provider="jina", outcome="injected", http_status=200) >= 1
        )
        fetch_results = [
            invocation_results.get(item["invocation_id"], {})
            for item in invocations
            if item.get("command") == "fetch"
        ]
        anysearch_extract_results = [
            invocation_results.get(item["invocation_id"], {})
            for item in invocations
            if item.get("command") == "anysearch-extract"
        ]
        if not fetch_results:
            violations.append("A5 did not execute fetch")
        if not any(
            _contains_attempt(
                item, provider_fragment="jina", error_type="quality_error"
            )
            for item in fetch_results
        ):
            violations.append("A5 fetch output did not record Jina quality_error")
        if any(
            _contains_attempt(item, provider_fragment="tavily")
            for item in fetch_results
        ):
            violations.append("A5 fetch attempted Tavily while disabled")
        standard_fetch_recovered = any(
            item.get("ok") is True
            and any(
                _contains_attempt(item, provider_fragment=provider, status="ok")
                for provider in ("zhipu", "firecrawl")
            )
            for item in fetch_results
        )
        explicit_extract_recovered = any(
            item.get("ok") is True for item in anysearch_extract_results
        )
        if not (standard_fetch_recovered or explicit_extract_recovered):
            violations.append(
                "A5 did not obtain a successful non-Tavily fetch recovery"
            )
        checks.append(
            "Jina challenge quality gate with Tavily disabled and a distinct fetch-provider recovery"
        )
    else:
        return False, checks, [f"unknown case: {case_id}"]
    return valid_fault, checks, violations


def inspect(case_dir: Path, *, sibling_names: Iterable[str] = ()) -> dict[str, Any]:
    manifest = load_json(case_dir / "private" / "case-manifest.json")
    case_id = manifest["case_id"]
    events = decode_jsonl(case_dir / "gateway-events.jsonl", schema=GATEWAY_SCHEMA)
    invocations = decode_jsonl(case_dir / "invocations.jsonl", schema=INVOCATION_SCHEMA)
    invocation_results = {
        item["invocation_id"]: _load_invocation_result(case_dir, item)
        for item in invocations
    }
    result_path = case_dir / "output" / "run-result.json"
    report_path = case_dir / "output" / "research-report.md"
    try:
        worker_result = load_json(result_path)
    except (FileNotFoundError, json.JSONDecodeError, ValueError, OSError):
        worker_result = {}
    report = (
        report_path.read_text(encoding="utf-8", errors="replace")
        if report_path.exists()
        else ""
    )

    valid_fault, checks, rule_violations = _case_rules(
        case_id, events, invocations, invocation_results
    )
    harness_violations: list[str] = []
    if any(
        item.get("case_id") != case_id or item.get("invocation_id") == "unattributed"
        for item in events
    ):
        harness_violations.append(
            "gateway events are not attributable to this case and invocation"
        )
    if any(
        item.get("source_commit") != manifest["runtime"]["source_commit"]
        or item.get("source_python") != PUBLIC_RUNTIME_IDENTITY["python"]
        or item.get("source_pythonpath") != PUBLIC_RUNTIME_IDENTITY["pythonpath"]
        for item in invocations
    ):
        harness_violations.append("source runtime identity mismatch")
    if count(events, outcome="rejected"):
        harness_violations.append("gateway rejected an unexpected path or method")

    violations = [
        *rule_violations,
        *_leak_violations(case_dir, sibling_names=sibling_names),
    ]
    missing_fields = sorted(REQUIRED_RESULT_FIELDS - set(worker_result))
    if missing_fields:
        violations.append("run-result missing: " + ",".join(missing_fields))
    if worker_result:
        if worker_result.get("status") not in {"completed", "ok", "success"}:
            violations.append("worker status is not completed")
        if worker_result.get("answer_complete") is not True:
            violations.append("worker marked answer incomplete")
        if worker_result.get("native_web_used"):
            violations.append("worker reported native web use")
        if worker_result.get("security_incident"):
            violations.append("worker reported a security incident")
        actual_doctors = sum(item.get("command") == "doctor" for item in invocations)
        if worker_result.get("doctor_calls") != actual_doctors:
            violations.append("worker doctor_calls disagrees with invocation log")
        violations.extend(_source_checks(worker_result, report, case_id))
    elif valid_fault:
        violations.append("worker result is missing or invalid")

    if not valid_fault or harness_violations:
        verdict = "HARNESS_INVALID"
    elif violations:
        verdict = "FAIL"
    else:
        verdict = "PASS"

    event_locators = [
        f"gateway-events.jsonl:{index}"
        for index, item in enumerate(events, start=1)
        if item.get("outcome") == "injected"
    ]
    invocation_locators = [
        f"invocations.jsonl:{index}" for index, _ in enumerate(invocations, start=1)
    ]
    return {
        "schema": VERDICT_SCHEMA,
        "case_id": case_id,
        "verdict": verdict,
        "source_commit": manifest["runtime"]["source_commit"],
        "observed": {
            "gateway_events": len(events),
            "injected": count(events, outcome="injected"),
            "forwarded": count(events, outcome="forwarded"),
            "suppressed": count(events, outcome="suppressed"),
            "invocations": len(invocations),
            "doctor_calls": sum(
                item.get("command") == "doctor" for item in invocations
            ),
            "verified_sources": sum(
                isinstance(item, dict) and item.get("evidence_status") == "verified"
                for item in worker_result.get("sources") or []
            ),
        },
        "checks": checks,
        "event_locators": event_locators,
        "invocation_locators": invocation_locators,
        "harness_violations": sorted(set(harness_violations)),
        "violations": sorted(set(violations)),
        "missing_result_fields": missing_fields,
    }


def inspect_suite(runtime_root: Path) -> dict[str, Any]:
    run_manifest = load_json(runtime_root / "private" / "run-manifest.json")
    opaque_names = {
        case_id: item["opaque_name"] for case_id, item in run_manifest["cases"].items()
    }
    cases: dict[str, Any] = {}
    for case_id, item in run_manifest["cases"].items():
        sibling_names = [
            name for sibling_id, name in opaque_names.items() if sibling_id != case_id
        ]
        cases[case_id] = inspect(Path(item["case_dir"]), sibling_names=sibling_names)
    doctor_total = sum(case["observed"]["doctor_calls"] for case in cases.values())
    suite_violations = (
        [] if doctor_total <= 1 else ["suite-wide doctor budget exceeded"]
    )
    return {
        "schema": "transient-search-suite-verdict.v1",
        "run_id": run_manifest["run_id"],
        "verdict": "PASS"
        if not suite_violations
        and all(case["verdict"] == "PASS" for case in cases.values())
        else "FAIL",
        "doctor_calls": doctor_total,
        "suite_violations": suite_violations,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--suite", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    value = (
        inspect_suite(arguments.path) if arguments.suite else inspect(arguments.path)
    )
    destination = arguments.output or arguments.path / (
        "suite-verdict.json" if arguments.suite else "verdict.json"
    )
    dump_public_json(destination, value)
    print(json.dumps(value, ensure_ascii=False))
    return 0 if value["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
