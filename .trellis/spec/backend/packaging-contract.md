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

## Wrong vs Correct

```text
Wrong: add assets/skills/.../bundled-skills/anysearch/NEW.md
       → git add, commit, ship. The wheel drops it silently.

Correct: add the file, add "assets/.../NEW.md" to package-data,
         run tests/test_package_data.py + npm run check:skill-parity.
```
