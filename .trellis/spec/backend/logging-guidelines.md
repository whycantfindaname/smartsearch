# Logging Guidelines

> The project logs through exactly one module: `src/smart_search/logger.py`. This file documents its actual behavior (including the 2026-08-28 fixes) so it does not regress.

---

## Architecture

- One std logger `smart_search` with a `NullHandler` by default — the CLI is a
  library-grade package and must stay silent unless explicitly configured.
- Console output does **not** go through `logging`. It goes through the MCP
  context (`ctx.info`) inside `log_info(ctx, message, is_debug=False)`.
- `SMART_SEARCH_LOG_TO_FILE=true` attaches a `FileHandler` at import time;
  the file lands in `config.log_dir` (default `~/.config/smart-search/logs/`,
  one file per day, UTF-8).

## Level Contract

`SMART_SEARCH_LOG_LEVEL` has an allowed set, guarded twice after the 2026-08-28
"invalid level bricks the CLI" incident:

1. `Config.set_config_value` rejects invalid values with a `ValueError`
   listing the supported set (`config.py`, `_validate_research_config_value`).
2. `Config.log_level` still falls back to `INFO` when the value comes from a
   hand-edited `config.json` — `logger.py` reads this property at **import
   time**, so an unguarded bad value raises `AttributeError` and kills every
   command.

Allowed: `DEBUG, INFO, WARNING, WARN, ERROR, CRITICAL, FATAL, NOTSET`.

Every `getattr(logging, ...)` call must pass a default: `getattr(logging,
config.log_level, logging.INFO)`.

## Don't

- Don't add a second module logger or use `print()` for diagnostics — route
  through `log_info`.
- Don't call `logger.info(...)` directly from providers/services; `log_info`
  exists so console (`ctx`) and file destinations stay consistent.
- Don't log exception strings without
  `sanitize_provider_error_message` (see [error-handling.md](./error-handling.md)).

## Tests

`tests/test_config_dir_override.py` pins the level validation, the hand-edited
fallback, and the file-logging path. Extend those when touching `config.py` /
`logger.py`.
