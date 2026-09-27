[Guide](../README.md) · [简体中文](../zh-CN/research.md)

# Search and research

## CLI and AI responsibilities

`smart-search` is not an MCP server. It is a normal CLI that AI agents can call through a skill:

```powershell
smart-search search "latest OpenAI Responses API changes" --format json
smart-search fetch "https://example.com/article" --format markdown
smart-search deep "Compare Responses API web_search with Chat Completions search" --format json
smart-search research "Compare Responses API web_search with Chat Completions search" --format markdown
```

The current architecture has two layers:

| Layer | Responsibility |
| --- | --- |
| CLI executor | Runs deterministic commands, provider routing, fallback, JSON/Markdown output, local config, smoke/regression checks |
| Skill / AI orchestration | Infers user intent, chooses normal search vs Deep Research, executes planned CLI steps, writes final source-backed answers |

Default `smart-search search` stays fast and live. `smart-search deep` is the explicit offline Deep Research planner. It does not call providers, run `doctor`, or fetch pages by default; it emits a `research_plan` that an AI agent or user can execute step by step. `smart-search research` is the live Deep Research executor: it uses the same planner shape, then runs discovery, fetch/read, gap check, and evidence-only synthesis.

Intent routing now has its own layer. Instead of letting a model pick providers directly, Smart Search first decides which capabilities are needed, then the existing capability-first provider registry chooses same-capability fallback:

```text
user query
 -> rules: URLs, explicit docs/current/fetch/vertical signals, strict validation
 -> semantic route: optional embeddings over capability examples
 -> classifier route: optional structured model classification
 -> merged required_capabilities
 -> provider fallback inside docs_search / web_search / web_fetch / vertical_search
```

`smart-search route "query"` explains this decision without calling search, docs, fetch, or provider APIs. `smart-search deep` keeps the offline planner contract and uses local/rules signals only.

## Capabilities and providers

| Capability | Main commands | Providers | Role |
| --- | --- | --- | --- |
| `main_search` | `search` | xAI Responses, OpenAI-compatible Chat Completions or Responses | Broad answer generation and synthesis |
| `docs_search` | `context7-library`, `context7-docs`, `exa-search` | Context7, Exa | Official docs, SDKs, APIs, framework/library evidence |
| `web_search` | `zhipu-search`, `zhipu-mcp-search`, intent-routed reinforcement inside `search` | Zhipu Web Search API, Zhipu Coding Plan MCP, Tavily, Firecrawl, TinyFish | Chinese, domestic, current, domain-filtered, or supplementary web discovery |
| `web_fetch` | `fetch`, `zhipu-mcp-reader` | Tavily, Jina Reader, Zhipu Coding Plan MCP Reader, Firecrawl, TinyFish | Exact URL content extraction for evidence |
| `vertical_search` | `anysearch-domains`, `anysearch-search`, `anysearch-extract`, `anysearch-batch`, `sciverse-catalog`, `sciverse-search`, `sciverse-semantic`, `sciverse-read`, `sciverse-relations` | AnySearch and Sciverse (experimental) | Explicit structured vertical domains; Sciverse covers academic literature search, semantic search, content chunks, and citation relations |
| `site_map` | `map` | Tavily | Site/documentation structure discovery |
| `deep_planner` | `deep` / `dr` | Local planner only | Offline plan generation; no provider call by default |
| `research_executor` | `research` / `rs` | Registered providers by capability | Live staged research: plan, discover, fetch/read, gap check, evidence-only synthesis |

Fallback is same-capability only:

| Capability | Fallback chain |
| --- | --- |
| `main_search` | xAI Responses -> OpenAI-compatible |
| `docs_search` | Context7 when a library subject matches a candidate title/id; Exa after an empty or low-confidence Context7 match, and for official domains, papers, product pages, and trusted-site discovery |
| `web_search` | Zhipu Web Search API -> Zhipu Coding Plan MCP `web_search_prime` -> Tavily -> Firecrawl -> TinyFish |
| `web_fetch` | Tavily -> Jina Reader with `JINA_API_KEY` -> Zhipu Coding Plan MCP `webReader` -> Firecrawl -> TinyFish |

