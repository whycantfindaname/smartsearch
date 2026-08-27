# Research: anysearch-cross-runtime-contract

- Query: Audit the contract for two machine-private AnySearch keys shared by standalone AnySearch and Smart Search's bundled AnySearch.
- Scope: internal only; the AnySearch source tree, Smart Search source/tests, and Smart Search Trellis docs. No network access and no key contents inspected.
- Date: 2026-08-27

## Findings

### Status

STATUS: COMPLETE. No read-only blocker prevented the audit. Implementation still needs a decision on the macOS-only adapter scope versus the requested all-runtime parity, and a provider-defined error code for quota/rate-limit key failures.

### Files found

- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/anysearch_cli.py`: Python REST client, key loading, error envelope, and batch implementation.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/anysearch_cli.js`: Node.js REST client; its environment variable names contain two spelling defects.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/anysearch_cli.sh`: Bash/curl/jq REST client and temporary-file batch implementation.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/anysearch_cli.ps1`: PowerShell HttpClient and batch implementation.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/generate.py`: generator for the four runtime constants/doc sections.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/shared/doc_spec.md`: shared protocol and rate-limit guidance.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/scripts/test_cli.py`: local HTTP-stub cross-runtime acceptance tests; currently does not inspect authorization headers.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/anysearch-skill/SKILL.md`: one-key `.env`/environment/CLI documentation and `auto_registered` guidance.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/src/smart_search/config.py`: Smart Search config path, JSON loading, masking, and config CLI backing; it currently has no AnySearch key entries.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/src/smart_search/delegation.py`: AnySearch dispatch/import contract; it resolves a bundled/global Skill but does not inject credentials.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/src/smart_search/service.py`: capability and config wrappers; AnySearch is delegated, not a main-search provider.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/scripts/sync_anysearch_skill.py`: syncs the public and packaged bundled trees while preserving local `.env` and `runtime.conf`.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/tests/test_config_dir_override.py`: existing default, override, Windows legacy, and path-source matrix.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/tests/test_service.py`: config set/list/unset, source, masking, and AnySearch capability-boundary tests.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/tests/test_cli.py`: CLI config masking and bundled-skill installation tests.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/tests/test_regression.py`: public/packaged documentation and AnySearch contract parity tests.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/tests/test_sync_anysearch_skill.py`: preservation and destination tests for bundled local runtime files.
- `/Users/jasonliao/Desktop/code/Skills/5-knowledge/smartsearch/.trellis/tasks/08-27-anysearch-dual-key-config/prd.md`: current dual-key requirements, including the proposed adapter and explicit scope conflict.

The four AnySearch runtime scripts and their shared generated constants/docs are byte-identical between the standalone source and the two Smart Search bundled locations. README files are not all identical. The two Smart Search destinations are explicitly listed at `sync_anysearch_skill.py:44-59`.

### 1. Current key loading and API error behavior

#### Python

- `_load_env` reads `<script_dir>/.env` and its parent at `anysearch_cli.py:22-49`; non-empty `.env` assignments overwrite the process environment. The documented order is `--api_key > .env > environment > anonymous` (`:25-30`). The parser default reads the correctly spelled `ANYSEARCH_API_KEY` (`:531-536`).
- `_build_headers` adds `Authorization: Bearer ...` only for a non-empty key (`:62-69`). `_call_rest` sends a 30-second request and raises `ApiError` on HTTP status `>=400`, or on a non-zero JSON `code`; it retains HTTP `status`, `request_id`, and `data` (`:79-110`). Missing `code` is accepted; JSON `null` is rejected because `None != 0`.
- Connection and timeout failures become `ApiError` with status `0` and no data (`:89-92`). Invalid JSON retains the HTTP status and includes the first 500 response characters in the exception message (`:94-102`).
- `_print_api_error` prints the message/request ID and raw non-empty dictionary `data` (`:113-125`). It does not print the retained status separately and does not mask data. Batch workers all receive the same `args.api_key`, preserve input order, and report only message/request ID (`:458-487`).

#### Node.js

- `loadEnv` has the same two `.env` paths and overwrite behavior (`anysearch_cli.js:24-48`), but `parseArgs` reads `process.env.ANYSEARCH_API_KEY` rather than `ANYSEARCH_API_KEY` (`:454-458`). Consequently the documented environment key is ignored by Node unless supplied through `--api_key`; the `.env` loader itself does not correct the typo.
- The generated base URL has the same extra `E` typo, `ANYESEARCH_API_BASE_URL`, at `:15-22`. The existing test harness sets `ANYSEARCH_API_BASE_URL` (`test_cli.py:199-212`), so Node's test invocation would not be isolated to the local stub. No tests were run because network access was prohibited.
- `restRequest` stores status/request ID/data only in `ApiError` for HTTP or non-zero-code errors (`anysearch_cli.js:59-94`). Invalid JSON and transport errors are generic `Error` objects without status, request ID, or data (`:95-107`). Missing `code` is accepted; a present JSON `null` or `false` is treated as non-zero by JavaScript strict comparison.
- `callOrExit` prints raw object `data` without masking and omits status (`:110-120`). `Promise.all` fans out batch requests concurrently with one shared `opts.apiKey`, preserves order, and prints only message/request ID for item failures (`:415-430`).

#### Bash

- `_load_env` reads the same script and parent `.env` paths and exports non-empty assignments over the environment; `API_KEY` then reads `ANYSEARCH_API_KEY` (`anysearch_cli.sh:35-63`). Per-command `--api_key` mutates this process-global variable, for example in batch parsing (`:390-395`).
- `_curl_rest` captures the HTTP status as a trailing line (`:138-161`). `_call_rest` rejects status `000`, non-object JSON, HTTP `>=400`, or a JSON expression other than `(.code // 0) == 0` (`:176-197`). Missing, `null`, and `false` `code` values are effectively treated as zero by jq's `//`; this differs from Python and Node for `null`/boolean envelopes.
- `_print_api_error` prints message/request ID and raw `.data` (`:163-174`); status is only folded into the fallback message. Invalid JSON includes the first 500 body characters (`:188-190`).
- Batch search launches one curl subprocess per item, stores raw responses in a temporary directory, preserves order, and reports only message/request ID for failures (`:521-574`). The temporary files are removed, but no status/data is exposed in the aggregate output.

#### PowerShell

- `Load-Env` reads the script and parent `.env` files and overwrites environment entries (`anysearch_cli.ps1:15-42`); `$apiKey` correctly starts from `$env:ANYSEARCH_API_KEY` (`:587-588`).
- `New-ApiHttpClient` adds the bearer header and sets a 30-second timeout (`anysearch_cli.ps1:53-64`). `ConvertFrom-ApiHttpResponse` recursively converts JSON objects, arrays, and primitives, then indexes the result as an envelope; it treats a successful HTTP status with missing or `null` `code` as success and returns only `Ok`, `Message`, `RequestId`, and `Data`; HTTP status is not retained as a field (`:67-81`, with conversion at `:221-250`). A non-object top-level response is therefore not rejected by the same explicit shape check used by Node/Bash.
- Parse failures report an HTTP status and a first-500-character raw snippet (`:67-74`). Single-call transport exceptions are collapsed into a connection-error message by `Invoke-RestRequest` (`:83-115`). `Get-RestBodyOrExit` prints raw serialized `Data` and does not mask it (`:117-125`).
- Batch uses one shared HttpClient/key for all concurrent requests, keeps input order, and prints only message/request ID for failed items (`:509-563`). Its returned error shape also has no status field.

#### Cross-runtime envelope differences

The currently observable envelope fields are HTTP status plus JSON `code`, `message`, `request_id`, and `data`. There is no stable key-identity or quota-specific field in the code/tests. The following differences must be resolved before claiming behavioral alignment:

| Condition | Python | Node.js | Bash | PowerShell |
| --- | --- | --- | --- | --- |
| Missing `code` | success | success | success | success |
| `code: null` | error | error | success | success |
| `code: false` | Python equality makes it success | strict comparison makes it error | jq `//` makes it success | relies on PowerShell coercive `-eq 0`; not an explicit contract |
| Invalid JSON | status retained internally; raw prefix in message | generic error; no status | raw prefix and status embedded in stderr | status and raw prefix in message; status not retained structurally |
| Single API error data | retained and printed raw | retained and printed raw | parsed and printed raw | serialized and printed raw |
| Batch API error data/status | discarded from display | discarded from display | discarded from display | discarded from display |

### 2. Smallest portable config-location algorithm

#### Direct evidence

Smart Search already implements the desired directory order in `config.py:_default_config_dir` and `_resolve_config_dir` (`config.py:121-166`):

1. A non-empty `SMART_SEARCH_CONFIG_DIR` is a directory override; `config.json` is appended (`:157-160`, `:176-187`).
2. On Windows, a non-empty `LOCALAPPDATA` selects `LOCALAPPDATA/smart-search` (`:123-127`).
3. Otherwise the default is `Path.home()/.config/smart-search` (`:127`).
4. On Windows only, if the preferred config is absent and the legacy home config exists, the legacy path is selected (`:162-166`). Existing tests cover override/default/legacy precedence (`test_config_dir_override.py:15-105`).

The current `config_file` property may create directories and, when the default directory cannot be created, fall back to `cwd/.smart-search` (`config.py:176-187`). That fallback is useful for Smart Search writes but would undermine a shared machine-private read contract if AnySearch silently chose it.

#### Recommended read-only resolver (recommendation, not current implementation)

Use the same resolver in the adapter and all direct runtimes, without creating directories:

```text
if SMART_SEARCH_CONFIG_DIR is non-empty:
    preferred = SMART_SEARCH_CONFIG_DIR/config.json
    do not probe legacy/default paths when this override is unusable
else if Windows and LOCALAPPDATA is non-empty:
    preferred = LOCALAPPDATA/smart-search/config.json
else:
    preferred = home/.config/smart-search/config.json

if Windows, no override, preferred is absent, and home/.config/smart-search/config.json exists:
    selected = legacy home path
else:
    selected = preferred
```

Read UTF-8 JSON and require a top-level object. For `ANYSEARCH_API_KEY` and `ANYSEARCH_API_KEY_FALLBACK`, accept only non-empty strings; ignore or return a non-secret configuration error for null, boolean, number, array, object, malformed JSON, or unreadable files. Do not inherit Smart Search's generic `str(value)` conversion (`config.py:212-225`, `:227-238`) for credentials, because it would turn malformed JSON types into plausible strings. Do not use the existing cwd fallback for this shared reader.

This file resolver alone does not currently connect the two consumers: Smart Search's `delegation.py` only returns bundled/global Skill resolution metadata (`:288-318`), and the standalone CLIs only inspect local `.env`/environment/CLI flags. The current task PRD proposes two `runtime.conf` entries invoking one lightweight Python adapter (`prd.md:19-29`); no such adapter or active `runtime.conf` was found in the searched source scope. The AnySearch sync/installer intentionally preserve local `.env` and `runtime.conf` rather than copying them (`sync_anysearch_skill.py:29`, `:116-126`; `skill_installer.py:11-13`; `test_sync_anysearch_skill.py:85-100`).

### 3. Primary/fallback switching

#### Direct evidence

- The current task PRD names `ANYSEARCH_API_KEY` and `ANYSEARCH_API_KEY_FALLBACK` and asks for one fallback after explicit authentication, permission, rate-limit, or quota rejection, while forbidding switching on timeout, connection, parse, 5xx, local parameter, and schema errors (`prd.md:19-29`).
- Current runtime code has no `auto_registered` branch. A repository search found `auto_registered` only in the AnySearch Skill/shared documentation (`SKILL.md:105-112`, `scripts/shared/doc_spec.md:235-237`) and mirrored copies, not in any executable CLI or test branch.
- The cross-runtime test stub exercises an HTTP 429 with a generic non-zero code/message/request ID and checks only that the error is surfaced (`test_cli.py:243-247`, `:258-278`). It does not establish that the failure belongs to one key rather than the account, endpoint, or service.
- Smart Search's existing recovery contract classifies 401/403, 429, and 5xx as broad provider failures but gives no AnySearch key-specific error code (`references/error-recovery.md:305-329`).

#### Recommendation / inference

The safest deterministic automatic switch currently supportable is one bounded retry with the fallback key only when the first request returns a valid JSON object and an explicit HTTP `401` or `403` authentication/permission response. This is a conservative inference from the status field, not proof that every 401/403 is key-scoped. Do not switch on generic 429, 408, 5xx, timeout, connection failure, invalid JSON, schema failure, or local validation failure. A 429 may represent account-wide quota or concurrency, and the current envelope does not distinguish those cases.

If the product requirement must include rate-limit/quota switching, the provider needs a stable error code/field whose semantics explicitly identify the supplied key. The current generic 429 test envelope is insufficient evidence. `auto_registered` must not trigger extraction, automatic persistence, or automatic switching: its shape is undocumented in code, and the current error printers would expose raw `data` if it contained a new key. Any user-approved persistence must target the central config contract, not the legacy `.env`, after the documentation is changed.

For batch requests, select a key per logical item before fan-out and keep the primary/fallback sequence local to that item; do not mutate a process-global key or write config while other items are in flight. Keep the existing maximum of five, input order, and partial-result behavior. This is an implementation recommendation based on the Python queue, Node `Promise.all`, Bash subprocesses, and PowerShell shared-client implementations, not a current behavior.

An explicit `--api_key` should remain a one-shot single-key override with no fallback, matching the task PRD (`prd.md:27`).

### 4. Exact update and test surface

#### Required if all four official runtimes must read the central file

- Update the four source CLIs: `anysearch-skill/scripts/anysearch_cli.py:22-110`, `anysearch-skill/scripts/anysearch_cli.js:16-108`, `anysearch-skill/scripts/anysearch_cli.sh:35-197`, and `anysearch-skill/scripts/anysearch_cli.ps1:15-125`. Add the shared resolver/key selection and normalize status/code/error metadata. Fix Node's `ANYESEARCH_*` typos at `:16` and `:458` as part of parity.
- Propagate those source changes to both bundled trees named by `sync_anysearch_skill.py:44-59`, or make the sync/generation route authoritative. `generate.py:154-169` currently regenerates only constants and doc blocks, so it cannot yet serve as a resolver source of truth without a generator change.
- Update the contract docs in the standalone source (`SKILL.md`, `README.md`, `README_zh.md`, `scripts/shared/doc_spec.md`, and `.env.example`) and the mirrored bundled `SKILL.md`, README, and shared doc. Also update Smart Search public and packaged copies of `SKILL.md`, `references/provider-routing.md`, `references/setup-config.md`, and `references/error-recovery.md`; the current wording assigns AnySearch ownership to `.env` (`provider-routing.md:111-118`, `setup-config.md:71-77`) and documents raw `auto_registered` persistence.
- Extend `anysearch-skill/scripts/test_cli.py:181-212`, `:224-289` with synthetic non-secret config files, override/default/Windows-legacy path cases, per-slot authorization assertions that never print values, explicit-CLI override, 401/403 one-retry behavior, no-switch transport/parse/5xx cases, and raw-data redaction assertions. Fix the local-stub base URL injection test for Node before using it as a cross-runtime gate.

#### Smart Search configuration and regression surface

- Add the two key names, strict credential typing, masked saved-config output, sources, and diagnostics to `smartsearch/src/smart_search/config.py:36-110`, `:212-252`, `:254-261`, `:345-357`, and `:977-1066`. The current generic masking path is useful (`:747-757`) but does not protect AnySearch CLI error data.
- Extend `smartsearch/tests/test_config_dir_override.py:15-105` for the two keys, malformed/non-string values, and read-only resolver behavior. Extend `tests/test_service.py:_reset_config` (`:10-58`), config set/list/unset (`:79-95`), and AnySearch boundary coverage (`:1543-1557`). Extend `tests/test_cli.py` masking assertions (`:1768-1795`, `:1903-1920`).
- Preserve the current external-Skill boundary: `service.py:1833-1910`, `:1975-1983` and the provider contract (`provider-capability-contract.md:175-181`, `:300-310`) explicitly keep AnySearch out of the provider fallback chain. `delegation.py` tests need changes only if launching the adapter becomes part of the dispatch contract; otherwise changing `main`/provider membership would violate the existing spec.
- Update `tests/test_regression.py:501-593` for new public/packaged documentation markers and continue comparing both copies. Keep `tests/test_sync_anysearch_skill.py:85-114` to prove private local files are preserved and add a negative assertion that central `config.json` is never copied into a bundled Skill tree.

#### Scope conflict to resolve before implementation

The current PRD says both macOS consumers should call one adapter while official Python/Node/Bash/PowerShell CLIs remain unchanged and Windows/Linux official CLIs are out of scope (`prd.md:21-30`, `:43-52`). The user requirement and this assignment ask for a cross-runtime contract audit and behavioral alignment. If the PRD remains authoritative, the four-CLI changes above become adapter tests only; if the user requirement supersedes it, all four runtimes and their mirrors require the changes above. The adapter file path is not present in the current tree, so it cannot be named more exactly without a design decision.

### 5. Risk register

- **Config types:** `Config._load_config_file` accepts only a top-level dict, but `get_saved_config` and `_get_config_value` stringify arbitrary non-null values (`config.py:196-225`, `:227-238`). A boolean/list/object in either AnySearch slot could otherwise become a truthy credential-like string. Require non-empty JSON strings for both slots.
- **Masking:** Smart Search masks known secret keys in normal saved-config output, but `config_list(show_secrets=True)` is an explicit raw path (`service.py:4485-4489`), and the four AnySearch CLIs print raw response `data` on single-call errors (`anysearch_cli.py:113-117`, `anysearch_cli.js:110-118`, `anysearch_cli.sh:163-174`, `anysearch_cli.ps1:117-125`). Invalid-response snippets can also include provider-echoed sensitive data. Never log authorization headers or an `auto_registered` payload containing a key.
- **Batch concurrency:** all four runtimes currently share one key across concurrent items, preserve order, and generally return exit success for partial item failures. A fallback implementation must be per-item and bounded, must preserve order, and must not mutate environment/config or race a shared client.
- **`auto_registered`:** documentation instructs agents to extract and save a returned key to `.env` (`SKILL.md:105-133`), but no executable implementation or exact envelope schema exists. This directly conflicts with a central config owner and is unsafe to automate.
- **Secret exposure through invocation:** `--api_key` is supported and can appear in process arguments or captured command diagnostics. Central-file lookup should be the normal path; the explicit flag should be treated as a one-shot override and never echoed.
- **Permissions:** the task PRD records a `0600` Smart Search config invariant (`prd.md:9-15`), but `_save_config_file` only opens/writes JSON and does not enforce mode (`config.py:204-210`). The implementation must verify/enforce the invariant at the chosen write boundary; the read-only adapter should fail closed rather than repair permissions.
- **Legacy `.env` copies:** ignored bundled `.env` files are preserved by sync/installer logic. Their contents were intentionally not read. If they remain a compatibility fallback, precedence must be explicit; if the central JSON is authoritative, stale `.env` values must not override it.

### Related specifications and external references

- `.trellis/workflow.md:7-11`, `:29-42` requires persisted research and task-scoped specs.
- `.trellis/spec/backend/provider-capability-contract.md:154-181`, `:307-310`, `:533-535`, `:653-705`, `:1384-1405` defines provider boundaries, machine-private AnySearch configuration, output/replay semantics, and public/packaged copy synchronization.
- `.trellis/spec/guides/code-reuse-thinking-guide.md:81-82`, `:178-189` supports a shared normalizer and parity regression for duplicated runtime mechanisms.
- Historical AnySearch acceptance scope was single-key and experimental (`.trellis/tasks/archive/2026-05/05-24-anysearch-acceptance-openai-streaming/prd.md:14-23`, `:31-40`); it is background, not an authority over the current task.
- External references: none consulted. Network access was explicitly prohibited. The internal sync script records the preferred source and official fallback ref (`sync_anysearch_skill.py:23-27`), but no external version or response schema was verified.

## Caveats / Not Found

- No real API key values were searched for, read, copied, or recorded. Existing ignored `.env` filenames were identified only as local-file boundaries; their contents were not inspected.
- No tests, live probes, Git operations, config writes, or network calls were run. This is an architecture audit, not implementation verification.
- No executable `auto_registered` handling, central AnySearch resolver, dual-key adapter, active `runtime.conf`, or provider-specific quota/auth error taxonomy was found in the requested scope.

### Implementation checklist

1. Resolve macOS-only adapter versus all-runtime parity scope and choose the new adapter location.
2. Define the exact two JSON key fields, strict string/type behavior, precedence against `.env`/environment/`--api_key`, and `0600` write boundary.
3. Implement one read-only path resolver matching override, Windows `LOCALAPPDATA`, macOS/Linux default, and Windows legacy fallback; avoid cwd fallback.
4. Define a stable key-specific 401/403 or quota error predicate and one bounded fallback attempt; explicitly reject generic 429/transport/parse/5xx switching.
5. Remove raw response-data/auto-registration secret exposure, then update source, generator/sync mirrors, docs, and the listed tests.
6. Run the synthetic cross-runtime gate only after fixing Node environment-name/base-URL parity and confirm no secret values appear in outputs or artifacts.

### Unresolved technical questions

- Does the requested cross-runtime behavior override the current PRD's macOS-only adapter and Windows/Linux out-of-scope clauses?
- What exact JSON envelope/code identifies a key-specific quota or rate-limit rejection, and is HTTP 401/403 guaranteed to be scoped to the supplied key?
- Should legacy `.env`/process environment remain a fallback for migration, and if so, should central JSON always win over it?
- Should both keys be required to be distinct/non-empty at config-write time, or may a single-key installation remain valid with anonymous/no-fallback behavior?
- Which component owns secure writes and permission enforcement for `config.json`: Smart Search config, the adapter, or an existing managed profile/runtime installer?
