# smart-search

[简体中文](README.zh-CN.md) | English

CLI-first, skill-driven web research for AI agents and terminal users. `smart-search` gives AI tools one reproducible command layer for live search, source discovery, page fetching, site mapping, provider diagnostics, offline Deep Research planning, and live Deep Research execution.

<p>
  <a href="https://www.npmjs.com/package/@konbakuyomu/smart-search">
    <img src="https://img.shields.io/npm/v/@konbakuyomu/smart-search?label=npm%20latest" alt="npm latest">
  </a>
</p>

![Star History Chart](https://api.star-history.com/svg?repos=konbakuyomu/smartsearch&type=Date)

## What It Is

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

## Install

Stable channel:

```powershell
npm install -g @konbakuyomu/smart-search@latest
smart-search --version
smart-search setup
```

Test channel:

```powershell
npm install -g @konbakuyomu/smart-search@next
smart-search --version
```

The npm package creates an isolated Python runtime during install. You still use the single `smart-search` command.

Prerequisites:

- Node.js / npm.
- Python 3.10 or newer available as `python`, `python3`, or `py -3` on Windows.

## Quick Start

1. Configure providers:

```powershell
smart-search setup
smart-search doctor --format json
```

2. If OpenAI-compatible `search` hangs or times out, generate the short troubleshooting report:

```powershell
smart-search doctor --format markdown
smart-search diagnose openai-compatible --format markdown
```

3. Run a normal live search:

```powershell
smart-search search "today's important AI news" --validation balanced --extra-sources 2 --format json
```

4. Inspect intent routing without running providers:

```powershell
smart-search route "React useEffect API docs" --format markdown
smart-search route "请核验这个链接里的说法 https://example.com/source" --format json
```

5. Fetch exact page evidence:

```powershell
smart-search fetch "https://example.com/source" --format markdown --output evidence.md
```

6. Plan Deep Research:

```powershell
smart-search deep "Deep research recent Bitcoin market movement" --budget standard --format json
```

7. Run live Deep Research when you want the CLI to execute the staged workflow:

```powershell
smart-search research "Deep research recent Bitcoin market movement" --budget deep --format markdown
```

8. Install the skill for AI tools when setup prompts you, or explicitly:

```powershell
smart-search setup --non-interactive --install-skills codex,claude,cursor,hermes
```

Skill installation writes the bundled `smart-search-cli` skill into user-level tool directories such as
`~/.codex/skills`, `~/.claude/skills`, `~/.cursor/skills`, and `~/.hermes/skills`. It does not initialize
Trellis, hooks, agents, or commands. `--skills-root PATH` is only an advanced override for portable or test installs.

9. After upgrading the CLI, refresh the installed global skill:

```powershell
smart-search skills status --targets codex --format json
smart-search skills update --targets codex --format json
```

`setup --install-skills` remains available for first-time setup. For routine synchronization after package updates, use
`skills status` and `skills update`; they only inspect or overwrite the managed `smart-search-cli` files and do not change
provider keys or create Trellis/hooks/agents/commands.

## Current Architecture

| Capability | Main commands | Providers | Role |
| --- | --- | --- | --- |
| `main_search` | `search` | xAI Responses, OpenAI-compatible Chat Completions | Broad answer generation and synthesis |
| `docs_search` | `context7-library`, `context7-docs`, `exa-search` | Context7, Exa | Official docs, SDKs, APIs, framework/library evidence |
| `web_search` | `zhipu-search`, `zhipu-mcp-search`, intent-routed reinforcement inside `search` | Zhipu Web Search API, Zhipu Coding Plan MCP, Tavily, Firecrawl | Chinese, domestic, current, domain-filtered, or supplementary web discovery |
| `web_fetch` | `fetch`, `zhipu-mcp-reader` | Tavily, Jina Reader, Zhipu Coding Plan MCP Reader, Firecrawl | Exact URL content extraction for evidence |
| `vertical_search` | delegated bundled AnySearch adapter; `sciverse-catalog`, `sciverse-search`, `sciverse-semantic`, `sciverse-read`, `sciverse-relations` | AnySearch Skill and Sciverse (experimental) | Agent-level supplemental retrieval plus explicit Sciverse academic search |
| `site_map` | `map` | Tavily | Site/documentation structure discovery |
| `deep_planner` | `deep` / `dr` | Local planner only | Offline plan generation; no provider call by default |
| `research_executor` | `research` / `rs` | Registered providers by capability | Live staged research: plan, discover, fetch/read, gap check, evidence-only synthesis |

Fallback is same-capability only:

| Capability | Fallback chain |
| --- | --- |
| `main_search` | xAI Responses -> OpenAI-compatible |
| `docs_search` | Context7 when a library subject matches a candidate title/id; Exa after an empty or low-confidence Context7 match, and for official domains, papers, product pages, and trusted-site discovery |
| `web_search` | Zhipu Web Search API -> Zhipu Coding Plan MCP `web_search_prime` -> Tavily -> Firecrawl |
| `web_fetch` | Tavily -> Jina Reader with `JINA_API_KEY` -> Zhipu Coding Plan MCP `webReader` -> Firecrawl |

AnySearch is an internal Smart Search capability. It is not a separately discoverable Skill and not a registered provider. A Smart Search retrieval workflow reads `bundled-skills/anysearch/CONTRACT.md` and invokes its `scripts/smart_search_anysearch.py` adapter for matching vertical, batch, and known-URL extraction work; the user does not need to invoke `/anysearch` separately. If the bundle or adapter is unavailable, research continues with other sources. AnySearch and Sciverse are not required by the `standard` minimum profile. Sciverse is also not a `docs_search` provider and does not join default `search` or `research` routing.

Jina Reader is a `web_fetch` provider only. `JINA_API_KEY` is required before Jina satisfies `SMART_SEARCH_MINIMUM_PROFILE=standard`; anonymous `r.jina.ai` behavior is treated as explicit/experimental fetch behavior and must not weaken fail-closed setup checks.

The CLI exposes observability fields such as `routing_decision`, `provider_attempts`, `providers_used`, `fallback_used`, `primary_sources`, `extra_sources`, and `source_warning`.

`routing_decision` keeps backward-compatible booleans such as `docs_intent`, `zh_current_intent`, `web_current_intent`, `fetch_intent`, and `supplemental_paths`, and also includes the unified router fields: `intent_router_mode`, `required_capabilities`, `intent_signals`, `confidence`, `router_engines_used`, and `degraded_reason`.

`extra_sources` are discovery candidates. For high-risk claims, news, policy, finance, health, selection decisions, and serious reviews, fetch key pages first and cite fetched text rather than treating a broad search answer as proof.

Routing rule of thumb: start with `search` for broad discovery and synthesis; use `research` when you want the CLI to execute the deeper evidence workflow; use Zhipu Web Search API for Chinese, domestic, policy, announcements, and current-news searches; use Zhipu Coding Plan MCP only when you explicitly want the Coding Plan quota route; use Context7 first for library/API/framework docs; use Exa for official domains, papers, product pages, trusted sites, and low-noise discovery; use Tavily/Firecrawl through `search --extra-sources` for horizontal candidates and through `fetch` for page evidence; use Jina for known-URL extraction; delegate to the bundled AnySearch adapter when its general, vertical, batch, or extraction capabilities can add evidence; use Sciverse only for explicit academic commands.

## Deep Research

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
- AnySearch is delegated at agent level when it can close a general, vertical, batch, or URL-extraction evidence gap; it never participates in Smart Search provider fallback.
- Sciverse is explicit-only in this release and does not participate in `research` provider fallback; use `sciverse-*` commands directly for academic relations.

Advanced routing overrides are available through `SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS` and `SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS`. They can reorder or disable registered providers inside their supported capability, but they cannot move a provider across capability boundaries.

Good user-facing smoke prompts:

```powershell
smart-search deep "深度搜索一下最近的比特币行情" --format json
smart-search deep "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --budget deep --format json
smart-search deep "帮我核验这个说法是真是假：某某工具已经完全替代 Tavily 做 AI 搜索了" --format json
smart-search deep "https://example.com/source" --format json
```

## Agentic Research Preview

The Preview adds a caller-controlled research runtime without changing the
default `search`, `deep`, or `research` behavior. It is intended for a Root
Agent that owns planning and synthesis while Smart Search performs
deterministic ResearchRun operations and stores an auditable workspace.

```bash
# Observe currently configured, reachable, and entitled research capabilities.
smart-search research-run capabilities --format json

# Install and check the isolated document sidecar with an explicit Python 3.12.
smart-search research-environment install --python /absolute/path/to/python3.12 --format json
smart-search research-environment doctor --format json

# Open a materialized Research Workspace in the read-only local visualizer.
smart-search research-view /path/to/research-workspace --port 8080
```

`research-run` also exposes `create`, `execute`, `import`, task-addition,
document-mining, claim, decision, citation-verification, and `materialize`
operations. These commands exchange structured JSON dossiers with the calling
Agent; they are not a replacement for the user-facing `research` command.

The dossier, append-only Trace, Artifact Registry, EvidenceItem, and Claim
records are authoritative. Markdown files and the visualizer are readable
projections and do not store hidden reasoning. Provider Research Agents are
attempted only when their capabilities are configured, reachable, and covered
by the current account entitlement. AnySearch is exposed only through Smart
Search and reads its two keys from Smart Search's private configuration. MinerU
remains an external Skill with separately managed credentials.

For a citation-backed final report, Root writes exact `[cite:<citation_id>]`
markers in `draft_report` and submits them with the existing `citations` mapping
to `research-run verify`. With `--workspace`, the same invocation validates the
complete Claim/Evidence/artifact/Trace chain and locators, renders numbered
citations and one References section, and persists three distinct projections:
`final_synthesis.md` for readers, authoritative
`evidence/citation_verification.json` for reverse-trace validation, and derived
`evidence/reference_register.json` for the audit mapping. Manifest entrypoints
are only the Workspace document index. The same contract applies to `quick`,
`standard`, and `deep` Research Workspaces.

The document sidecar requires an explicit Python 3.12 interpreter and creates a
dedicated virtual environment, by default under
`$SMART_SEARCH_CONFIG_DIR/research-sidecar`. Smart Search saves
`SMART_SEARCH_SIDECAR_PYTHON` only after the health check succeeds; it does not
install dependencies into the supplied interpreter itself.

See [Research Runtime Configuration](docs/architecture/research-runtime-config.md),
[Agentic Research architecture](skills/smart-search-cli/references/agentic-research-architecture.md),
and the [smart-search-cli Skill](skills/smart-search-cli/SKILL.md) for the full
contract and orchestration guidance.

The current Preview implementation and acceptance evidence are indexed in the
[Stage G research index](docs/acceptance/stage-g-research-index.md), with a
[portable evidence bundle](docs/research-runs/run-stage-g-seq-20260823T191412Z/README.md)
that can be read on another machine without the ignored local Workspace. These
artifacts are published on the Preview branch only; they do not mean the branch
has been merged or the active macOS Skill has been replaced.

## Provider And API Key Guide

Use `smart-search setup` for normal configuration. Environment variables remain supported for CI and advanced users.
The default interactive setup wizard includes optional smart intent router prompts, so embeddings and classifier routing can be configured without `--advanced`.

| Provider / route | Used for | Main config keys | Official docs | Key / dashboard |
| --- | --- | --- | --- | --- |
| xAI Responses API | Primary live search with `web_search,x_search` tools | `XAI_API_KEY`, `XAI_API_URL`, `XAI_MODEL`, `XAI_TOOLS` | [docs.x.ai](https://docs.x.ai/docs) | [xAI API keys](https://console.x.ai/team/default/api-keys) |
| OpenAI-compatible Chat Completions | Primary search through OpenAI or a compatible relay; no xAI search tools are sent here | `OPENAI_COMPATIBLE_API_URL`, `OPENAI_COMPATIBLE_API_KEY`, `OPENAI_COMPATIBLE_MODEL`, `OPENAI_COMPATIBLE_FALLBACK_MODELS`, `OPENAI_COMPATIBLE_STREAM` | [OpenAI platform docs](https://platform.openai.com/docs) | [OpenAI API keys](https://platform.openai.com/api-keys) or your relay provider |
| Exa | Low-noise official docs, API, paper, product, trusted-page discovery | `EXA_API_KEY` | [Exa docs](https://docs.exa.ai/) | [Exa API keys](https://dashboard.exa.ai/api-keys) |
| Context7 | SDK, library, framework, and API documentation fallback | `CONTEXT7_API_KEY`, `CONTEXT7_BASE_URL` | [Context7 docs](https://context7.com/docs) | [Context7](https://context7.com/) |
| Zhipu Web Search API | Chinese, domestic, current, or domain-filtered web discovery | `ZHIPU_API_KEY`, `ZHIPU_API_URL`, `ZHIPU_SEARCH_ENGINE` | [Zhipu web search docs](https://docs.bigmodel.cn/cn/guide/tools/web-search) | [Zhipu API keys](https://open.bigmodel.cn/usercenter/apikeys) |
| Zhipu Coding Plan Remote MCP | Coding Plan quota web search, page reading, and open-source repo discovery | `ZHIPU_MCP_API_KEY`, `ZHIPU_MCP_SEARCH_API_URL`, `ZHIPU_MCP_READER_API_URL`, `ZHIPU_MCP_ZREAD_API_URL` | [search MCP](https://docs.bigmodel.cn/cn/coding-plan/mcp/search-mcp-server), [reader MCP](https://docs.bigmodel.cn/cn/coding-plan/mcp/reader-mcp-server), [zread MCP](https://docs.bigmodel.cn/cn/coding-plan/mcp/zread-mcp-server) | [Zhipu API keys](https://open.bigmodel.cn/usercenter/apikeys) |
| Tavily | Extra web sources, URL fetch, and site map | `TAVILY_API_URL`, `TAVILY_API_KEY`, `TAVILY_ENABLED` | [Tavily docs](https://docs.tavily.com/) | [Tavily app](https://app.tavily.com/home) |
| Jina Reader | Known URL page extraction for `web_fetch`; key required for standard minimum profile | `JINA_API_KEY`, `JINA_READER_API_URL`, `JINA_RESPOND_WITH`, `JINA_TIMEOUT_SECONDS` | [Jina Reader](https://jina.ai/reader/) | [Jina AI](https://jina.ai/) |
| Firecrawl | Fetch fallback and supplementary web sources | `FIRECRAWL_API_URL`, `FIRECRAWL_API_KEY` | [Firecrawl docs](https://docs.firecrawl.dev/) | [Firecrawl API keys](https://www.firecrawl.dev/app/api-keys) |
| AnySearch Skill | Agent-level general, vertical, batch, and URL extraction through the bundled adapter at `bundled-skills/anysearch/scripts/smart_search_anysearch.py` | `ANYSEARCH_API_KEY`, `ANYSEARCH_API_KEY_FALLBACK` in Smart Search private config | [AnySearch docs](https://www.anysearch.com/docs) | [AnySearch API keys](https://www.anysearch.com/console/api-keys) |
| Sciverse | Explicit experimental academic search, semantic paper retrieval, document chunks, and citation/reference relations; not a default fallback | `SCIVERSE_API_TOKEN`, `SCIVERSE_API_URL`, `SCIVERSE_TIMEOUT_SECONDS` | [Sciverse Agent Tools](https://github.com/opendatalab/Sciverse-Agent-Tools) | Sciverse dashboard / token provider |

Intent router configuration:

| Key | Purpose |
| --- | --- |
| `SMART_SEARCH_INTENT_ROUTER` | `hybrid`, `rules`, or `off`; default `hybrid` |
| `INTENT_EMBEDDING_API_URL` | Optional OpenAI-compatible embeddings endpoint for semantic capability routing; recommended setup preset uses `https://api.siliconflow.cn/v1/embeddings` |
| `INTENT_EMBEDDING_API_KEY` | Optional embeddings API key; masked by `doctor` and config output |
| `INTENT_EMBEDDING_MODEL` | Embeddings model name; recommended setup preset uses `Qwen/Qwen3-Embedding-8B` |
| `INTENT_EMBEDDING_THRESHOLD` | Semantic route threshold, default `0.74`; recommended 8B setup value `0.475`; model-specific |
| `INTENT_EMBEDDING_MARGIN` | Required top-vs-second semantic margin, default `0.05`; recommended 8B setup value `0.053`; ambiguous matches remain signals only |
| `INTENT_CLASSIFIER_API_URL` | Optional OpenAI-compatible chat-completions endpoint for structured intent classification |
| `INTENT_CLASSIFIER_API_KEY` | Optional classifier API key; masked by `doctor` and config output |
| `INTENT_CLASSIFIER_MODEL` | Classifier model name |
| `INTENT_ROUTER_TIMEOUT_SECONDS` | Timeout for optional remote router calls, default `8` |

Default `hybrid` is fail-open: if embeddings or classifier settings are missing or fail, routing records `degraded_reason` and falls back to local rules. Semantic routing may add a capability only when the top similarity score is at least `INTENT_EMBEDDING_THRESHOLD` and the top-vs-second score gap is at least `INTENT_EMBEDDING_MARGIN`; otherwise it records an ambiguous signal without adding a capability. The classifier may add capabilities, but unknown capability names and provider names are ignored. Providers are still selected only by capability.

For normal setup, use the Qwen3-Embedding-8B preset: `INTENT_EMBEDDING_API_URL=https://api.siliconflow.cn/v1/embeddings`, `INTENT_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B`, `INTENT_EMBEDDING_THRESHOLD=0.475`, and `INTENT_EMBEDDING_MARGIN=0.053`. `smart-search setup` automatically fills the 8B threshold/margin when the 8B model is selected and those values are not already configured.

Embedding cosine scores are model-specific. Keep `route-calibrate` for advanced re-checks: run it after changing `INTENT_EMBEDDING_MODEL`, changing embedding endpoints, or expanding the real query calibration set:

```powershell
smart-search route-calibrate --models "Qwen/Qwen3-Embedding-8B" --format markdown
```

Use the report's recommended `INTENT_EMBEDDING_THRESHOLD` and `INTENT_EMBEDDING_MARGIN` before judging routing quality. The primary calibration metric is semantic-only Macro-F1; full-route Macro-F1 is reported to verify rules/classifier fallback behavior.

Important boundaries:

- xAI official live search uses the Responses API `/responses` route through `XAI_*`. Compatible relays and gateways use Chat Completions `/chat/completions` through `OPENAI_COMPATIBLE_*`.
- `OPENAI_COMPATIBLE_STREAM=true` or `smart-search search --stream` sets `stream=true` only for OpenAI-compatible `search` and provider-side `fetch` calls. It is a relay compatibility switch for long requests and does not change xAI Responses behavior, URL description, or source ranking.
- `OPENAI_COMPATIBLE_FALLBACK_MODELS` is fail-over, not a time slice. The primary model keeps the remaining `--timeout` budget. A fallback model is tried only after a hard failure such as `model_not_found`, auth, empty content, or a non-retryable protocol error. `doctor` and `diagnose openai-compatible` warn when a configured fallback id is missing from `/models`.
- Legacy `SMART_SEARCH_API_URL`, `SMART_SEARCH_API_KEY`, `SMART_SEARCH_API_MODE`, `SMART_SEARCH_MODEL`, and `SMART_SEARCH_XAI_TOOLS` are not supported config keys. Use `XAI_*` or `OPENAI_COMPATIBLE_*` explicitly.
- Do not force xAI `web_search` / `x_search` tools or legacy `search_parameters` into the OpenAI-compatible Chat Completions route.
- `zhipu-search` support is the Web Search API route, not Zhipu Chat Completions `tools=[web_search]`, not Search Agent, and not the MCP Server.
- Zhipu Coding Plan support is a separate Remote MCP route. `web_search_prime` maps to `web_search`, `webReader` maps to `web_fetch`, and zread tools map to explicit repo/docs discovery commands. It is not mixed into the existing `/paas/v4/web_search` Zhipu REST provider.
- Zhipu Coding Plan MCP requires its own Coding Plan entitlement. A normal `ZHIPU_API_KEY` for Web Search API does not prove `zhipu-mcp-search` or zread access. If `ZHIPU_MCP_API_KEY` is absent or unauthorized, Smart Search skips those MCP providers; the `standard` minimum profile and same-capability fallback still work through the configured REST/search/fetch providers.
- Jina Reader is not a general search provider. `JINA_API_KEY` is required for Jina to count toward `standard`; `JINA_RESPOND_WITH=readerlm-v2` also requires `JINA_API_KEY`.
- `ZHIPU_SEARCH_ENGINE` defaults to `search_std`. Supported official values include `search_std`, `search_pro`, `search_pro_sogou`, and `search_pro_quark`; custom values remain allowed for future services.
- `TAVILY_API_URL` affects Tavily only. It does not proxy Zhipu. For Tavily Hikari / pooled endpoints, use `https://<host>/api/tavily`; setup normalizes root-host or `/mcp` inputs to that REST base.
- `TAVILY_ENABLED` defaults to `true`. Set it to `false` to disable Tavily even when a key is present: Tavily is removed from web-search and fetch routing, direct Tavily calls and `doctor` make no Tavily request, and `map` returns a local configuration error. This does not enable Firecrawl or change same-capability fallback boundaries.
- `FIRECRAWL_API_URL` defaults to `https://api.firecrawl.dev/v2`.
- AnySearch is not a provider, setup-wizard capability, or separately discoverable Skill. The agent reads `bundled-skills/anysearch/CONTRACT.md` inside the Smart Search workflow and follows that internal contract without requiring a separate slash invocation. The bundled adapter reads its two key fields from Smart Search's existing private `config.json`; setup does not print or migrate their values. The bundled snapshot is refreshed from `jason-liao-skills/main/skill-packages/anysearch`; the official repository is used only when the preferred repository is reachable and that package is absent.
- Sciverse uses native HTTP/OpenAPI at `https://api.sciverse.space` by default. It requires `SCIVERSE_API_TOKEN`, returns `config_error` without a network request when the token is absent, sends `Authorization: Bearer ...` when configured, and remains explicit-only: not `docs_search`, not `standard`, and not default `search` / `research` fallback.
- `doctor` and `route` report intent router status, embedding model, threshold, margin, their config source, timeout, and degradation behavior. They do not expose router API keys.

Non-interactive setup example:

```powershell
smart-search setup --non-interactive `
  --xai-api-key "your-xai-key" `
  --xai-model "grok-4-fast" `
  --openai-compatible-api-url "https://api.openai.com/v1" `
  --openai-compatible-api-key "your-openai-or-relay-key" `
  --openai-compatible-model "gpt-4.1" `
  --openai-compatible-stream "false" `
  --validation-level "balanced" `
  --fallback-mode "auto" `
  --minimum-profile "standard" `
  --intent-router "hybrid" `
  --intent-embedding-api-url "https://api.siliconflow.cn/v1/embeddings" `
  --intent-embedding-api-key "your-siliconflow-key" `
  --intent-embedding-model "Qwen/Qwen3-Embedding-8B" `
  --intent-embedding-threshold "0.475" `
  --intent-embedding-margin "0.053" `
  --exa-key "your-exa-key" `
  --context7-key "your-context7-key" `
  --zhipu-key "your-zhipu-key" `
  --zhipu-api-url "https://open.bigmodel.cn/api" `
  --zhipu-search-engine "search_pro_sogou" `
  --zhipu-mcp-key "your-zhipu-coding-plan-key" `
  --jina-key "your-jina-key" `
  --tavily-api-url "https://api.tavily.com" `
  --tavily-key "your-tavily-key" `
  --firecrawl-api-url "https://api.firecrawl.dev/v2" `
  --firecrawl-key "your-firecrawl-key"
```

Minimum profile defaults to `standard`, requiring at least:

- one `main_search` provider: xAI Responses or OpenAI-compatible;
- one `docs_search` provider: Exa or Context7;
- one `web_fetch` provider: Tavily, Jina with `JINA_API_KEY`, Zhipu Coding Plan MCP Reader, or Firecrawl.

Missing required capabilities fail closed with a configuration error. Use `SMART_SEARCH_MINIMUM_PROFILE=off` only for local experiments.

AnySearch is optional and does not satisfy or change the `standard` minimum profile. The bundled adapter reads its ordered dual keys from Smart Search's private `config.json`; an ignored `.env` may remain as an upstream snapshot artifact but is not a credential source. Snapshot updates preserve `.env`, `runtime.conf`, and the adapter, and none of these local files or private config is committed.

Experimental Sciverse configuration is also optional and does not satisfy or change the `standard` minimum profile:

```powershell
smart-search setup --non-interactive --sciverse-token "your-sciverse-token" --sciverse-api-url "https://api.sciverse.space"
smart-search sciverse-catalog --collection papers --format json
smart-search sciverse-search "transformer retrieval" --year-from 2020 --page-size 5 --format json
smart-search sciverse-semantic "attention mechanism" --top-k 3 --mode balanced --format json
smart-search sciverse-read "doc-id-from-search" --offset 0 --limit 4096 --format json
smart-search sciverse-relations "unique-id-from-search" --relation CITATIONS --page-size 25 --format json
```

Use `doc_id` for `sciverse-read` and `unique_id` for `sciverse-relations`. `CITATIONS` means papers citing the target paper; `REFERENCES` means papers cited by the target paper; `RELATED_WORKS` means related work suggestions. `--filters-advanced` and `--sort-advanced` accept JSON arrays for fields not promoted to first-class CLI flags.

Local config path:

- Windows default: `%LOCALAPPDATA%\smart-search\config.json`.
- Linux/macOS default: `~/.config/smart-search/config.json`.
- `SMART_SEARCH_CONFIG_DIR` is an advanced override for CI, containers, sandboxes, or portable installs.
- `SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS` and `SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS` are advanced `research` routing overrides. They accept provider CSV values and can only reorder or disable providers inside existing capability boundaries.
- Earlier Windows source builds defaulted to `~\.config\smart-search\config.json`, while some installs were already pinned to `%LOCALAPPDATA%\smart-search` through `SMART_SEARCH_CONFIG_DIR`. If the new Windows default file is missing but the old home config exists, Smart Search reads the old file as `legacy_windows_home` so upgrades do not lose configuration. `doctor` reports the active path, default path, old home path, `SMART_SEARCH_CONFIG_DIR`, and whether that override merely matches the current default.

Provider timeouts:

- `search --timeout` defaults to `120` seconds and is the initial wait window for xAI Responses. When it expires, Smart Search polls `GET /v1/request-status/{request_id}` on compatible gateways and keeps waiting while the request is running.
- `search --max-try N` replays only explicit terminal xAI HTTP 504 failures; it defaults to five logical attempts.
- `XAI_SOFT_TIMEOUT_SECONDS` defaults to `120` for direct provider calls without a CLI timeout. `XAI_STATUS_POLL_SECONDS` defaults to `15` and `XAI_HARD_TIMEOUT_SECONDS` defaults to `7200`.
- Gateways without the request-status extension are treated as unknown and remain bounded by `XAI_HARD_TIMEOUT_SECONDS`.
- The hard deadline covers connection attempts, retry waits, response waiting, and status polling. Automatic retries are limited to connection failures that happen before request submission; protocol or terminal-state failures after submission are returned without replaying the request.
- `TAVILY_ENABLED` accepts `true`, `1`, or `yes` as enabled; any other value disables Tavily without making a Tavily network request.
- `TAVILY_TIMEOUT_SECONDS` controls the Tavily `doctor` connectivity check timeout and defaults to `30`.
- `SCIVERSE_TIMEOUT_SECONDS` controls explicit Sciverse academic API calls and defaults to `30`.
- Raise `TAVILY_TIMEOUT_SECONDS` for slower Tavily Hikari / pooled / community endpoints before treating the provider as unhealthy.

## Commands

| Command | Alias | Purpose |
| --- | --- | --- |
| `search` | `s` | Fast live search and broad synthesis |
| `route` | `rt` | Explain required capabilities without running providers |
| `deep` | `dr` | Offline Deep Research plan |
| `research` | `rs` | Live Deep Research execution |
| `research-run` | `rr` | Deterministic Agent-facing ResearchRun dossier operations |
| `research-view` | `rv` | Read-only local Research Workspace visualizer |
| `research-environment` | `research-env`, `renv` | Install or health-check the isolated Python 3.12 document sidecar |
| `fetch` | `f` | Fetch one URL as JSON, Markdown, or content |
| `map` | `m` | Map a website structure |
| `exa-search` | `exa`, `x` | Exa source discovery |
| `exa-similar` | `xs` | Similar pages from one URL |
| `zhipu-search` | `z`, `zp` | Zhipu Web Search API |
| `zhipu-mcp-search` | `zmcp-search` | Zhipu Coding Plan MCP `web_search_prime` |
| `zhipu-mcp-reader` | `zmcp-reader` | Zhipu Coding Plan MCP `webReader` |
| `zhipu-mcp-search-doc` | `zmcp-doc` | Search open-source repository docs through zread MCP |
| `zhipu-mcp-repo-structure` | `zmcp-tree` | Read repository structure through zread MCP |
| `zhipu-mcp-read-file` | `zmcp-file` | Read one repository file through zread MCP |
| `sciverse-catalog` | `sv-catalog` | Experimental Sciverse academic field catalog |
| `sciverse-search` | `sv-search`, `sv` | Experimental Sciverse structured academic search |
| `sciverse-semantic` | `sv-semantic` | Experimental Sciverse semantic paper search |
| `sciverse-read` | `sv-read` | Experimental Sciverse document chunk read by `doc_id` |
| `sciverse-relations` | `sv-relations` | Experimental Sciverse citation/reference/related-work relations by `unique_id` |
| `context7-library` | `c7`, `ctx7` | Resolve Context7 library candidates |
| `context7-docs` | `c7d`, `c7docs`, `ctx7-docs` | Fetch Context7 docs |
| `route-calibrate` | `route-cal`, `rcal` | Evaluate embedding router models and recommend threshold/margin |
| `doctor` | `d` | Masked config and connectivity check |
| `diagnose` | `diag` | Focused OpenAI-compatible troubleshooting report |
| `setup` | `init` | Interactive or scripted setup |
| `config` | `cfg` | Local config read/write |
| `model` | `mdl` | Show explicit provider model settings; use `config set XAI_MODEL` or `OPENAI_COMPATIBLE_MODEL` to change them |
| `smoke` | `sm` | Provider routing smoke tests |
| `regression` | `reg` | Offline regression checks |

Smoke output includes `status` (`healthy`, `degraded`, or `failed`) and explicit `skipped_cases`. A healthy or degraded smoke report remains `ok: true` with exit code `0`; only failed smoke is non-zero.

Useful examples:

```powershell
smart-search search "query" --validation balanced --extra-sources 3 --timeout 90 --format json --output result.json
smart-search route "React useEffect API docs" --format markdown
smart-search route-calibrate --models "Qwen/Qwen3-Embedding-8B" --format markdown
smart-search research "query" --budget deep --fallback auto --format json --output research.json
smart-search search "query" --stream --format json
smart-search search "query" --no-stream --format json
smart-search config set OPENAI_COMPATIBLE_FALLBACK_MODELS "grok-4.3-fast" --format json
smart-search search "nba report" --format content
smart-search exa-search "OpenAI Responses API documentation" --include-domains platform.openai.com developers.openai.com --num-results 5 --include-text --format json
smart-search context7-library "react" "hooks" --format json
smart-search context7-docs "/reactjs/react.dev" "useEffect cleanup" --format json
smart-search zhipu-search "today China AI news" --search-engine search_pro_sogou --count 5 --format json
smart-search zhipu-mcp-search "today China AI news" --count 5 --format json
smart-search zhipu-mcp-reader "https://example.com/source" --format json
smart-search zhipu-mcp-search-doc "owner/repo" "install" --format json
smart-search sciverse-search "transformer retrieval" --year-from 2020 --page-size 5 --format json
smart-search sciverse-relations "unique-id-from-search" --relation CITATIONS --format json
smart-search exa-similar "https://example.com/source" --num-results 5 --format json
smart-search fetch "https://example.com/source" --format markdown --output page.md
smart-search map "https://docs.example.com" --instructions "Find API reference pages" --max-depth 1 --limit 50 --format json
smart-search doctor --format markdown
smart-search diagnose openai-compatible --format markdown
smart-search smoke --mock --format json
smart-search regression
```

## Output And Evidence Policy

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

## Troubleshooting

If `doctor` reports `config_error`:

```powershell
smart-search setup
smart-search config list --format json
smart-search doctor --format markdown
```

If OpenAI-compatible `search` hangs or times out after `doctor` passes:

```powershell
smart-search doctor --format markdown
smart-search diagnose openai-compatible --format markdown
```

The diagnose report masks the API key and says whether the problem is missing config, the upstream/relay hanging on the real Smart Search prompt, or a stream/no-stream compatibility mismatch.

If search is slow:

- reduce `--extra-sources`;
- split broad questions into smaller queries;
- use `exa-search` or `zhipu-search` for source discovery, then `fetch` key pages.

If installed CLI health is uncertain:

```powershell
smart-search --help
smart-search --version
smart-search regression
smart-search smoke --mock --format json
```

On Windows npm/mise installs, verify non-ASCII JSON piping:

```powershell
smart-search deep "深度搜索一下最近的比特币行情" --format json | ConvertFrom-Json
```

## Development

```powershell
.\.venv\Scripts\python.exe -m compileall -q src tests
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m smart_search.cli regression
.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json
npm test
npm pack --dry-run
```

## Latest stable release notes

### v0.1.15

This stable release contains the provider reliability and packaging hardening work validated through source, live-provider, and packed-install release gates.

- Context7 automatic documentation selection now requires query-subject overlap with the candidate title or id; same-capability Exa fallback handles empty or low-confidence results.
- AnySearch moved out of the Smart Search provider layer and is delegated through the bundled AnySearch adapter.
- Provider failures use a consistent error taxonomy, and `TAVILY_ENABLED=false` prevents accidental Tavily routing or network requests.
- Mock and live smoke reports distinguish healthy, degraded, failed, and skipped checks.
- Release safety includes a read-only CI matrix, public/package Skill parity, and a fresh temporary-prefix tarball install smoke.
- npm release publication is serialized, and stable merge or squash commits no longer race into an automatic beta publication.

## Release lanes

Stable releases use Git tags and npm `latest`:

```powershell
git tag vX.Y.Z
git push origin vX.Y.Z
```

Test releases use npm prereleases and do not move `latest`. A push to `main` publishes the next `<package.json version>-beta.N` version under npm dist-tag `next`; `N` resets for each stable base version. Before creating a beta, the workflow compares the current stable `package.json` version with its first parent, so a merge or squash release bump skips the beta and the matching `vX.Y.Z` tag publishes npm `latest`. The `chore(release): bump version to X.Y.Z` title remains a legacy fallback. For example, after `0.1.10-beta.1` and `0.1.10-beta.2`, the next `main` publish is `0.1.10-beta.3`.

GitHub Actions also supports manual backfill for historical test builds through `workflow_dispatch`. Use an explicit `target_ref` plus an exact version such as `0.1.9-beta.1`, and publish it with a non-`latest` tag such as `backfill`. npm versions are immutable: old `*-dev.*` packages cannot be renamed in place, only superseded by new `*-beta.N` packages and optionally deprecated later with npm owner credentials.

Stable GitHub releases read optional body text from `.github/releases/vX.Y.Z.md` and append npm package, dist-tag, and workflow-run metadata automatically. Add that file before tagging a stable version so the GitHub Release page explains what changed instead of only listing package metadata.

The read-only `CI` workflow runs on pull requests, pushes to `main`, and manual dispatch. It verifies Ubuntu Node 18/Python 3.10, Ubuntu Node 24/Python 3.12, and Windows Node 22/Python 3.12 without publishing. Its package gate checks public/package skill parity, packs a real tarball, installs it under a fresh temporary npm prefix, and runs version, packaged regression, and mock smoke there.

Release closeout checklist:

1. Verify the registry and tags before changing anything: `npm view @konbakuyomu/smart-search versions --json`, `npm view @konbakuyomu/smart-search dist-tags --json`, and `gh release list --repo konbakuyomu/smartsearch --limit 100`.
2. For historical beta backfill, publish the replacement `*-beta.N` package through Actions with `create_github_release=false` if the workflow token cannot create releases, then create the missing GitHub prerelease locally with `gh release create vX.Y.Z-beta.N --target <commit> --prerelease --latest=false`.
3. Treat npm `E409` during parallel backfills as a registry concurrency failure, not a version-design failure. Re-run the affected version serially after checking whether the package already exists.
4. Do a machine-readable gap check: expected beta versions minus npm versions must be empty, and expected `v*beta*` releases minus GitHub prereleases must be empty.
5. Install the selected test build explicitly, for example `mise use -g "npm:@konbakuyomu/smart-search@0.1.10-beta.3" -y --pin`, then run `mise reshim`, `where.exe smart-search`, `smart-search --version`, `smart-search regression`, `smart-search smoke --mock --format json`, and a non-ASCII JSON pipe such as `smart-search deep "深度搜索一下最近的比特币行情" --format json | ConvertFrom-Json`.

## License

MIT