TinyFish covers both `web_search` and `web_fetch` with a single `TINYFISH_API_KEY`. It never satisfies `main_search` or `docs_search`, and it is appended after every existing provider so current configurations keep their provider order.

AnySearch and Sciverse are intentionally not part of the `web_search` fallback chain and are not required by the `standard` minimum profile. Sciverse is also not a `docs_search` provider and does not join default `search` or `research` routing; use explicit `sciverse-*` commands when you need academic metadata, semantic paper hits, document chunks, or citation/reference relations.

Jina Reader is a `web_fetch` provider only. `JINA_API_KEY` is required before Jina satisfies `SMART_SEARCH_MINIMUM_PROFILE=standard`; anonymous `r.jina.ai` behavior is treated as explicit/experimental fetch behavior and must not weaken fail-closed setup checks.

The CLI exposes observability fields such as `routing_decision`, `provider_attempts`, `providers_used`, `fallback_used`, `primary_sources`, `extra_sources`, and `source_warning`.

`routing_decision` keeps backward-compatible booleans such as `docs_intent`, `zh_current_intent`, `web_current_intent`, `fetch_intent`, and `supplemental_paths`, and also includes the unified router fields: `intent_router_mode`, `required_capabilities`, `intent_signals`, `confidence`, `router_engines_used`, and `degraded_reason`.

`extra_sources` are discovery candidates. For high-risk claims, news, policy, finance, health, selection decisions, and serious reviews, fetch key pages first and cite fetched text rather than treating a broad search answer as proof.

Routing rule of thumb: start with `search` for broad discovery and synthesis; use `research` when you want the CLI to execute the deeper evidence workflow; use Zhipu Web Search API for Chinese, domestic, policy, announcements, and current-news searches; use Zhipu Coding Plan MCP only when you explicitly want the Coding Plan quota route; use Context7 first for library/API/framework docs; use Exa for official domains, papers, product pages, trusted sites, and low-noise discovery; use Tavily/Firecrawl through `search --extra-sources` for horizontal candidates and through `fetch` for page evidence; use Jina for known-URL extraction; use AnySearch only when you explicitly need experimental vertical-domain search; use Sciverse only when you explicitly need academic-field catalog/search/semantic/read/relations commands.

## Research planning and execution

Use normal search when you want a fast answer:

```powershell
smart-search search "React useEffect cleanup docs" --format json
```

Use offline Deep Research planning when you want decomposition before execution:

```powershell
smart-search deep "OpenAI Responses API web_search vs Chat Completions search: which should I use?" --budget deep --format json
smart-search dr "https://example.com/source" --format json
```

Planner output includes:

- `mode="deep_research"` and `query_mode="deep"`;
- `intent_signals`, such as recency, docs/API intent, known URL, claim risk, source authority, and cross-validation need;
- `decomposition`, with 1-6 subquestions depending on budget and difficulty;
- `capability_plan`, choosing from existing CLI blocks;
- `steps[]`, each with `tool`, `purpose`, `command`, `output_path`, and `subquestion_id`;
- `evidence_policy="fetch_before_claim"`;
- `gap_check`, which fetches missing evidence or downgrades unsupported claims.
- `usage_boundary`, which explains that `search` is live, `deep` is offline planning, and execution happens through planned commands.

Deep Research is not a fixed topic recipe system. Market research, product comparison, technical docs, news or policy, claim verification, and URL-first prompts are examples of user language, not required schema enums.

Allowed planned tools are:

```text
search, exa-search, exa-similar, zhipu-search, context7-library, context7-docs, fetch, map
```

`doctor` is preflight, not a research step. `smart-search deep` itself is offline; live research starts when an agent or user executes `steps[].command`.

Use live Deep Research execution when you want the CLI to run the staged workflow:

