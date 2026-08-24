# Migration Design

## Authority Mapping

| Knowledge type | Target | Rule |
| --- | --- | --- |
| Current provider contract | `.trellis/spec/backend/provider-capability-contract.md` | Add only verified rules absent from the current spec. |
| Historical provider decision or incident | This task's `research/*.md` | Preserve background, final decision, still-valid boundary, validation limit, and source paths. |
| Completed workflow evidence already represented by Trellis | Existing `.trellis/tasks/archive/**` | Link rather than duplicate. |
| CodeStable framework templates, gates, tools, hooks | No migration target | Retain only until Trellis platform lifecycle validation passes, then retire. |
| User-facing current behavior | README / Skill docs | Update only if migration reveals current documentation drift; do not store history here. |

## Migration Phases

### A. Additive knowledge migration

1. Write the two compact historical research documents.
2. Create an original-path-to-authority mapping.
3. Amend the provider spec only for verified missing durable rules.
4. Run code/spec/README/Skill consistency checks.

No `.codestable` file is deleted in this phase.

### B. Trellis platform validation

Use a disposable task or documented dry run to validate Codex and Claude platform discovery, identity, task lifecycle, context injection/check path, and archive behavior. Do not modify global Infra configuration.

### C. CodeStable retirement

After A and B pass, remove CodeStable framework content, hooks, tools, gates, empty directories, and process records already represented by the new summaries. Update `STRUCTURE.md` and repository references in the same retirement change.

## Conflict Resolution

When an old CodeStable statement conflicts with current code, tests, provider spec, or reviewed Skill behavior, preserve it only as superseded historical context. Current verified behavior wins; old live observations remain timestamped history.

## Rollback

- Rollback A by reverting only new summaries/spec deltas; `.codestable` remains intact.
- Rollback C independently if a missing dependency is found; the additive Trellis knowledge remains available.
- Never combine source deletion with the first migration change.
