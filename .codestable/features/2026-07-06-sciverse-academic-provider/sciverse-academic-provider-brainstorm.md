---
doc_type: feature-brainstorm
feature: 2026-07-06-sciverse-academic-provider
status: confirmed
summary: 以实验性 vertical_search provider 方式接入 Sciverse，第一版提供显式学术检索与引用关系命令，不进入默认路由。
tags: [provider, vertical_search, academic, sciverse, experimental]
---

# Sciverse 学术检索 Provider Brainstorm

> Stage 0 | 2026-07-06 | 下一步：design

## 想做什么、为什么

GitHub issue #18 提议把 Sciverse 接入为学术文献检索 provider。这个方向值得采纳，但不应该把它当成普通网页搜索或通用 docs_search 的替代品。

核心原因是：Sciverse 的价值不只是“搜到论文网页”，而是把学术文献当结构化对象处理。它能做字段 catalog、结构化论文检索、语义片段召回、全文切片读取，以及引用/被引/相关工作关系分页。这里真正补上的空白，是 Smart Search 目前 Exa / AnySearch 都不擅长的“结构化学术证据 + 引用网络”能力。

不过它仍应保守接入。学术 provider 的 token、配额、字段 schema、全文可读性和引用关系语义都比普通 provider 更复杂，第一版应该先作为显式实验能力存在，不进入 `standard` 最低配置，也不自动参与默认 `search` / `research` fallback。

## 考虑过的方向

### 方向 A：拒绝 #18，继续依赖 Exa / AnySearch

- 描述 / 价值 / 代价：实现成本最低，也不会增加 provider 维护面；但学术场景仍只能靠网页相关度或通用 vertical 结果，缺少 DOI/作者/期刊/年份/开放获取状态等结构化过滤，也没有引用网络。
- 结论：否决。#18 指向的是一个真实能力缺口，不是重复 provider。

### 方向 B：把 Sciverse 放进 `docs_search`

- 描述 / 价值 / 代价：论文确实有“文档”属性，路由上看似能复用 docs_search；但 docs_search 当前主要服务库/API/官方文档，自动混入 Sciverse 会让普通 docs 查询变得更重，也会把 token 和学术 schema 风险带进默认路径。
- 结论：否决作为第一版入口。后续可以在单独 routing 任务里评估“明确论文/DOI/文献综述意图”时是否补充路由。

### 方向 C：作为实验性 `vertical_search` provider 显式接入

- 描述 / 价值 / 代价：和 AnySearch 的定位一致，先提供独立命令让用户主动调用；不会影响 `standard` 最低配置和默认搜索链；代价是用户需要知道自己要用 Sciverse。
- 结论：选定。它把风险收在可控边界里，也和现有 provider capability 架构一致。

### 方向 D：直接启动/托管 Sciverse MCP server

- 描述 / 价值 / 代价：贴近 issue 中 MCP server 的接入描述，也可以复用 MCP tool 名；但 Smart Search 会变成 Node MCP 进程宿主，带来进程生命周期、npx 版本、stdio/HTTP transport、用户本机 Node 环境等额外问题。
- 结论：否决为第一版首选。除非 native HTTP/OpenAPI 走不通，否则不建议让 Smart Search 自己 spawn MCP server。

### 方向 E：基于 OpenAPI/HTTP 写 native provider adapter

- 描述 / 价值 / 代价：直接对 `https://api.sciverse.space` 的 OpenAPI endpoint 发请求，和 Smart Search 现有 Python provider / config / timeout / error normalization 更贴合；代价是需要把 5 个 MVP 命令的参数映射设计清楚。
- 结论：选定。Sciverse 仓库的 `openapi.yaml` 已暴露 `search_papers`、`semantic_search`、`list_catalog`、`list_paper_relations`、`read_content` 等 operationId，适合 native adapter。

## 已敲定的设计点

