# Reconcile release baseline

## Goal

在独立发布工作树中建立同时包含 beta.8 与三个本地 provider 提交的统一基线，并选择性吸收 PR #21，且不触碰原工作树脏改动。

## Requirements

- 分支 `codex/release-0.1.15` 必须基于 `origin/main=667c465`。
- 按顺序整合 `18f4611`、`e5357cf`、`ebc8ce5`、`6a30a9a`，保留作者信息。
- PR #21 冲突时保留当前 live-proven AnySearch `get_sub_domains` 实现，仅吸收缺失行为。
- 解决冲突后不得出现丢失的 OpenAI fallback、Zhipu MCP session、Sciverse explicit-only 或 packaged skill 文件。

## Acceptance Criteria

- [ ] 四个来源提交的预期行为都能在发布分支中定位。
- [ ] focused provider tests、compileall 和 `git diff --check` 通过。
- [ ] 原工作树 dirty path 集合与任务开始前一致。

## Out Of Scope

- 本任务不修改 provider 行为设计，不做版本 bump，不执行远程 push。
