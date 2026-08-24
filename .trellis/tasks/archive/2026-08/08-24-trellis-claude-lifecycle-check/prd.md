# Validate Trellis Claude lifecycle

## Goal

Disposable lifecycle validation for CodeStable retirement evidence.

## Requirements

- Validate the repository-local Claude Trellis platform without changing user-level Claude or Infra configuration.
- Exercise task planning, context validation, session activation, hook context resolution, finish, and archive.
- Preserve the archived disposable task as migration evidence and disable archive auto-commit.

## Acceptance Criteria

- [ ] `task.py validate` accepts curated implement/check context.
- [ ] The Claude workflow hook resolves this task while it is active.
- [ ] `task.py finish` clears the session pointer and `archive --no-commit` records completion.

## Notes

- This is a disposable, lightweight validation task created by the CodeStable migration task.
