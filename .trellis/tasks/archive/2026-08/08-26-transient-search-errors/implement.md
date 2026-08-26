# Implementation plan

## 1. Establish isolated branch workspaces

- Record the current heads and clean/dirty state of all Smart Search and
  personal Skills worktrees.
- Keep the existing preview worktree in place and create isolated worktrees for
  Smart Search `main` and `lwj_dev`.
- Stop if unrelated tracked changes overlap any target file.

## 2. Implement and test on Smart Search `lwj_dev`

- Keep Smart Search `main` read-only and exactly aligned with its remote main
  ref; it is the implementation baseline, not a commit target for this task.
- Add HTTP `499` / `request_cancelled` provider classification and network-class
  CLI exit handling in `lwj_dev`.
- Generalize the logical retry decision to cover only xAI terminal `504` and
  OpenAI-compatible `429 concurrency_limit_exceeded`.
- Make the search loop honor `--max-try`; standardize defaults at `120/5`.
- Add structured recovery metadata and Markdown rendering for exhausted
  concurrency and cancellation.
- Make `references/error-recovery.md` the single extensible recovery catalog;
  keep `SKILL.md` and other references as short links to it rather than copying
  the matrix into several documents.
- Update both bundled Skill copies and keep them identical.
- Add provider, CLI, help/default, Markdown/JSON recovery, and Skill-parity
  tests.
- Run targeted tests, then the branch-supported full Python suite and
  `git diff --check`.
- Commit the focused `lwj_dev` change.

## 3. Integrate into preview

- Merge updated `lwj_dev` into
  `preview/multi-source-agentic-research` in the existing worktree.
- Preserve preview-only research runtime, sidecar, terminology, visualization,
  and bundled AnySearch assets.
- Reconcile the preview Skill text with the single `error-recovery.md` catalog
  and preserve preview-only Skill references.
- Run targeted tests, preview's full supported suite, Skill parity, and
  `git diff --check`.

## 4. Synchronize the governed personal Skill

- Run the read-only macOS adaptation audit before changing global Skill source.
- Update `main:skill-packages/smart-search-cli` from the clean Smart Search
  `lwj_dev` commit, preserving documented personal portability adaptations.
- Update provenance to the exact source commit and commit personal Skills
  `main`.
- Preview, apply, validate, and commit package-aware merges for `macos`,
  `oppo_windows`, and `oppo_linux` using only `smart-search-cli`.
- Do not push any branch.

## 5. Refresh and verify the active macOS Skill

- Run the governed macOS projection/apply command for the selected profile.
- Verify the package, immutable cache, `~/.codex/skills/smart-search-cli`, and
  `~/.claude/skills/smart-search-cli` resolve to the same refreshed content.
- Run `smart-search skills status` only as an npm-bundle comparison; do not use
  it to overwrite the governed personal adaptation.
- Run one `doctor` probe and one controlled mock/targeted CLI check. A live
  provider search is optional evidence only if the service is available; a
  transient upstream failure is reported rather than hidden.

## 6. Quality check and closeout

- Run the Trellis check phase against the final diffs and acceptance criteria.
- Update the backend error/provider spec only if the implementation establishes
  a durable repository rule not already captured.
- Commit/archive the Trellis task and record the session.
- Report branch commits, tests, activation/hash evidence, live evidence, and
  the explicit fact that no push/tag/release occurred.

## Review gates and rollback points

- Gate A: do not leave the read-only `main` baseline until it is clean and
  equal to its remote main ref.
- Gate B: do not sync the personal Skill until `lwj_dev` and preview pass their
  branch-appropriate suites and the read-only `main` baseline is verified
  clean/equal to `origin/main`.
- Gate C: do not refresh active runtime projections until all four personal
  Skills branches are committed and clean.
- On a merge conflict, resolve only named target files and re-run that branch's
  tests. Abort the merge if unrelated branch content would be overwritten.

## Completion evidence (2026-08-26)

- Smart Search `main` remained read-only and clean at
  `ae02b4b02f79104460a4ebcfc2778f73911bda9d`, equal to `origin/main`.
- Smart Search `lwj_dev` committed
  `ef3af983729219e8a3a31428bf1f51049467d4fe`; its full suite passed with
  `450 passed`, and Skill parity verified 11 files.
- Smart Search `preview/multi-source-agentic-research` integrated the change in
  `de038a41573f3e8fb5fce5d308dbb277fab3abd7`; its full suite passed with
  `572 passed`, and Skill parity verified 30 files.
- Governed personal Skills commits: `main`
  `30515399e41c4d8634f45abb5aba600de08c3b38`; `macos` final
  `9c96c6c2dcb4ee37cf17177ca16769416702b2bd`; `oppo_windows` final
  `764470724e632e3546108a7edbee432d3ca11e45`; `oppo_linux` final
  `6dbcd1efbce8ba861393d0b786e19c037ad638d2`.
- The governed macOS source, immutable cache, Codex projection, and Claude
  projection all resolved to the same `SKILL.md` SHA-256:
  `a411907d649aa92bb46cfc620643fb1b7628dde9f00518f4a3aa192a6656b90f`.
- The one allowed doctor probe was healthy; one fresh live search succeeded
  with `logical_attempts=1`, `logical_retry_max_attempts=5`, and no replay.
  Raw output: `/tmp/smart-search-live-20260826.json`.
- No push, tag, or release was performed.
