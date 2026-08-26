# Smart Search Error Recovery Catalog

## Purpose

This document is the single extensible decision catalog for errors from all
Smart Search channels. It covers the main answer providers, direct discovery
providers, URL fetch providers, vertical providers, research/evidence flows,
and shared configuration failures. Agents must identify the failed channel
before choosing a recovery action.

The catalog separates provider-level transport retry, transport fallback,
same-capability provider fallback, CLI-level logical replay, and a new
operator request. These are different operations. A retry or fallback in one
layer does not authorize another layer to repeat the request.

When a new error is discovered, add its observed signature, submission
knowledge, and operator action to this catalog first. Do not copy the rule into
`SKILL.md` or another reference. Runtime code changes are needed only when the
new rule changes machine classification, automatic behavior, or the structured
output schema; a documentation-only operator response belongs here alone.

## Authority and evidence

The catalog describes the behavior implemented by:

- `src/smart_search/provider_errors.py` for shared public error types and
  credential-safe messages;
- `src/smart_search/providers/` for provider transport behavior and response
  normalization;
- `src/smart_search/service.py` for capability fallback, empty-result handling,
  and research/evidence outcomes;
- `src/smart_search/cli.py` for logical replay and structured recovery; and
- provider, service, CLI, and regression tests under `tests/`.

Provider documentation may describe additional upstream failures. Add them
here only after Smart Search has produced an observable sanitized signature or
the implementation has an explicit branch for them. Do not present a
theoretical upstream error as a supported Smart Search contract.

## How to use this catalog

1. Read `ok`, `error_type`, `provider`, `tool`, `provider_attempts`,
   `fallback_used`, and `recovery` from the returned JSON.
2. Locate the channel section below. Use the last relevant failed attempt, not
   just the top-level message, when a fallback chain ran.
3. Distinguish an error from `empty`, `skipped`, `disabled`, `not_configured`,
   or `degraded`. These statuses can change routing without being transport
   failures.
4. Let built-in retries and fallbacks finish. Do not wrap the command in an
   additional retry loop.
5. Preserve the sanitized JSON when reporting a new signature. Never record
   API keys, authorization headers, or raw credential-bearing URLs.

## Recovery layers

| Layer | Owner | Meaning | Agent action |
| --- | --- | --- | --- |
| Transport retry | Individual provider client | Repeats a bounded HTTP/connection attempt inside one provider call. | Wait for the command to finish; do not duplicate it externally. |
| Transport fallback | OpenAI-compatible main provider | Switches stream to non-stream after a retryable stream failure or empty stream. | Inspect transport attempts; do not count this as a new logical search. |
| Model fallback | OpenAI-compatible main provider | Tries a configured fallback model with the remaining timeout budget. | Inspect `model_role`, `fallback_from_model`, and `model_fallback_used`. |
| Same-capability fallback | Smart Search service | Tries another configured provider that serves the same capability. | Inspect every `provider_attempts[]` entry and use the successful provider's evidence. |
| Logical replay | Search CLI | Repeats the full logical search only for an exact approved safe marker. | Never add another loop around `--max-try`. |
| Fresh operator request | User or Agent | Starts a new command after the failure condition changes. | Make at most one fresh request when the relevant channel section permits it. |

## Shared error vocabulary

