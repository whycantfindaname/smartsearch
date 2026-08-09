---
doc_type: issue-analysis
issue: 2026-07-06-gh-17-zhipu-mcp-session
status: confirmed
root_cause_type: state-pollution
related:
  - gh-17-zhipu-mcp-session-report.md
tags:
  - provider
  - zhipu-mcp
  - session
---

# GitHub Issue #17 zhipu-mcp AUTH_ERROR 根因分析

## 1. 问题定位

| 关键位置 | 说明 |
|---|---|
| `src/smart_search/providers/zhipu_mcp.py:121` | `ZhipuMCPProvider.call_tool()` 是所有 zhipu-mcp search / reader / zread 工具调用的统一入口。 |
| `src/smart_search/providers/zhipu_mcp.py:138` | 当前 payload 直接构造 JSON-RPC `tools/call`，没有先发送 `initialize`。 |
| `src/smart_search/providers/zhipu_mcp.py:143` | 当前 headers 只包含 `Authorization`、`Content-Type`、`Accept`，没有 `Mcp-Session-Id`。 |
| `src/smart_search/service.py:2940` | service 为 search / reader / zread 各自创建 `ZhipuMCPProvider`，三个端点都会复用同一 provider 类，因此同一协议缺口会同时影响三个端点。 |
| `tests/test_zhipu_mcp_provider.py:67` | 现有测试只断言第一笔请求就是 `tools/call`，反而固化了缺少握手的旧行为。 |

## 2. 失败路径还原

**正常路径**：用户配置 `ZHIPU_MCP_API_KEY` -> provider 首次调用前向对应 MCP endpoint 发送 JSON-RPC `initialize` -> 从响应 header 读取 `Mcp-Session-Id` -> 后续 `tools/call` 带上该 session header -> 远端识别同一有状态 streamableHttp 会话并返回工具结果。

**失败路径**：用户配置 `ZHIPU_MCP_API_KEY` -> `smart-search doctor` 或 web_search / web_fetch 调用 `ZhipuMCPProvider.call_tool()` -> 代码直接发送 `tools/call` -> headers 里没有 `Mcp-Session-Id` -> 智谱 Coding Plan MCP 按无会话请求处理，返回 `MCP error -401: Api key not found` -> Smart Search 将其归一化为 `auth_error`，provider 不可用。

**分叉点**：`src/smart_search/providers/zhipu_mcp.py:138` — 代码把 MCP endpoint 当作无状态 JSON-RPC 工具端点使用，但远端实际需要先建立有状态会话。

## 3. 根因

**根因类型**：state-pollution

**根因描述**：Zhipu Coding Plan MCP 的 streamableHttp 端点要求一次会话状态：先握手拿 session id，再带 session id 调工具。当前 provider 没有保存和复用会话状态，导致每次工具请求都像“没登录的第一包请求”，远端无法把 Authorization 关联到 MCP session，于是返回 401 文本错误。

**是否有多个根因**：否。配置键、fallback 链和 service wrapper 均能把请求送到同一个 provider；真正失败点在 provider 协议层缺少 initialize/session header。

## 4. 影响面

- **影响范围**：影响所有通过 `ZHIPU_MCP_API_KEY` 启用的 Zhipu Coding Plan MCP endpoint，包括 `zhipu-mcp` 的 `web_search_prime`、`zhipu-mcp-reader` 的 `webReader`、以及 zread 的 `search_doc` / `get_repo_structure` / `read_file`。
- **潜在受害模块**：`doctor` 的 zhipu-mcp 连接测试、`web_search` 同能力 fallback、`web_fetch` 同能力 fallback、显式 `zhipu-mcp-*` CLI 命令。
- **数据完整性风险**：无。本问题只导致 provider 调用失败，不会写入或损坏用户数据。
- **严重程度复核**：维持 P1。已配置该 provider 的用户路径稳定失败，但仍可通过同能力其他 provider 绕过，且最低 profile 不强制要求 zhipu-mcp。

## 5. 修复方案

### 方案 A：在 `ZhipuMCPProvider` 内做窄协议修复

- **做什么**：在 provider 内新增初始化握手方法；首次 `call_tool()` 前发送 JSON-RPC `initialize`，读取并缓存 `Mcp-Session-Id`，再在同一 provider 实例生命周期内给 `tools/call` 加该 header。补充 focused tests 覆盖 search、reader、zread、缺 session header、HTTP auth error 和 SSE 解析。
- **优点**：改动集中在协议适配层；search / reader / zread 自动一并修好；不改变 CLI、config、service 的公开契约。
- **缺点 / 风险**：service 当前每次 wrapper 调用都会创建 provider 实例，因此缓存粒度是单次 service wrapper 生命周期；不过这已经满足“首次调用前握手，然后调用工具”的协议要求。
- **影响面**：`src/smart_search/providers/zhipu_mcp.py`、`tests/test_zhipu_mcp_provider.py`，必要时在 provider contract 里补一句 session 行为。

### 方案 B：在 service 层维护 endpoint 级 provider/session 缓存

- **做什么**：让 service 保存 search / reader / zread provider 单例，跨多次 CLI/service 调用复用 `Mcp-Session-Id`。
- **优点**：网络握手次数更少，长生命周期进程内更高效。
- **缺点 / 风险**：会把远端 session 状态引入全局 service 层，增加测试隔离、过期 session、并发访问和配置热更新风险；比当前 bug 所需更大。
- **影响面**：`service.py`、provider、更多 service/doctor 测试。

### 推荐方案

**推荐方案 A**，理由：#17 的根因是 provider 协议层缺失有状态握手，不是 service routing 或 config 问题。把 initialize/session 放在 `ZhipuMCPProvider` 内是最小充分修复，能覆盖三个端点，又不会扩大到全局缓存和 CLI 契约变化。用户本轮已要求开始修复 #17，因此按方案 A 进入 `cs-issue-fix`。
