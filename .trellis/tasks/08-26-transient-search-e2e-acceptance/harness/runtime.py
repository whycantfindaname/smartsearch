"""Source-runtime identity and private configuration helpers."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Iterable
from pathlib import Path

PYTHON = Path("/Users/jasonliao/miniconda3/envs/codex/bin/python")
SOURCE_WORKTREE = Path(
    "/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch-lwj_dev-wt"
)
SOURCE_PYTHONPATH = SOURCE_WORKTREE / "src"
ACTIVE_SMART_SEARCH_SKILL = Path(
    "/Users/jasonliao/.codex/skills/smart-search-cli/SKILL.md"
)
ACTIVE_LANGUAGE_SYSTEM = Path("/Users/jasonliao/.codex/skills/language-system/SKILL.md")

SECRET_KEYS = (
    "XAI_API_KEY",
    "OPENAI_COMPATIBLE_API_KEY",
    "INTENT_EMBEDDING_API_KEY",
    "INTENT_CLASSIFIER_API_KEY",
    "EXA_API_KEY",
    "CONTEXT7_API_KEY",
    "ZHIPU_API_KEY",
    "ZHIPU_MCP_API_KEY",
    "JINA_API_KEY",
    "TAVILY_API_KEY",
    "FIRECRAWL_API_KEY",
    "ANYSEARCH_API_KEY",
    "SCIVERSE_API_TOKEN",
)

PRIVATE_URL_KEYS = (
    "XAI_API_URL",
    "OPENAI_COMPATIBLE_API_URL",
    "INTENT_EMBEDDING_API_URL",
    "INTENT_CLASSIFIER_API_URL",
    "EXA_BASE_URL",
    "CONTEXT7_BASE_URL",
    "ZHIPU_API_URL",
    "ZHIPU_MCP_SEARCH_API_URL",
    "ZHIPU_MCP_READER_API_URL",
    "ZHIPU_MCP_ZREAD_API_URL",
    "JINA_READER_API_URL",
    "TAVILY_API_URL",
    "FIRECRAWL_API_URL",
    "ANYSEARCH_API_URL",
    "SCIVERSE_API_URL",
)

SMART_SEARCH_KEYS = (
    SECRET_KEYS
    + PRIVATE_URL_KEYS
    + (
        "XAI_MODEL",
        "XAI_TOOLS",
        "OPENAI_COMPATIBLE_MODEL",
        "OPENAI_COMPATIBLE_FALLBACK_MODELS",
        "OPENAI_COMPATIBLE_STREAM",
        "SMART_SEARCH_MINIMUM_PROFILE",
        "SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS",
        "SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS",
        "SMART_SEARCH_INTENT_ROUTER",
        "INTENT_EMBEDDING_MODEL",
        "INTENT_CLASSIFIER_MODEL",
        "JINA_RESPOND_WITH",
        "TAVILY_ENABLED",
        "SMART_SEARCH_RETRY_MAX_ATTEMPTS",
        "SMART_SEARCH_RETRY_MULTIPLIER",
        "SMART_SEARCH_RETRY_MAX_WAIT",
        "SMART_SEARCH_LOG_TO_FILE",
        "SMART_SEARCH_DEBUG",
        "SSL_VERIFY",
    )
)

PASSTHROUGH_ENV = (
    "HOME",
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "TMPDIR",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE",
    "CURL_CA_BUNDLE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "SMART_SEARCH_CONFIG_DIR",
)


def source_environment(*, overrides: dict[str, str] | None = None) -> dict[str, str]:
    allowed = set(PASSTHROUGH_ENV) | set(SMART_SEARCH_KEYS)
    environment = {key: value for key, value in os.environ.items() if key in allowed}
    environment["PYTHONPATH"] = str(SOURCE_PYTHONPATH)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["SMART_SEARCH_LOG_TO_FILE"] = "false"
    environment["SMART_SEARCH_DEBUG"] = "false"
    if overrides:
        environment.update(overrides)
    return environment


def source_commit() -> str:
    return subprocess.check_output(
        ["git", "-C", str(SOURCE_WORKTREE), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def source_help() -> str:
    result = subprocess.run(
        [str(PYTHON), "-m", "smart_search.cli", "search", "--help"],
        env=source_environment(),
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout


def assert_source_runtime() -> dict[str, str]:
    if not PYTHON.is_file():
        raise RuntimeError(f"source Python missing: {PYTHON}")
    if not (SOURCE_PYTHONPATH / "smart_search" / "cli.py").is_file():
        raise RuntimeError(f"source package missing: {SOURCE_PYTHONPATH}")
    help_text = source_help()
    if "--timeout SECONDS" not in help_text or "default: 120" not in help_text:
        raise RuntimeError("source search help does not expose timeout 120")
    if "--max-try ATTEMPTS" not in help_text or "default: 5" not in help_text:
        raise RuntimeError("source search help does not expose max-try 5")
    return {
        "python": str(PYTHON),
        "pythonpath": str(SOURCE_PYTHONPATH),
        "source_commit": source_commit(),
    }


def config_values(keys: Iterable[str]) -> dict[str, str]:
    selected = list(dict.fromkeys(keys))
    code = (
        "import json,sys; from smart_search.config import config; "
        "keys=json.loads(sys.argv[1]); "
        "print(json.dumps({k:(config._get_config_value(k) or '') for k in keys}))"
    )
    result = subprocess.run(
        [str(PYTHON), "-c", code, json.dumps(selected)],
        env=source_environment(),
        text=True,
        capture_output=True,
        check=True,
    )
    values = json.loads(result.stdout)
    if not isinstance(values, dict):
        raise TypeError("unexpected configuration probe output")
    return {str(key): str(value or "") for key, value in values.items()}


def private_redaction_values() -> tuple[list[str], list[str]]:
    values = config_values((*SECRET_KEYS, *PRIVATE_URL_KEYS))
    secrets = [values[key] for key in SECRET_KEYS if values.get(key)]
    private_urls = [values[key] for key in PRIVATE_URL_KEYS if values.get(key)]
    return secrets, private_urls
