# Implementation plan

## Phase 1: Contract and task context

1. Add this command, depth, routing, packaging, and test contract to the backend
   spec without duplicating the Research Workflow Reference.
2. Curate `implement.jsonl` and `check.jsonl` with only applicable spec and
   research/design context.
3. Start the Trellis task on `preview/multi-source-agentic-research` with
   `lwj_dev` as its integration base; do not touch Smart Search `main`.

## Phase 2: CLI and runtime contracts

1. Add one static service projection for workflows, depths, and advanced
   interfaces.
2. Add `smart-search modes` to argparse and the command dispatcher, reusing the
   existing format/output path.
3. Replace product-mode `quick` with `focused` in CLI choices, planner
   normalization, ResearchFrame validation, and current design artifacts.
4. Preserve unrelated lightweight diagnostic names and keep the compact
   `research` live execution pipeline unchanged.

## Phase 3: Skill progressive disclosure

1. Rewrite public `SKILL.md` as purpose, decision path, shared invariants, and
   Reference router.
2. Expand `research-workflow.md` with the complete focused/standard/deep
   capability and stopping contract plus the Root lifecycle currently repeated
   in the entrypoint.
3. Keep architecture/data mechanics in `agentic-research-architecture.md` and
   compact planner/executor behavior in `deep-research-mode.md`.
4. Remove `current-search-flow.md` and `cli-contract.md` from the governed Skill
   after migrating any unique stable mechanism to its actual owner.
5. Update READMEs and copy the entire public Skill tree to the packaged mirror
   through the repository's parity workflow.

## Phase 4: Verification and correction

1. Add focused unit/regression/package tests before running the full suite.
2. Run `quick_validate.py` on public and packaged Skills, parity, package-data,
   Python tests, tarball smoke, diff whitespace, and Trellis check.
3. Fix every in-scope failure. Isolate only failures reproduced on the clean
   pre-change baseline as unrelated.
4. Perform one adversarial read of the final CLI output and Skill routing tree.

## Phase 5: Integration and governed activation

1. Commit the verified preview change.
2. Integrate to `lwj_dev` in an isolated worktree, preserving its Trellis and
   branch-only changes; verify again. Leave Smart Search `main` unchanged.
3. Update personal `skill-packages/smart-search-cli` on personal `main`, then
   package-aware merge to `macos`, `oppo_windows`, and `oppo_linux`.
4. Refresh macOS immutable cache and Codex/Claude activation, then compare the
   source, native package, cache, and activation hashes.
5. Run task closeout and report commits, tests, activation, deferred native
   Windows/Linux checks, and the explicit no-push/no-release status.

## Implementation record

### Preview implementation

- Phases 1–3 completed on `preview/multi-source-agentic-research`.
- Added the offline `modes` projection and JSON/Markdown/content renderers.
- Replaced the public research depth value with
  `focused|standard|deep`; obsolete `quick` inputs are rejected by both CLI
  parsers and `ResearchFrame` validation.
- Reduced `SKILL.md` to 61 lines of routing and shared invariants. Moved the
  complete depth matrix, Root lifecycle, Preview source boundary, persistence,
  and finalization contract into `references/research-workflow.md`.
- Removed `current-search-flow.md` and `cli-contract.md` from both governed
  Skill trees. No host-specific Linux snapshot or private path was retained.
- Public and packaged Skill trees contain 29 byte-identical files.

### Verification evidence

- Focused contract suite: `335 passed`, then superseded by the final full run.
- Final full Python suite: `639 passed`.
- Fatal Ruff rules on changed Python/test files: passed. The repository-wide
  unrestricted Ruff run reports 163 pre-existing style findings and is not the
  project quality gate.
- `quick_validate.py`: public Skill valid; packaged Skill valid.
- `npm run check:skill-parity`: 29 files match.
- `NPM_CONFIG_USERCONFIG=/dev/null npm run smoke:tarball`: passed; the packed
  install now verifies `modes`, research depths, regression, and mock smoke.
- `git diff --check`: passed.
- `task.py validate 08-31-smart-search-workflow-routing`: passed with only the
  expected context-injection size warning for the large provider contract.

### Integration and governed activation

- Preview implementation commit:
  `55a38d4c211cce4bf1b9042622e0a6fb41437780`.
- Isolated `lwj_dev` integration commit:
  `70a425bea6c8316d4a73c0a731d5dbee541ed38f`. The integration retained the
  three `lwj_dev`-specific Trellis Agent files and passed the full `639`
  Python tests after installing the isolated sidecar dependencies.
- Smart Search `main` stayed at
  `ae02b4b02f79104460a4ebcfc2778f73911bda9d` throughout the task.
- Personal Skills common package commit:
  `2ff5310b2f44c045d878d8a5249efcbdcef6c50a` on `main`, sourced from
  `preview/multi-source-agentic-research@55a38d4c`.
- Profile-aware native commits:
  `macos@5345599f297b247c4e2261ba163d14dcc8424423`,
  `oppo_windows@f50937902faa99426c03142a144d5d6f572e2859`, and
  `oppo_linux@fbc3087573bcce16f72894a56fa699724610c3c8`.
  macOS and Windows merged without conflicts. Linux surfaced conflicts in
  `SKILL.md` and `README.md`; the final `SKILL.md` uses the common router while
  Linux profile/config/artifact adaptations remain only in its package README.
- Personal-package `quick_validate.py` passed on main and all three native
  packages. Package-aware merge tests passed (`8 tests`). The global personal
  management validator's profile/catalog skill-set mismatch was reproduced
  unchanged on the pre-update `5444eeec` baseline, so it remains an unrelated
  repository warning rather than an in-scope failure.
- The stale workspace manifest still selected archived `partner-skill` for
  four managed targets. Removing only those generated activation entries made
  `validate-global` and `preview-global` pass; `sync-global` then rebuilt the
  governed targets. QMD was not refreshed because no inventory or notebook
  content changed.
- macOS immutable cache commit and governed source commit both equal
  `5345599f297b247c4e2261ba163d14dcc8424423`. Source, cache, Codex, and Claude
  `SKILL.md` SHA-256 are all
  `cf2b6c4fcf478b87e176962a3e38b82115eaaddfc583950e55e7c3d7bdf8ea0e`;
  their `research-workflow.md` SHA-256 values are all
  `322f7ee564243bb997c4f81d92fbf5c11b8823fddeabc3cb7654cf195a898604`.
- Post-activation `validate-global` and cached-Skill `quick_validate.py`
  passed. `modes` JSON/Markdown, the focused planner contract (two
  decomposition items, four steps, fetch retained), and obsolete `quick`
  rejection with exit code 2 passed against the Preview source entrypoint.
- One real Preview-source `search` completed in 16.4 seconds with `ok=true`,
  non-empty content, and one source. No `doctor` probe was run during this
  task.
- No branch was pushed or tagged, and no package was published or released.

Phase 5 is complete. Task archival and the Trellis session journal are the
remaining closeout operations.
