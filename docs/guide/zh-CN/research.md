[手册目录](../README.md) · [English](../en/research.md)

# 搜索与研究

## CLI 与 AI 的职责

它是一个普通命令行工具，不提供 MCP Server。AI 工具通过 `smart-search-cli` skill 调它，脚本和终端用户也可以直接调它：

```powershell
smart-search search "今天 OpenAI Responses API 有什么新变化" --format json
smart-search fetch "https://example.com/article" --format markdown
smart-search deep "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --format json
smart-search research "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --format markdown
```

当前架构分两层：

| 层 | 负责什么 |
| --- | --- |
| CLI 执行层 | 稳定执行命令、provider 路由、同能力兜底、JSON/Markdown 输出、本机配置、smoke/regression |
| Skill / AI 编排层 | 判断用户意图，决定普通搜索还是 Deep Research，按计划执行 CLI 积木，最后写出有来源支撑的回答 |

`smart-search search` 保持快速、直接联网。`smart-search deep` 是显式 Deep Research 离线规划入口：默认不联网、不跑 provider、不抓网页，只输出 `research_plan`。真正联网可以由 AI 或用户继续执行 `steps[].command`，也可以交给新的 `smart-search research` live 执行器完成。`research` 会按 plan -> discover -> fetch/read -> gap check -> evidence-only synthesis 执行。

现在意图路由单独成了一层。可以把它理解成“更聪明的分诊台”：先判断用户到底需要哪些能力，再让已有 provider 注册表在同一能力内兜底，而不是让模型直接乱选 provider：

```text
用户问题
 -> 规则路由：URL、文档/实时/抓取/垂直搜索硬信号、strict 校验
 -> 语义路由：可选 embeddings，对典型例句做相似度
 -> 模型路由：可选小模型输出结构化能力分类
 -> 合并成 required_capabilities
 -> 在 docs_search / web_search / web_fetch / vertical_search 内选择 provider 和兜底
```

`smart-search route "query"` 只解释这次会需要哪些能力，不执行搜索、文档查询、网页抓取或 provider 调用。`smart-search deep` 仍保持离线 planner 契约，只使用本地/rules 信号。

## 能力与服务商

| 能力 | 主要命令 | Provider | 负责什么 |
| --- | --- | --- | --- |
| `main_search` | `search` | xAI Responses、OpenAI-compatible Chat Completions 或 Responses | 综合回答、快速搜索、初步总结 |
| `docs_search` | `context7-library`、`context7-docs`、`exa-search` | Context7、Exa | 官方文档、SDK、API、框架/库文档 |
| `web_search` | `zhipu-search`、`zhipu-mcp-search`、`search` 内部意图补强 | 智谱 Web Search API、智谱 Coding Plan MCP、Tavily、Firecrawl、TinyFish | 中文、国内、时效、域名过滤、补充来源 |
| `web_fetch` | `fetch`、`zhipu-mcp-reader` | Tavily、Jina Reader、智谱 Coding Plan MCP Reader、Firecrawl、TinyFish | 已知 URL 正文抓取、证据提取 |
| `vertical_search` | `anysearch-domains`、`anysearch-search`、`anysearch-extract`、`anysearch-batch`、`sciverse-catalog`、`sciverse-search`、`sciverse-semantic`、`sciverse-read`、`sciverse-relations` | AnySearch 和 Sciverse（实验） | 显式结构化垂直域；Sciverse 覆盖学术文献检索、语义搜索、正文片段和引用关系 |
| `site_map` | `map` | Tavily | 文档站、产品站、目录型站点结构 |
| `deep_planner` | `deep` / `dr` | 本地 planner | 离线生成 Deep Research 计划，不默认联网 |
| `research_executor` | `research` / `rs` | 按 capability 注册的 provider | live 深度研究执行：规划、发现、抓取/读取、gap check、仅基于证据综合 |

同能力兜底关系：

| 能力 | 兜底链 |
| --- | --- |
| `main_search` | xAI Responses -> OpenAI-compatible |
| `docs_search` | Context7 只在库主体命中候选 title/id 时使用；低置信度或空 Context7 命中后由 Exa 同能力兜底，并处理官方域名、论文、产品页、可信站点发现 |
| `web_search` | 智谱 Web Search API -> 智谱 Coding Plan MCP `web_search_prime` -> Tavily -> Firecrawl -> TinyFish |
| `web_fetch` | Tavily -> 带 `JINA_API_KEY` 的 Jina Reader -> 智谱 Coding Plan MCP `webReader` -> Firecrawl -> TinyFish |

