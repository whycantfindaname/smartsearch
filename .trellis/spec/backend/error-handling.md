# Error Handling

> How provider failures cross the service call boundaries. Authority: `src/smart_search/provider_errors.py` ("Stable provider failure classification shared by service call boundaries").

---

## The Rule

**No raw exception text ever reaches CLI output or persisted research records.** Every
provider failure is classified into the public taxonomy and sanitized before it is
rendered, returned, or written to disk.

---

## The Public Taxonomy (frozen)

`APPROVED_PROVIDER_ERROR_TYPES` (`provider_errors.py`) — exactly these nine:

`parameter_error`, `auth_error`, `timeout`, `rate_limited`, `request_cancelled`,
`network_error`, `parse_error`, `provider_error`, `runtime_error`

`ProviderCallError` downgrades any unknown `error_type` to `runtime_error`.
Never invent new types in call sites.

## Signatures

```python
classify_provider_exception(exc, *, additional_secrets=()) -> tuple[str, str]
provider_call_error(exc, *, additional_secrets=()) -> ProviderCallError
sanitize_provider_error_message(value, *, additional_secrets=(), limit=300) -> str
ProviderCallError(error_type, error, *, additional_secrets=())
```

## HTTP status → error_type mapping

| Status | error_type |
| --- | --- |
| 400, 422 | `parameter_error` |
| 401, 403 | `auth_error` |
| 408 | `timeout` |
| 429 | `rate_limited` |
| 499 | `request_cancelled` |
| 500–599 | `network_error` |
| other | `provider_error` |

`httpx.TimeoutException`/`asyncio.TimeoutError` → `timeout`; `json.JSONDecodeError`/
`UnicodeDecodeError`/`httpx.DecodingError` → `parse_error`; `httpx.RequestError` →
`network_error`; everything else → `runtime_error`.

## Convention: secrets travel as `additional_secrets`

Every provider call site passes its API key so the sanitizer can redact it before the
message leaves the module:

```python
# providers/exa.py — the pattern every provider follows
except Exception as exc:
    error_type, error = classify_provider_exception(exc, additional_secrets=(api_key,))
```

`sanitize_provider_error_message` redacts in order: explicit secrets → URL
credentials (`user:pass@`) → `key/token/secret/authorization` assignments →
`Bearer` tokens. Sanitization happens inside `ProviderCallError.__init__` too, so
constructing the exception is already safe.

## Wrong vs Correct

```python
# Wrong: raw exception leaks URLs, headers, possibly keys
output["error"] = str(exc)

# Correct
error_type, error = classify_provider_exception(exc, additional_secrets=(api_key,))
output["error_type"], output["error"] = error_type, error
```

## Validation Matrix (service call boundary)

- unclassified `error_type` → silently becomes `runtime_error`
- missing `additional_secrets` for a keyed provider → review blocker (secret may reach output)
- empty/None exception message → falls back to the class name, never an empty string

## Tests

`tests/test_provider_errors.py` asserts the taxonomy mapping and redaction. When
touching a provider, keep its error payload shape
`{"provider", "error_type", "error", "elapsed_ms"}` consistent with the existing
provider modules.
