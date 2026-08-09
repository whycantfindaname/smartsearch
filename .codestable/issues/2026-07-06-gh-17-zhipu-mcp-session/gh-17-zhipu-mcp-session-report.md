---
doc_type: issue-report
issue: 2026-07-06-gh-17-zhipu-mcp-session
status: confirmed
severity: P1
summary: GitHub issue #17 reports that configured zhipu-mcp calls return AUTH_ERROR -401 even when the same key works after an MCP initialize/session handshake.
tags:
  - github
  - provider
  - zhipu-mcp
---

# GitHub Issue #17 zhipu-mcp AUTH_ERROR Issue Report

## 1. 问题现象

GitHub issue #17 报告：在 `smart-search 0.1.14b8` 的 `@next` 通道中，已配置 `ZHIPU_MCP_API_KEY` 后，`smart-search doctor` 对 `zhipu-mcp` 始终返回 `AUTH_ERROR`，错误文本为 `MCP error -401: Api key not found, please get your apikey`。`web_search` / `web_fetch` 尝试使用 zhipu-mcp 时也会失败。2026-07-06 通过 `gh issue view 17 -R konbakuyomu/smartsearch` 复核，远程 issue 仍为 `OPEN`，正文仍指向相同现象。

## 2. 复现步骤

1. 在 macOS 26.5.1 / Python 3.14.6 / Node v26.4.0 环境中安装 `smart-search 0.1.14b8`。
2. 配置 `ZHIPU_MCP_API_KEY`。
3. 运行 `smart-search doctor`，或运行会触发 zhipu-mcp 的 `web_search` / `web_fetch`。
4. 观察到：zhipu-mcp 返回 `AUTH_ERROR` / `MCP error -401: Api key not found, please get your apikey`。

复现频率：GitHub issue 描述为稳定复现。当前本机未配置 `ZHIPU_MCP_API_KEY`，只能复现到 `config_error: ZHIPU_MCP_API_KEY is not configured`，无法本机复现远端 401。

## 3. 期望 vs 实际

**期望行为**：配置有效的 `ZHIPU_MCP_API_KEY` 后，zhipu-mcp provider 可以正常调用 `web_search_prime`、`webReader` 和 zread 相关工具。

**实际行为**：GitHub issue 报告 zhipu-mcp 在已配置 key 时仍返回 401 AUTH_ERROR，导致该 provider 不可用。

## 4. 环境信息

- 涉及模块 / 功能：Zhipu Coding Plan Remote MCP provider；`zhipu-mcp-search`、`zhipu-mcp-reader`、doctor 连接测试。
- 相关文件 / 函数：`src/smart_search/providers/zhipu_mcp.py` 的 `ZhipuMCPProvider.call_tool()`；`src/smart_search/service.py` 的 zhipu-mcp provider 构造和 doctor 测试路径。
- 运行环境：GitHub issue 环境为 macOS 26.5.1 / Python 3.14.6 / Node v26.4.0 / `smart-search 0.1.14b8`。
- 其他上下文：GitHub issue 提供了 curl 对照测试：同一把 key 在先做 MCP `initialize` 并带 `Mcp-Session-Id` 后可成功调用；当前本机 `smart-search doctor --format json` 显示 `ZHIPU_MCP_API_KEY` 未配置。

## 5. 严重程度

**P1** — 已配置用户会看到一个公开 provider 路线完全不可用；不过该路线属于 Zhipu Coding Plan Remote MCP，标准最低配置仍可由其他同能力 provider 绕过。

## 备注

- GitHub issue: https://github.com/konbakuyomu/smartsearch/issues/17
- 用户在 2026-07-06 明确要求“现在开始修复 #17”，本报告状态更新为 `confirmed`，进入 `cs-issue-analyze` / `cs-issue-fix`。