| `error_type` or status | Meaning in Smart Search | Default response |
| --- | --- | --- |
| `config_error` | A required key, endpoint, capability, or compatible option is missing or disabled. | Correct configuration first; do not retry the same command unchanged. |
| `parameter_error` | The request, model, URL, filter, limit, relation, or config value is invalid. | Correct the input; do not retry the same payload. |
| `auth_error` | HTTP `401`/`403` or a provider-native authentication rejection. | Verify the correct key, entitlement, endpoint, and account; retry only after one changes. |
| `timeout` | HTTP `408` or a transport timeout. | Let built-in handling finish, then use channel fallback or one fresh request after the condition changes. |
| `rate_limited` | HTTP `429`. It may represent quota, concurrency, or provider policy. | Do not infer safe replay from the type alone; follow the exact channel signature. |
| `request_cancelled` | HTTP `499`; submission outcome is not proven. | Never automatically replay or start another main provider peer. |
| `network_error` | Connection failure, ordinary HTTP `5xx`, empty final content, or an exhausted network path. | Inspect attempts and use same-capability fallback; no generic logical replay. |
| `parse_error` | JSON, SSE, Unicode, or provider response shape could not be decoded or validated. | Preserve a sanitized excerpt, switch to a same-capability provider, and report the schema drift. |
| `provider_error` | The provider or JSON-RPC tool rejected the call without a narrower stable type. | Read the provider-native message, correct the named condition, or use same-capability fallback. |
| `runtime_error` | An unexpected local/provider exception did not match a stable type. | Preserve the exception class/message and command version; treat as a bug candidate. |
| `quality_error` | Content was returned but failed a quality gate, such as an empty or challenge page. | Do not cite it; continue the fetch fallback chain. |
| `evidence_error` | Retrieval ran, but strict validation did not obtain enough citable evidence. | Fetch stronger sources or downgrade the claim; do not repeat synthesis alone. |
| `empty` | A provider completed without usable normalized results/content. | Continue same-capability fallback. Empty is not proof that the provider is down. |
| `skipped` / `disabled` | A breaker, explicit config, or capability policy prevented a call. | Read the reason; do not bypass an intentional disablement. |
| `degraded` | An optional route failed while the command retained a usable primary result. | Keep the primary result, disclose the missing route, and avoid claiming cross-validation. |

HTTP statuses not listed in the shared classifier, including `402`, `404`,
`405`, `409`, `413`, `415`, `432`, and `433`, default to
`provider_error`. This fallback does not mean the failures have the same
cause. Use the sanitized provider message and the channel section below to
distinguish billing, missing resources, method/media mismatch, conflicts,
payload size, or plan limits. These statuses receive no generic transport
retry or logical replay.

## Main search default budget

The default search command is:

```powershell
smart-search search QUERY --timeout 120 --max-try 5 --format json --output PATH
```

`--timeout` is the hard timeout for one logical search call. `--max-try` is the
maximum number of logical calls, including the first call. It is a bounded
safety budget, not a general retry switch. A result records
`logical_attempts`, `logical_retry_used`, and `logical_retry_max_attempts`.

## Main provider channel

The main provider channel owns broad answer generation and synthesis. xAI
Responses and OpenAI-compatible Chat Completions are peer providers. With
`--fallback auto`, Smart Search may move to another configured peer after a
known failed attempt. Peer fallback is not logical replay.

### xAI Responses

| Observed signature | Built-in behavior | Automatic logical replay | Required handling |
| --- | --- | --- | --- |
| Missing `XAI_API_KEY`, with no other configured main provider | Minimum-profile `config_error`. | No | Configure xAI or a separate OpenAI-compatible peer. |
| Connection failure before request submission | Bounded provider transport retry. | No additional replay | Wait for the existing attempt budget. If it still fails, inspect network/DNS/TLS and make one fresh request only after the condition changes. |
| HTTP `400`/`422` | `parameter_error`. | No | Check model, tool names, endpoint mode, and payload compatibility. |
| HTTP `401`/`403` | `auth_error`. | No | Verify `XAI_API_KEY`, endpoint, account access, and model entitlement. |
| HTTP `404` | `provider_error`; xAI documents unknown models and invalid endpoint paths under this status. | No | Verify the configured model and `XAI_API_URL`. Do not retry the same route unchanged. |
| HTTP `405`/`415` | `provider_error`; the endpoint rejected the method or media type. | No | Treat this as an incompatible endpoint/relay contract. Verify the Responses route and JSON request handling. |
| Generic HTTP `408`/timeout | `timeout`. | No | Preserve the attempt. A timeout does not prove rejection. |
| Generic HTTP `429` | `rate_limited`. A separately configured peer may still run. | No | Wait for the provider limit window or use the completed peer fallback result. |
| HTTP `499` | `request_cancelled`; main peer fallback stops. | Never | Treat submission as uncertain. Confirm no usable result arrived before any later fresh request. |
| Exact HTTP `504` plus `upstream_server_error` | Final result is eligible for the bounded CLI retry budget. | Yes, within `--max-try` | Let the CLI complete its budget. Do not add another retry loop. |
| Other HTTP `5xx` | `network_error`; a configured main peer may run. | No | Use peer fallback or report the failure; do not replay by status alone. |
| Status monitor reports `running` after the soft wait | The same request continues to be polled within the hard deadline. | No new request | Keep waiting for the current command. Do not start a duplicate search. |
| Terminal/unknown status before the response connection completes, post-submission connection loss, or hard timeout | Outcome is uncertain; main peer fallback stops. | Never | Preserve the request/attempt metadata and check for a late result. Do not replay automatically. |
| Empty final answer | Recorded as an empty/network failure; a configured peer may run. | No | Use the peer result if available; otherwise report the empty outcome. |

