# Quality Guidelines

> Testing and review conventions specific to this repo. Everything here is enforced by a gate or was learned from a real failure.

---

## Running the Suite

```bash
python -m pytest tests/ -q          # ~20s, no network
```

- `tests/test_release_workflow.py` shells out to **node**; in nvm shells export
  the bin dir first: `export PATH="$PATH:$(ls -d ~/.nvm/versions/node/*/bin | tail -1)"`.
  Without it, 5 release-workflow tests fail with `FileNotFoundError: 'node'` —
  an environment problem, not a code problem.
- Environment fact: the repo venv is uv-managed and has no pip; build wheels
  with `uv build --wheel`.

## Isolation Contract (tests/conftest.py)

The autouse fixture `isolate_smart_search_config` points `Config._config_file`
at a tmp path, deletes every `_CONFIG_KEYS` env var, and sets
`SMART_SEARCH_MINIMUM_PROFILE=off`. Consequences:

- environment config never leaks between tests — each test states explicitly
  what it needs (`monkeypatch.setenv(...)` or `config.set_config_value(...)`);
- a value "persisted" by one test is invisible to the next unless re-set.

## Test Fakes Must Mirror Real Signatures

Fakes that replace `httpx.AsyncClient` (e.g. `FakeZhipuMCPClient`) are injected
via `monkeypatch.setattr` and receive the **real constructor kwargs**. When you
add a kwarg to any `httpx.AsyncClient(...)` call site, update the fakes in the
same change:

```bash
grep -rn "def __init__(self, timeout" tests/
```

Known failure mode: adding a kwarg at call sites without updating the fakes
produced 50 failures whose only visible symptom was *empty call-recording
lists* — the `TypeError` was swallowed by provider error handling. See
[error-handling.md](./error-handling.md).

## Gates Before Reporting Done

| Gate | Command |
| --- | --- |
| Full suite | `python -m pytest tests/ -q` |
| Skill mirror parity | `npm run check:skill-parity` |
| Tarball content | `npm run pack:dry` (and `npm run smoke:tarball` for release) |
| Regression contracts | included in the suite (`tests/test_regression.py`) |

See [packaging-contract.md](./packaging-contract.md) for what each packaging
gate actually protects.

## Conventions

- `subprocess`/`Popen` with `text=True` must pin `encoding="utf-8"` — Windows
  ANSI codepages otherwise corrupt non-ASCII payloads (this project's payloads
  are frequently Chinese). See `document_sidecar.py`, `cli.py`.
- Blocking IO (subprocess stdio, non-trivial file IO) must not be awaited
  directly inside `async def` paths — wrap with `asyncio.to_thread`.
- POSIX-only assertions (e.g. file mode `0o600`) need
  `@pytest.mark.skipif(os.name == "nt", ...)`; CI runs Windows.
- Lint: `ruff` with the repo default ruleset; changed files must not add new
  findings versus `HEAD` (the existing codebase has a baseline).
