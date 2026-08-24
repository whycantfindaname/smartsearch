# CodeStable Retirement Record

Date: 2026-08-24

## Result

CodeStable was retired as a second project-governance system after the additive
knowledge migration and repository-local Codex/Claude Trellis lifecycle checks
passed. The retirement removes the exact 71 tracked paths formerly returned by
`git ls-files .codestable`; it does not change Smart Search runtime behavior,
Provider configuration, API credentials, or global Infra state.

## Preserved Knowledge

- [`sciverse-history.md`](sciverse-history.md) preserves the Sciverse decision,
  current/superseded boundaries, and historical validation limits.
- [`provider-incidents.md`](provider-incidents.md) preserves the Zhipu MCP
  session incident and AnySearch/Context7 contract-drift history.
- [`migration-map.md`](migration-map.md) assigns every former source family one
  Trellis authority or retirement disposition.
- The original files remain available in the immutable repository snapshot
  [`020b4dc904e2b19643aeece0c00b25d011eb1fc5`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable).

## Preconditions Verified

- [`trellis-lifecycle-validation.md`](trellis-lifecycle-validation.md) records
  create, validate, start, hook resolution, finish, and archive checks for both
  repository-local platform projections.
- A repository-wide caller scan found no active CodeStable hook, gate, or tool
  consumer outside the migration history itself.
- `.codestable/attention.md` contained only generic CodeStable operating rules,
  not uncaptured Smart Search-specific knowledge.
- `STRUCTURE.md` and `.gitignore` now expose Trellis and its Codex/Claude
  projections as tracked repository governance instead of describing dual
  governance.

## Recovery

Until the retirement is committed, `git restore --source
020b4dc904e2b19643aeece0c00b25d011eb1fc5 -- .codestable` restores the former
tree. After commit, the same snapshot remains the recovery source. Restoring it
would reintroduce CodeStable as historical files only; Trellis remains the
active governance authority unless the repository rules are separately changed.

## Final Verification

- `git ls-files --deleted .codestable` returned the same 71 mapped paths.
- The active-caller scan found no CodeStable hook, tool, gate, or hook-config
  reference outside the migration history.
- `python3 .trellis/scripts/task.py validate
  08-24-migrate-codestable-to-trellis` accepted four implement and four check
  context entries.
- `npm run check:skill-parity` verified all 29 public/packaged Skill files.
- `/Users/jasonliao/miniconda3/envs/codex/bin/python -m pytest tests -q`
  completed with `560 passed`.
- `git diff --check` completed without errors.
