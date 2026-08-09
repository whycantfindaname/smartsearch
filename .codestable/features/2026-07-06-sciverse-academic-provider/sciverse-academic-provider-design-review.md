---
doc_type: feature-design-review
feature: 2026-07-06-sciverse-academic-provider
status: passed
reviewed: 2026-07-06
round: 4
---

# sciverse-academic-provider feature design 审查报告

## 1. Scope And Inputs

- Design: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md`
- Checklist: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-checklist.yaml`
- Intent / brainstorm: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-brainstorm.md`
- Roadmap: none
- Related docs: `.codestable/requirements/sciverse-academic-search.md`, `.codestable/requirements/VISION.md`, `.trellis/spec/backend/provider-capability-contract.md`, README.md, README.zh-CN.md, public skill and packaged skill provider-routing references
- Trellis context checked: `.trellis/tasks/06-12-integrate-pr-fixes-beta/prd.md`, `design.md`, `implement.md`
- Code facts checked: `src/smart_search/config.py`, `src/smart_search/service.py`, `src/smart_search/cli.py`, `src/smart_search/providers/anysearch.py`, `src/smart_search/providers/`
- Live upstream facts checked in round 4: GitHub issue #18, `npm view sciverse-mcp-server`, `gh repo view opendatalab/Sciverse-Agent-Tools`, Sciverse `openapi.yaml`

### Independent Review

- Status: local-only
- Detection: native-agent
- Provider / agent: none
- Raw output: none
- Merge policy: 本轮运行在 inline mode，且当前宿主 sub-agent 工具规则要求用户明确请求 sub-agent 后才能派发；主线程按 design-review checklist 做本地事实核验并记录降级风险
- Gate effect: local-only downgrade risk recorded

## 2. Design Summary

- Goal: 以实验性 `vertical_search` provider 方式接入 Sciverse，第一版只暴露显式 `sciverse-*` CLI 命令，不进入默认 `search` / `research` fallback，也不改变 `standard` minimum profile。
- Key contracts: 新增 `SCIVERSE_API_TOKEN` / `SCIVERSE_API_URL` / `SCIVERSE_TIMEOUT_SECONDS`，新增 `SciverseProvider` native HTTP adapter，MVP 覆盖 catalog/search/semantic/read/relations，不覆盖 `get_resource`。
- Steps: 6 个 pending step，按 provider/config、计算节点、service/capability、CLI、文档同步、回归/live smoke 切片；每步有可独立验证的退出信号。
- Checks: 17 个 pending check，覆盖范围守护、名词契约、流程约束、挂载点和验收场景；README.zh-CN 同步与参数边界已纳入。
- Baseline / validation: design frontmatter 校验通过；checklist YAML 校验通过（PyYAML 不可用时使用 fallback parser）；`git diff --check` 对当前 tracked diff 通过。当前 git 状态只显示 #18 的新 CodeStable docs/requirements 为 untracked；显式 secret scan 未命中已知临时 key 子串或 `SCIVERSE_API_TOKEN` 明文赋值。
- Round 2 findings resolution: README.zh-CN 同步范围已写入 design 第 1/2/3/4 节与 checklist；search page_size、semantic top_k、read limit、relations page_size 参数边界已写入流程约束、推进策略、验收场景、Acceptance Coverage Matrix 与 checklist。
- Round 4 upstream check: issue #18 仍为 OPEN；`sciverse-mcp-server` 仍为 `0.9.0` / `Apache-2.0` / Node `>=18`；Sciverse repo GitHub `licenseInfo` 仍为 `Other`；OpenAPI 仍为 `0.9.0` 且包含 catalog/search/semantic/read/relations/get_resource、relations enum 和参数上限。
- Round 4 hygiene note: 因相关 CodeStable 文档仍是 untracked，`git diff --check` 不会覆盖它们；额外尾空格扫描发现 design 中 11 处 Markdown 硬换行尾部空格，见 nit finding。

## 3. Findings

### blocking

- none

### important

- none

### nit

- FDR-002 `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md:48` design 里有 11 处 Markdown 硬换行尾部空格。
  - Evidence: 命中行为 48、51、54、57、60、238、241、244、247、250、253；当前文件未纳入 git index，所以 `git diff --check` 没覆盖这些尾空格。
  - Impact: 不阻塞用户 review，但如果后续直接 stage/commit，核心 `git diff --check` gate 可能会报 whitespace error。
  - Expected fix scope: 进入实现或提交前把这些硬换行改成普通换行/空行，或改用不触发 diff check 的 Markdown 写法。

### suggestion

- FDR-001 capability status 里如果显示 Sciverse 已配置，最好同时暴露 `explicit_only` / `route_enabled=false` 或等价文案，避免用户把“配置了”误解成“会进入默认 vertical fallback”。这不是本轮 blocking，但实现和 code review 可以顺手复核。

### learning

- 对 true external provider，先用显式命令和 capability diagnostics 接入、暂不进入默认 routing，是当前 provider contract 下更容易验收和回滚的路径。
- Sciverse 的 `unique_id` / `doc_id` 分层是 MVP 的关键认知点：relations 用 `unique_id`，read 用 `doc_id`，CLI help、渲染和测试都应反复证明这个区别。

### praise

- design 已把“不进入 docs_search / standard / 默认 search-research fallback / MCP server 宿主 / get_resource”写成反向核对项，适合作为后续 acceptance 的范围守护。
- round 3 已把中英 README 同步和 Sciverse OpenAPI 参数上限补成可执行契约，降低了 #19 类 provider 文档漂移复发风险。

## 4. User Review Focus

- 用户需要重点拍板：是否接受 Sciverse 只做显式 experimental vertical provider；是否同意第一版包含 relations 但不包含 `get_resource`。
- implement 需要重点遵守：Sciverse 只能通过显式命令触发；provider HTTP 细节必须留在 `SciverseProvider` 内；默认路由和 standard minimum profile 不得变化；README.md 与 README.zh-CN.md 都必须同步。
- code review / QA / acceptance 需要重点复核：secret masking、默认路由反向测试、relations 方向语义、`unique_id` vs `doc_id`、参数越界本地 `parameter_error`、README/public skill/packaged skill 同步。

## 5. Evidence Confidence Ledger

| Check | Verdict | Evidence Class | Basis | Follow-up |
|---|---|---|---|---|
| Acceptance Coverage Matrix | pass | E/C | design 第 3 节覆盖 happy path、JSON 校验、参数上限、错误映射、standard/profile、默认路由、文档同步 | none |
| DoD Contract | pass | E | design 与 checklist 都列出 validation commands，CMD-006 已改为 source checkout live smoke | none |
| Steps and checks traceability | pass | E | checklist steps/checks 均来自 design 对应章节，README.zh-CN 和参数边界有独立 check | none |
| Roadmap contract compliance | n/a | E | design frontmatter 无 roadmap / roadmap_item | none |
| Module interface design | pass | E/C | design 已记录 `SciverseProvider` interface/seam/adapter；代码事实显示现有 provider 形状确实是 config/service/CLI/provider 分层 | none |
| Validation and artifacts | pass | E/C | compileall、focused pytest、regression、mock smoke、diff check、optional live smoke 已列；清洁度规则覆盖 debug/TODO/secrets；额外发现 untracked design 尾空格 | 提交前清理 FDR-002 |

Summary: E=6, C=4, H=0, H-only core checks=none。

## 6. Residual Risk

- 本轮按 inline mode 做 local-only review，没有独立 Task agent 的第二上下文审查；后续 code review/QA 需要更严地复核范围守护和 provider routing。
- 没有真实 `SCIVERSE_API_TOKEN` 时，live smoke 只能作为 supporting gate 延后；mock tests 必须成为 blocking 证据。
- Sciverse upstream schema 近期活跃，implement 开始前应重新确认 OpenAPI version / operationId / enum 没变。
- `approval-report.md` 仍显示 `status: pending`，但本轮正式 design-review 已按 local-only fallback 落盘；若用户想保留文档洁净，后续可单独把该旧授权草稿标记为 superseded。

## 7. Verdict

- Status: passed
- Next: 交给用户整体 review；用户确认后可把 design frontmatter `status` 从 `draft` 改为 `approved`，再进入 `cs-feat-impl`。进入提交前清理 FDR-002 的尾空格。
