# Add accepted Agentic Research terminology

## Goal

Add the seven user-approved Agentic Research concepts to the Smart Search
project termbase as accepted project terminology.

## Requirements

- Add `Project Agent`, `Search Scout`, `Evidence Miner`,
  `Provider Research Agent`, `ResearchRun`, `Research Workspace`, and
  `Research Trace` to `.terminology/termbase.json`.
- Preserve the exact English technical names and define their project-specific
  scope in Chinese.
- Record `Native Research` as a deprecated name for
  `Provider Research Agent`.
- Keep all entries project-scoped; do not modify or propose global terminology.
- Do not change product behavior or unrelated documentation.

## Acceptance Criteria

- [x] The termbase contains ten unique accepted concepts: the existing three
      entries plus the seven approved additions.
- [x] Each new concept has a stable ID, definition, scope note, preferred
      English label, project evidence, and a 2026-08-25 check date.
- [x] `Native Research` is deprecated and is not an accepted preferred label.
- [x] The language-system project termbase validator passes.
- [x] The repository worktree contains no unrelated changes before commit.

## Notes

- This is a lightweight, data-only terminology update. No design or
  implementation plan is required.
