# Trellis Platform Lifecycle Validation

Date: 2026-08-24

## Scope

Validate the repository-local Codex and Claude Trellis platform projections before retiring CodeStable. The check did not modify user-level Codex, Claude, or Infra configuration and did not create a Git commit.

## Shared Preconditions

- `trellis platforms` reported both `Claude Code (.claude)` and `Codex (.codex, .agents/skills)`.
- `python3 .trellis/scripts/get_developer.py` returned `jasonliao`.
- `.trellis/.developer` remained ignored as machine-local identity state.

## Codex Lifecycle

Disposable task: `.trellis/tasks/archive/2026-08/08-24-trellis-codex-lifecycle-check`

Observed sequence:

1. Created a lightweight planning task with curated `implement.jsonl` and `check.jsonl` entries.
2. `task.py validate` accepted one real implement-context entry and one real check-context entry.
3. `task.py start` changed status from `planning` to `in_progress` under the isolated context ID `codex-lifecycle-check`.
4. `.codex/hooks/inject-workflow-state.py` resolved the active task and emitted the `in_progress` workflow state.
5. `task.py finish` cleared that session pointer.
6. `task.py archive --no-commit` marked and moved the task into the August 2026 archive.

## Claude Lifecycle

Disposable task: `.trellis/tasks/archive/2026-08/08-24-trellis-claude-lifecycle-check`

Observed sequence:

1. Created a lightweight planning task with curated `implement.jsonl` and `check.jsonl` entries.
2. `task.py validate` accepted one real implement-context entry and one real check-context entry.
3. `task.py start` changed status from `planning` to `in_progress` under the isolated context ID `claude-lifecycle-check`.
4. `.claude/hooks/inject-workflow-state.py` resolved the active task and emitted the `in_progress` workflow state.
5. `task.py finish` cleared that session pointer.
6. `task.py archive --no-commit` marked and moved the task into the August 2026 archive.

## Result and Limit

The repository-local platform files, developer identity, task planning, context validation, session activation, hook resolution, finish path, and archive path worked for both projections. This proves the checked repository workflow, not activation of user-level Codex hook permissions or any global Claude/Infra installation.