### OpenAI-compatible Chat Completions

| Observed signature | Built-in behavior | Automatic logical replay | Required handling |
| --- | --- | --- | --- |
| Missing URL/key or no valid main provider | `config_error`. | No | Set `OPENAI_COMPATIBLE_API_URL` and `OPENAI_COMPATIBLE_API_KEY`; verify the endpoint exposes `/chat/completions`. |
| Invalid model/payload, HTTP `400`/`422` | `parameter_error`; non-retryable. | No | Use `smart-search model current` and verify the model against `/models`; correct the payload or provider mode. |
| HTTP `401`/`403` | `auth_error`; non-retryable. | No | Verify key, endpoint, relay account, and model entitlement. |
| HTTP `402`/`404`/`405`/`409`/`415`, or another unlisted HTTP status | `provider_error`; non-retryable by the shared client. | No | Read the sanitized provider message. Resolve billing, model/route, method/media, or relay-state problems before one fresh request. |
| HTTP `408`, transport timeout, connection error, or remote protocol error | Bounded transport retry. A retryable stream failure may fall back to non-stream. | No | Let transport handling finish. If the final search shape still hangs, run `smart-search diagnose openai-compatible --format markdown`. |
| Exact HTTP `429` plus `concurrency_limit_exceeded` | Final result is eligible for bounded CLI replay with backoff. | Yes, within `--max-try` | Let the CLI finish; then follow the structured recovery cooldown. |
| Other HTTP `429` | Bounded provider transport retry may run; final type is `rate_limited`. | No | Honor the provider window and do not turn it into a logical search loop. |
| HTTP `499` | `request_cancelled`; peer/model fallback stops. | Never | Treat the result as possibly submitted and confirm no result arrived before a later fresh request. |
| HTTP `500`/`502`/`503`/`504` without the approved marker | Bounded provider transport retry; model or peer fallback may run. | No | Use completed fallback results or report the final attempt. |
| Empty stream or retryable stream failure | One non-stream transport fallback; repeated stream failures open a local stream breaker. | No | Use the non-stream result. If the breaker is open, do not force stream until its cooldown expires. |
| Primary model hard failure | A configured fallback model may run with the remaining timeout budget; repeated failures open a model breaker. | No | Inspect `model_role`, `fallback_from_model`, and breaker state; fix unavailable models before re-enabling them. |

For a failed main search, inspect `provider_attempts`, `logical_attempts`,
`logical_retry_used`, `transport_fallback_used`, `model_fallback_used`, and
`routing_decision.main_search_chain`. Run `doctor` at most once. Use
`diagnose openai-compatible` only when the OpenAI-compatible search-shaped
request is the suspected bottleneck; it is a diagnostic call, not a repair.

## Exa channel

Exa serves direct `exa-search`/`exa-similar` calls and the `docs_search`
capability. It discovers candidate URLs; successful discovery is not evidence
until the relevant URL is fetched.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Missing `EXA_API_KEY` | `config_error` before the provider call. | Configure the key, or use another configured `docs_search` provider. |
| HTTP `400`/`422`, including invalid domain/date/category filters | `parameter_error`; no useful retry with the same payload. | Correct the filter values and submit one fresh command. |
| HTTP `401`/`403` | `auth_error`. | Verify the Exa key and account entitlement before retrying. |
| HTTP `408`/`429`/`500`/`502`/`503`/`504`, timeout, or connection failure | Bounded provider transport retry, then the shared final error type. | Wait for the provider call to finish. In an automatic docs route, use the recorded same-capability outcome; for a direct command, wait for the condition to change before one fresh call. |
| HTTP `402`, `404`, `409`, or another unlisted status | `provider_error`; no built-in retry. | Follow the sanitized Exa message for billing, resource, or request-state correction; otherwise use Context7 or another discovery route. |
| Invalid JSON | `parse_error`. | Preserve the sanitized response excerpt and use Context7 or another suitable discovery route. |
| `ok: true` with zero results | `empty`, not a transport error. | Broaden filters or change the query; do not retry unchanged. |

Exa failure must not trigger a new main `search` loop. When Exa ran as a
supplemental route, the primary answer may still be usable but is not
cross-validated by Exa.

