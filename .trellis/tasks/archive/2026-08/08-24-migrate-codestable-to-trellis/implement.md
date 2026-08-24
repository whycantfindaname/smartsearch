# Implementation Checklist

1. [x] Verify the inventory against all tracked `.codestable` files and current `.trellis` archives/specs.
2. [x] Write `research/sciverse-history.md` with current/superseded decisions and historical validation limits.
3. [x] Write `research/provider-incidents.md` for Zhipu MCP session handling and provider-contract drift.
4. [x] Add a source-to-target migration map with current code/spec evidence.
5. [x] Amend the provider capability spec only for confirmed gaps; no migration-specific amendment was needed because the durable rules were already present.
6. [x] Validate Codex and Claude Trellis platform and disposable task lifecycle behavior.
7. [x] Run relevant Smart Search tests, Skill parity, path/reference checks, and `git diff --check`.
8. [x] Present the additive migration for review without deleting `.codestable`.
9. [x] After separate approval, retire CodeStable framework files and update `STRUCTURE.md` and remaining references.
10. [x] Repeat validation and archive this task only after the retirement change is accepted.

## Validation Commands

- `trellis platforms`
- `python3 .trellis/scripts/get_developer.py`
- `python3 .trellis/scripts/task.py validate 08-24-migrate-codestable-to-trellis`
- `rg --hidden "\\.codestable|CodeStable" .`
- `npm run check:skill-parity`
- `python -m pytest tests -q`
- `git diff --check`

## Rollback Points

- Stop after additive migration if any source cannot be mapped unambiguously.
- Do not enter retirement while CodeStable hooks/tools still have an unverified caller.
- Keep deletion as a separate reviewable change so it can be reverted without discarding the new Trellis summaries.