TinyFish 是可选的 `web_search` + `web_fetch` provider，两段能力共用同一个 `TINYFISH_API_KEY`。它不满足 `main_search` 和 `docs_search`，并且排在所有既有 provider 之后，因此不会改变当前配置的行为和顺序。

AnySearch 和 Sciverse 当前都只作为实验 `vertical_search` 暴露，不进入 `web_search` 兜底链，也不是 `standard` 最低配置要求。Sciverse 也不是 `docs_search`，不会加入默认 `search` / `research` 路由；需要学术字段、语义论文命中、正文片段或引用/参考文献关系时，请显式运行 `sciverse-*` 命令。

Jina Reader 只属于 `web_fetch`，不是通用搜索 provider。只有配置 `JINA_API_KEY` 后，它才可以满足 `SMART_SEARCH_MINIMUM_PROFILE=standard`；匿名 `r.jina.ai` 只能当显式/实验抓取能力，不能让最低配置检查放松。

这里有一个重要边界：兜底只在同一类能力里发生。不会用 Context7 去查普通新闻，也不会用 Firecrawl 假装做文档语义检索。

输出里会保留可观测字段：

| 字段 | 作用 |
| --- | --- |
| `routing_decision` | 为什么触发了某些补强路径 |
| `provider_attempts` | 每个 provider 的尝试结果 |
| `providers_used` | 最终用到哪些 provider |
| `fallback_used` | 是否触发同能力兜底 |
| `primary_sources` | 主搜索回答里带出的来源 |
| `extra_sources` | Tavily / Firecrawl 等额外发现的候选来源 |
| `source_warning` | 来源和回答之间可能存在的证据边界提醒 |

`routing_decision` 会保留旧字段：`docs_intent`、`zh_current_intent`、`web_current_intent`、`fetch_intent`、`supplemental_paths`；同时新增统一路由字段：`intent_router_mode`、`required_capabilities`、`intent_signals`、`confidence`、`router_engines_used`、`degraded_reason`。

`extra_sources` 只是候选来源，不等于自动事实校验。新闻、政策、财经、医疗、严肃评测、工具选型等高风险问题，建议先发现来源，再 `fetch` 关键网页正文，最后只基于抓到的正文写结论。

搜索引擎选择速记：先用 `search` 做宽泛探索和综合；想让 CLI 执行完整证据流时用 `research`；中文、国内、政策、公告、当前新闻优先补 `zhipu-search`；只有明确要用 Coding Plan 额度时才走 `zhipu-mcp-*`；库/API/框架文档优先用 Context7；官方域名、论文、产品页、可信站点和低噪声发现再用 Exa；Tavily/Firecrawl 通过 `search --extra-sources` 做横向候选，通过 `fetch` 做正文证据；Jina 用于已知 URL 正文抓取；AnySearch 只在明确要实验性垂直搜索时使用；Sciverse 只在明确要学术 catalog/search/semantic/read/relations 时使用。

## 研究规划与执行

普通问题用：

```powershell
smart-search search "React useEffect cleanup 文档" --format json
```

需要先拆解、规划、再由你或 AI 分步执行时用：

```powershell
smart-search deep "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --budget deep --format json
smart-search dr "https://example.com/source" --format json
```

Deep Research 不是固定题材配方。行情、选型、技术文档、新闻政策、真假核验、用户给 URL 这些只是用户语言示例，不是 schema 枚举。它会先抽取 `intent_signals`，再生成 `decomposition` 和 `capability_plan`。

计划里会包含：

- `mode="deep_research"` 和 `query_mode="deep"`；
- `intent_signals`：是否强时效、是否 docs/API、是否给 URL、是否高风险、是否需要权威来源、是否需要交叉验证；
- `decomposition`：复杂问题拆成 1-6 个子问题；
- `capability_plan`：选择需要的能力；
- `steps[]`：每一步的 `tool`、`purpose`、`command`、`output_path`、`subquestion_id`；
- `evidence_policy="fetch_before_claim"`；
- `gap_check`：关键结论没有正文证据就继续抓，或者降级成未验证候选。
- `usage_boundary`：说明 `search` 是直接联网，`deep` 是离线规划，真正执行发生在计划命令里。

Deep Research 只允许组合现有 CLI 积木：

```text
search, exa-search, exa-similar, zhipu-search, context7-library, context7-docs, fetch, map
```

`doctor` 是 preflight 配置预检，不是 research step。`smart-search deep` 这一步本身是离线 planner；后续执行计划里的 `steps[].command` 时才会联网。

换句话说，`doctor` 只是配置预检；它帮助 AI 判断当前 provider 是否可用，但不算 Deep Research 的取证步骤。

