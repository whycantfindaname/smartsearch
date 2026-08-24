# Migrate Valuable CodeStable Knowledge into Trellis

## Goal

Retire CodeStable as a second project-governance system without losing Smart Search-specific decisions and incident knowledge. Migrate only durable, current, non-duplicative knowledge into the proper Trellis authority, validate both Codex and Claude Trellis workflows, and delete `.codestable` only in a separately reviewable retirement step.

## Background

- `.codestable` mixes project-specific knowledge with a large copy of CodeStable's own workflow, gates, hooks, and maintenance utilities.
- Trellis now owns project workflow, task context, checks, archives, Codex integration, and Claude integration.
- Current high-value historical content is concentrated in Sciverse product boundaries, Zhipu MCP session handling, and AnySearch/Context7 provider-contract drift.
- Existing `.trellis/spec/backend/provider-capability-contract.md` and archived Trellis tasks already cover part of this material. Copying everything would create conflicting authorities.
- `STRUCTURE.md` currently documents CodeStable and Trellis as coexisting governance systems and must be updated only after the new boundary is verified.

## Requirements

1. Build a traceable inventory that classifies each `.codestable` content family as migrate, summarize, retain temporarily, or retire.
2. Preserve only Smart Search-specific decisions, incident causes, validation limits, and source paths; do not copy CodeStable framework templates or full approval/review chains.
3. Consolidate Sciverse's durable provider boundary into the existing provider capability spec only where the rule is still missing and verified against current code/tests.
4. Create concise task-local history for:
   - Sciverse native HTTP, explicit-only routing, structured academic evidence, and historical live-validation limits.
   - Zhipu MCP `initialize -> Mcp-Session-Id -> tools/call` handling and AnySearch/Context7 external-contract drift.
5. Preserve historical capability observations as historical evidence. Do not convert an old token limitation, success, or failure into a current entitlement claim.
6. Verify the generated Codex and Claude Trellis platform files, `jasonliao` identity, task planning, context manifests, check path, and archive path before retiring CodeStable hooks or tools.
7. Separate additive knowledge migration from destructive CodeStable retirement so the latter can be reviewed and rolled back independently.
8. Update repository structure/governance documentation and ignore rules to describe Trellis as the sole active task/spec system after retirement.

## Acceptance Criteria

- [x] Every retained CodeStable conclusion has one declared Trellis authority and links back to its original source path.
- [x] `research/sciverse-history.md` and `research/provider-incidents.md` preserve the three identified project-specific knowledge groups without copying redundant process files.
- [x] Provider spec changes are limited to verified missing rules and agree with current code, tests, README behavior, and public/packaged Skill copies.
- [x] Old statements that model AnySearch as an internal Smart Search provider do not enter Trellis specs.
- [x] Codex and Claude are both reported by `trellis platforms`, and the `jasonliao` workspace exists.
- [x] A disposable Trellis lifecycle check demonstrates create, plan, start, check/context validation, finish, and archive on both platform configurations before CodeStable hooks/tools are removed.
- [x] `rg --hidden "\\.codestable|CodeStable"` is reviewed; remaining references after retirement are intentional history or the retirement record.
- [x] Existing Smart Search tests and package/Skill parity checks remain unchanged by knowledge migration.
- [x] Migration and retirement are split into separately reviewable changes; deleting `.codestable` is not part of the first additive migration.
- [x] `STRUCTURE.md`, `AGENTS.md`, and platform entrypoints describe the final Trellis ownership without claiming deployment or runtime changes.

## Out of Scope

- Changing Smart Search runtime behavior, provider routing, API keys, or current entitlements.
- Mechanically importing every CodeStable file into Trellis.
- Rewriting README files as historical archives.
- Using future implementation plans as evidence of current provider behavior.
- Deleting `.codestable` before knowledge mapping and both platform lifecycle checks pass.

## Known Migration Set

- Sciverse: `.codestable/requirements/sciverse-academic-search.md` plus the representative feature brainstorm and acceptance files.
- Zhipu MCP: `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/` root-cause and fix records.
- Provider drift: `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/` plus the existing Trellis provider-selection archive.
