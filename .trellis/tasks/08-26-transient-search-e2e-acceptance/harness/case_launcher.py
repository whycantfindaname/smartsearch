"""Neutral worker-facing source CLI launcher with audit logging."""

from __future__ import annotations

import fcntl
import os
import subprocess
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

try:
    from .runtime import PYTHON, private_redaction_values, source_environment
    from .schema import (
        INVOCATION_SCHEMA,
        append_jsonl,
        command_fingerprint,
        decode_jsonl,
        flag_names,
        load_json,
        monotonic_ns,
        option_value,
        redact_text,
    )
except ImportError:
    from runtime import PYTHON, private_redaction_values, source_environment
    from schema import (
        INVOCATION_SCHEMA,
        append_jsonl,
        command_fingerprint,
        decode_jsonl,
        flag_names,
        load_json,
        monotonic_ns,
        option_value,
        redact_text,
    )


ALLOWED_COMMANDS = {
    "search",
    "research",
    "route",
    "fetch",
    "map",
    "exa-search",
    "exa-similar",
    "zhipu-search",
    "zhipu-mcp-search",
    "zhipu-mcp-reader",
    "anysearch-extract",
    "context7-library",
    "context7-docs",
    "sciverse-catalog",
    "sciverse-search",
    "sciverse-semantic",
    "sciverse-read",
    "sciverse-relations",
    "doctor",
}
PUBLIC_RUNTIME_IDENTITY = {
    "python": "<source-python>",
    "pythonpath": "<source-pythonpath>",
}


def _remove_option(argv: list[str], option: str) -> list[str]:
    result: list[str] = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == option:
            index += 2
            continue
        if item.startswith(option + "="):
            index += 1
            continue
        result.append(item)
        index += 1
    return result


def _safe_output_path(case_dir: Path, argv: Sequence[str]) -> Path | None:
    raw = option_value(argv, "--output")
    if raw is None:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = case_dir / path
    resolved = path.resolve(strict=False)
    output_root = (case_dir / "output").resolve()
    if resolved != output_root and output_root not in resolved.parents:
        raise ValueError("--output must stay inside the assigned output directory")
    resolved.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    return resolved


def _search_contract(
    argv: Sequence[str], output_path: Path | None
) -> dict[str, object]:
    timeout = option_value(argv, "--timeout")
    max_try = option_value(argv, "--max-try")
    format_name = option_value(argv, "--format")
    return {
        "explicit_timeout_120": timeout in {"120", "120.0"},
        "explicit_max_try_5": max_try == "5",
        "explicit_json_format": format_name == "json",
        "explicit_output": output_path is not None,
    }


