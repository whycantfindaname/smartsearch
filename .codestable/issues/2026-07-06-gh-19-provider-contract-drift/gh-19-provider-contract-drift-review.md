---
doc_type: issue-review
issue: 2026-07-06-gh-19-provider-contract-drift
status: passed
reviewer: self
reviewed: 2026-07-06
round: 2
---

# gh-19-provider-contract-drift 代码审查报告

## 1. Scope And Inputs

- Issue report: `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-report.md`
- Issue analysis: `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-analysis.md`
- Fix note: `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-fix-note.md`
- Review-fix scope: 只修 round 1 blocking finding REV-001，涉及 `src/smart_search/service.py` 与 `tests/test_service.py`。
- Diff basis: 当前工作区仍包含 #19 的完整未提交修复；本轮复审重点审查 review-fix 增量和它对既有 #19 修复的影响。

### Independent Review

- 当前 developer 指令为 inline 模式，明确禁止 dispatch implement/check sub-agents。
- 环节 A 独立隔离 Task agent: skipped-by-inline-mode。
- OCR CLI: 本轮未重新启用；round 1 已确认 `where.exe ocr` 不可用。
- Gate effect: 本报告为 local-only self review。`reviewer: self` 不能满足 CodeStable 默认 commit gate；提交前仍需要允许独立 Task agent review，或由用户明确批准 self-review fallback。

## 2. Diff Summary

- `src/smart_search/service.py`：新增更具体 React 生态候选检测；当候选列表里存在同时命中 React 家族 token 与额外 query token 的库时，跳过 `/reactjs/react.dev` 的 preferred-id 强 boost。
- `tests/test_service.py`：新增 `React Native docs` 反例，要求 `/react-native/react-native` 胜过 `/reactjs/react.dev`；保留 `React useEffect cleanup docs` 仍选 `/reactjs/react.dev` 的正例。
- `gh-19-provider-contract-drift-fix-note.md`：补充 review-fix 方案、文件范围和验证结果。

## 3. Adversarial Pass

- 复测 round 1 反例：候选含 `/reactjs/react.dev` 与 `/react-native/react-native`，查询 `React Native docs`。
- 结果：`_select_context7_library_candidate()` 现在选中 `/react-native/react-native`。
- 反向正例：查询 `React useEffect cleanup docs`，候选含 Artifactory Cleanup 与 React 主站，仍选中 `/reactjs/react.dev`。
- 结论：REV-001 的错误覆盖路径已关闭，且没有牺牲原本要修的 React 主文档选择路径。

## 4. Findings

### blocking

none

### important

none

### nit

none

### suggestion

- 后续若要继续增强 Context7 rerank，可把 preferred id 规则扩展成可测试的数据表；本次不做，避免把 review-fix 扩大成 provider ranking 重构。

### learning

- preferred-id 映射适合修常见库误排，但必须让位于同生态、更具体的 id/title token 命中。

### praise

- 新增反例测试同时覆盖“React 主站仍可赢”和“React Native 更具体库可赢”，比只调分数更能锁住用户可见行为。

## 5. Test And QA Focus

- `.\.venv\Scripts\python.exe -m pytest tests\test_service.py -q`：`92 passed`。
- `.\.venv\Scripts\python.exe -m compileall -q src tests`：通过。
- `.\.venv\Scripts\python.exe -m pytest tests\test_anysearch_provider.py tests\test_service.py tests\test_cli.py tests\test_smoke.py tests\test_providers_new.py tests\test_intent_router.py -q`：`222 passed`。
- `.\.venv\Scripts\python.exe -m pytest -q`：`306 passed`。
- `.\.venv\Scripts\python.exe -m smart_search.cli regression`：`243 passed`。
- `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json`：`ok=true`，`failed_cases=[]`。
- `git diff --check`：通过；仅有 Git CRLF warning，无 whitespace error。
- 选择器探针：`React useEffect cleanup docs` -> `/reactjs/react.dev`；`React Native docs` -> `/react-native/react-native`。

## 6. Residual Risk

- 本轮复审是 inline self-review，缺少 CodeStable 默认要求的独立 Task agent reviewer；默认 commit gate 仍会因 `reviewer: self` 阻塞。
- Context7 外部结果排序和库 ID 仍可能继续漂移；本次只修已确认的 React 主站强 boost 误伤 React 生态库，不引入通用 schema/ranking 框架。

## 7. Verdict

- Status: passed
- Next: `cs-issue-fix` 的 review-fix 代码层面已完成；提交前需要解决 CodeStable 独立 review gate（允许 Task agent review，或用户明确批准 self-review fallback）。
