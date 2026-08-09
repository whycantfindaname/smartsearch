---
doc_type: feature-acceptance
feature: 2026-07-06-sciverse-academic-provider
status: passed
accepted: 2026-07-06
round: 1
---

# Sciverse 学术检索 Provider 验收报告

> 阶段：阶段 3（验收闭环）
> 验收日期：2026-07-06
> 关联方案 doc：`.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md`

## 1. 接口契约核对

对照方案第 2.1 节名词层：

**接口示例逐项核对**：
- [x] `SciverseProvider.list_catalog()`：`sciverse-catalog` -> `GET /meta-catalog`，输出 `fields/default_fields/filter_operators`。代码落点：`src/smart_search/providers/sciverse.py`、`src/smart_search/service.py`、`src/smart_search/cli.py`。
- [x] `SciverseProvider.search_papers()`：`sciverse-search` 支持 query、常用字段参数、`filters_advanced/sort_advanced` JSON array、分页和排序。代码落点：provider/service/CLI/tests。
- [x] `SciverseProvider.semantic_search()`：`sciverse-semantic` 支持 `query/top_k/mode/source_types`，输出 `hits/results`。代码落点：provider/service/CLI/tests。
- [x] `SciverseProvider.read_content()`：`sciverse-read DOC_ID` 用 `doc_id` 读取正文片段，输出 `text/bytes_returned/next_offset/more`。代码落点：provider/service/CLI/tests。
- [x] `SciverseProvider.list_paper_relations()`：`sciverse-relations UNIQUE_ID` 用 `unique_id` 和 `CITATIONS/REFERENCES/RELATED_WORKS` 查询关系，输出 `items/total_count/page/total_pages/relation_direction`。代码落点：provider/service/CLI/tests。

**名词层“现状 -> 变化”逐项核对**：
- [x] 新增 native HTTP adapter：`src/smart_search/providers/sciverse.py` 集中处理 endpoint、Bearer token、timeout、HTTP error、schema drift 和 response normalization。
- [x] 新增配置：`SCIVERSE_API_TOKEN`、`SCIVERSE_API_URL`、`SCIVERSE_TIMEOUT_SECONDS` 已加入 config allow-list、默认值、mask 显示和 setup flags。
- [x] 新增 service wrappers：`sciverse_catalog/search/semantic/read/relations` 均经 service 调 provider。
- [x] 新增 CLI 命令：`sciverse-catalog/search/semantic/read/relations` 及 `sv-*` alias 已登记。
- [x] 输出契约：provider 输出包含 `ok/provider/tool/elapsed_ms/raw` 和命令专属字段。
- [x] 错误映射：config/auth/parameter/rate-limit/timeout/network/provider/parse 路径由 provider tests 和 CLI tests 覆盖。

**流程图核对**：
- [x] CLI 解析 -> service wrapper -> token gate -> provider HTTP request -> response/error normalization -> render 输出，均有实际落点。
- [x] 无 token 分支本地返回 `config_error`；QA 手工命令确认 `sciverse-catalog` exit 3 且 `error_type=config_error`。

## 2. 行为与决策核对

**需求摘要逐项验证**：
- [x] 配置 token 后的 catalog/search/semantic/read/relations 本地契约由 mock provider 和 CLI/service tests 覆盖。
- [x] 没有 token 时返回清楚配置错误，且不发网络请求；provider tests 覆盖 no-token no-request，QA 额外跑了 CLI no-token 命令。
- [x] `SMART_SEARCH_MINIMUM_PROFILE=standard` 不变：service tests 与 mock smoke 均证明 required 仍是 `main_search/docs_search/web_fetch`。
- [x] 默认 `search` / `research` 不调用 Sciverse：`RESEARCH_PROFILE_ORDER["vertical_search"]` 仍只有 `anysearch`，`_run_vertical_search_fallback()` 只配置 AnySearch；mock smoke 中 Sciverse 仅在 `explicit_only`。

**明确不做逐项核对**：
- [x] 不放入 `docs_search`：provider profile exclusions 和文档均声明 not docs_search；routing tests 证明 docs route 不含 Sciverse。
- [x] 不加入默认 `search` / `research` fallback：service route 只把 Sciverse 标为 explicit-only/route-disabled。
- [x] 不启动或托管 `sciverse-mcp-server` / `npx`：`rg "sciverse-mcp-server|npx|sciverse-resource|get_resource" src tests README.md README.zh-CN.md skills src\smart_search\assets\skills .trellis\spec\backend\provider-capability-contract.md` 无命中。
- [x] 不实现 `get_resource` / `sciverse-resource`：CLI parser 和 docs 只有五个 `sciverse-*` 显式命令。
- [x] 不泄露 token：config info masked；QA secret-like scan `secret_like_hits=0`。

