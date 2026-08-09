---
doc_type: issue-report
issue: 2026-07-06-gh-19-provider-contract-drift
status: confirmed
severity: P1
summary: GitHub issue #19 reports Context7 and AnySearch contract drift causing stale README examples, wrong Context7 library selection, AnySearch domain discovery failure, and unsupported vertical-search parameters.
tags:
  - github
  - provider
  - context7
  - anysearch
---

# GitHub Issue #19 Context7 / AnySearch Contract Drift Issue Report

## 1. 问题现象

GitHub issue #19 报告：`smart-search 0.1.14-beta.8` 中 Context7 和 AnySearch 的外部 provider 契约与当前适配层 / README 示例不一致，导致旧 Context7 React library id 失败、Context7 自动 library 选择偏到不相关库、AnySearch domain discovery 调用不存在工具、AnySearch CVE 垂直搜索示例失败。

当前本机 live smoke 已复现其中四个现象：

- `smart-search context7-docs "/facebook/react" "useEffect cleanup" --format json` 返回 301 network_error。
- `smart-search context7-library "React useEffect cleanup docs" "React useEffect cleanup docs" --format json` 的第一个结果是 `/devopshq/artifactory-cleanup`，`/reactjs/react.dev` 排在后面。
- `smart-search anysearch-domains --format json` 返回 `tool 'list_domains' not found`。
- `smart-search anysearch-search "CVE-2024-3094" --domain security.cve --max-results 1 --format json` 返回 `Invalid tag: security.cve`。

## 2. 复现步骤

1. 在已配置 Context7 和 AnySearch 的环境中使用 `smart-search 0.1.14-beta.8`。
2. 运行 `smart-search context7-docs "/facebook/react" "useEffect cleanup" --format json`。
3. 运行 `smart-search context7-library "React useEffect cleanup docs" "React useEffect cleanup docs" --format json`。
4. 运行 `smart-search anysearch-domains --format json`。
5. 运行 `smart-search anysearch-search "CVE-2024-3094" --domain security.cve --max-results 1 --format json`。
6. 观察到：Context7 旧 ID 返回 301，自动 library 首位不是 React，AnySearch `list_domains` 不存在，`security.cve` 垂直搜索返回 invalid tag。

复现频率：当前本机稳定复现上述四项。

## 3. 期望 vs 实际

**期望行为**：README / skill 示例应使用仍可用的 Context7 library id；Context7 自动 docs 流程应选中与用户查询匹配的库；AnySearch domain discovery 应调用当前存在的工具；AnySearch 垂直搜索应支持当前协议要求的结构化参数。

**实际行为**：README / skill 中仍有 `/facebook/react` 和 `security.cve` 示例；Context7 搜索结果首位可能是不相关库；AnySearch `anysearch-domains` 调用不存在的 `list_domains`；CLI 缺少传入 `sub_domain_params` 或等效结构化参数的能力。

## 4. 环境信息

- 涉及模块 / 功能：Context7 docs_search；AnySearch vertical_search；README / public skill / packaged skill provider examples。
- 相关文件 / 函数：`src/smart_search/service.py` 的 Context7 自动 docs 流程和 AnySearch service wrapper；`src/smart_search/providers/anysearch.py`；`src/smart_search/cli.py` 的 `anysearch-search` 参数；`README.md`、`README.zh-CN.md`、`skills/smart-search-cli/**`、`src/smart_search/assets/skills/smart-search-cli/**`。
- 运行环境：GitHub issue 环境为 Windows / PowerShell / `smart-search 0.1.14-beta.8` / npm `next`；当前本机配置了 Context7 与 AnySearch，live smoke 复现。
- 其他上下文：当前 AnySearch MCP `tools/list` live 返回 `batch_search`、`extract`、`get_sub_domains`、`search`；当前 `smart-search anysearch-search --help` 只有 `--domain`、`--sub-domain`、`--max-results`，没有 `--sub-domain-params`。

## 5. 严重程度

**P1** — 公开文档示例和 provider 适配层同时失准，会影响显式 CLI 调用和自然语言自动调用；Context7 属于 `standard` 最低配置的可选 docs_search provider，AnySearch 虽是实验 provider，但当前示例会直接误导用户。

## 备注

- GitHub issue: https://github.com/konbakuyomu/smartsearch/issues/19
- 当前 `/reactjs/react.dev` live 调用可返回 `useEffect cleanup` 内容，说明 Context7 整体可用，旧 React ID 和选择策略是单独问题。
- 本报告只记录现象和可验证线索；根因判断和修复方案留给 `cs-issue-analyze` 阶段。