```powershell
smart-search research "OpenAI Responses API web_search vs Chat Completions search: which should I use?" --budget deep --fallback auto --format json
smart-search rs "https://example.com/source" --fallback off --format markdown
```

`research` runs plan -> discover -> fetch/read -> gap check -> evidence-only synthesis. It defaults to `--fallback auto`, which permits same-capability fallback even when a normal `search` configuration is conservative. `--fallback off` tries only the first provider selected inside each capability, which is useful for debugging provider behavior.

Research JSON includes `final_answer`, `citations`, `evidence_items`, `gap_check`, `provider_attempts`, `fallback_used`, `degraded`, `route_policy_version`, and `evidence_dir`. Discovery snippets are candidates only; citations are produced only from fetched/read evidence. If fallback cannot close a gap, `research` finishes degraded and lists unsupported gaps instead of inventing evidence.

The research router is capability-first plus provider-advantage:

- Context7 first for library/API/framework docs only after query subject tokens match a candidate title or id. Description, trust, and benchmark metadata only break ties; no eligible candidate is an empty Context7 result and falls back to Exa for the same capability.
- Zhipu Web Search API first for Chinese, domestic, current, policy, and announcement searches.
- Zhipu Coding Plan MCP remains a separate quota route through `web_search_prime` and `webReader`.
- Jina is favored for known public URLs, PDFs, and arXiv extraction; ReaderLM-v2 still requires `JINA_API_KEY`.
- Firecrawl is favored for JS-heavy, dynamic, browser-like, OCR/PDF, or robust fallback extraction.
- AnySearch participates only when vertical intent is clear, such as CVE, finance, legal, academic, or codebase/repository searches.
- Sciverse is explicit-only in this release and does not participate in `research` provider fallback; use `sciverse-*` commands directly for academic relations.

Advanced routing overrides are available through `SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS` and `SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS`. They can reorder or disable registered providers inside their supported capability, but they cannot move a provider across capability boundaries.

Good user-facing smoke prompts:

```powershell
smart-search deep "深度搜索一下最近的比特币行情" --format json
smart-search deep "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --budget deep --format json
smart-search deep "帮我核验这个说法是真是假：某某工具已经完全替代 Tavily 做 AI 搜索了" --format json
smart-search deep "https://example.com/source" --format json
```

## Output and evidence

Use JSON for agents and scripts:

```powershell
smart-search search "query" --format json
smart-search doctor --format json
```

Use Markdown for human-readable reports, detailed diagnostics, source lists, and fetched page text:

```powershell
smart-search doctor --format markdown
smart-search diagnose openai-compatible --format markdown
smart-search smoke --mock --format markdown
smart-search exa-search "OpenAI Responses API documentation" --format markdown
smart-search fetch "https://example.com" --format markdown
```

Use `content` for compact terminal reading:

```powershell
smart-search search "nba report" --format content
smart-search doctor --format content
```

`content` is intentionally brief. Use `doctor --format markdown` for general human troubleshooting, `diagnose openai-compatible --format markdown` for OpenAI-compatible search hangs/timeouts, and JSON formats for complete machine-readable contracts.

When `search` has primary content but an optional phase reaches the deadline, JSON keeps the content and completed sources with `partial_success=true`; inspect `timeout_phase`, `timed_out_phases`, and `phase_attempts` before retrying or broadening source work.

Save multi-source evidence under an explicit stable folder. The default uses the platform temp directory; the commands below use a Windows explicit path example:

```powershell
smart-search exa-search "Reuters Iran Hormuz latest" --format json --output C:\tmp\smart-search-evidence\iran-hormuz\01-exa.json
smart-search fetch "https://example.com/source" --format markdown --output C:\tmp\smart-search-evidence\iran-hormuz\02-fetch.md
```

For claim-level evidence:

1. Discover candidate URLs with `search`, `exa-search`, `zhipu-search`, or `exa-similar`.
2. Fetch exact URLs with `fetch`.
3. Cite fetched text in the final answer.
4. Unsupported key claims must be fetched or downgraded to unverified candidates.