**关键决策落地**：
- [x] native HTTP/OpenAPI adapter：provider 直接调用 `/meta-catalog`、`/meta-search`、`/agentic-search`、`/content`、`/meta-paper-relations`。
- [x] explicit-only：`sciverse` 是 experimental `vertical_search`，`route_enabled.sciverse=false`。
- [x] 第一版包含 relations：`sciverse-relations` 已实现并文档化方向。
- [x] 第一版不做 resource：无相关命令或托管逻辑。
- [x] 高级字段 JSON 逃生舱：CLI 层验证 `--filters-advanced` / `--sort-advanced` 为 JSON array。

**挂载点反向核对（可卸载性）**：
- [x] 配置 key 挂载点：`config.py`、CLI setup/config、tests。
- [x] Provider capability 诊断：`service.py` / `cli.py` capability status 中 `explicit_only=["sciverse"]`。
- [x] CLI 命令入口：`cli.py` parser/dispatch/render 和 `tests/test_cli.py`。
- [x] 契约文档入口：README、中文 README、provider contract、public skill、packaged skill。
- [x] 反向 grep：Sciverse 代码引用集中在 provider/config/service/CLI/tests/docs/skills/CodeStable 产物；未发现方案外运行时挂载点。
- [x] 拔除沙盘推演：删除 provider 文件、service wrapper/profile、config keys、CLI command/parser、tests/docs/skill 条目即可卸载；没有默认 route 残留。

## 3. 验收场景核对

- [x] S1 配置缺失：未配置 token 时显式命令返回 `config_error`。
  - 证据来源：QA-006，CLI no-token 命令 exit 3。
- [x] S2 Catalog happy path：Bearer header、fields/default_fields/filter_operators。
  - 证据来源：`tests/test_sciverse_provider.py` in QA-002。
- [x] S3 结构化搜索：query/year/page_size payload、`unique_id/doc_id/title/metadata/pagination`。
  - 证据来源：`tests/test_sciverse_provider.py` + `tests/test_cli.py` in QA-002。
- [x] S4 JSON 逃生舱：非 JSON array 本地 `parameter_error` 且不调 service。
  - 证据来源：`tests/test_cli.py` in QA-002。
- [x] S5 语义搜索：`top_k/mode/source_types` payload 和 `hits/doc_id/offset/score` 输出。
  - 证据来源：`tests/test_sciverse_provider.py` + `tests/test_cli.py` in QA-002。
- [x] S6 正文读取：`doc_id/offset/limit` 和 `text/bytes_returned/next_offset/more` 输出。
  - 证据来源：`tests/test_sciverse_provider.py` + `tests/test_cli.py` in QA-002。
- [x] S7 引用关系：`unique_id/relation/page_size` 和 `items/total_count/page/total_pages/relation_direction`。
  - 证据来源：`tests/test_sciverse_provider.py` + `tests/test_cli.py` in QA-002。
- [x] S8 参数上限：search/semantic/read/relations 越界本地 `parameter_error`。
  - 证据来源：`tests/test_sciverse_provider.py` in QA-002。
- [x] S9 错误映射：401/403、400、429、timeout、502/503 和 schema drift。
  - 证据来源：provider tests + review round 3 + QA-002。
- [x] S10 standard profile 不变。
  - 证据来源：service tests + mock smoke。
- [x] S11 默认路由不变。
  - 证据来源：service tests + mock smoke。
- [x] S12 文档同步。
  - 证据来源：regression marker tests、diff review 和 grep。

**review 报告重点复核**：
- [x] design CMD-001 到 CMD-005 已全部运行并通过。
- [x] Sciverse schema drift、CLI exit code、无 token config_error、默认 search/research 不出现 `sciverse`、secret masking 均在 QA matrix 中覆盖。
- [x] review residual risk 中的 live token smoke 因当前环境无 token 保持 supporting residual risk；未承载核心验收缺口。

**QA 报告重点复核**：
- [x] 验证证据来源：`.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-qa.md`
- [x] QA 状态：passed。
- [x] Feature type: functional；功能性核心路径均有 mock/unit/service/CLI/smoke 运行证据。
- [x] failed / blocked 项为 none。
- [x] residual-risk 只有真实 token live smoke 和 OCR 不可用；二者均非核心 blocking gate。

