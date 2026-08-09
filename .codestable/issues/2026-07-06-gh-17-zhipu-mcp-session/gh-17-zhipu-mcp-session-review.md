---
doc_type: issue-review
issue: 2026-07-06-gh-17-zhipu-mcp-session
status: passed
reviewer: self
reviewed: 2026-07-06
round: 1
---

# gh-17-zhipu-mcp-session 代码审查报告

## 1. Scope And Inputs

- Report: `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-report.md`
- Analysis: `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-analysis.md`
- Fix note: `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-fix-note.md`
- Evidence pack: none
- Gate results: start gate passed; commit gate initially blocked only because review evidence was missing
- DoD results: none
- Implementation evidence: current diff + fix-note validation section
- Diff basis: `git status --short` shows three modified tracked files plus this #17 issue directory; `git diff --stat` shows provider, focused tests, and provider contract changes
- Baseline dirty files: none outside this #17 scope; untracked `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/` is this unit's evidence directory

### Independent Review

- Detection: Task agent capability exists in this host, but current developer workflow state explicitly requires inline mode and says not to dispatch implement/check sub-agents; `where.exe ocr` returned not found
- 环节 A 独立隔离 Task agent: local-only + skipped-by-user
- 环节 B OCR CLI: not-available
- OCR severity mapping: High->blocking/important, Medium->nit/suggestion, Low->discarded
- Merge policy: 用户明确批准 self-review fallback 后，本报告只合并主 agent 本地只读 review 结果
- Gate effect: user-approved downgrade; downstream gate must run with `CODESTABLE_ALLOW_SELF_REVIEW_FALLBACK=1`

## 2. Diff Summary

- 新增：
  - `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/approval-report.md`
  - `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-analysis.md`
  - `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-fix-note.md`
  - `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-review.md`
  - `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/worktree-override.md`
- 修改：
  - `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/gh-17-zhipu-mcp-session-report.md`
  - `.trellis/spec/backend/provider-capability-contract.md`
  - `src/smart_search/providers/zhipu_mcp.py`
  - `tests/test_zhipu_mcp_provider.py`
- 删除：none
- 未跟踪 / staged：#17 issue directory is untracked and in-scope; no staged files
- 风险热点：provider auth/session protocol, async HTTP error paths, secret masking, same-capability fallback behavior

## 3. Adversarial Pass

- 假设的生产 bug：provider 可能仍然在某些路径裸发 `tools/call`，或初始化失败时泄漏真实 key / 误报成功。
- 主动攻击过的反例：
  - search / reader / zread 是否都先 `initialize` 再 `tools/call`
  - `Mcp-Session-Id` 缺失时是否失败而不是裸发工具请求
  - initialize HTTP 401 和 tool HTTP 401 是否都归一化为 `auth_error` 且不回显 key
  - SSE tool 响应是否仍能解析
  - 是否引入 service/CLI/config 额外契约变化
  - 是否把用户真实 key 写进仓库
- 结果：没有升级为 blocking / important 的问题。live 远端验证因本机未安全配置真实 `ZHIPU_MCP_API_KEY` 保留为 residual risk。

## 4. Findings

### blocking

none

### important

none

### nit

none

### suggestion

none

### learning

- Zhipu Coding Plan MCP 是 stateful MCP-over-HTTP，不应当和 AnySearch 这类无状态 JSON-RPC tool call 路径混为一谈。
- provider contract 与 mock tests 同步是必要的；否则测试会继续固化“第一包就是 `tools/call`”的错误协议。

### praise

- 修复范围保持在 provider 协议层，没有扩到 CLI/config/service。
- `tests/test_zhipu_mcp_provider.py` 现在会在旧行为回退时失败：第一笔请求必须是 `initialize`，后续 `tools/call` 必须携带 `Mcp-Session-Id`。
- exact secret substring scan 未命中用户真实 key；仓库中只出现环境变量名和测试假 key。

## 5. Test And QA Focus

- QA 必须重点复核：
  - `tests/test_zhipu_mcp_provider.py` 中 search / reader / zread 三类 endpoint 的 initialize/session 顺序
  - `smart-search doctor --format json` 在真实 `ZHIPU_MCP_API_KEY` 配置后的 zhipu-mcp 连接状态
  - `smart-search zhipu-mcp-search "测试" --format json` 的 live 远端行为
- Evidence pack residual risks / gate warnings：无 evidence pack；`git diff --check` 仅报告 Windows 行尾提示，不是 whitespace error
- 建议新增或加强的测试：当前单元测试已覆盖本次根因；live test 需要用户本机安全配置 key 后执行
- 不能靠 review 完全确认的点：智谱远端真实 endpoint 是否在当前时间点返回正常结果；本轮没有使用真实 key 做 live 网络调用

## 6. Residual Risk

- Live 远端验证尚未执行。本轮通过 mock HTTP 精确验证协议顺序和错误处理，但仍建议在不暴露 key 的前提下由用户本机运行一次 `smart-search doctor --format json` 或 `smart-search zhipu-mcp-search "测试" --format json`。

## 7. Verdict

- Status: passed
- Next: issue-fix commit gate；若 gate 通过，可按 scoped-commit 询问用户是否提交 #17 到 beta 分支。
