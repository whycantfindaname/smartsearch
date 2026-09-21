# Smart Search desktop protocol v1

Both native clients implement this contract. The Python core owns configuration,
validation, routing and status. Do not open an HTTP listener or invoke a shell.

Launch bundled `backend/smart-search.exe --desktop-backend` on Windows;
`Contents/Resources/backend/smart-search --desktop-backend` in the macOS bundle.
For development an explicitly selected backend path may override this location.
Redirect UTF-8 stdin/stdout/stderr; keep the console hidden on Windows. Each stdin
and stdout line is one compact JSON object. stderr is diagnostic, never protocol.

Request: `{"id":1,"method":"initialize","params":{"protocol_version":1}}`.
Response: `{"id":1,"result":{...}}` or
`{"id":1,"error":{"code":"parameter_error","message":"..."}}`.
Events: `{"event":"activity","data":{...}}`,
`{"event":"run","data":{"run_id":"...","status":"finished","result":{...}}}`.
IDs are positive integers and each request receives one response. Each process has
a new `generation` UUID; discard data from a previous client/process generation.
Methods below return result objects. Ordinary business errors have `ok:false`.

| Method | Parameters | Result |
| --- | --- | --- |
| `ping` | `{}` | `protocol_version`, `version`, `generation` |
| `initialize` | `protocol_version:1`, optional absolute `config_dir`, `app_version`, `lang:auto\|zh\|en`, `enable_update_checks:true` for production native clients | full state below |
| `language.set` | `lang:auto\|zh\|en` | refreshed state; refuses changes during environment writes or CLI updates |
| `get_state` | `{}` | full state, local/read-only |
| `profile.select` | absolute `config_dir` | full state |
| `config.preview` | `set` object, `unset` key array | `ok`, `minimum_profile_ok`, `missing`, `capability_status` |
| `config.apply` | `set`, `unset`, `revision` from state | `ok`, `error`, `error_type`, refreshed `status` |
| `provider.test` | `provider`, `overrides` containing ONLY actual edited values (not masked placeholders) | `ok`, `run_id`; completion via run event/result |
| `run.start` | `command` catalog id, `arguments` string array (arguments following the command) | `ok`, `run_id` |
| `run.cancel` | `run_id` owned by this backend | `ok`, `status:"cancelling"`; wait for terminal event |
| `run.result` | `run_id` | `ok`, `run_id`, `status`, `result` or null |
| `providers.reset` | optional `providers` id array | `ok`, `cleared` |
| `skills.status` | optional `targets` id array | `ok`, `targets` array |
| `skills.install` | nonempty `targets` array | `ok`, `run_id` |
| `skills.catalog` | `{}` | all Agent targets compared with verified stable Skills or clearly labelled bundled/cache fallback; `source`, `cached`, `targets`, `cli_version`, `compatibility`, `plan_id`, `can_sync` |
| `skills.check` | `{}` | check and cache official npm stable Skills; completion via `skills` event; never writes Agent directories |
| `skills.auto` | `enabled` boolean | persisted daily Skills check preference; no automatic installation |
| `skills.sync` | `confirm:true`, nonempty `targets`, `plan_id` from catalog | explicit backup and sync; completion via `skills` event with `result.installed` (paths and backups) / `result.failed` |
| `activity.list` | optional absolute `directories` array, `limit` 1..1000 | `ok`, `runs`, `errors`, `enabled` |
| `activity.clear` | `{}` | `ok`, clears completed metadata only |
| `activity.enabled` | `enabled` boolean | `ok`, `enabled` |
| `activity.details` | `run_id`, optional absolute `config_dir` | `ok`, `run`, metadata-only `events`, `events_truncated` |
| `cli.status` | `{}` | `bundled_path`, `external_path`, `version`, external version or null |
| `cli.enable` | `confirm:true`, sent only by explicit user action | `ok`, `path`, `message`; refuses command conflicts |
| `environment.status` | `{}` | current environment snapshot without probing or network |
| `environment.check` | `{}` | starts read-only local discovery; completion via `environment` event |
| `environment.verify` | `{}` | starts local Node/independent-engine checks; no repair or provider/AI request |
| `environment.install` | `confirm:true`, `plan_id` from detection, `targets` (`codex`/`claude`), optional `replace_modified:false` | starts the checked plan; completion via `environment` event |
| `environment.cancel` | `{}` | cancels only the cancellable download stage; package-manager writes are not force-cancelled |
| `app.update-check` | `{}`; explicit manual check | update state immediately; completion via `updates` event |
| `updates.state` | `{}` | latest update state (no network) |
| `updates.auto` | `enabled` boolean | save automatic-check preference, return update state |
| `updates.download` | `{}`; explicit click | pinned compatible package download; state/events report bytes and SHA256 verification |
| `updates.cancel` | `{}` | cancel the package download; terminal event follows |
| `updates.installer` | `{}`; explicit install/open click | reverified absolute installer `path`, `version`; refuses active owned runs/CLI update |
| `cli.update` | `confirm:true`, exact checked `version` | call only the identified npm/mise manager; terminal event includes actual version and bounded sanitized log |
| `shutdown` | `{}` | `ok`; cancels own work and exits |

