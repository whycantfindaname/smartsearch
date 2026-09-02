# Smart Search 受管交付 RUNBOOK

本 RUNBOOK 是 Smart Search 与 Agent Infra 之间的跨平台交付合同说明。它只描述
已经完成项目开发后如何证明发布就绪、把结果交给下游、交给平台并进行真实消费者
验收；产品目的、架构、普通测试和 Trellis 任务仍由本仓库自己的文档与规范拥有。

<!-- MANAGED-SYNC:STATUS-BLOCK:BEGIN -->
- Registry ID: `smartsearch`
- Authority branch: `lwj_dev`; `main` 只跟随 upstream（origin = `konbakuyomu/smartsearch`）
- Publication: fork = `whycantfindaname/smartsearch`, branch `lwj_dev`
- Delivery schema: `jason-agent-infra.managed-delivery-workflow.v2`
- Contract: `.jason-liao-agent-infra/managed-project.json`
- Delivery errors: `.jason-liao-agent-infra/errors.md`
- Downstream consumer: `skills-common`（由 Skills 的 `updating-agent-skills` 流程传播）
- Target platforms: `macos`, `oppo_linux`, `oppo_windows`
- Provider/request recovery errors: `skills/smart-search-cli/references/error-recovery.md`
<!-- MANAGED-SYNC:STATUS-BLOCK:END -->

## 边界与前置条件

仓库 fetch、分支收敛、upstream review 和远端发布由 Agent Infra registry 及其平台
profile 拥有，本 RUNBOOK 不复制这些命令，也不把它们伪装成项目阶段。开始项目交付
前，先让当前平台的 Infra 收敛命令报告 checkout 身份、分支和工作树可解释。

本合同的普通项目验证（完整 pytest、npm test、lint、架构检查和 Trellis quality
gate）继续由本仓库自己的 CI/Trellis 运行。只有直接证明 Smart Search 可作为发布物
生成、安装和使用的最小门禁才属于这里。

## v2 生命周期

| 合同阶段 | 本项目声明的动作 | 所有者 | 默认是否执行 |
| --- | --- | --- | --- |
| `release_readiness` | checkout/Skill 镜像检查、Skill parity、packed tarball 安装 smoke | Smart Search | `sync project --through readiness` |
| `downstream_propagation` | 将本次 producer commit 传播到 Skills `main`，再合并到原生 profile | Skills `updating-agent-skills` + Infra | 由下游流程执行；本合同不伪造项目命令 |
| `platform_activation` | governed package、immutable cache 和平台目标的安装/回读 | 选定 Infra profile/adapter | `sync current-machine` 的平台流程 |
| `functional_verification` | 一次 doctor 与一个固定、无敏感内容的真实搜索请求 | Smart Search + 选定平台 | 仅显式 `sync verify smartsearch` |

合同只声明 Smart Search 能真实执行的 `release_readiness` 与
`functional_verification` 命令。下游传播和平台激活需要 Skills/Infra 的外部状态，
所以它们由各自 owner 的流程完成，不能用一个空操作或重复检查冒充完成证据。

## 发布就绪

从 Smart Search authority branch 的干净、已提交工作树开始：

```bash
python3 scripts/managed_sync.py inspect
npm run --silent check:skill-parity
npm run --silent smoke:tarball
```

等价的 Infra 入口是：

```bash
agent-infra sync project smartsearch \
  --workspace-root /absolute/workspace --through readiness
```

三个门禁按依赖顺序执行：

1. `inspect` 确认当前分支是 `lwj_dev`、工作树 clean，并比较源码 Skill 与打包镜像。
2. `check:skill-parity` 逐文件确认 `skills/smart-search-cli/` 与
   `src/smart_search/assets/skills/smart-search-cli/` 相同，忽略明确的机器本地文件。
3. `smoke:tarball` 在临时前缀打包并安装 npm tarball，验证版本、公开 modes、regression、
   mock smoke 和 OpenCode Skill 安装；临时目录不属于仓库变更。

任一门禁失败即停止本项目交付，不进入下游传播。完整普通测试仍按项目
`.trellis/spec/backend/quality-guidelines.md` 运行，不由本合同替代。

## 下游传播与平台交接

Smart Search 的 producer commit 通过 Skills 仓库的 `updating-agent-skills` 流程进入
`skill-packages/smart-search-cli`，然后由 package-aware 合并传播到选定平台分支。
该流程拥有下游工作树、package pin、immutable cache 和运行时投影；Smart Search
只提供已通过 release readiness 的 producer identity，不直接修改 Skills 或平台目录。

平台 profile 再按自己的 `RUNBOOK.md`/adapter 将 governed package 安装到目标运行时并
回读来源一致性。平台路径、service manager、secret、runtime root 和机器特有错误不
写入本合同。

## 显式功能验收

只有用户或显式平台流程指定 `sync verify smartsearch` 才允许真实 provider 请求：

```bash
agent-infra sync verify smartsearch \
  --workspace-root /absolute/workspace --format json
```

运行前必须满足选定平台的私有配置、主 provider 和 profile 声明的 Grok2API gate。
合同命令只记录配置是否存在与探针结果，不读取或写出密钥。一次验收最多一次 doctor/
恢复探针；doctor 成功不等于 live，固定搜索成功才报告 `live`，doctor 成功而搜索
失败只能报告 `activated`/diagnostic-ready。

## 恢复

恢复不是正向 sync stage。恢复 owner 是选定的 Infra platform adapter；restore
authority 是该 profile 为 `smart-search-config` 与 `anysearch-credentials` 维护的
恢复权威。恢复必须选择平台 receipt 中的精确上一代 generation，并在恢复后只运行
一次本合同声明的功能验收。只有记录了精确 pre-state、restore authority 和接受性探针
才能报告 `rollback-ready`；实际恢复且探针通过后才是 `rollback-verified`。

## 失败处理

本 RUNBOOK 的稳定交付错误均在 [`errors.md`](./errors.md) 定义，包含含义、检查、
修复和停止条件。provider/request 恢复错误仍以
[`skills/smart-search-cli/references/error-recovery.md`](../skills/smart-search-cli/references/error-recovery.md)
为唯一权威，不复制到交付错误目录。

## 兼容桥接

同目录 `README.md` 暂时只是指向本 RUNBOOK 的迁移入口。中央 registry 所有采用者均
切换到 `RUNBOOK.md` 并通过验证后，才可删除该桥接文件。
