# Integrate smart-search PR fixes and beta release

## Goal

Integrate GitHub PRs #12, #13, and #14 into a repo-owned branch, resolve their overlapping skill-documentation contracts, run full regression, publish the next beta from `main`, upgrade the local `smart-search` installation to that beta, and reply to each PR with the final integration outcome.

This task exists because the three PRs are individually useful but overlap in user-facing contracts:

- #12 fixes Deep Research runtime evidence output so omitted `--evidence-dir` uses the platform temporary directory instead of `C:/tmp`.
- #13 fixes npm wrapper repair guidance so failed runtime repair recommends stable reinstall, not `@next`.
- #14 splits the large `smart-search-cli` skill reference into focused files, but its docs must be reconciled with #12 so public skill docs, packaged skill docs, tests, and runtime behavior all describe the same default evidence directory.

## Requirements

R1. Use a repo-owned integration branch named `codex/integrate-smartsearch-prs-beta`; do not merge the three contributor PR branches directly into `main`.

R2. Preserve #12 runtime behavior: `smart-search deep` default `evidence_dir` must be generated under `tempfile.gettempdir()/smart-search-evidence/<timestamp>-<slug>`.

R3. Preserve #13 npm repair guidance: runtime repair failures must recommend `npm install -g @konbakuyomu/smart-search` and must not recommend `@next`.

R4. Preserve #14's skill reference split while fixing its docs/code mismatch: the public skill tree and packaged skill tree must stay synchronized, and the new reference files must clearly say that default Deep Research output uses the platform temp directory while explicit `--evidence-dir PATH` is preserved.

R5. Keep README examples clear: examples may show explicit stable output paths, but they must not imply `C:/tmp` is the runtime default.

R6. Run source, CLI, packaging, and release regression checks before pushing.

R7. Push the integrated result to `main` only after checks pass, allowing the existing GitHub Actions beta publish workflow to create the next `next` prerelease.

R8. After publish succeeds, upgrade the local mise-managed `smart-search` installation to the new beta and verify the bare command resolves to that beta.

R9. Reply separately on PRs #12, #13, and #14 using GitHub comments, explaining exactly what was accepted and how it was integrated.

R10. Do not touch the existing `00-bootstrap-guidelines/` task except for observing that it exists.

## Acceptance Criteria

- [ ] Task planning artifacts exist: `prd.md`, `design.md`, and `implement.md`.
- [ ] Task status is moved from `planning` to `in_progress` only after planning artifacts are written.
- [ ] Branch `codex/integrate-smartsearch-prs-beta` contains the integrated PR changes and the #12/#14 contract reconciliation.
- [ ] Public and packaged `smart-search-cli` skill files are byte-for-byte synchronized for all markdown/YAML skill assets.
- [ ] Deep Research default evidence directory is absolute, under the platform temporary directory, and reflected in the command/output contract.
- [ ] Wrapper repair tests prove the reinstall hint uses stable `@konbakuyomu/smart-search` and excludes `@next`.
- [ ] Required source regression passes:
  - `.\.venv\Scripts\python.exe -m compileall -q src tests`
  - `.\.venv\Scripts\python.exe -m pytest -q`
  - `node npm/scripts/test-wrapper-repair.js`
  - `npm pack --dry-run`
  - `git diff --check`
- [ ] Required CLI regression passes:
  - `.\.venv\Scripts\python.exe -m smart_search.cli regression`
  - `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json`
  - `.\.venv\Scripts\python.exe -m smart_search.cli deep "Deep research default evidence directory" --format json`, with `evidence_dir` under the platform temporary directory.
- [ ] Integration branch is merged or fast-forwarded into `main`, pushed to `origin/main`, and the beta publish workflow succeeds.
- [ ] `npm view @konbakuyomu/smart-search dist-tags versions --json` shows `next` advanced from `0.1.14-beta.6` to the new expected beta.
- [ ] Local mise install is updated with `mise use -g "npm:@konbakuyomu/smart-search@<new-beta>" -y --pin`, followed by `mise reshim`.
- [ ] `where.exe smart-search` and `smart-search --version` prove the local bare command hits the new beta.
- [ ] Packaged CLI smoke passes after local upgrade:
  - `smart-search regression`
  - `smart-search smoke --mock --format json`
- [ ] GitHub comments are posted on PR #12, #13, and #14.

## Notes

Known starting point:

- Current `origin/main` / local `main` is `a8bcab8`, tagged `v0.1.14-beta.6`.
- Current npm `next` is expected to be `0.1.14-beta.6`; the next main push is expected to publish `0.1.14-beta.7` unless another beta lands first.
- PR heads fetched for review:
  - #12: `WilliamTrouvaille:fix/deep-evidence-dir`
  - #13: `WilliamTrouvaille:fix/wrapper-repair-install-tag`
  - #14: `WilliamTrouvaille:refactor/smart-search-cli-skill-references`
