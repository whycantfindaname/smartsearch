"""Verify, sanitize, copy durable evidence, and stop owned gateways."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

try:
    from .cleanup_run import cleanup
    from .runtime import private_redaction_values
    from .schema import dump_public_json, load_json, redact_text
    from .verify_run import inspect, inspect_suite
except ImportError:
    from cleanup_run import cleanup
    from runtime import private_redaction_values
    from schema import dump_public_json, load_json, redact_text
    from verify_run import inspect, inspect_suite


EXPECTED_CASES = {"A1", "A2", "A3", "A4", "A5"}


def _sanitize_text_tree(
    destination: Path, *, secrets: list[str], private_values: list[str]
) -> None:
    for path in destination.rglob("*"):
        if not path.is_file():
            continue
        try:
            value = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        path.write_text(
            redact_text(value, secrets=secrets, private_values=private_values),
            encoding="utf-8",
        )


def _copy_tree(
    source: Path,
    destination: Path,
    *,
    secrets: list[str] | None = None,
    private_values: list[str] | None = None,
) -> None:
    if source.exists():
        shutil.copytree(source, destination)
        _sanitize_text_tree(
            destination, secrets=secrets or [], private_values=private_values or []
        )


def _copy_public_file(
    source: Path,
    destination: Path,
    *,
    secrets: list[str],
    private_values: list[str],
) -> None:
    shutil.copy2(source, destination)
    try:
        value = destination.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    destination.write_text(
        redact_text(value, secrets=secrets, private_values=private_values),
        encoding="utf-8",
    )


def _case_redaction_values(case_source: Path) -> tuple[list[str], list[str]]:
    secrets, private_values = private_redaction_values()
    manifest = load_json(case_source / "private" / "case-manifest.json")
    return secrets, [
        *private_values,
        str(case_source),
        str(manifest.get("gateway_endpoint") or ""),
    ]


def finalize(runtime_root: Path, artifact_root: Path) -> Path:
    run_manifest = load_json(runtime_root / "private" / "run-manifest.json")
    suite = inspect_suite(runtime_root)
    if suite["verdict"] != "PASS":
        raise RuntimeError(
            "only a passing suite may be materialized as final durable evidence"
        )
    destination = artifact_root / run_manifest["run_id"]
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        preflight = runtime_root / "preflight.json"
        if preflight.exists():
            shutil.copy2(preflight, destination / "preflight.json")
        dump_public_json(destination / "suite-verdict.json", suite)
        lines = [
            "# Smart Search fault-injected acceptance",
            "",
            f"- Run: `{run_manifest['run_id']}`",
            f"- Source commit: `{run_manifest['runtime']['source_commit']}`",
            f"- Suite verdict: **{suite['verdict']}**",
            f"- Doctor probes: `{suite['doctor_calls']}` / `1`",
            "",
            "## Cases",
            "",
        ]
        for case_id, case in suite["cases"].items():
            case_source = Path(run_manifest["cases"][case_id]["case_dir"])
            case_destination = destination / case_id
            case_destination.mkdir(mode=0o700)
            secrets, private_values = _case_redaction_values(case_source)
            for name in ("gateway-events.jsonl", "invocations.jsonl"):
                _copy_public_file(
                    case_source / name,
                    case_destination / name,
                    secrets=secrets,
                    private_values=private_values,
                )
            _copy_tree(
                case_source / "cli-results",
                case_destination / "cli-results",
                secrets=secrets,
                private_values=private_values,
            )
            _copy_tree(
                case_source / "output",
                case_destination / "output",
                secrets=secrets,
                private_values=private_values,
            )
            dump_public_json(case_destination / "verdict.json", case)
            locators = ", ".join(case["event_locators"]) or "missing"
            lines.append(
                f"- {case_id}: **{case['verdict']}**; injected evidence `{locators}`; "
                f"verified sources `{case['observed']['verified_sources']}`."
            )
        (destination / "acceptance-summary.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        return destination
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        cleanup(runtime_root)


def parse_assignment(value: str) -> tuple[str, Path]:
    case_id, separator, path = value.partition("=")
    if not separator or not case_id or not path:
        raise argparse.ArgumentTypeError("expected CASE_ID=/absolute/case/path")
    if case_id not in EXPECTED_CASES:
        raise argparse.ArgumentTypeError(f"unknown case id: {case_id}")
    resolved = Path(path)
    if not resolved.is_absolute():
        raise argparse.ArgumentTypeError("case path must be absolute")
    return case_id, resolved


def inspect_selected(case_dirs: dict[str, Path]) -> dict[str, Any]:
    if set(case_dirs) != EXPECTED_CASES:
        missing = sorted(EXPECTED_CASES - set(case_dirs))
        extra = sorted(set(case_dirs) - EXPECTED_CASES)
        raise ValueError(
            f"selected suite must contain A1-A5; missing={missing}, extra={extra}"
        )
    opaque_names = {case_id: path.name for case_id, path in case_dirs.items()}
    cases = {
        case_id: inspect(
            path,
            sibling_names=[
                name
                for sibling_id, name in opaque_names.items()
                if sibling_id != case_id
            ],
        )
        for case_id, path in sorted(case_dirs.items())
    }
    doctor_calls = sum(case["observed"]["doctor_calls"] for case in cases.values())
    suite_violations = (
        [] if doctor_calls <= 1 else ["suite-wide doctor budget exceeded"]
    )
    return {
        "schema": "transient-search-selected-suite-verdict.v1",
        "verdict": (
            "PASS"
            if not suite_violations
            and all(case["verdict"] == "PASS" for case in cases.values())
            else "FAIL"
        ),
        "doctor_calls": doctor_calls,
        "source_commits": sorted({case["source_commit"] for case in cases.values()}),
        "suite_violations": suite_violations,
        "cases": cases,
    }


def _copy_failed_audit(
    source: Path, destination: Path, superseded_by: dict[str, Any]
) -> None:
    verdict = inspect(source)
    if verdict["verdict"] != "FAIL" or verdict["harness_violations"]:
        raise RuntimeError(
            "failed audit must be a valid FAIL, not PASS or HARNESS_INVALID"
        )
    destination.mkdir(mode=0o700, parents=True)
    secrets, private_values = _case_redaction_values(source)
    dump_public_json(destination / "verdict.json", verdict)
    for name in ("gateway-events.jsonl", "invocations.jsonl"):
        _copy_public_file(
            source / name,
            destination / name,
            secrets=secrets,
            private_values=private_values,
        )
    invocations = [
        json.loads(line)
        for line in (source / "invocations.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    initial_search = next(
        item for item in invocations if item.get("command") == "search"
    )
    output_relative = str(initial_search.get("output_relative") or "")
    if not output_relative:
        raise RuntimeError("failed audit search output is missing")
    _copy_public_file(
        source / output_relative,
        destination / "initial-search-result.json",
        secrets=secrets,
        private_values=private_values,
    )
    dump_public_json(
        destination / "supersession.json",
        {
            "schema": "transient-search-failed-attempt-supersession.v1",
            "case_id": verdict["case_id"],
            "failed_source_commit": verdict["source_commit"],
            "failed_verdict": verdict["verdict"],
            "failure_evidence": verdict["violations"],
            "superseded_by_case": superseded_by["case_id"],
            "superseded_by_source_commit": superseded_by["source_commit"],
            "superseded_by_verdict": superseded_by["verdict"],
        },
    )


def finalize_selected(
    case_dirs: dict[str, Path],
    artifact_root: Path,
    run_id: str,
    *,
    preflights: list[Path] | None = None,
    failed_audits: dict[str, Path] | None = None,
    cleanup_roots: list[Path] | None = None,
) -> Path:
    suite = inspect_selected(case_dirs)
    if suite["verdict"] != "PASS":
        raise RuntimeError(
            "only a passing selected suite may be materialized as final durable evidence"
        )
    destination = artifact_root / run_id
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    try:
        for index, preflight in enumerate(preflights or [], start=1):
            shutil.copy2(preflight, destination / f"preflight-{index}.json")
        dump_public_json(destination / "suite-verdict.json", suite)
        lines = [
            "# Smart Search fault-injected acceptance",
            "",
            f"- Run: `{run_id}`",
            f"- Source commits: `{', '.join(suite['source_commits'])}`",
            f"- Suite verdict: **{suite['verdict']}**",
            f"- Doctor probes: `{suite['doctor_calls']}` / `1`",
            "",
            "## Cases",
            "",
        ]
        for case_id, case in suite["cases"].items():
            case_source = case_dirs[case_id]
            case_destination = destination / case_id
            case_destination.mkdir(mode=0o700)
            secrets, private_values = _case_redaction_values(case_source)
            for name in ("gateway-events.jsonl", "invocations.jsonl"):
                _copy_public_file(
                    case_source / name,
                    case_destination / name,
                    secrets=secrets,
                    private_values=private_values,
                )
            _copy_tree(
                case_source / "cli-results",
                case_destination / "cli-results",
                secrets=secrets,
                private_values=private_values,
            )
            _copy_tree(
                case_source / "output",
                case_destination / "output",
                secrets=secrets,
                private_values=private_values,
            )
            dump_public_json(case_destination / "verdict.json", case)
            locators = ", ".join(case["event_locators"]) or "missing"
            lines.append(
                f"- {case_id}: **{case['verdict']}** at `{case['source_commit']}`; "
                f"injected evidence `{locators}`; verified sources `{case['observed']['verified_sources']}`."
            )
        for case_id, source in sorted((failed_audits or {}).items()):
            _copy_failed_audit(
                source,
                destination / "failed-attempts" / case_id,
                suite["cases"][case_id],
            )
            lines.extend(
                [
                    "",
                    "## Superseded attempts",
                    "",
                    (
                        f"- {case_id}: valid FAIL retained as sanitized correction evidence; "
                        f"superseded by final `{suite['cases'][case_id]['source_commit']}` PASS."
                    ),
                ]
            )
        (destination / "acceptance-summary.md").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )
        return destination
    except Exception:
        shutil.rmtree(destination, ignore_errors=True)
        raise
    finally:
        for runtime_root in cleanup_roots or []:
            cleanup(runtime_root)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("runtime_root", type=Path, nargs="?")
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--case", action="append", type=parse_assignment, default=[])
    parser.add_argument("--preflight", action="append", type=Path, default=[])
    parser.add_argument(
        "--failed-audit", action="append", type=parse_assignment, default=[]
    )
    parser.add_argument("--cleanup-root", action="append", type=Path, default=[])
    arguments = parser.parse_args()
    if arguments.case:
        if arguments.runtime_root is not None or not arguments.run_id:
            parser.error(
                "selected finalization requires --run-id and no positional runtime_root"
            )
        case_dirs = dict(arguments.case)
        if len(case_dirs) != len(arguments.case):
            parser.error("duplicate --case assignment")
        failed_audits = dict(arguments.failed_audit)
        if len(failed_audits) != len(arguments.failed_audit):
            parser.error("duplicate --failed-audit assignment")
        destination = finalize_selected(
            case_dirs,
            arguments.artifact_root,
            arguments.run_id,
            preflights=arguments.preflight,
            failed_audits=failed_audits,
            cleanup_roots=arguments.cleanup_root,
        )
    else:
        if arguments.runtime_root is None:
            parser.error("runtime_root is required unless --case is used")
        destination = finalize(arguments.runtime_root, arguments.artifact_root)
    print(json.dumps({"artifact": str(destination)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
