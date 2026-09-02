# Packaging & Distribution Contract

> This contract applies when adding or moving files under `src/smart_search/assets/`, changing `package.json` `files` or `[tool.setuptools.package-data]`, bumping versions, or refreshing the bundled AnySearch Skill snapshot. The project ships through three surfaces that must stay in sync; each has an executable guard.

---

## The Three Surfaces

| Surface | Manifest | Consumed by |
| --- | --- | --- |
| npm tarball | `package.json` → `files` | npm users (`postinstall.js` bootstraps a venv and pip-installs the source tree) |
| wheel | `pyproject.toml` → `[tool.setuptools.package-data]` (+ discovered package modules) | `pip install .` and the npm postinstall venv |
| installed skill files | `skill_installer.py` (`_load_skill_files`, prefers `importlib.resources`), managed via `smart-search skills update --targets ...` | the user's AI tool skill directories (`~/.codex/skills`, `~/.claude/skills`, ...) |

Key consequence: **the wheel path feeds npm users too.** A file missing from
package-data is missing from the installed skill files even though `git` and
the npm tarball both have it.

## Contract 1: Every bundled asset must be wheel-reachable

Every file under `src/smart_search/assets/` must either (a) match a
package-data glob, (b) be a package module (a parent chain of `__init__.py`
files), or (c) be a machine-local name that must never ship (see Contract 2's
exclusion set).

Guard: `tests/test_package_data.py` fails with the exact uncovered paths.

Known failure that motivates this contract: `bundled-skills/anysearch/CONTRACT.md`
existed on disk and in the tarball but had no package-data pattern → every
pip-installed copy of the bundled skill was broken. When adding any bundled
file, add the matching package-data line in the same change.

## Contract 2: Public skill tree must byte-match the packaged mirror

`skills/smart-search-cli/` ↔ `src/smart_search/assets/skills/smart-search-cli/`,
byte-identical, excluding `__pycache__`, `*.pyc`, and the machine-local names
`config.json`, `.env` (stripped from the tarball by `package.json` exclusions;
`runtime.conf` is additionally preserved by the sync script and never copied
into the bundled skill).

Guard: `npm run check:skill-parity`. Refresh the bundled AnySearch Skill
snapshot only via `scripts/sync_anysearch_skill.py` (it preserves
machine-local names and the Smart Search adapter overlay — see its
`PRESERVED_NAMES` and overlay lists).

## Contract 3: Tarball content is pinned

`npm run smoke:tarball` (`npm/scripts/smoke-packed-install.js`) asserts exact
file/prefix rules: required entries present, and `.env`, `runtime.conf`,
`__pycache__`, and the retired nested `bundled-skills/anysearch/SKILL.md`
absent. Update both sides of an assertion together — adding a file to `files`
without the smoke check (or vice versa) is a silent drift.

## Contract 4: Versions move together

- `package.json` = `pyproject.toml` = `package-lock.json` `packages[""].version`.
- Bump via `npm version ...` (the `version` npm script runs
  `sync-python-version.js`) or `npm run set-version`.
- `sidecar/pyproject.toml` is intentionally independent at `0.1.0`, but the
  two copies (`sidecar/` and `src/smart_search/assets/sidecar/`) must stay
  byte-identical — `tests/test_sidecar_packaging.py` enforces it.

## Scenario: managed delivery handoff

### 1. Scope / Trigger

Use this handoff when the repeatable way to produce, install, identify, or
verify the Smart Search release artifact changes. Ordinary product tests,
lint, architecture notes, and Trellis task state do not trigger it.

### 2. Signatures

The portable contract lives at `.jason-liao-agent-infra/managed-project.json`
with schema `jason-agent-infra.managed-delivery-workflow.v2`. Its release
readiness commands are `python3 scripts/managed_sync.py inspect`,
`npm run --silent check:skill-parity`, and
`npm run --silent smoke:tarball`; explicit live acceptance is
`python3 scripts/managed_sync.py verify-live`.

### 3. Contracts

- `.jason-liao-agent-infra/RUNBOOK.md` is the human delivery handoff and
  `errors.md` is the stable delivery-error catalog; the colocated `README.md`
  is only a bounded migration bridge.
- Release readiness proves a clean authority checkout, public/packaged Skill
  parity, and behavior of a temporary packed install. It does not publish,
  activate a host runtime, or perform a provider request.
- Skills propagation and platform activation remain owned by their Infra/Skills
  profiles. Provider/request recovery remains in the Skill reference catalog.

### 4. Validation & Error Matrix

| Condition | Required result |
| --- | --- |
| public and packaged Skill trees differ | stop before packed smoke; use `SS_SYNC_SKILL_PARITY_DRIFT` |
| packed install misses a declared file or behavior | stop publication; use `SS_SYNC_PACKED_SMOKE_FAILED` |
| contract is changed but not committed | Infra sync rejects the stale contract before running stages |
| provider gate is absent during explicit verification | retain pending live state; use `SS_VERIFY_EXTERNAL_GATE_MISSING` |

### 5. Good / Base / Bad Cases

- Good: update both Skill surfaces, run parity and packed smoke, commit the
  contract, then hand the producer commit to the downstream updater.
- Base: a source-only refactor with no artifact or delivery change stays in
  the normal project test/Trellis workflow.
- Bad: mark a listening provider or a local dirty tree as a published release,
  or copy a platform path into the portable contract.

### 6. Tests Required

- Run `npm run --silent check:skill-parity` and
  `npm run --silent smoke:tarball` for every release-readiness contract change.
- Run the focused release suite (`tests/test_release_workflow.py`,
  `tests/test_package_data.py`, and `tests/test_regression.py`) when packaging
  files or behavior changes.
- Run explicit live verification only with the selected platform's external
  gates and never retry its bounded probe loop.

### 7. Wrong vs Correct

Wrong: update `skills/smart-search-cli/SKILL.md`, skip the packaged mirror,
and let a later platform activation discover the drift.

Correct: keep both Skill surfaces byte-identical, pass the artifact gates,
commit the contract, and report platform/live states only from their own
independent owner and probe.

## Wrong vs Correct

```text
Wrong: add assets/skills/.../bundled-skills/anysearch/NEW.md
       → git add, commit, ship. The wheel drops it silently.

Correct: add the file, add "assets/.../NEW.md" to package-data,
         run tests/test_package_data.py + npm run check:skill-parity.
```