## Context7 channel

Context7 serves library resolution and versioned documentation snippets. It is
not a general-news or broad-web provider.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Missing `CONTEXT7_API_KEY` | `config_error`. | Configure Context7 or allow Exa in the same `docs_search` capability. |
| Invalid/unknown library id or HTTP `400`/`422` | `parameter_error`. | Run `context7-library` again, choose a returned id, then call `context7-docs`. |
| HTTP `401`/`403` | `auth_error`. | Verify key and entitlement before retrying. |
| HTTP `202` | Context7 accepted a library that is not finalized. Smart Search may expose it as an empty/no-snippet response. | Wait for indexing to finish, then make one fresh Context7 request or use Exa. |
| HTTP `301` | The Context7 client follows the redirect inside the same call. | Use the final response; if the redirected library id is returned, preserve that id for later calls. |
| HTTP `404` | `provider_error`; the library id does not exist. | Resolve the library again and use the returned id. Do not retry the missing id unchanged. |
| HTTP `409` | `provider_error`; the resource already exists or conflicts with current state. | Use the existing library/resource or reconcile its state before a fresh request. |
| HTTP `408`/`429`/`5xx`, timeout, or network failure | Bounded transport retry, then a shared final error. | Let the provider budget finish; automatic docs routing may continue to Exa. |
| No eligible library candidate | Recorded as `empty`; automatic docs routing continues to Exa. | Refine the library name or use Exa. Do not invent a library id. |
| Non-JSON text response | Preserved as content with no normalized result list. | Treat it as unverified text; use Exa/fetch if a citable URL is required. |

## Zhipu channels

### Zhipu REST Web Search

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Missing `ZHIPU_API_KEY` | `config_error`. | Configure the key or use another `web_search` provider. |
| HTTP `400`/`422` | `parameter_error`. | Check engine, recency/domain filters, content size, and query constraints. |
| HTTP `401`/`403` | `auth_error`. | Verify key, endpoint, and product entitlement. |
| HTTP `408`/`500`/`502`/`503`/`504`, timeout, or network failure | Bounded transport retry. | Let it finish; same-capability routing may continue to Zhipu MCP, Tavily, or Firecrawl. |
| HTTP `429` | Returned immediately as `rate_limited`; this provider path deliberately does not retry it. The provider message may indicate concurrency excess, upload frequency, exhausted balance, or an account restriction. | Use the next configured `web_search` provider. For concurrency/frequency, wait before one fresh direct call; for balance or account restriction, recharge or contact the provider instead of retrying. |
| Empty `search_result` | `empty`. | Continue same-capability fallback or broaden the query. |

### Zhipu Coding Plan MCP and reader

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Missing `ZHIPU_MCP_API_KEY` | `config_error` before network access. | Configure the Coding Plan key or use another provider. |
| HTTP `401`/`403`, or content such as `MCP error -401` / `Api key not found` | `auth_error`. | Verify the Coding Plan key and endpoint family. |
| Initialize response lacks `Mcp-Session-Id` or returns a JSON-RPC error | `provider_error`. | Preserve the message and use the REST/Tavily/Firecrawl route; retry only after the MCP service changes. |
| Tool result has `isError: true` or error content | `provider_error`, except recognized `-401` auth content. No sources are emitted. | Correct the tool arguments or use same-capability fallback. Never cite URLs embedded in an error payload. |
| Invalid SSE/JSON or malformed tool response | `parse_error` or `provider_error`. | Record the sanitized payload shape and use another provider. |
| Timeout/network/HTTP `5xx` | Shared transport error; no outer logical replay. | Use the next provider in `web_search` or `web_fetch`. |

## Tavily channel

Tavily can serve `web_search`, `web_fetch`, and `map`.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| `TAVILY_ENABLED=false` | `disabled`; no Tavily network call is made. Direct `map` returns `config_error`. | Respect the disablement. Do not bypass it with direct HTTP calls. |
| Missing `TAVILY_API_KEY` | Tavily is unavailable; `map` returns `config_error`. | Configure the key or use another `web_search`/`web_fetch` provider. `map` has no same-capability fallback. |
| HTTP `400`/`422`, `401`/`403`, `408`, `429`, or `5xx` | Shared parameter/auth/timeout/rate/network classification. | Correct permanent errors; for transient errors use same-capability fallback rather than a shell retry loop. |
| Response reports `success: false`, `error`, or `detail` | `provider_error`. | Follow the provider message or use fallback. |
| HTTP `432` | `provider_error`; Tavily plan usage limit exceeded. | Upgrade/change the plan limit or wait for its reset. Do not retry the same request immediately. |
| HTTP `433` | `provider_error`; Tavily pay-as-you-go limit exceeded. | Increase the pay-as-you-go limit or disable that route until billing changes. |
| Missing/non-list `results`, non-object result, or non-text extract content | `parse_error`. | Report schema drift and use Jina/Zhipu MCP reader/Firecrawl for fetch, or another web search provider. |
| Empty search/extract result | `empty`. | Continue same-capability fallback. |

