"""Canonical schemas and redaction for the transient-search acceptance harness."""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

GATEWAY_SCHEMA = "transient-search-gateway-event.v1"
INVOCATION_SCHEMA = "transient-search-invocation.v1"
VERDICT_SCHEMA = "transient-search-verdict.v1"
RESULT_SCHEMA = "transient-search-worker-result.v1"

SECRET_KEY_RE = re.compile(
    r"(?i)(authorization|proxy-authorization|cookie|set-cookie|api[_-]?key|secret|token|password|signed[_-]?url)"
)
BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+\-/=]+")
ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s,;]+"
)
LOCAL_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9])/(?:Users|home|tmp|private/var)/[^\s\"'<>]+"
)


def monotonic_ns() -> int:
    return time.monotonic_ns()


def public_path_category(provider: str) -> str:
    return {
        "openai-compatible": "main_search",
        "context7": "docs_search",
        "exa": "docs_search",
        "jina": "web_fetch",
        "launcher": "local_invocation",
    }.get(provider, "provider")


def redact_text(
    value: str,
    *,
    secrets: Sequence[str] = (),
    private_values: Sequence[str] = (),
) -> str:
    """Mask only private values while preserving public research URLs."""
    text = value
    for secret in sorted({item for item in secrets if item}, key=len, reverse=True):
        text = text.replace(secret, "[REDACTED_SECRET]")
    for private in sorted(
        {item for item in private_values if item}, key=len, reverse=True
    ):
        text = text.replace(private, "[REDACTED_PRIVATE_VALUE]")
    text = BEARER_RE.sub("Bearer [REDACTED_SECRET]", text)
    text = ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=[REDACTED_SECRET]", text)
    text = LOCAL_PATH_RE.sub("[REDACTED_LOCAL_PATH]", text)
    return text


def redact(
    value: Any,
    *,
    key: str = "",
    secrets: Sequence[str] = (),
    private_values: Sequence[str] = (),
) -> Any:
    if SECRET_KEY_RE.search(key):
        return "[REDACTED_SECRET]"
    if isinstance(value, dict):
        return {
            str(item_key): redact(
                item_value,
                key=str(item_key),
                secrets=secrets,
                private_values=private_values,
            )
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [
            redact(item, key=key, secrets=secrets, private_values=private_values)
            for item in value
        ]
    if isinstance(value, str):
        return redact_text(value, secrets=secrets, private_values=private_values)
    return value


def write_private_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def dump_public_json(
    path: Path,
    value: dict[str, Any],
    *,
    secrets: Sequence[str] = (),
    private_values: Sequence[str] = (),
) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    public = redact(value, secrets=secrets, private_values=private_values)
    path.write_text(
        json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.chmod(path, 0o600)


def append_jsonl(
    path: Path,
    value: dict[str, Any],
    *,
    secrets: Sequence[str] = (),
    private_values: Sequence[str] = (),
) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    public = redact(value, secrets=secrets, private_values=private_values)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(public, ensure_ascii=False, sort_keys=True) + "\n")
        stream.flush()
    os.chmod(path, 0o600)


def decode_jsonl(path: Path, *, schema: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    values: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict) or value.get("schema") != schema:
            raise ValueError(f"unsupported schema at {path}:{line_number}")
        values.append(value)
    return values


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"expected JSON object: {path}")
    return value


def command_fingerprint(command: str, argv: Sequence[str]) -> str:
    """Detect unchanged outer retries without persisting queries or URLs."""
    normalized: list[str] = [command]
    skip_next = False
    for index, item in enumerate(argv):
        if skip_next:
            skip_next = False
            continue
        if item == "--output" and index + 1 < len(argv):
            normalized.extend(["--output", "<OUTPUT>"])
            skip_next = True
        else:
            normalized.append(item)
    return hashlib.sha256("\0".join(normalized).encode("utf-8")).hexdigest()


def flag_names(argv: Sequence[str]) -> list[str]:
    return sorted({item.split("=", 1)[0] for item in argv if item.startswith("--")})


def option_value(argv: Sequence[str], option: str) -> str | None:
    for index, item in enumerate(argv):
        if item == option and index + 1 < len(argv):
            return argv[index + 1]
        if item.startswith(option + "="):
            return item.split("=", 1)[1]
    return None


def count(values: Iterable[dict[str, Any]], **filters: Any) -> int:
    return sum(
        all(value.get(key) == expected for key, expected in filters.items())
        for value in values
    )
