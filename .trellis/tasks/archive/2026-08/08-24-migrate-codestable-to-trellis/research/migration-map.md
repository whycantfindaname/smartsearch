# CodeStable to Trellis Migration Map

This map records the additive Phase A disposition for every tracked
`.codestable` content family. Phase C retirement was later completed after the
separate Trellis lifecycle validation; the table keeps the original migration
decisions while the retirement result is recorded in
[`retirement-record.md`](retirement-record.md).

CodeStable sources below use the immutable GitHub snapshot at
[`020b4dc904e2b19643aeece0c00b25d011eb1fc5`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable),
so their citations survive Phase C retirement.

## Authority rules

- Durable current provider behavior has one authority:
  `.trellis/spec/backend/provider-capability-contract.md`.
- Dated decisions, incidents, and validation limits live only in this task's
  `research/` notes and link to the original records.
- Trellis owns task workflow. CodeStable templates, gates, reviews, approval
  chains, hooks, and maintenance utilities receive no Trellis copy.
- AnySearch is an external Skill/delegation path. Historical records that model
  it as an internal provider are preserved only as superseded context.

## Family dispositions

| Tracked source family | Unique content | One target / retirement disposition |
| --- | --- | --- |
| [`.codestable/requirements/sciverse-academic-search.md`](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/requirements/sciverse-academic-search.md) | User need, structured academic-evidence boundary, explicit-only first version | Summarized in [`sciverse-history.md`](sciverse-history.md); retain source through Phase B, then retire with CodeStable. Current rules stay in the existing provider contract. |
| [`.codestable/features/2026-07-06-sciverse-academic-provider/`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/) decision and evidence records (`brainstorm`, `design`, `acceptance`, `qa`, `review`) | Native HTTP vs MCP-hosting decision, command/evidence semantics, routing boundary, dated validation limits | Summarized once in [`sciverse-history.md`](sciverse-history.md); retain source through Phase B, then retire. No second spec or ADR is created. |
| [Sciverse approval, design-review, checklist, and worktree override](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/) | CodeStable process state, review chain, execution checklist, branch exception | No migration target; retain temporarily for source traceability, then retire in Phase C. |
| [`.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/) report, analysis, fix note, and review | Stateful MCP failure, root cause, narrow provider-layer fix, no-live-key limit | Summarized once in [`provider-incidents.md`](provider-incidents.md); retain source through Phase B, then retire. Durable handshake rule already exists in the provider contract. |
| [Zhipu approval and worktree override](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/) | CodeStable review fallback and branch-process evidence | No migration target; retain temporarily, then retire in Phase C. |
| [`.codestable/issues/2026-07-06-gh-19-provider-contract-drift/`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/) report, analysis, fix note, and review | AnySearch/Context7 contract drift, root cause, scoped repair, dated probes | Summarized once in [`provider-incidents.md`](provider-incidents.md); retain source through Phase B, then retire. Current AnySearch architecture is explicitly marked superseded. |
| [Provider-drift approval and worktree override](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/2026-07-06-gh-19-provider-contract-drift/) | CodeStable review authorization and branch-process evidence | No migration target; retain temporarily, then retire in Phase C. |
| [`.codestable/reference/**`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/reference/) | CodeStable system overview, conventions, approval/execution/governance/tool documentation | No migration target; Trellis workflow/specs already own governance. Retain through Phase B dependency checks, then retire wholesale. |
| [`.codestable/gates/**`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/gates/) | CodeStable roadmap/goal gates | No migration target; retain through Phase B caller checks, then retire wholesale. |
| [`.codestable/tools/**`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/tools/) | CodeStable context, review, branch/worktree, DoD, evidence, backlog, publishing, validation, and finish utilities | No migration target; do not copy utilities into Trellis. Retain through Phase B caller checks, then retire wholesale. |
| [`.codestable/hooks/**`](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/hooks/) | CodeStable Codex hook registration | No migration target; retain until both Trellis platform lifecycle checks pass and callers are reviewed, then retire in Phase C. |
| [`.codestable/requirements/VISION.md`](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/requirements/VISION.md) | CodeStable requirement index/status | No migration target; the only unique project requirement is represented by `sciverse-history.md`. Retain temporarily, then retire. |
| [`.codestable/attention.md`](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/attention.md) | CodeStable attention/maintenance queue | No migration target; retire in Phase C after confirming it contains no uncaptured project-specific item. It is not copied into Trellis workflow. |
| [`.codestable/.gitignore`](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/.gitignore) | Ignore rules scoped to CodeStable runtime artifacts | No migration target; retire with the directory in Phase C. Repository `.gitignore` changes are outside Phase A. |
| Placeholder families: [audits](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/audits/), [brainstorms](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/brainstorms/), [compound](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/compound/), [features root](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/), [goals](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/goals/), [issues root](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/issues/), [refactors](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/refactors/), [requirements root](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/requirements/), and [roadmap](https://github.com/whycantfindaname/smartsearch/tree/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/roadmap/) `.gitkeep` files | Empty directory placeholders only | No migration target; retire with empty CodeStable directories in Phase C. |

## Existing Trellis knowledge kept by reference

- The archived [provider-selection and AnySearch task](../../archive/2026-08/08-07-provider-selection-and-anysearch/prd.md)
  remains its own completed task record; this migration does not duplicate it.
- The current provider contract already contains all verified durable material
  needed from these histories: Sciverse native HTTP and explicit-only routing,
  Zhipu MCP session initialization, Context7 candidate eligibility, and the
  external-Skill AnySearch boundary. Phase A therefore leaves that concurrently
  modified file untouched.

## Coverage statement

At the additive stage, the table assigned exactly one target or retirement
disposition to every one of the 71 paths returned by
`git ls-files .codestable`. The three project-specific record groups were
summarized; Phase C then removed the CodeStable process, governance, utility,
hook, index, ignore, and placeholder files after caller and lifecycle checks.
