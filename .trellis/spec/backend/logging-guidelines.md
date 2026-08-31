# Logging Guidelines

> The project logs through exactly one module: `src/smart_search/logger.py`. This file documents its actual behavior so it does not regress.

---

## Architecture

- One std logger `smart_search` with a `NullHandler` by default — the CLI is a
  library-grade package and must stay silent unless explicitly configured.
- User-facing console rendering lives in the CLI layer (`rich.Console`,
  stderr, `src/smart_search/cli.py`), not in `logging`. `log_info(ctx,
  message, is_debug=False)` feeds the module logger; `await ctx.info(message)`
  fires only when a caller passes a context object — and no current call site
  does (`ctx=None` everywhere). Treat `ctx` as a reserved interface, not a
  working output channel.
- `SMART_SEARCH_LOG_TO_FILE=true` attaches a `FileHandler` at import time;
  the file lands in `config.log_dir` (default `~/.config/smart-search/logs/`,
  one file per day, UTF-8).

## Level Contract

`SMART_SEARCH_LOG_LEVEL` is guarded twice, because `logger.py` reads the value
at **import time** and an unguarded invalid value raises `AttributeError` that
kills every CLI command:

1. `Config.set_config_value` rejects invalid values with a `ValueError`
   listing the supported set (`config.py`, `_validate_research_config_value`).
2. `Config.log_level` still falls back to `INFO` when the value comes from a
   hand-edited `config.json`.

Allowed: `DEBUG, INFO, WARNING, WARN, ERROR, CRITICAL, FATAL, NOTSET`.

Every `getattr(logging, ...)` call must pass a default: `getattr(logging,
config.log_level, logging.INFO)`.

## Don't

- Don't add a second module logger or use `print()` for diagnostics — route
  through `log_info`.
- Don't call `logger.info(...)` directly from providers/services; `log_info`
  exists so the logger stays the single destination.
- Don't log exception strings without
  `sanitize_provider_error_message` (see [error-handling.md](./error-handling.md)).

## Tests

`tests/test_config_dir_override.py` pins the level validation, the hand-edited
fallback, and the file-logging path. Extend those when touching `config.py` /
`logger.py`.