`run.start` catalog identifiers can include subcommands, e.g.
`model/current`. `diagnose` selects its provider via its catalog fields. Arguments do not repeat command
tokens. A secret configuration mutation uses `config.apply`, not CLI arguments.
`provider.test` tests a snapshot of the effective configuration at click time,
merged with any actual edits. No configuration or health changes are persisted.
Its completion scope is `current` when overrides are empty and `draft` when edits
are supplied. UI labels say “测试” or “用未保存的修改测试” accordingly.

Full state extends `smart_search.ui_api.state()`:

- `ok`, `values` (masked effective values), `saved_values` (masked file values),
  `sources` (`environment/config_file/default`), `revision`, `config_path`;
- `minimum_profile` (`ok/required/missing`), `capability_status`,
  `capability_chains`, `provider_health`, `provider_profiles`, `probe_kinds`;
- `provider_checks`: last in-memory test per provider for this App session, with
  `status/checked_at/source/scope/probe/message`. Scope is `current` or `draft`, and a draft
  test must never be described as a verified saved configuration. No entry means
  not tested during this session; cooldown `closed` alone is not a successful probe.
- `metadata.fields`: key, section, tier, kind, label_zh/en, help_zh/en, default, placeholder,
  choices, provider, capabilities, key_url, docs_url; sections include
  getting_started, providers, routing, reliability, diagnostics. Consume
  `metadata.sections` order, label_zh/en and blurb_zh/en instead of alphabetic ordering;
- `skill_targets`: id, label, default;
- `protocol_version:1`, `version`, `generation`, `config_dir`, `cli`, `updates`, `environment`, `skills`,
  `commands` (catalog below), `activity` (activity.list result).

Catalog entry: `id`, `label`, `description`, `experimental`, `fields`.
Field: `name` (argparse dest), `label`, `help`, `flags` (empty for positional),
`kind` (`text/int/float/bool/choice`), `choices`, `required`, `default`, `multiple`.
Send positionals in catalog order; optional values as flag then value; checked
boolean flags as a standalone flag; repeated values repeat the flag. Do not send
empty optional fields. Forms can show advanced parameters in an expander.
Commands already represented by config/skills/provider UI are not duplicated in
the ordinary tool catalog. CLI compatibility does not require arbitrary shell UI.

Activity run fields: `run_id`, `command`, `origin` (`app/cli`), `config_dir`,
`version`, `pid`, `status` (`running/finished/failed/cancelled/stale/interrupted`),
`phase`, `provider`, `model`, `started_at`, `updated_at`, `finished_at`,
`elapsed_ms`, `error_type`, `exit_code`, `sources_count`, `sequence`, `config_revision`.
Timestamps are Unix seconds. Live rows update at least every two seconds when
events arrive; duration may tick locally, but never fabricate percent complete.
No request arguments, query, content, headers or credentials are in the journal.
`config_revision` in an activity row is an opaque identifier for that invocation's
frozen snapshot, not a hash of secret values or the optimistic-save revision.

Editing rules: empty untouched or erased secret input means KEEP; an explicit
Clear control adds the key to `unset`; entering a replacement adds `set[key]`.
Read-only environment fields show the masked effective value and its source.
Save sends the displayed revision; conflicts keep the draft and offer refresh.

Native UI destinations: Overview, Providers, Search & Research, Activity,
Update Skills, Settings & About. Use native controls/theme/keyboard/focus.
Current results render readable content and sources, with JSON in an advanced
expander and explicit copy/export. Never make raw JSON the primary UI.
Business `result.display_text` reuses the existing CLI Markdown formatter, keeping
plans, lists, diagnostics and sources readable without a second native formatter.
This additive desktop-only field is not added to public CLI JSON output.
Close with own active work offers background/stop-and-quit/return. Background
has a tray/menu-bar entry. Never terminate external CLI processes.

Update state contains `checking/auto_check/last_attempt/last_success/error`,
independent `app` and `cli` checked versions, `download` and `cli_update` states.
The backend emits `updates` when these change. Automatic checks require native
handshake opt-in, run at startup when due and at most once per 24 hours, and stop
with the App. Checking never downloads or installs. Cached results retain their
time and errors; package actions require successful fresh metadata.