def _sanitize_file(
    path: Path, *, secrets: Sequence[str], private_values: Sequence[str]
) -> None:
    if not path.exists() or not path.is_file():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    path.write_text(
        redact_text(text, secrets=secrets, private_values=private_values),
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def main(*, case_dir: str | Path | None = None) -> int:
    owned_case_dir = Path(case_dir or "").resolve()
    manifest = load_json(owned_case_dir / "private" / "case-manifest.json")
    requested = list(sys.argv[1:])
    if not requested:
        raise SystemExit("usage: smart-search <allowed-command> [arguments]")
    command = requested[0]
    if command not in ALLOWED_COMMANDS:
        raise SystemExit("command not permitted by this research launcher")
    if command == "doctor" and manifest["case_id"] != "A2":
        raise SystemExit(
            "doctor is unavailable unless an observed recovery object authorizes it"
        )

    lock_path = owned_case_dir / "private" / "launcher.lock"
    lock_path.touch(mode=0o600, exist_ok=True)
    with lock_path.open("r+") as lock_stream:
        try:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SystemExit(
                "parallel Smart Search invocations are not permitted"
            ) from error

        invocations_path = owned_case_dir / "invocations.jsonl"
        prior_invocations = decode_jsonl(invocations_path, schema=INVOCATION_SCHEMA)
        if command == "doctor" and any(
            item.get("command") == "doctor" for item in prior_invocations
        ):
            raise SystemExit("doctor budget already consumed")

        effective = list(requested)
        forced_provider = str(manifest.get("force_search_provider") or "")
        if command == "search" and forced_provider:
            effective = _remove_option(effective, "--providers")
            effective.extend(["--providers", forced_provider])

        try:
            output_path = _safe_output_path(owned_case_dir, effective)
        except ValueError as error:
            raise SystemExit(str(error)) from error

        invocation_id = f"inv-{len(prior_invocations) + 1:04d}-{uuid.uuid4().hex[:8]}"
        active_path = owned_case_dir / "private" / "active-invocation"
        active_path.write_text(invocation_id, encoding="utf-8")
        os.chmod(active_path, 0o600)
        started_ns = monotonic_ns()
        environment = source_environment(
            overrides={
                str(key): str(value) for key, value in manifest["environment"].items()
            }
        )
        command_line = [str(PYTHON), "-m", "smart_search.cli", *effective]
        try:
            result = subprocess.run(
                command_line,
                env=environment,
                cwd=owned_case_dir / "output",
                text=True,
                capture_output=True,
                check=False,
            )
        finally:
            try:
                active_path.unlink()
            except FileNotFoundError:
                pass
        ended_ns = monotonic_ns()

        secrets, private_values = private_redaction_values()
        secrets = [*secrets, "local-acceptance-placeholder"]
        private_values = [*private_values, str(manifest.get("gateway_endpoint") or "")]
        command_dir = owned_case_dir / "cli-results"
        command_dir.mkdir(mode=0o700, exist_ok=True)
        stdout_path = command_dir / f"{invocation_id}.stdout"
        stderr_path = command_dir / f"{invocation_id}.stderr"
        stdout_path.write_text(
            redact_text(result.stdout, secrets=secrets, private_values=private_values),
            encoding="utf-8",
        )
        stderr_path.write_text(
            redact_text(result.stderr, secrets=secrets, private_values=private_values),
            encoding="utf-8",
        )
        os.chmod(stdout_path, 0o600)
        os.chmod(stderr_path, 0o600)
        if output_path is not None:
            _sanitize_file(output_path, secrets=secrets, private_values=private_values)

        requested_argv = requested[1:]
        effective_argv = effective[1:]
        append_jsonl(
            invocations_path,
            {
                "schema": INVOCATION_SCHEMA,
                "case_id": manifest["case_id"],
                "seq": len(prior_invocations) + 1,
                "invocation_id": invocation_id,
                "command": command,
                "command_fingerprint": command_fingerprint(command, requested_argv),
                "requested_flags": flag_names(requested_argv),
                "effective_flags": flag_names(effective_argv),
                "search_contract": _search_contract(requested_argv, output_path)
                if command == "search"
                else None,
                "source_commit": manifest["runtime"]["source_commit"],
                "source_python": PUBLIC_RUNTIME_IDENTITY["python"],
                "source_pythonpath": PUBLIC_RUNTIME_IDENTITY["pythonpath"],
                "output_relative": str(output_path.relative_to(owned_case_dir))
                if output_path is not None
                else "",
                "stdout_relative": str(stdout_path.relative_to(owned_case_dir)),
                "stderr_relative": str(stderr_path.relative_to(owned_case_dir)),
                "return_code": result.returncode,
                "started_monotonic_ns": started_ns,
                "ended_monotonic_ns": ended_ns,
            },
            secrets=secrets,
            private_values=private_values,
        )
        if result.stdout:
            sys.stdout.write(
                redact_text(
                    result.stdout, secrets=secrets, private_values=private_values
                )
            )
        if result.stderr:
            sys.stderr.write(
                redact_text(
                    result.stderr, secrets=secrets, private_values=private_values
                )
            )
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
