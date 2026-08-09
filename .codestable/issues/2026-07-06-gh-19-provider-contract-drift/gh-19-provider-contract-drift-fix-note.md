---
doc_type: issue-fix
issue: 2026-07-06-gh-19-provider-contract-drift
status: completed
path: standard
fix_date: 2026-07-06
related:
  - gh-19-provider-contract-drift-analysis.md
tags:
  - github
  - provider
  - context7
  - anysearch
---

# GitHub Issue #19 Context7 / AnySearch 契约漂移修复记录

## 1. 实际采用方案

采用 analysis 中确认的方案 A：同步当前 AnySearch / Context7 外部契约并做最小健壮化。

- AnySearch：`anysearch-domains` 保持 CLI 名称不变；无 domain 时通过 `tools/list` schema 返回可用顶层 domain；有 domain 时调用当前 `get_sub_domains`；`anysearch-search` 增加 `--sub-domain-params` JSON object 入口并透传给 provider，输出只回显参数 key。
- Context7：公开示例从 `/facebook/react` 改为 `/reactjs/react.dev`；research 自动 docs 路径加入候选重排，按 query token、preferred id、title/description 匹配、trust/benchmark score 选择候选，不再盲取第一个结果。
- 同步 README、中文 README、public skill、packaged skill、provider contract spec 和回归测试。

2026-07-06 review-fix 追加：修复 code review REV-001。Context7 候选选择中，React 主站 preferred-id boost 只在没有更具体 React 生态候选时生效；若候选列表里存在同时命中 React 家族 token 和额外 query token 的库（例如 `React Native docs` 命中 `/react-native/react-native` 的 `react` + `native`），则跳过 `/reactjs/react.dev` 的强 boost，让更具体候选胜出。

## 2. 改动文件清单

- `src/smart_search/providers/anysearch.py`
- `src/smart_search/service.py`
- `src/smart_search/cli.py`
- `README.md`
- `README.zh-CN.md`
- `skills/smart-search-cli/references/cli-core.md`
- `skills/smart-search-cli/references/command-patterns.md`
- `skills/smart-search-cli/references/provider-routing.md`
- `src/smart_search/assets/skills/smart-search-cli/references/cli-core.md`
- `src/smart_search/assets/skills/smart-search-cli/references/command-patterns.md`
- `src/smart_search/assets/skills/smart-search-cli/references/provider-routing.md`
- `.trellis/spec/backend/provider-capability-contract.md`
- `tests/test_anysearch_provider.py`
- `tests/test_cli.py`
- `tests/test_intent_router.py`
- `tests/test_providers_new.py`
- `tests/test_service.py`
- `tests/test_smoke.py`
- `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-analysis.md`
- `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/worktree-override.md`
- `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-fix-note.md`

Review-fix 追加修改：

- `src/smart_search/service.py`
- `tests/test_service.py`
- `.codestable/issues/2026-07-06-gh-19-provider-contract-drift/gh-19-provider-contract-drift-fix-note.md`

## 3. 验证结果

- `.\.venv\Scripts\python.exe -m compileall -q src tests`：通过。
- `.\.venv\Scripts\python.exe -m pytest tests\test_anysearch_provider.py tests\test_service.py tests\test_cli.py tests\test_smoke.py tests\test_providers_new.py tests\test_intent_router.py -q`：`222 passed`。
- `.\.venv\Scripts\python.exe -m pytest tests\test_regression.py -q`：`11 passed`。
- `.\.venv\Scripts\python.exe -m pytest -q`：`306 passed`。
- `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json`：`ok=true`，`failed_cases=[]`。
- `.\.venv\Scripts\python.exe -m smart_search.cli regression`：`243 passed`。
- `git diff --check`：通过；仅输出 Git 的 CRLF 提示，无 whitespace error。
- stale scan：`/facebook/react`、`security.cve`、`call_tool("list_domains")`、`"list_domains"` 在 `src`、`tests`、README、skill 和 provider spec 范围内无命中。
- `.\.venv\Scripts\python.exe -m pytest tests\test_service.py -q`：`92 passed`。
- `React useEffect cleanup docs` / `React Native docs` 选择器探针：分别选中 `/reactjs/react.dev` 与 `/react-native/react-native`。

Live smoke：

- `anysearch-domains --format json`：`exit=0`，`ok=true`，`tool=get_sub_domains`，`total=17`，首个 domain 为 `general`。
- `anysearch-domains security --format json`：`exit=0`，`ok=true`，`tool=get_sub_domains`，`domain=security`，`total=1`。
- `anysearch-search "CVE-2024-3094" --domain security --sub-domain vuln --sub-domain-params '{"type":"cve","value":"CVE-2024-3094"}' --max-results 1 --format json`：`exit=0`，`ok=true`，`tool=search`，`domain=security`，`sub_domain=vuln`，`sub_domain_params_keys=["type","value"]`，`total=1`。
- `context7-docs "/reactjs/react.dev" "useEffect cleanup" --format json`：`exit=0`，`ok=true`，`library_id=/reactjs/react.dev`，`content_length=2467`。
- `research "React useEffect cleanup docs" --fallback auto --format json`：`exit=0`，`ok=true`，自动 docs 路径选中 `selected_context7_library=/reactjs/react.dev`，`evidence_count=1`，`providers=context7`。

## 4. 遗留事项

- 未处理 GitHub issue #17、#18、#16；其中 #17 仍依赖用户确认或配置独立的 `ZHIPU_MCP_API_KEY`，#18 应走 feature 流程，#16 属于 FAQ/docs 澄清。
- 本次未引入 schema-driven MCP 通用适配层；该方向属于后续独立 roadmap / feature，不放入 #19 修复。