如果你希望 CLI 直接执行完整 live Deep Research，用：

```powershell
smart-search research "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --budget deep --fallback auto --format json
smart-search rs "https://example.com/source" --fallback off --format markdown
```

`research` 会执行 plan -> discover -> fetch/read -> gap check -> evidence-only synthesis。默认 `--fallback auto`，会在同一 capability 内兜底；`--fallback off` 只尝试每个 capability 选中的第一个 provider，适合手动调试某个 provider。

`research` JSON 会包含 `final_answer`、`citations`、`evidence_items`、`gap_check`、`provider_attempts`、`fallback_used`、`degraded`、`route_policy_version` 和 `evidence_dir`。发现阶段的 snippet 只是候选，不会直接变成 citation；只有 fetch/read 到正文的来源才会被引用。兜底仍然补不齐证据时，`research` 会降级输出 gap，不会编造结论。

`research` 的路由是 capability-first 加 provider 优势：

- Context7 优先处理库/API/框架文档，但自动选择必须让查询主体词命中候选的 title 或 id。description、trust、benchmark 只用于同类候选的次级排序；没有合格候选时 Context7 记为空，再由同能力 Exa 兜底。
- 智谱 Web Search API 优先处理中文、国内、时效、政策、公告搜索。
- 智谱 Coding Plan MCP 仍是单独额度路线，通过 `web_search_prime` 和 `webReader` 加入对应 capability。
- Jina 优先用于已知公开 URL、PDF、arXiv 正文抽取；ReaderLM-v2 仍要求 `JINA_API_KEY`。
- Firecrawl 优先用于 JS-heavy、动态页面、浏览器式抽取、OCR/PDF 或强兜底抓取。
- AnySearch 只在垂直意图清楚时加入，例如 CVE、金融、法律、学术、代码库/仓库搜索。
- Sciverse 第一版是 explicit-only，不参与 `research` provider 兜底；学术引用关系请直接使用 `sciverse-*` 命令。

高级路由覆盖项是 `SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS` 和 `SMART_SEARCH_RESEARCH_DISABLED_PROVIDERS`。它们只能在 provider 已支持的 capability 内调整顺序或禁用，不能把 provider 移到另一个 capability。

可以用这些标准问题测试是否进入深搜模式：

```powershell
smart-search deep "深度搜索一下最近的比特币行情" --format json
smart-search deep "OpenAI Responses API web_search 和 Chat Completions 联网搜索怎么选" --budget deep --format json
smart-search deep "帮我核验这个说法是真是假：某某工具已经完全替代 Tavily 做 AI 搜索了" --format json
smart-search deep "https://example.com/source" --format json
```

看到输出里有 `mode=deep_research`、`decomposition`、多步 `steps`、`evidence_policy=fetch_before_claim`、`preflight.executed_by_deep_command=false`，就说明已经进入 Deep Research 计划模式。

## 输出与证据

AI 和脚本解析优先用 JSON：

```powershell
smart-search search "query" --format json
smart-search doctor --format json
```

给人看连接状态、详细排障报告、冒烟结果、来源列表、网页正文时用 Markdown：

```powershell
smart-search doctor --format markdown
smart-search smoke --mock --format markdown
smart-search exa-search "OpenAI Responses API documentation" --format markdown
smart-search fetch "https://example.com" --format markdown
```

终端快速扫正文或摘要用 content：

```powershell
smart-search search "nba战报" --format content
smart-search doctor --format content
```

`content` 刻意保持很短，只适合快速看结论。完整排障给人看用 `doctor --format markdown`，给脚本和 AI 解析用 `doctor --format json`。

主答案已经生成、但可选阶段到达 deadline 时，JSON 会保留主答案和已完成来源，并返回 `partial_success=true`；重试或扩展来源前先查看 `timeout_phase`、`timed_out_phases` 和 `phase_attempts`。

多来源研究建议显式指定稳定目录保存证据文件。默认使用平台临时目录，以 Windows 显式路径为例：

```powershell
smart-search exa-search "Reuters Iran Hormuz latest" --format json --output C:\tmp\smart-search-evidence\iran-hormuz\01-exa.json
smart-search fetch "https://example.com/source" --format markdown --output C:\tmp\smart-search-evidence\iran-hormuz\02-fetch.md
```

写 claim-level 结论时建议流程：

1. 用 `search`、`exa-search`、`zhipu-search` 或 `exa-similar` 找候选 URL。
2. 用 `fetch` 抓关键 URL 正文。
3. 最终回答只引用 fetch 正文能支撑的事实。
4. 没有 fetch 的来源标为未验证候选。
