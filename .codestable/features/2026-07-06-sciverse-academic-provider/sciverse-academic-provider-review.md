---
doc_type: feature-review
feature: 2026-07-06-sciverse-academic-provider
status: passed
reviewer: subagent
reviewed: 2026-07-06
round: 3
---

# sciverse-academic-provider 代码审查报告

## 1. Scope And Inputs

- Design: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-design.md`
- Checklist: `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-checklist.yaml`
- Evidence pack: none
- Gate results: none
- DoD results: none
- Implementation evidence: 当前工作区 diff、实现阶段验证命令、三轮独立 subagent review 输出
- Diff basis: `git status --short` 显示本 feature 的 provider、config、service、CLI、测试、README、provider contract、public skill 与 packaged skill 资产改动；`git diff --cached --name-status` 为空
- Baseline dirty files: 当前 dirty/untracked 文件均属于本 Sciverse feature 或其 requirement/design 产物；未发现本轮范围外 dirty 文件

### Independent Review

- Detection: `multi_agent_v1` subagent 可用；Paseo MCP 未暴露；`where.exe ocr` 未找到 OCR CLI
- 环节 A 独立隔离 Task agent: native-agent + completed（三轮）
- 环节 B OCR CLI: not-available
- OCR severity mapping: High->blocking/important, Medium->nit/suggestion, Low->discarded；本轮未启用 OCR
- Merge policy: subagent findings 已逐条本地核验；第一轮 3 个 important 已修复，第二轮 1 个 important 已修复，第三轮无 blocking/important
- Gate effect: reviewer=`subagent`，满足下游 gate；OCR 缺失不阻塞

## 2. Diff Summary

- 新增：
  - `src/smart_search/providers/sciverse.py`
  - `tests/test_sciverse_provider.py`
  - `.codestable/features/2026-07-06-sciverse-academic-provider/sciverse-academic-provider-review.md`
- 修改：
  - `src/smart_search/config.py`
  - `src/smart_search/providers/__init__.py`
  - `src/smart_search/service.py`
  - `src/smart_search/cli.py`
  - `tests/test_service.py`
  - `tests/test_cli.py`
  - `tests/test_regression.py`
  - `README.md`
  - `README.zh-CN.md`
  - `.trellis/spec/backend/provider-capability-contract.md`
  - `skills/smart-search-cli/**`
  - `src/smart_search/assets/skills/smart-search-cli/**`
- 删除：none
- 未跟踪 / staged：staged none；untracked 包含本 feature CodeStable 产物、Sciverse provider/test、requirement 文档
- 风险热点：跨 provider/config/service/CLI/docs/tests；远程 HTTP provider 的 auth、错误语义、schema drift、默认路由边界和 secret masking

## 3. Adversarial Pass

- 假设的生产 bug：Sciverse 上游返回 200 但 schema 漂移，本地误判为成功空结果，或者默认 `search/research` 意外调用 Sciverse 消耗 token。
- 主动攻击过的反例：无 token + 非法参数、HTTP 401/429/timeout、合法 JSON 但 root 非 object、`200 {}`、`{"data": ...}` envelope、核心字段类型错误、结果列表 item 非 object、CLI invalid JSON、配置 Sciverse token 后默认 vertical routing。
- 结果：前两轮 subagent review 找到的 schema drift / exit code / config precedence 问题已修复；第三轮复审无 blocking/important。剩余仅为可选测试补强建议，交给 QA 重点复核。

## 4. Findings

### blocking

none

### important

none

### nit

none

### suggestion

- [ ] REV-SUG-001 `tests/test_sciverse_provider.py:249` 可补 `{"message": {"text": "schema changed"}}` 这类 object message 漂移 fixture。
- [ ] REV-SUG-002 `tests/test_sciverse_provider.py:258` / `tests/test_sciverse_provider.py:260` 可补 `{"hits": [1]}`、`{"items": [1]}`，防未来重构遗漏同一个 item object guard。

### learning

- Provider schema drift 不能只防 invalid JSON；`200 {}`、envelope、核心字段缺失和列表 item 类型错误也必须归一到 `parse_error` / `provider_error`，不能当成功空结果。
- CLI exit code taxonomy 适合集中处理：`auth_error/config_error -> 3`，`rate_limited/timeout/parse_error/provider_error/network_error -> 4`，不要给单个 provider 打散补丁。

### praise

- Sciverse 保持 explicit-only：`RESEARCH_PROFILE_ORDER["vertical_search"]` 仍只有 AnySearch，`_run_vertical_search_fallback()` 也只组装 AnySearch。
- 无 token precedence 已明确：五个 public method 先返回 `config_error`，再做参数校验；测试证明无 token 时即使参数非法也不发网络请求。
- 文档与 skill public / packaged copy 同步，并新增 provider contract marker regression，降低后续漂移风险。

## 5. Test And QA Focus

- QA 必须重点复核：design CMD-001 到 CMD-005；Sciverse schema drift；CLI exit code；无 token config_error；默认 search/research 不出现 `sciverse`；secret masking。
- Evidence pack residual risks / gate warnings：无 evidence pack；review residual risk 是未做 live token smoke。
- 建议新增或加强的测试：可选补 `message` object、`hits/items` 非 object item fixture；当前不阻塞。
- 不能靠 review 完全确认的点：无真实 `SCIVERSE_API_TOKEN` 时不能确认 live catalog/search/semantic/read/relations 远端授权与字段可用性。

## 6. Residual Risk

- Live Sciverse smoke 依赖真实 token；当前环境未配置 token 时只能用 mock/provider/CLI/service/regression 证据放行，live 链路保持 supporting residual risk。
- OCR CLI 不可用，行级 OCR 扫描未执行；subagent review 与本地 diff review 已覆盖本轮关键风险。

## 7. Verdict

- Status: passed
- Next: `cs-feat-qa`
