#!/usr/bin/env python3
"""Smart Search-owned, fail-closed adapter for the bundled AnySearch CLI.

The upstream ``anysearch_cli.py`` remains the transport and output owner. This
adapter only supplies credentials from Smart Search's machine-private config,
limits fallback attempts, and removes credential-shaped response data from
diagnostics before it reaches the caller.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import re
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

CONFIG_DIR_ENV = "SMART_SEARCH_CONFIG_DIR"
PRIMARY_KEY_NAME = "ANYSEARCH_API_KEY"
FALLBACK_KEY_NAME = "ANYSEARCH_API_KEY_FALLBACK"
UPSTREAM_SCRIPT_NAME = "anysearch_cli.py"
RETRY_STATUSES = frozenset({401, 403, 429})
_INVALID_RESPONSE_PREFIXES = ("Invalid JSON response", "Invalid API response")
_SENSITIVE_FIELD_NAMES = {
    "apikey",
    "authorization",
    "accesstoken",
    "authtoken",
    "secret",
    "token",
}
_SENSITIVE_TEXT = re.compile(
    r"(?i)(?P<prefix>[\"']?(?:api[_-]?key|authorization|access[_-]?token|"
    r"auth[_-]?token|secret|token)[\"']?\s*[:=]\s*)"
    r"(?P<quote>[\"']?)(?P<scheme>Bearer\s+)?(?P<value_quote>[\"']?)"
    r"(?P<value>[^,\s}\"']+)(?P=value_quote)(?P=quote)"
)


class AdapterError(RuntimeError):
    """A local adapter/configuration error that must not reach the network."""


class _CommandFailure(RuntimeError):
    """An upstream command reported an API error after safe rendering."""


class Credentials:
    __slots__ = ("fallback", "primary")

    def __init__(self, primary: str, fallback: str | None = None) -> None:
        self.primary = primary
        self.fallback = fallback


class _Utf8ImportStream(io.StringIO):
    """Capture import-time output without triggering the CLI's stream wrapper."""

    @property
    def encoding(self) -> str:
        return "utf-8"


