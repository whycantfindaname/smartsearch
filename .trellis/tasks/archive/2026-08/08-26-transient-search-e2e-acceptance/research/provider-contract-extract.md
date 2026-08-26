# Focused provider and Skill contract

This is a task-scoped extract of
`.trellis/spec/backend/provider-capability-contract.md`. The source spec remains
authoritative. This extract exists because the full spec exceeds Trellis's
context-injection size and would otherwise be truncated.

## Capability and fallback boundaries

- Main search peers are `xai-responses` and `openai-compatible`.
- Documentation search uses Context7 and Exa by intent. Context7 is for
  libraries, APIs, SDKs, and frameworks; Exa is for official domains, papers,
  product pages, trusted sites, and low-noise discovery.
- Web fetch order is Tavily, Jina, Zhipu MCP reader, then Firecrawl, restricted
  to configured providers.
- Sciverse is explicit-only and route-disabled in normal research fallback. An
  Agent may choose an explicit Sciverse command for a genuine academic task;
  it is not an automatic generic fallback.
- Fallback stays inside a capability. A provider failure does not authorize a
  new main-search loop or a cross-capability substitute.
- Discovery results are candidates. A source-dependent claim requires fetched
  or read evidence; strict research degrades or exposes a gap when evidence
  cannot be closed.

## Search and recovery contract

- Source `search` defaults to `--timeout 120 --max-try 5`.
- `--max-try` counts the first logical call and applies only to exact approved
  safe markers: xAI HTTP `504 upstream_server_error` and OpenAI-compatible HTTP
  `429 concurrency_limit_exceeded`.
- HTTP `499` maps to `request_cancelled`; submission outcome is uncertain, so
  automatic logical replay and main-provider peer/model fallback stop.
- Generic HTTP `429`, ordinary HTTP `5xx`, timeouts, network failures, and
  uncertain submission results receive no generic logical replay.
- Failed special cases expose a structured `recovery` object with replay
  safety, cooldown, one doctor command, one-probe limit, and a plain-language
  recommendation.
- `doctor` is a diagnostic probe. It does not repair provider state, clear
  concurrency, cancel accepted work, or change configuration. Repeated probes
  add traffic.
- JSON remains the machine-readable contract. Provider attempts and logical
  attempts must remain visible; an Agent must not hide failures behind an outer
  retry loop.

## Provider-specific test boundaries

- Context7 HTTP `408`, `429`, `5xx`, timeout, and network failures receive a
  bounded provider transport retry. An automatic docs route may then continue
  to Exa.
- Exa HTTP `402` is a non-retryable `provider_error`. The Agent follows the
  sanitized billing/resource message or uses another suitable discovery route.
- `TAVILY_ENABLED=false` removes Tavily from web search and fetch, makes direct
  Tavily/doctor paths local-only, and permits no Tavily network request.
- Jina is a known-URL fetch provider. An empty response or recognized
  Cloudflare/JavaScript challenge marker is `quality_error`; that content is
  ineligible for citation and fetch continues to Zhipu MCP reader or
  Firecrawl.
- Provider errors stay in `provider_attempts`; successful same-capability
  fallback does not erase them.

## Packaging, diagnostics, and security

- Runtime Skill injection uses bundled package assets. A Skill contract change
  updates both `skills/smart-search-cli/**` and
  `src/smart_search/assets/skills/smart-search-cli/**`, which must remain
  byte-identical.
- `smart-search skills status` is read-only. The governed personal Skills
  package is synchronized through its own package-aware workflow.
- Credentials, authorization headers, cookies, signed URLs, config values, and
  raw request bodies must not appear in command output, logs, tests, task
  artifacts, or generated recovery commands.
- Live-key work requires a targeted exact-value secret scan before durable
  artifacts or commits are accepted.
