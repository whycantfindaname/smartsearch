# Validate Trellis Codex lifecycle

## Goal

Disposable lifecycle validation for CodeStable retirement evidence.

## Requirements

- Validate the repository-local Codex Trellis platform without changing user-level Codex or Infra configuration.
- Exercise task planning, context validation, session activation, hook context resolution, finish, and archive.
- Preserve the archived disposable task as migration evidence and disable archive auto-commit.

## Acceptance Criteria

- [ ] `task.py validate` accepts curated implement/check context.
- [ ] The Codex workflow hook resolves this task while it is active.
- [ ] `task.py finish` clears the session pointer and `archive --no-commit` records completion.

## Notes

- This is a disposable, lightweight validation task created by the CodeStable migration task.