Only stable official GitHub assets matching the system and architecture with a
SHA256 are downloadable. The pinned asset includes ID/version/size/hash; streamed
bytes go to a temporary file and rename only after verification. `ready` means
downloaded, not installed. Hash verification is not system code signing. Windows
handles drafts and owned tasks, stops its backend and releases the installer
presence mutex before opening the verified Inno installer and exiting; macOS opens
the verified DMG and explains normal installation. Neither replaces files itself.

`cli.status` and full refresh re-resolve the effective entry. Ownership fields
include `manager/manager_label/can_update/resolved_path/update_note`; unknown,
project, ambiguous, or unsupported constrained installations remain manual.
CLI updates use the original manager with an exact checked version, no shell or
bulk upgrade. The frontends prevent quit/reconnect during the manager operation;
no forced cancellation or rollback is promised. Readback must confirm the target
effective version before `cli_update.status` becomes `finished`.

Environment snapshots/events contain `status`, `busy`, `can_cancel`, `message`,
`error`, bounded sanitized `log`, `steps`, `node`, `python`, `cli`, `targets`,
`plan`, `plan_id`, `can_install`, `blocked`, `checked_at`, `tools_dir`, `config_dir`
and a shell-quoted `invocation` for the user's AI test instructions. Download
stages add actual `received`/`total` bytes. `ready` means the operation ended;
each step and target must still be inspected. It never means an AI has invoked
the skill. Files, installed AI commands, local engine execution and provider
configuration are distinct facts. Checks do not run legacy auto-repair wrappers.

New runtimes and the npm prefix live in `%LOCALAPPDATA%/SmartSearchTools` or
`~/.local/share/smart-search-tools`, outside the App bundle. Their manifest stores
only independent paths, not secrets. AI skills invoke that independent Node/npm
installation with absolute paths; no App executable or running App is required.
Windows publishes only the new installation's user PATH entries and preserves
existing entries; already running clients require a refreshed environment. A
sibling node.exe makes the npm shim independent of another Node earlier in PATH.
macOS GUI clients use the absolute invocation without modifying shell profiles.

Codex user skills use `.agents/skills`, with `.codex/skills` reported as a legacy
location; Claude uses `.claude/skills` or its explicit `CLAUDE_CONFIG_DIR`. Changed
skill files are kept unless replacement was explicitly chosen; replacement first
backs up the old tree and preserves extra files. Installation is checked again
against `plan_id` before mutation. Environment writes exclude competing CLI/App
updates, skills writes and profile switching; clients keep the operation busy
across page changes and guard exit/reconnect until its actual terminal event.

## Agent Skills updates

Skills state has `auto_check`, `last_attempt`, `checking`, `busy`, `source`
(`version`, `checked_at`, `integrity`, `url`), `cached`, `error`, all `targets`,
`cli_version`, `cli_ready`, `compatibility`, `plan_id`, `can_sync`, and `result`.
Automatic checks use the production handshake opt-in and the independent daily
Skills preference. They download only official npm data, with SHA512 and bounded
archive validation; no lifecycle script or package code runs. A failed check keeps
old installations and labels previous data as cached. Sync requires a successful
check in this session and a verified independent CLI at least as new as the source.
The confirmed fingerprint is rechecked against the current source, target files
and CLI invocation. Skills writes exclude environment/CLI updates, language and
profile changes; closing waits for the writer. Existing `skills.status/install`
remain compatible bundled-source APIs; native clients use the new stable-source
methods and pass no Skill targets to `environment.install`.

Every target uses the shared registry/path resolver, including Cline and Roo Code.
Managed local invocation notes are composed consistently and recognized by the
generic CLI comparator. Explicit sync backs up changed trees, atomically replaces
files, preserves extras and refuses linked paths. `stale` means content differs,
not an Agent software version or proof that its Skill is loaded. Clients keep
selection across refresh, show changed filenames and backup paths, and instruct
users to reload the Agent before testing real invocation.

## Interface language

Native clients resolve their independent App preference and pass `lang` at initialize.
Legacy protocol v1 clients omitting it keep Chinese presentation. State includes the
resolved `language`. `language.set` refreshes local metadata without reconnecting,
restarting tasks, changing CLI preferences or making provider requests. Subsequent
status events render owned message templates in the current App language. Completed
results and task input snapshots retain their original contents. JSON keys, status
codes, provider/model IDs and upstream/user content remain unchanged. Raw third-party
errors are redacted but not translated by matching their text against a dictionary.
