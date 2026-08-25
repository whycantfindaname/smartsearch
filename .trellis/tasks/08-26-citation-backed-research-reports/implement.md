# Implement citation-backed research reports

## Preconditions

- [ ] The user has approved the final planning summary after these artifacts
      were written.
- [ ] The concurrent `08-26-stage-g-reference-index` task has finished or its
      remaining edits are confirmed non-overlapping.
- [ ] Current branch, worktree status, active Trellis task, and the matching
      Smart Search Skill source/mirror topology have been re-read.

## Implementation

1. [ ] Add citation-marker parsing and deterministic source grouping around the
       existing final-citation verification path.
2. [ ] Return rendered Markdown, the reference register, and the unchanged
       authoritative backtrace from `research-run verify`.
3. [ ] Persist the register and new manifest entrypoint atomically with the
       finalized report and verification output.
4. [ ] Update the visualizer to distinguish report References, the audit
       register, and the Workspace document index.
5. [ ] Update the public Skill source, packaged mirror, architecture reference,
       CLI documentation, README/STRUCTURE surfaces that describe Workspace
       output, and release parity expectations.

## Focused validation

6. [ ] Test first-appearance numbering, repeated citations, source
       deduplication, missing bibliographic fields, and multiple locators.
7. [ ] Test unknown markers, conflicting mappings, invalid locators,
       candidate-only inputs, atomic failure, and legacy materialization.
8. [ ] Parameterize the report contract over `quick`, `standard`, and `deep`.
9. [ ] Test CLI JSON/Markdown output, Workspace manifest/register projection,
       visualizer summary, and Skill source/package parity.

## Quality gate

10. [ ] Run the focused research runtime, Workspace, CLI, visualizer, E2E, and
        release-workflow tests.
11. [ ] Run the repository's full Python suite, `npm test`, package smoke,
        Markdown links, terminology checks, secret scan, and `git diff --check`.
12. [ ] Inspect one generated Workspace report as a reader and its register as
        an auditor; prove that every displayed citation resolves and no internal
        IDs leak into the human References section.
13. [ ] Run a fresh Trellis check, update reusable specs only if implementation
        established a durable convention, then prepare focused commits. Push or
        activation requires separate explicit authorization.

## Rollback point

- Revert the additive renderer, register projection, docs, and tests together.
  Existing Workspaces require no rewrite; verify one legacy Workspace remains
  readable after rollback.