## Jina Reader channel

Jina is a known-URL fetch provider, not a general search provider.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| No key under the standard profile | `not_configured`; anonymous Reader remains explicit/experimental only. | Configure `JINA_API_KEY` or use Tavily/Zhipu MCP reader/Firecrawl. |
| `JINA_RESPOND_WITH` set without a key | `config_error` before network access. | Add the key or remove `JINA_RESPOND_WITH`. |
| HTTP `400`/`422`, `401`/`403`, `408`, `429`, or `5xx` | Shared error classification; Jina itself does not add a transport retry loop. A `429` can reflect RPM, token, per-key/IP, or concurrency limits. | Correct permanent errors. For `429`, wait for the applicable limit window or reduce concurrency; otherwise continue the fetch fallback chain. |
| Empty body or a Cloudflare/JavaScript challenge marker | `quality_error`; content must not be cited. | Continue to the next fetch provider, normally Zhipu MCP reader or Firecrawl. |
| Timeout/network failure | `timeout`/`network_error`. | Use the next configured fetch provider. |

## Firecrawl channel

Firecrawl serves `web_search` and robust URL scraping, especially for dynamic
or challenge-prone pages.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Missing `FIRECRAWL_API_KEY` | Provider is unavailable; all-missing fetch routes return `config_error`. | Configure the key or use another fetch provider. |
| HTTP/auth/rate/timeout/`5xx` failure | Shared provider classification. | Continue same-capability fallback or wait for the condition to change before one fresh direct request. |
| HTTP `402` | `provider_error`; Firecrawl credits are exhausted or billing is not configured. | Top up credits, enable the intended billing policy, or keep Firecrawl disabled until that changes. |
| HTTP `404` | `provider_error`; endpoint, job id, or resource is missing. | Verify `FIRECRAWL_API_URL` and the resource id; do not retry unchanged. |
| HTTP `409` | `provider_error`; the resource state conflicts with the operation. | Re-read/reconcile state before a fresh request. |
| HTTP `413` | `provider_error`; the request payload is too large. | Reduce batch size, schema, or input size before retrying. |
| Response reports a tool error | `provider_error`. | Follow the sanitized provider message; do not treat it as empty success. |
| Missing `data`, missing `web`, non-object search items, or non-text Markdown | `parse_error`. | Report schema drift and use another provider. |
| Scrape succeeds but Markdown is empty | Firecrawl performs its bounded empty-content attempts with increasing `waitFor`; final state is `empty`. | Let those attempts finish, then use the remaining fetch chain or report empty content. |

Firecrawl may include a more precise code inside a `408` or `5xx` response.
Smart Search currently preserves that sanitized message while retaining the
shared `timeout`/`network_error` type:

- `SCRAPE_TIMEOUT`: increase the provider/page timeout only when the page is
  expected to finish, or use another fetch provider.
- `SCRAPE_SSL_ERROR` or `SCRAPE_DNS_RESOLUTION_ERROR`: verify the target URL,
  certificate, and DNS. Do not weaken TLS verification as a generic fix.
- `SCRAPE_ACTION_ERROR`, `SCRAPE_ALL_ENGINES_FAILED`, or
  `SCRAPE_SITE_ERROR`: simplify the scrape or use the next fetch provider.
- `SCRAPE_PDF_PREFETCH_FAILED`, `SCRAPE_PDF_INSUFFICIENT_TIME_ERROR`, or
  `SCRAPE_PDF_ANTIBOT_ERROR`: use a direct PDF/document extraction route or
  report the blocked source.
- `SCRAPE_UNSUPPORTED_FILE_ERROR`: use a supported file or a dedicated
  document parser; retrying the same URL is not a fix.