## 4. 术语一致性

- `Sciverse` / `sciverse`：provider id、配置、CLI、service、docs 一致。
- `vertical_search`：仅用于 experimental explicit-only 能力，不写成 `docs_search` 或 standard provider。
- `unique_id`：relations 入参和文档说明一致。
- `doc_id`：read 入参和文档说明一致。
- `CITATIONS` / `REFERENCES` / `RELATED_WORKS`：CLI choices、provider enum、文档方向说明一致。
- 防冲突：未发现 `sciverse-resource` / `get_resource` 用户命令；未发现 Sciverse MCP server 托管逻辑。

## 5. 领域影响盘点（提示而非代写）

- [x] 候选：`Sciverse` 作为 explicit-only experimental `vertical_search` provider，不进入 default route。建议后续如需长期沉淀，走 `cs-domain` 写 ADR；accept 阶段不直接写。
- [x] 候选：`doc_id` 与 `unique_id` 的语义区分。当前已在 design、README、provider contract 和 skill 中说明；若后续还有学术 provider，可走 `cs-domain` 写 CONTEXT 术语。
- [x] 当前 `.codestable/requirements` 下没有 `CONTEXT.md` 或 `adrs/`，本次不代写领域文档。

## 6. requirement delta / clarification 回写

- [x] 方案 frontmatter 指向 `requirement: sciverse-academic-search`。
- [x] 用户已明确批准 req delta；approval report：`.codestable/features/2026-07-06-sciverse-academic-provider/approval-report.md`，frontmatter `status: approved`。
- [x] 已机械应用 delta：`.codestable/requirements/sciverse-academic-search.md` 从 `draft` 升级为 `current`。
- [x] 已保留原始愿景和边界，并追加 `2026-07-06-sciverse-academic-provider` 变更日志。
- [x] 已同步 `.codestable/requirements/VISION.md`：`sciverse-academic-search` 从 Draft 移到 Current。

结论：requirement delta 已获 owner approval 并按 proposed delta 机械应用；未扩大能力范围。

## 7. roadmap 回写

- [x] 非 roadmap 起头：design frontmatter 没有 `roadmap` / `roadmap_item` 字段，跳过 roadmap items.yaml 和主文档回写。

## 8. attention.md 候选盘点

- [x] 本 feature 未暴露需要补入 `.codestable/attention.md` 的通用工作流候选。
- [x] 可复用知识分流：Sciverse explicit-only provider 分类和 `doc_id`/`unique_id` 术语更适合后续 `cs-domain`，不是 attention 短规则。

## 9. 遗留

- 后续优化点：
  - 可选补强测试：`message` object schema drift fixture。
  - 可选补强测试：`hits/items` 非 object item fixture。
- 已知限制：
  - 当前环境无 `SCIVERSE_API_TOKEN`，未运行真实 Sciverse live smoke。
  - OCR CLI 不可用，code review 使用 independent subagent fallback。
- 阻塞项：none

## 10. 最终审计

- 验证证据来源：`sciverse-academic-provider-qa.md`
- Evidence sources：evidence pack none；gate results none；DoD results none。
- 聚合命令：
  - `.\.venv\Scripts\python.exe -m compileall -q src tests` -> exit 0。
  - `.\.venv\Scripts\python.exe -m pytest tests\test_sciverse_provider.py tests\test_service.py tests\test_cli.py tests\test_smoke.py -q` -> exit 0，`232 passed`。
  - `.\.venv\Scripts\python.exe -m smart_search.cli regression` -> exit 0，`256 passed`。
  - `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json` -> exit 0，`ok=true`。
  - `git diff --check` -> exit 0，无 whitespace error。
- 场景复核：re-verified 12 / trust-prior-verify 0；live smoke 为 supporting skipped。
- 交付物复核：代码 / 配置 / schema / 路由 / 文档 / provider contract / skill / requirement / VISION 均落盘。
- 完整工作区复核：tracked diff 和 untracked 文件均属于本 Sciverse feature；无 staged diff。
- diff 清洁度：通过；无 debug 输出、临时 TODO/FIXME、注释掉代码、无用 import、方案外文件或 secret-like token。
- 知识沉淀出口：领域候选已分流到第 5 节；attention 无候选。
- 结论：通过；owner-approved requirement delta 已应用，当前无未处理验收缺口。
