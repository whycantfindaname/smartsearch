# Sciverse Provider History

This note preserves the project-specific decision record from 2026-07-06. It
is historical context, not evidence that a token, entitlement, upstream schema,
or live endpoint is available now. The current provider contract remains
`.trellis/spec/backend/provider-capability-contract.md`.

## Decision preserved from 2026-07-06

- Sciverse filled a distinct academic-evidence gap: field catalog discovery,
  structured paper filtering, semantic passage retrieval, bounded content
  reads, and paginated citation/reference/related-work relationships. It was
  not adopted as another broad web or documentation search route. Sources:
  [requirement](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/requirements/sciverse-academic-search.md),
  [brainstorm](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-brainstorm.md),
  and [acceptance](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-acceptance.md).
- Smart Search selected a native Python HTTP/OpenAPI adapter over starting or
  hosting `sciverse-mcp-server`. The rejected MCP-hosting approach would have
  added Node/npx, process-lifecycle, and transport ownership without improving
  the five-command MVP. The selected endpoints were `GET /meta-catalog`,
  `POST /meta-search`, `POST /agentic-search`, `GET /content`, and
  `POST /meta-paper-relations`. Sources: [brainstorm directions D/E](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-brainstorm.md)
  and [design](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md).
- Routing was deliberately explicit-only. The five `sciverse-*` commands did
  not enter `docs_search`, the default `search` or `research` fallback chains,
  or the `standard` minimum profile. The feature exposed capability diagnostics
  without making configuration imply automatic routing. Sources:
  [requirement boundary](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/requirements/sciverse-academic-search.md),
  [design decisions](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md),
  and [acceptance routing checks](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-acceptance.md).
- Evidence identifiers remained intentionally distinct: `unique_id` addressed
  paper relations, while `doc_id` addressed readable content. Full text was
  conditional on source data and authorization; binary/multimodal
  `get_resource` output was excluded from v1. Sources: [requirement boundary](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/requirements/sciverse-academic-search.md)
  and [design terminology](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md).

## Validation boundary

On 2026-07-06, mock provider, service, CLI, regression, and mock-smoke checks
were reported as passing, including no-token/no-network behavior and reverse
checks that default routing did not call Sciverse. The environment did not have
`SCIVERSE_API_TOKEN`, so catalog/search/semantic/read/relations were not
validated against the live remote service. This dated evidence must not be used
as a current entitlement or reachability claim. Sources: [QA report](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-qa.md)
and [acceptance report](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-acceptance.md).

## Superseded and current boundaries

- The historical design described AnySearch as an internal experimental
  `vertical_search` provider. That topology is superseded. AnySearch is now an
  external Skill/delegation path and must not be reintroduced as a Smart Search
  provider or fallback member. The old statement is retained only to explain
  the 2026-07-06 comparison. Source: [historical design](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md).
- The durable Sciverse rule remains: native HTTP/OpenAPI, explicit-only
  academic commands, no default route, and no contribution to `standard`.
  Current implementation and tests determine whether that rule is still
  satisfied; this history note does not override them. Original decision
  sources: [brainstorm](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-brainstorm.md)
  and [acceptance](https://github.com/whycantfindaname/smartsearch/blob/020b4dc904e2b19643aeece0c00b25d011eb1fc5/.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-acceptance.md).
