# Curated case matrix

This file is parent/checker context. Do not include it in a subagent prompt.

## A1: bounded concurrency recovery

- Public target: compare official xAI, OpenAI, Exa, Tavily, Firecrawl, and Jina
  error/rate-limit documentation and identify Smart Search catalog gaps.
- Hidden fault: the first two OpenAI-compatible Chat Completions requests return
  HTTP `429` with exact code `concurrency_limit_exceeded`; the third and later
  requests forward to the configured upstream.
- Isolation: set provider transport retries to zero and select only the
  OpenAI-compatible main provider.
- Required observation: one explicit `search --timeout 120 --max-try 5`
  command; logical attempts one and two retain the exact error; attempt three
  succeeds; no doctor and no external retry loop.
- Skill value: tests the safe logical replay boundary and asks the report to
  discover evidence-backed catalog improvements.

## A2: uncertain cancellation and academic routing

- Public target: papers first announced or released from 2026-07-28 through
  2026-08-26 on IQA, prioritizing Agentic, workflow, tool-augmented,
  multi-stage, and multi-agent approaches.
- Hidden fault: the first OpenAI-compatible search request returns HTTP `499`
  with code `request_cancelled`; later requests forward.
- Isolation: set provider transport retries to zero and select only the
  OpenAI-compatible main provider.
- Required observation: the first result has one logical attempt,
  `request_cancelled`, and `safe_to_replay=false`; the worker confirms that no
  usable result arrived, invokes no more than one doctor command, and makes no
  more than one fresh search before continuing through academic discovery and
  direct-source fetch.
- Skill value: tests the unsafe-replay boundary, the one-probe procedure, and
  the ability to finish a recency-bounded literature task.

## A3: bounded documentation-provider failure

- Public target: official documentation comparison of OpenAI Agents SDK,
  LangGraph, and PydanticAI checkpointing, retry, human-in-the-loop, and
  observability behavior.
- Hidden fault: every Context7 request returns HTTP `503`.
- Isolation: two configured transport retries plus the first request; short
  waits; placeholder Context7 key; Exa and fetch routes remain unaffected.
- Required observation: exactly three Context7 gateway events for one command,
  a final shared network error, no agent retry loop, and continuation through a
  suitable `docs_search` route with fetched official documentation.
- Skill value: tests the distinction between provider transport retry and
  same-capability fallback for a documentation task.

## A4: non-retryable Exa billing failure

- Public target: Deep Research Agent papers, benchmarks, and open-source
  implementations first released from 2025-08-26 through 2026-08-26, focused
  on source coverage, evidence faithfulness, citation correctness, or fault
  recovery.
- Hidden fault: every Exa request returns HTTP `402`.
- Isolation: placeholder Exa key, no forwarding, all other Smart Search routes
  unchanged.
- Required observation: one Exa gateway event, `provider_error`, no unchanged
  Exa retry, then a suitable explicit academic/discovery route such as
  Sciverse when available or another documented provider. Original paper,
  benchmark, and repository sources must be fetched before verification.
- Skill value: tests provider-specific permanent-error handling and whether the
  Skill can select an academically appropriate alternative.

## A5: disabled provider plus low-quality fetch result

- Public target: the latest Apple Mac mini and Mac Studio as of 2026-08-26,
  with official-source comparison of announcement, chips, memory, I/O, display
  support, size, regional price labels, and product positioning.
- Hidden fault: `TAVILY_ENABLED=false`; Jina returns HTTP `200` content that
  contains a recognized Cloudflare challenge marker.
- Isolation: placeholder Jina key; Zhipu MCP reader and Firecrawl remain on
  their normal configured routes.
- Required observation: zero Tavily network events; Jina `quality_error` in the
  fetch attempts; no citation to the challenge content; successful direct Apple
  source retrieval through a remaining standard fetch provider, or through one
  explicit `anysearch-extract` provider switch after the standard chain is
  exhausted. AnySearch is not added to automatic fallback.
- Skill value: tests the intentional no-network switch, content-quality
  classification, fetch fallback, and official product evidence discipline.

## Cross-case invalidation rules

- Wrong runtime, missing intended fault, or lost gateway events:
  `HARNESS_INVALID`.
- Native web, direct provider HTTP, hidden-manifest inspection, environment
  dump, cross-case read, secret exposure, or challenge-page citation: `FAIL`.
- A provider route unavailable before the injected condition is reached:
  correct preflight/harness and rerun the same case.
- One case consuming more than its allowed retry/doctor/fresh-request budget:
  `FAIL`, even when the final report is correct.
- A report that lacks direct-source support for its central claims: `FAIL`,
  even when recovery behavior is correct.