def resolve_config_file(
    *,
    platform: str | None = None,
    home: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> Path:
    """Resolve Smart Search's config file without creating or probing folders."""

    env = os.environ if environ is None else environ
    override = str(env.get(CONFIG_DIR_ENV, "")).strip()
    if override:
        return Path(override).expanduser() / "config.json"

    platform_name = platform or sys.platform
    home_path = Path.home() if home is None else Path(home)
    legacy = home_path / ".config" / "smart-search" / "config.json"
    if platform_name.startswith("win"):
        local_appdata = str(env.get("LOCALAPPDATA", "")).strip()
        preferred = (
            Path(local_appdata).expanduser() / "smart-search" / "config.json"
            if local_appdata
            else legacy
        )
        if not preferred.exists() and legacy.exists():
            return legacy
        return preferred
    return legacy


def _read_json_object(config_file: Path) -> dict[str, Any]:
    try:
        raw = config_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AdapterError(
            "AnySearch requires a readable Smart Search config.json with both API key slots."
        ) from exc
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AdapterError("AnySearch Smart Search config.json is not valid JSON.") from exc
    if not isinstance(value, dict):
        raise AdapterError("AnySearch Smart Search config.json must contain a JSON object.")
    return value


def load_credentials(config_file: Path | None = None) -> Credentials:
    """Load and strictly validate the ordered AnySearch key pair."""

    selected_file = config_file or resolve_config_file()
    config = _read_json_object(selected_file)
    values: dict[str, str] = {}
    invalid: list[str] = []
    for name in (PRIMARY_KEY_NAME, FALLBACK_KEY_NAME):
        value = config.get(name)
        if not isinstance(value, str) or not value.strip():
            invalid.append(name)
        else:
            values[name] = value.strip()
    if invalid:
        raise AdapterError(
            "AnySearch Smart Search config requires non-empty string values for "
            f"{PRIMARY_KEY_NAME} and {FALLBACK_KEY_NAME}."
        )
    if values[PRIMARY_KEY_NAME] == values[FALLBACK_KEY_NAME]:
        raise AdapterError("AnySearch Smart Search API key slots must contain different values.")
    return Credentials(values[PRIMARY_KEY_NAME], values[FALLBACK_KEY_NAME])


def _extract_explicit_key(argv: Sequence[str]) -> tuple[str | None, list[str]]:
    """Extract ``--api_key`` from any argv position and normalize its location."""

    explicit: str | None = None
    remaining: list[str] = []
    index = 0
    while index < len(argv):
        token = str(argv[index])
        if token == "--":
            remaining.extend(argv[index:])
            break
        if token == "--api_key":
            if index + 1 >= len(argv):
                raise AdapterError("--api_key requires a non-empty value.")
            value = str(argv[index + 1])
            index += 2
        elif token.startswith("--api_key="):
            value = token.split("=", 1)[1]
            index += 1
        else:
            remaining.append(argv[index])
            index += 1
            continue
        if explicit is not None:
            raise AdapterError("--api_key may be supplied only once.")
        explicit = value
    if explicit is not None and not explicit.strip():
        raise AdapterError("--api_key requires a non-empty value.")
    return explicit, remaining


def _is_offline_invocation(argv: Sequence[str]) -> bool:
    if not argv:
        return True
    if any(token in {"-h", "--help"} for token in argv):
        return True
    return next((token for token in argv if not str(token).startswith("-")), "") == "doc"


def _load_upstream_cli() -> ModuleType:
    script = Path(__file__).resolve().with_name(UPSTREAM_SCRIPT_NAME)
    if not script.is_file():
        raise AdapterError("Bundled AnySearch Python CLI is missing.")

    # The upstream module loads .env at import time. Temporarily remove key
    # variables so the adapter never inherits them as a credential source; all
    # network calls below receive an explicit key argument.
    saved_environment = os.environ.copy()
    base_override = os.environ.get("ANYSEARCH_API_BASE_URL", "").strip()
    for name in (PRIMARY_KEY_NAME, FALLBACK_KEY_NAME):
        os.environ.pop(name, None)

    def import_module() -> ModuleType:
        spec = importlib.util.spec_from_file_location("smart_search_bundled_anysearch_cli", script)
        if spec is None or spec.loader is None:
            raise AdapterError("Bundled AnySearch Python CLI could not be loaded.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    saved_stdout, saved_stderr = sys.stdout, sys.stderr
    import_stream = _Utf8ImportStream()
    sys.stdout, sys.stderr = import_stream, import_stream
    try:
        module = import_module()
    except ModuleNotFoundError as exc:
        if exc.name != "requests":
            raise AdapterError("Bundled AnySearch Python CLI could not be loaded.") from exc
        # AnySearch lists requests in its own requirements file, but the
        # Smart Search package intentionally does not make it a global
        # dependency. Supply a small standard-library compatibility transport
        # so the unchanged upstream CLI remains usable in a minimal runtime.
        requests_compat = _requests_compat_module()
        previous_requests = sys.modules.get("requests")
        sys.modules["requests"] = requests_compat
        try:
            try:
                module = import_module()
            except Exception as retry_exc:
                raise AdapterError("Bundled AnySearch Python CLI could not be loaded.") from retry_exc
        finally:
            if previous_requests is None:
                sys.modules.pop("requests", None)
            else:
                sys.modules["requests"] = previous_requests
    except AdapterError:
        raise
    except Exception as exc:
        raise AdapterError("Bundled AnySearch Python CLI could not be loaded.") from exc
    finally:
        # Do not leave a value loaded from a bundled .env in this process.
        sys.stdout, sys.stderr = saved_stdout, saved_stderr
        os.environ.clear()
        os.environ.update(saved_environment)

    # A bundled .env must not override the endpoint used by this adapter.
    module.API_BASE_URL = (base_override or "https://api.anysearch.com").rstrip("/")
    original_render_doc = module._render_doc
    module._render_doc = lambda: _rewrite_doc(original_render_doc())
    return module


def _rewrite_doc(text: str) -> str:
    """Keep offline upstream help aligned with the Smart Search adapter boundary."""

    rewritten = text.replace(
        "Auth: Header \"Authorization: Bearer <API_KEY>\" (optional, anonymous has lower rate limits)",
        "Auth: Header \"Authorization: Bearer <API_KEY>\" (required by the Smart Search adapter)",
    )
    rewritten = rewritten.replace(
        "python scripts/anysearch_cli.py",
        "python3 scripts/smart_search_anysearch.py",
    )
    rewritten = rewritten.replace(
        "- On rate limit error with auto_registered api_key in response: present key "
        "to user for approval, then save to .env and retry",
        "- On HTTP 401/403/429 from a valid primary response: the adapter may try its configured fallback once",
    )
    return rewritten.replace(
        "- On anonymous quota exhausted: inform user that a key provides higher limits; "
        "suggest configuring one via .env or environment variable",
        "- Without valid Smart Search credentials: fail locally before making a request; anonymous access is disabled",
    )


def _requests_compat_module() -> ModuleType:
    """Return the minimum requests surface used by the unchanged Python CLI."""

    requests_module = ModuleType("requests")

    class ConnectionError(Exception):
        pass

    class Timeout(Exception):
        pass

    class Response:
        def __init__(self, status_code: int, body: bytes, headers: Any) -> None:
            self.status_code = status_code
            self.text = body.decode("utf-8", errors="replace")
            self.headers = headers

        def json(self) -> Any:
            return json.loads(self.text)

    def request(
        method: str,
        url: str,
        *,
        json: Any = None,
        params: Any = None,
        headers: Any = None,
        timeout: float = 30,
    ) -> Response:
        if params:
            query = urllib.parse.urlencode(params, doseq=True)
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        body = None if json is None else __import__("json").dumps(json, ensure_ascii=False).encode("utf-8")
        request_obj = urllib.request.Request(url, data=body, headers=headers or {}, method=method)
        try:
            response = urllib.request.urlopen(request_obj, timeout=timeout)
            return Response(response.status, response.read(), response.headers)
        except urllib.error.HTTPError as exc:
            return Response(exc.code, exc.read(), exc.headers)
        except TimeoutError as exc:
            raise Timeout() from exc
        except urllib.error.URLError as exc:
            raise ConnectionError() from exc

    requests_module.request = request
    requests_module.exceptions = SimpleNamespace(ConnectionError=ConnectionError, Timeout=Timeout)
    return requests_module


class _ResponseState(threading.local):
    last: tuple[int, bool | None, bool | None] | None = None


def _response_schema_is_valid(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    code = value.get("code")
    if "code" in value and (isinstance(code, bool) or not isinstance(code, int)):
        return False
    message = value.get("message")
    if message is not None and not isinstance(message, str):
        return False
    request_id = value.get("request_id")
    return request_id is None or isinstance(request_id, str)


def _install_response_probe(module: ModuleType) -> tuple[Any, _ResponseState]:
    """Record only response status and JSON-object shape, never response data."""

    original_request = module.requests.request
    state = _ResponseState()

    def recorded_request(*args: Any, **kwargs: Any) -> Any:
        headers = kwargs.get("headers")
        authorization = headers.get("Authorization") if isinstance(headers, Mapping) else None
        if (
            not isinstance(authorization, str)
            or not authorization.startswith("Bearer ")
            or not authorization.removeprefix("Bearer ").strip()
        ):
            raise AdapterError("AnySearch adapter blocked a request without a non-empty Bearer header.")
        response = original_request(*args, **kwargs)
        status = int(getattr(response, "status_code", 0) or 0)
        object_shape: bool | None = None
        schema_valid: bool | None = None
        try:
            raw = getattr(response, "text", None)
            if isinstance(raw, str):
                parsed = json.loads(raw)
            elif callable(getattr(response, "json", None)):
                parsed = response.json()
            else:
                parsed = None
            object_shape = isinstance(parsed, dict)
            schema_valid = _response_schema_is_valid(parsed)
        except (TypeError, ValueError, json.JSONDecodeError):
            object_shape = False
            schema_valid = False
        state.last = (status, object_shape, schema_valid)
        return response

    module.requests.request = recorded_request
    return original_request, state


def _restore_response_probe(module: ModuleType, original_request: Any) -> None:
    module.requests.request = original_request


def _field_name_is_sensitive(name: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return normalized in _SENSITIVE_FIELD_NAMES or normalized == "apikey"


def _sanitize_value(value: Any, secrets: Sequence[str]) -> Any:
    if isinstance(value, dict):
        sanitized: dict[Any, Any] = {}
        for key, nested in value.items():
            normalized = str(key).lower().replace("-", "_")
            if normalized == "auto_registered" or _field_name_is_sensitive(key):
                continue
            sanitized[key] = _sanitize_value(nested, secrets)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_value(item, secrets) for item in value]
    if isinstance(value, tuple):
        return tuple(_sanitize_value(item, secrets) for item in value)
    if isinstance(value, str):
        return _sanitize_text(value, secrets)
    return value


def _sanitize_text(value: str, secrets: Sequence[str]) -> str:
    sanitized = str(value)
    for secret in sorted({item for item in secrets if item}, key=len, reverse=True):
        sanitized = sanitized.replace(secret, "[redacted]")
    return _SENSITIVE_TEXT.sub(
        r"\g<prefix>\g<quote>\g<scheme>\g<value_quote>[redacted]"
        r"\g<value_quote>\g<quote>",
        sanitized,
    )


def _safe_api_error(module: ModuleType, error: Exception, secrets: Sequence[str]) -> Exception:
    if not isinstance(error, module.ApiError):
        return error
    return module.ApiError(
        _sanitize_text(str(error), secrets),
        status=getattr(error, "status", 0),
        request_id=_sanitize_text(str(getattr(error, "request_id", "") or ""), secrets),
        data=_sanitize_value(getattr(error, "data", None), secrets),
    )


def _can_use_fallback(module: ModuleType, error: Exception, state: _ResponseState) -> bool:
    if not isinstance(error, module.ApiError):
        return False
    status = int(getattr(error, "status", 0) or 0)
    if status not in RETRY_STATUSES:
        return False
    if str(error).startswith(_INVALID_RESPONSE_PREFIXES):
        return False
    response = getattr(state, "last", None)
    if response is None:
        return False
    response_status, object_shape, schema_valid = response
    return response_status == status and object_shape is not False and schema_valid is not False


def _print_safe_api_error(error: Exception, secrets: Sequence[str]) -> None:
    request_id = getattr(error, "request_id", "")
    detail = f" (request_id: {_sanitize_text(str(request_id), secrets)})" if request_id else ""
    print(f"API Error: {_sanitize_text(str(error), secrets)}{detail}", file=sys.stderr)
    data = _sanitize_value(getattr(error, "data", None), secrets)
    if isinstance(data, dict) and data:
        print(f"Response data: {json.dumps(data, ensure_ascii=False)}", file=sys.stderr)


def _execute(module: ModuleType, forwarded: list[str], credentials: Credentials | None, secrets: Sequence[str]) -> int:
    parser = module.build_parser()
    try:
        args = parser.parse_args(forwarded)
    except SystemExit as exc:
        return int(exc.code or 0)

    if args.command is None:
        module.cmd_doc(args) if hasattr(module, "cmd_doc") else print(module._render_doc())
        return 0
    if args.command == "doc" and credentials is None:
        args.func(args)
        return 0
    if credentials is None:
        # ``doc`` and help are the only accepted no-key paths.
        return 0

    original_request, state = _install_response_probe(module)
    original_rest = module._call_rest
    original_or_exit = module._call_or_exit
    original_print_error = module._print_api_error
    primary = credentials.primary
    fallback = credentials.fallback

    def call_rest(method: str, path: str, api_key: str, *, payload: Any = None, params: Any = None) -> dict:
        # A command may issue more than one request on the same thread. Clear
        # the probe before each logical call so an error raised before the
        # request reaches ``recorded_request`` cannot inherit another item's
        # retryable status.
        state.last = None
        try:
            return original_rest(method, path, api_key, payload=payload, params=params)
        except module.ApiError as error:
            if fallback and api_key == primary and _can_use_fallback(module, error, state):
                state.last = None
                try:
                    return original_rest(method, path, fallback, payload=payload, params=params)
                except module.ApiError as fallback_error:
                    raise _safe_api_error(module, fallback_error, secrets) from None
            raise _safe_api_error(module, error, secrets) from None

    def call_or_exit(method: str, path: str, api_key: str, *, payload: Any = None, params: Any = None) -> dict:
        try:
            return call_rest(method, path, api_key, payload=payload, params=params)
        except module.ApiError as error:
            _print_safe_api_error(error, secrets)
            raise _CommandFailure from None

    module._call_rest = call_rest
    module._call_or_exit = call_or_exit
    module._print_api_error = lambda error: _print_safe_api_error(error, secrets)
    try:
        try:
            args.func(args)
        except _CommandFailure:
            return 1
        except SystemExit as exc:
            return int(exc.code or 0)
        except Exception as exc:  # noqa: BLE001 - adapter boundary must sanitize upstream failures
            print(f"AnySearch adapter error: {_sanitize_text(str(exc), secrets)}", file=sys.stderr)
            return 1
        return 0
    finally:
        module._call_rest = original_rest
        module._call_or_exit = original_or_exit
        module._print_api_error = original_print_error
        _restore_response_probe(module, original_request)


def main(argv: Sequence[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    try:
        explicit, remaining = _extract_explicit_key(raw_argv)
        offline = _is_offline_invocation(remaining)
        if explicit is not None:
            credentials = Credentials(explicit)
        elif offline:
            credentials = None
        else:
            credentials = load_credentials()
        module = _load_upstream_cli()
    except AdapterError as exc:
        print(f"AnySearch configuration error: {_sanitize_text(str(exc), ())}", file=sys.stderr)
        return 1

    forwarded = list(remaining)
    if credentials is not None:
        forwarded = ["--api_key", credentials.primary, *forwarded]
    secrets = tuple(
        value
        for value in (credentials.primary if credentials else "", credentials.fallback if credentials else "")
        if value
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = _execute(module, forwarded, credentials, secrets)
    sys.stdout.write(_sanitize_text(stdout.getvalue(), secrets))
    sys.stderr.write(_sanitize_text(stderr.getvalue(), secrets))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
