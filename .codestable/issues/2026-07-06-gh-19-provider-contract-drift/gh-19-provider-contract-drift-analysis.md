---
doc_type: issue-analysis
issue: 2026-07-06-gh-19-provider-contract-drift
status: confirmed
root_cause_type: data-format
related:
  - gh-19-provider-contract-drift-report.md
tags:
  - github
  - provider
  - context7
  - anysearch
---

# GitHub Issue #19 Context7 / AnySearch 契约漂移根因分析

## 1. 问题定位

| 关键位置 | 说明 |
|---|---|
| `src/smart_search/providers/anysearch.py:91` | `AnySearchProvider.list_domains()` 仍调用旧 MCP tool `list_domains`。当前 live `tools/list` 返回的是 `batch_search`、`extract`、`get_sub_domains`、`search`。 |
| `src/smart_search/service.py:2799` | `anysearch_domains()` 直接包装 provider 的 `list_domains()`，所以 `smart-search anysearch-domains` 必然跟着调用旧 tool。 |
| `src/smart_search/providers/anysearch.py:69` | 点号简写只把 `security.cve` 拆成 `domain=security`、`sub_domain=cve`。当前 AnySearch 对 CVE 使用的是 `domain=security`、`sub_domain=vuln`，且需要结构化 `sub_domain_params`。 |
| `src/smart_search/cli.py:2871` | `anysearch-search` CLI 只暴露 `--domain`、`--sub-domain`、`--max-results`，没有传入 `sub_domain_params` 的入口。 |
| `src/smart_search/providers/anysearch.py:102` | `vertical_search()` 构造的 JSON-RPC arguments 没有 `sub_domain_params` 字段，即使上层想传也传不出去。 |
| `src/smart_search/service.py:1146` | Deep Research / research docs 路径在 Context7 返回候选后直接取第一个 `id` 继续抓 docs，没有匹配或置信度选择逻辑。 |
| `src/smart_search/providers/context7.py:87` | `context7-docs` 对调用者传入的 library id 原样请求 Context7。旧示例 `/facebook/react` 当前返回 301 network_error；`/reactjs/react.dev` 可返回 useEffect cleanup 内容。 |
| `README.md:413` / `README.zh-CN.md:464` / `skills/smart-search-cli/references/command-patterns.md:35` | 公开 README、中文 README、public skill 和 packaged skill 仍展示 `/facebook/react` 示例。 |
| `README.md:347` / `README.zh-CN.md:356` / `skills/smart-search-cli/references/command-patterns.md:38` | 公开 README、中文 README、public skill 和 packaged skill 仍展示 `security.cve` CVE 示例。 |
| `.trellis/spec/backend/provider-capability-contract.md:352` | 项目 provider 契约 spec 仍写 AnySearch tools 是 `list_domains`、`search`、`extract`、`batch_search`，已经落后于当前外部 MCP。 |
| `tests/test_anysearch_provider.py:90` / `tests/test_service.py:1604` / `tests/test_cli.py:2531` | 测试仍把 `list_domains` 作为正确行为，导致旧契约被测试固定下来。 |

## 2. 失败路径还原

**正常路径**：用户运行 `smart-search anysearch-domains security --format json` → CLI 调 `service.anysearch_domains()` → provider 调当前 AnySearch domain discovery tool → 返回可用 sub domains 和所需参数。用户再运行 `anysearch-search` 并提供当前协议需要的 `domain`、`sub_domain`、`sub_domain_params` → AnySearch 返回结构化垂直搜索结果。

**失败路径**：用户运行 `smart-search anysearch-domains --format json` → `src/smart_search/service.py:2799` 调 `AnySearchProvider.list_domains()` → `src/smart_search/providers/anysearch.py:93` 发送 tool name `list_domains` → 当前 AnySearch MCP 返回 `tool 'list_domains' not found` → CLI 返回 provider_error。用户运行 `smart-search anysearch-search "CVE-2024-3094" --domain security.cve` → `src/smart_search/providers/anysearch.py:69` 拆成 `security` + `cve` → `vertical_search()` 未发送 `sub_domain_params` → AnySearch 返回 `Invalid tag: security.cve`。

**正常路径**：用户运行 `smart-search context7-docs "/reactjs/react.dev" "useEffect cleanup" --format json` → provider 请求 Context7 context API → 返回 React useEffect cleanup 内容。

**失败路径**：用户按 README / skill 示例运行 `smart-search context7-docs "/facebook/react" "useEffect cleanup" --format json` → `src/smart_search/providers/context7.py:87` 原样请求旧 id → Context7 返回 301 → service 标记 `network_error`。在自动 docs 流程中，`context7_library("React useEffect cleanup docs", ...)` 当前 live 结果首位是 `/devopshq/artifactory-cleanup`，`/reactjs/react.dev` 排第 11；`src/smart_search/service.py:1146` 直接取第一个 id，会把 React 文档问题导向不相关库。

**分叉点**：

- `src/smart_search/providers/anysearch.py:91` — 本地仍信任旧 AnySearch tool name。
- `src/smart_search/providers/anysearch.py:102` — 本地 AnySearch search 参数模型缺少当前协议要求的结构化参数。
- `src/smart_search/service.py:1146` — Context7 自动路径直接取第一候选，缺少匹配选择。
- 文档 / skill 示例 — 用户入口仍指向外部已失效的旧 id 和旧垂直域表达。

## 3. 根因

**根因类型**：data-format