- 已确认：#18 按 feature 处理，不走 issue-fix。它不是现有行为坏了，而是新增实验 provider 能力。
- 已确认：Sciverse 归属 `vertical_search`，provider id 暂定 `sciverse`，标记 experimental。
- 已确认：第一版不计入 `SMART_SEARCH_MINIMUM_PROFILE=standard`，也不改变 `standard` fail-closed 规则。
- 已确认：第一版只提供显式 CLI 命令，不接入默认 `smart-search search` 和 `smart-search research` fallback。
- 已确认：MVP 命令面包含 `sciverse-catalog`、`sciverse-search`、`sciverse-semantic`、`sciverse-read`、`sciverse-relations`。
- 已确认：第一版把 `list_paper_relations` 放进 MVP。理由是引用/被引/相关工作关系正是它区别 Exa/AnySearch 的核心价值；少了 relations，Sciverse 会退化成“另一个论文搜索接口”。
- 已确认：`get_resource` 暂不进 MVP。它返回图表图片/二进制资源，会牵涉输出文件、base64、Markdown 图片引用、多模态消费方式，适合第二版单独设计。
- 已确认：优先实现 native HTTP/OpenAPI provider adapter，不让 Smart Search 第一版自行启动 Sciverse MCP server。
- 已确认：配置项先收敛为 `SCIVERSE_API_TOKEN`、`SCIVERSE_API_URL`、`SCIVERSE_TIMEOUT_SECONDS`。
- 倾向：`sciverse-search` 支持常用显式参数，并保留 JSON `--filters-advanced` / `--sort-advanced` 逃生舱，避免第一版追满所有学术字段。
- 倾向：provider 输出保留 Sciverse 原始关键字段，同时归一化顶层 `provider`、`query`、`results` / `hits`、`provider_attempts`、`error_type` 等 Smart Search 通用观测字段。
- 待验证：没有真实 `SCIVERSE_API_TOKEN` 时只能做 schema/mock 测试；有 token 后需要 live smoke 验证 catalog/search/semantic/read/relations 全链路。

## 选定方向与遗留问题

选定方向：采纳 #18，但以保守的实验性 `vertical_search` provider 进入。第一版目标不是“让所有学术问题自动走 Sciverse”，而是先提供一组可靠的显式命令，让用户在需要学术结构化证据、全文片段和引用网络时主动调用。

第一版明显不做：不进入 `standard` 最低配置；不默认参与 `search` / `research` fallback；不把 Sciverse 放进 docs_search；不在 Smart Search 内 spawn/托管 MCP server；不处理 `get_resource` 图片资源。

design 阶段需要继续拆清楚的问题：

- CLI 参数形态：哪些字段做一等参数，哪些只走 JSON 逃生舱。
- 输出 schema：`search_papers` 的 `results`、`semantic_search` 的 `hits`、`read_content` 的文本片段、`relations` 的关系分页如何统一到 Smart Search 风格。
- 错误归一化：401/400/429/502/503 分别映射到 `auth_error`、`provider_error`、`rate_limit`、`network_error` / `provider_error` 的边界。
- live 验证条件：是否能拿到 `SCIVERSE_API_TOKEN`，以及没有 token 时 doctor/setup 如何给出清楚但不阻塞 standard profile 的提示。

## 当前证据

- GitHub issue #18 当前仍为 open，标题是“[Feature] 支持 Sciverse 作为学术文献检索 provider（vertical_search 学术域补充）”，更新时间为 2026-07-06T04:46:50Z。
- 当前 README / provider contract 已把 `vertical_search` 定位为实验性垂直能力；AnySearch 不进入 `web_search` fallback，也不要求 `standard` minimum profile。Sciverse 应复用这个边界。
- `gh repo view opendatalab/Sciverse-Agent-Tools` 显示仓库 2026-07-03 仍有 push，描述为面向 LLM agents 的 Sciverse Open Platform retrieval capabilities。
- `npm view sciverse-mcp-server` 显示当前版本为 `0.9.0`，不是 issue 文本里的 `0.8.1`；bin 包含 `sciverse-mcp-server`、`sciverse-mcp`、`sciverse-mcp-http`；Node engine 为 `>=18`。
- Sciverse README 当前列出 6 个工具：`list_catalog`、`search_papers`、`semantic_search`、`list_paper_relations`、`read_content`、`get_resource`。
- Sciverse `openapi.yaml` 当前 version / `x-sciverse-tools-version` 为 `0.9.0`，并包含 `list_paper_relations`，其 relation enum 为 `CITATIONS`、`REFERENCES`、`RELATED_WORKS`。
- license 证据有轻微不一致：GitHub API `licenseInfo` 返回 `Other`，npm package 与 README 写的是 `Apache-2.0`。design 阶段应把许可来源作为待核对项记录，不在第一版里误写成“GitHub API 已确认 Apache-2.0”。