- `SCRAPE_ZDR_VIOLATION_ERROR`: remove the option that conflicts with Zero
  Data Retention, or change the approved data-retention policy first.

## Sciverse channel

Sciverse is explicit-only academic vertical search. It is not part of default
`search`, `research`, or `docs_search` fallback.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Missing `SCIVERSE_API_TOKEN` | `config_error` before network access. | Configure the token or use another explicit academic source. |
| Invalid collection/filter/sort/mode/source type, missing id/query, invalid page, `page_size`, `top_k`, offset, limit, or relation | `parameter_error` before network access. | Correct the named field. Current bounds include search `page_size` 1–50, semantic `top_k` 1–30, read limit 1–16384, and relation `page_size` 1–200. |
| HTTP `400`/`422`, `401`/`403`, `408`, `429`, or `5xx` | Shared provider classification. | Correct permanent errors; after transient failure make at most one fresh explicit command when still needed. |
| HTTP `404` or another unlisted status | `provider_error`; no automatic retry or fallback. | Verify document id, endpoint, collection, and provider-native message before a fresh explicit command. |
| Invalid JSON or missing/wrong response fields | `parse_error`. | Preserve tool name and schema message; report provider contract drift. |
| Empty result set | Successful explicit query with zero results. | Change filters/query; do not route it into ordinary web search automatically. |

## AnySearch compatibility channel

AnySearch remains a delegated external Skill and is not a generic Smart Search
fallback. Smart Search compatibility commands expose explicit vertical-domain
calls only.

| Observed signature | Built-in behavior | Required handling |
| --- | --- | --- |
| Invalid `--sub-domain-params`, malformed `--param`, or more than five batch queries | `parameter_error` before network access. | Correct local arguments; use `anysearch-domains` to inspect valid domains. |
| HTTP `400`/`422`, `401`/`403`, `408`, `429`, or `5xx` | Shared provider classification. | Correct permanent errors or wait before one fresh explicit call. Do not convert it into default web fallback. |
| HTTP `402`, `404`, `409`, or another unlisted status | `provider_error`; no automatic retry. | Resolve billing, domain/tool availability, or resource state through the delegated AnySearch Skill. |
| JSON-RPC `error` or tool `isError: true` | `provider_error`; result sources are empty and error URLs are not evidence. | Correct domain/tool arguments or follow the AnySearch Skill's provider-specific procedure. |
| Invalid JSON | `parse_error`. | Preserve the sanitized response and report protocol drift. |
| Timeout/network failure | `timeout`/`network_error`. | Use another explicitly approved vertical source or report the gap. |
| Domain listing returns no usable enum | Empty/unavailable domain catalog, not a successful search. | Verify the endpoint and AnySearch Skill configuration; do not guess domain names. |

## Research, routing, and evidence channel

| Observed signature | Meaning | Required handling |
| --- | --- | --- |
| Standard minimum profile lacks `main_search`, `docs_search`, or `web_fetch` | `config_error`; research/search fails closed. | Configure one provider for every required capability or explicitly use the profile policy intended for the environment. |
| Embedding or classifier router component fails | Routing degrades to rules and records the component failure. | Continue if the rule route is adequate; disclose degraded semantic routing when it affects provider selection. |
| Supplemental discovery/fetch provider fails but main answer succeeds | The search may remain `ok: true`; the failed attempt stays visible. | Keep the primary answer but do not claim the missing provider verified it. |
| All configured fetch providers return empty | Top-level `network_error` with `provider_attempts`. | Report that content extraction failed; do not cite discovery snippets as fetched evidence. |
| Strict validation has no sufficient fetched sources | `evidence_error`. | Fetch stronger primary sources, narrow/downgrade the claim, or state the evidence gap. Re-running synthesis alone cannot create evidence. |
| `fallback=off` or a provider filter excludes alternatives | Reduced routing is intentional. | Do not silently re-enable providers; report the constrained result. |

## Safe logical replay matrix

