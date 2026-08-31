# Smart Search 受管同步指南（人的操作手册）

本指南让任何操作者（无论是否使用 Agent）完成 Smart Search 在受管项目同步框架中的
五个阶段。框架权威：Agent Infra `main` 的 `docs/runbooks/managed-project-sync.md`；
仓库收敛由 Infra registry 拥有，本仓库只拥有“项目怎么做”。

<!-- MANAGED-SYNC:STATUS-BLOCK:BEGIN -->
- Registry ID: smartsearch
- Managed branch: lwj_dev（开发权威）；main 仅跟随 upstream（origin = konbakuyomu/smartsearch）
- Publication: fork = whycantfindaname/smartsearch，branch lwj_dev（companion manifest clone_remote=fork）
- Workflow status: full_workflow
- 合同: .agent-infra/managed-project.json
- 错误目录: docs/managed-sync-errors.md
- Provider/请求恢复错误: skills/smart-search-cli/references/error-recovery.md（不在本指南范围）
<!-- MANAGED-SYNC:STATUS-BLOCK:END -->

## 阶段 1 — 仓库收敛（由 Infra 执行）

目标：让登记分支达到可解释状态。

```bash
agent-infra sync repositories --platform macos
```

预期：`lwj_dev` clean + 与 `fork/lwj_dev` 对齐；`main` 仅 fast-forward 到 `origin/main`。
停止条件：dirty、diverged、branch/remote mismatch —— 按输出给出的下一条命令处理，
不在本阶段 merge/push。普通同步不运行测试、doctor 或 provider 请求。

## 阶段 2 — 项目工作流（本仓库）

前置：阶段 1 输出全部收敛；工作树干净且在 `lwj_dev`。

1. 上游整合（仅当 `origin/main` 有新提交）：把该精确 commit 合并到 `lwj_dev`：

```bash
git -C <smartsearch> merge --no-ff <origin/main exact commit>
```

   冲突即停：记录 pre-merge HEAD 与冲突路径，`git merge --abort`，交给人决定。
2. 合同入口检查与聚焦验证：

```bash
agent-infra sync project smartsearch --through source
# 等价人工命令：
python3 scripts/managed_sync.py inspect
npm run check:skill-parity
npm run smoke:tarball
```

预期：源码 Skill 与打包 Skill 一致；packed tarball 安装后 `--version`、`modes`、
`regression`、`smoke --mock` 全部通过。失败时查错误目录对应 anchor。

## 阶段 3 — 下游传播（Skills 仓库）

在 personal Skills 仓库 main-first 更新 `skill-packages/smart-search-cli`，producer
commit 绑定本次 `lwj_dev` SHA；随后 package-aware 合并到原生分支。命令由
`updating-agent-skills` 拥有（`scripts/update_global_skill.py`、
`scripts/merge_global_skill_profile.py`），本仓库不复制。

## 阶段 4 — 当前平台激活（仅本机）

```bash
agent-infra sync current-machine
```

macOS 依次回读 governed package → immutable cache → `~/.codex/skills/smart-search-cli`
→ Claude skills 目标的来源一致性。普通同步在此结束，输出
`functional_verification=not_run`。

## 阶段 5 — 显式功能验收（只能显式运行）

外部闸门（全部满足才运行）：
- 机器私有 `~/.config/smart-search/config.json` 存在且校验通过；
- 有效的主 provider；
- profile 声明的 Grok2API 账户/会话与非空模型列表（runtime-optional 仅针对普通搜索，
  完整验收需要这些闸门）。

```bash
agent-infra sync verify smartsearch
```

一次验收最多一次 doctor/恢复探针。失败保留真实 error code 与 pending live 状态，
不重复探针。密钥、账户内容不得进入输出或 receipt。

## Rollback 提示

- 阶段 2 合并后未推送：普通 revert；已推送：只新增 revert，不 rewrite。
- 打包/传播失败：回到上一个已知一致的 producer commit，重跑阶段 2–3。
- 激活失败：用平台 adapter 的 prior receipt 恢复 cache/link 指针。