**根因描述**：外部 provider 的数据契约已经变化，但 smart-search 的代码、spec、测试、README 和 skill 示例仍按旧契约工作。AnySearch 从 `list_domains` 漂移到 `get_sub_domains`，并且垂直搜索从单纯 `domain.sub_domain` 漂移到需要 `sub_domain_params` 的结构化调用；Context7 的 React library id 从旧 `/facebook/react` 漂移到当前可用的 `/reactjs/react.dev`，同时 Context7 search 排序不能保证第一个结果就是语义最匹配的库。本地实现没有契约发现 / 参数透传 / 候选重排，所以外部服务一变，显式 CLI 和自动调用路径一起失准。

**是否有多个根因**：是。

1. 主根因：AnySearch 外部 MCP tool 和参数 schema 漂移，本地 provider / CLI / spec / tests 未同步。
2. 次根因：Context7 旧 library id 和自动候选选择策略过于脆弱，本地示例和自动 docs 流程未做匹配重排或低置信度保护。
3. 配套根因：public skill 与 packaged skill、README、测试都把旧契约固化，导致发布资产和回归测试会继续传播旧行为。

## 4. 影响面

- **影响范围**：不只影响 issue 中四条命令；所有 `anysearch-domains` 用户、需要 AnySearch 结构化垂直搜索参数的用户、复制 README / skill 示例的用户、以及 Deep Research / research 中触发 Context7 自动 docs 的用户都可能受影响。
- **潜在受害模块**：`AnySearchProvider`、`service.anysearch_*` wrappers、CLI parser、Context7 research docs path、README / README.zh-CN、`skills/smart-search-cli/**`、`src/smart_search/assets/skills/smart-search-cli/**`、provider capability spec、AnySearch / Context7 相关测试。
- **数据完整性风险**：无持久化数据损坏风险；风险主要是错误 evidence、空 evidence、错误 provider 错误类型、以及 agent 被 skill 示例误导后产生错误研究路径。
- **严重程度复核**：维持 P1。Context7 属于 `standard` 最低配置中的 docs_search 可选 provider，AnySearch 虽是 experimental，但当前公开文档和 skill 会直接引导用户走失败命令；影响面超过单个边界场景。

## 5. 修复方案

### 方案 A：同步当前外部契约并做最小健壮化

- **做什么**：
  - AnySearch：把 domain discovery 从 `list_domains` 改为 `get_sub_domains`，保持 CLI 名称 `anysearch-domains` 兼容；给 `anysearch-search` 增加 `--sub-domain-params`，解析 JSON 后透传给 provider；更新 provider arguments、输出中保留 `sub_domain_params` 摘要但不泄露敏感值。
  - Context7：把 README / skill 示例从 `/facebook/react` 改为 `/reactjs/react.dev`；在自动 docs 流程中加入候选选择函数，按 id/title/description token 匹配、trust_score、benchmark_score 对候选重排；React 这类常见库可加小型稳定 id 映射或 exact-title 优先规则；低置信度时不要盲取第一个，可回退 Exa 或返回明确 gap。
  - 同步更新 `.trellis/spec/backend/provider-capability-contract.md`、README、README.zh-CN、public skill、packaged skill、AnySearch / Context7 tests。
- **优点**：直击当前根因，改动可控；保留现有 CLI 名称兼容；能用测试固定新契约；不会把 AnySearch 提升进默认 fallback 链。
- **缺点 / 风险**：需要定义 `--sub-domain-params` 的 JSON 解析错误行为；Context7 候选选择启发式需要覆盖典型但不能保证所有库都完美；AnySearch 外部 schema 后续继续变动时仍需维护。
- **影响面**：会动 provider、service、CLI、README、skill assets、spec、tests；属于 provider/public contract 修复。

### 方案 B：只修文档与示例，代码行为暂不变

- **做什么**：把 README / skill 中 `/facebook/react` 和 `security.cve` 示例改成当前可用或标注为过时；说明 AnySearch 垂直搜索复杂参数暂不支持，建议用户直接用 MCP 客户端。
- **优点**：改动最小，能快速减少用户复制失败示例。
- **缺点 / 风险**：`anysearch-domains` 仍然失败，`anysearch-search` 仍然无法完成 CVE 结构化搜索，自动 Context7 仍可能选错库；GitHub issue 的核心代码问题没有解决。
- **影响面**：只动 README / skill assets / 可能的 docs tests；不能关闭该 bug。

### 方案 C：引入 schema-driven MCP 适配层

- **做什么**：给 MCP 类 provider 做统一 `tools/list` capability discovery、tool schema 缓存、参数校验和 schema-driven CLI 扩展；AnySearch、Zhipu MCP、未来 Sciverse 等 provider 走同一层。
- **优点**：长期抗漂移能力最好；未来接 Sciverse / 其他 MCP provider 时复用度高。
- **缺点 / 风险**：范围明显超出 #19，设计和测试成本高；容易与当前 beta integration 任务互相放大风险；需要重新界定多个 provider 的公共抽象。
- **影响面**：会动 provider 架构、配置、CLI、测试、spec，适合作为后续 roadmap / feature，不适合作为本 issue 的第一修复批次。

### 推荐方案

**推荐方案 A**。理由：它覆盖 GitHub issue #19 的真实失败路径，同时保持修复范围在 AnySearch / Context7 两条 provider 契约内；比文档-only 更完整，又不会像 schema-driven MCP 抽象那样把一个 bug 修成架构迁移。实现时应分两批提交或至少分两组测试：先 AnySearch 契约同步，再 Context7 示例和候选选择策略，最后统一跑 provider contract、README/skill 同步和 regression。
