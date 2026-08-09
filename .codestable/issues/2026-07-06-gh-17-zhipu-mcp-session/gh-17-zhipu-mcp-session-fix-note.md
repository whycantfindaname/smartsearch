---
doc_type: issue-fix
issue: 2026-07-06-gh-17-zhipu-mcp-session
status: completed
path: standard
fix_date: 2026-07-06
related:
  - gh-17-zhipu-mcp-session-analysis.md
tags:
  - provider
  - zhipu-mcp
  - session
---

# GitHub Issue #17 zhipu-mcp AUTH_ERROR 修复记录

## 1. 实际采用方案

采用 analysis 推荐的方案 A：在 `ZhipuMCPProvider` 内做窄协议修复。

外部行为变化：`zhipu-mcp` / `zhipu-mcp-reader` / `zhipu-mcp-zread` 首次调用工具前会先向对应 MCP endpoint 发送 JSON-RPC `initialize`，从响应 header 读取并缓存 `Mcp-Session-Id`，随后 `tools/call` 请求会带上 `Mcp-Session-Id`。

第一性原则 pre-pass：

- 本次真正改变的外部行为：已配置 `ZHIPU_MCP_API_KEY` 时，provider 不再裸发 `tools/call`，而是按智谱 Coding Plan MCP 的 stateful streamableHttp 协议先握手再调用工具。
- 不可破的约束：不改变 `ZHIPU_MCP_API_KEY` / endpoint config / CLI 命令签名；不把 Zhipu MCP 并入 Zhipu Web Search REST provider；fallback 仍保持同能力内回退。
- 最小充分改动：只在 provider 协议层新增 initialize/session 处理，并补充 focused tests 与 provider contract note。
- 明确没做的事：没有引入通用 MCP client 抽象；没有在 service 层做全局 session 单例；没有使用或落盘真实用户 key。

## 2. 改动文件清单

- `src/smart_search/providers/zhipu_mcp.py`
  - 新增 `_MCP_PROTOCOL_VERSION`、`ZhipuMCPSessionError`、`_jsonrpc_error_message()`。
  - 新增 provider 内部 request id、session id 缓存、统一 headers 构造。
  - `call_tool()` 发送 `tools/call` 前先调用 `_ensure_session()`；`tools/call` header 带 `Mcp-Session-Id`。
  - 初始化失败、缺 session header、HTTP 401/403 继续归一化为不泄漏 key 的 provider/auth 错误。
- `tests/test_zhipu_mcp_provider.py`
  - Fake client 改为支持顺序响应，覆盖 initialize -> tools/call。
  - 覆盖 search、reader、zread 三类 endpoint 都带 session。
  - 覆盖 initialize 401、initialize 缺 `Mcp-Session-Id`、tool HTTP 401、SSE tool 响应解析。
- `.trellis/spec/backend/provider-capability-contract.md`
  - 补充 Zhipu Coding Plan MCP 的 stateful MCP-over-HTTP session 契约。
  - 补充测试要求：必须断言 initialize 先于 `tools/call`，并发送 `Mcp-Session-Id`。
- `.codestable/issues/2026-07-06-gh-17-zhipu-mcp-session/`
  - report 状态更新为 `confirmed`。
  - 新增 analysis、worktree override、fix-note。

## 3. 验证结果

- `python .codestable/tools/codestable-worktree-gate.py --root . --json start --unit .codestable/issues/2026-07-06-gh-17-zhipu-mcp-session`：通过。
- `.\.venv\Scripts\python.exe -m pytest tests/test_zhipu_mcp_provider.py -q`：`9 passed`。
- `.\.venv\Scripts\python.exe -m compileall -q src tests`：通过。
- `.\.venv\Scripts\python.exe -m pytest tests/test_zhipu_mcp_provider.py tests/test_service.py tests/test_cli.py -q`：`197 passed`。
- `.\.venv\Scripts\python.exe -m pytest tests -q`：`308 passed`。
- `.\.venv\Scripts\python.exe -m smart_search.cli regression`：`245 passed`。
- `.\.venv\Scripts\python.exe -m smart_search.cli smoke --mock --format json`：`ok=true`。
- `git diff --check`：无 whitespace 错误；仅报告 Windows 工作树行尾提示。

复现步骤验证：本机未配置 `ZHIPU_MCP_API_KEY`，且本次未把用户真实 key 写入命令或日志，因此没有执行 live `doctor`。通过 mock HTTP 回归精确验证了 issue #17 的协议差异：裸 `tools/call` 不再发生，所有工具调用前都先 `initialize` 并携带 `Mcp-Session-Id`。

## 4. 遗留事项

- 若要完全确认远端线上行为，还需要用户在本机安全配置 `ZHIPU_MCP_API_KEY` 后运行 live `smart-search doctor --format json` 或 `smart-search zhipu-mcp-search "测试" --format json`。这一步不需要把 key 发给我。
- CodeStable implementation review 已完成，用户明确批准 self-review fallback。严格 worktree commit gate 仍不接受 `reviewer: self`，该 P1 gate 降级已由用户在 2026-07-06 明确接受。