| Observed outcome | Stable `error_type` | Automatic logical replay | Required handling |
| --- | --- | --- | --- |
| xAI HTTP `504` with exact `upstream_server_error` | `network_error` | Yes, within `--max-try` | Replay with the CLI budget only; stop on success. |
| OpenAI-compatible HTTP `429` with exact `concurrency_limit_exceeded` | `rate_limited` | Yes, within `--max-try` | Replay with the CLI budget and bounded backoff. |
| Generic HTTP `429` | `rate_limited` | No | Return the failure; do not turn ordinary rate limiting into a replay loop. |
| HTTP `499` | `request_cancelled` | No | The upstream may have accepted the request; do not duplicate it automatically. |
| Ordinary HTTP `5xx` | `network_error` | No | Preserve the failure and provider attempts. |
| Timeout/network failure without a safe marker | `timeout` or `network_error` | No | A timeout does not prove that the request was not accepted. |
| Uncertain submission result | provider-specific or `network_error` | No | Treat the result as possibly committed; do not replay automatically. |

The two safe cases require the provider identity, expected HTTP status, stable
error type, and exact marker. An unrelated message containing the marker is
not sufficient. Same-capability fallback is a separate decision and does not
authorize logical replay of the failed search.

## Structured recovery object

For actionable `concurrency_limit_exceeded` and `request_cancelled` outcomes,
failed search JSON includes `recovery` with:

- `kind`: `concurrency_limit_exceeded` or `request_cancelled`.
- `transient`: `true`.
- `safe_to_replay`: whether an automatic logical replay is safe. HTTP `499` is
  always `false`.
- `automatic_retry_exhausted`: whether the bounded automatic budget was
  consumed.
- `wait_seconds`: the cooldown to observe before a new action.
- `doctor_command`: normally `smart-search doctor --format json`.
- `doctor_max_attempts`: `1`.
- `recommendation`: the next action in plain language.

Markdown renders the same fields under `## Recovery`. Generated doctor
commands contain no user query or other search payload.

## Recovery procedure

1. Read the JSON result and preserve `provider_attempts`, `logical_attempts`,
   and `recovery`.
2. If no `recovery` object exists, do not add an agent-side retry loop. Follow
   the normal provider-specific diagnosis or evidence fallback contract.
3. For `concurrency_limit_exceeded`, wait `recovery.wait_seconds`, run
   `recovery.doctor_command` at most once, and make at most one fresh search
   only if the probe is healthy and the result is still required.
4. For `request_cancelled`, first check whether a usable result arrived through
   another channel. Only when it did not and the result remains necessary may
   the caller wait, run the one probe, and make one fresh search.
5. `doctor` is a diagnostic probe, not a repair operation. It does not clear
   upstream concurrency, cancel an already accepted request, or change
   provider configuration. Repeated probes add traffic and can worsen the
   incident.
6. Do not wrap the CLI in a shell-level `timeout`, call native web search as a
   silent fallback, or retry based only on `error_type`.

## Adding a new error rule

Add a new row to the existing channel section. Create a new channel section
only when the provider has a distinct capability, protocol, or fallback path.
Record:

1. the command, provider/tool, Smart Search version/commit, and observation
   date;
2. the sanitized exact signature: HTTP status, stable `error_type`, provider
   code, and relevant attempt status;
3. whether the operation was rejected before submission, remained read-only,
   may have been submitted, or has unknown outcome;
4. built-in transport retry, transport/model fallback, same-capability
   fallback, and logical replay behavior as separate fields;
5. the operator action, cooldown or configuration change, and the maximum
   number of fresh requests; and
6. an implementation/test/log locator that can be read back.

A documentation-only handling rule changes this file alone. Change runtime
code and tests only when classification, automatic behavior, output fields, or
secret sanitization must change. Keep `SKILL.md` as a pointer to this catalog;
do not add individual error rows there.

## Evidence and safety boundaries

- Keep the original query out of generated `doctor_command` values.
- Do not cite an unsuccessful search as evidence. If a fresh search is not safe
  or does not recover, use the ordinary source-discovery and `fetch` workflow
  and label the degraded path.
- Do not claim that HTTP `499` means the provider rejected the request; its
  defining property here is that submission state is uncertain.

## Provider documentation references

These upstream pages help interpret sanitized provider messages. They do not
override Smart Search's implemented classification or retry boundaries. Last
checked: 2026-08-26.

- [xAI debugging errors](https://docs.x.ai/developers/debugging)
- [Context7 API guide](https://context7.com/docs/api-guide)
- [Zhipu API error codes](https://docs.bigmodel.cn/cn/faq/api-code)
- [Tavily HTTP errors](https://help.tavily.com/articles/8645538886-understanding-http-errors)
- [Firecrawl API errors](https://docs.firecrawl.dev/api-reference/errors)
- [Jina Reader API and rate limits](https://jina.ai/reader/)
