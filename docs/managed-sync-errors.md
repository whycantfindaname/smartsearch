# Smart Search 受管同步错误目录（当前有效）

只记录仓库/打包/传播/激活错误的当前有效处理。历史处理由 Git history 保留，不在本文件
堆叠版本。搜索 provider 与请求恢复错误见
`skills/smart-search-cli/references/error-recovery.md`（source authority，Smart Search
`lwj_dev`），不复制到本目录。

## SS_SYNC_DIRTY_UNSCOPED

- 阶段：仓库收敛 / 项目工作流前置
- 含义：工作树存在无法归属到当前任务的改动。
- 检查：`git status --short`；对每个路径确认归属。
- 处理：属于其他任务 → 先完成或提交该任务；不明 → 停止并交给人决定。
- 停止条件：未确认归属前不得提交、不得覆盖。

## SS_SYNC_BRANCH_MISMATCH

- 阶段：仓库收敛
- 含义：当前分支/remote 与登记（companion manifest）不一致。
- 检查：`git branch --show-current`、`git remote -v`、manifest `branch`/`clone_remote`。
- 处理：以登记为准切回/修复 remote；若登记本身过时，先在 Agent Infra manifest 修正。
- 停止条件：身份未对齐前零修改。

## SS_SYNC_SKILL_PARITY_DRIFT

- 阶段：项目工作流
- 含义：`skills/smart-search-cli` 与 `src/smart_search/assets/skills/smart-search-cli`
  不一致。
- 检查：`npm run check:skill-parity`（输出差异文件）。
- 处理：以源码 Skill 为准，同步打包副本后重跑；不得只改一侧。
- 停止条件：差异未消除前不进入打包 smoke。

## SS_SYNC_PACKED_SMOKE_FAILED

- 阶段：项目工作流
- 含义：`npm run smoke:tarball` 在临时安装后行为校验失败。
- 检查：重跑并记录失败子命令（`--version` / `modes` / `regression` / `smoke --mock`）。
- 处理：按失败子命令定位 npm 打包面（`files`、bin wrapper、sidecar 资源）；修复后
  必须重跑完整 smoke。
- 停止条件：未通过前不得推送或传播下游。

## SS_SYNC_PUSH_REJECTED

- 阶段：发布（阶段 2 之后）
- 含义：`fork/lwj_dev` 推送被拒或远端回读与本地不一致。
- 检查：`git ls-remote fork refs/heads/lwj_dev` 对比本地 `lwj_dev`。
- 处理：确认远端无他人新提交；有则停止并交给人决定合并策略。禁止 force。
- 停止条件：远端与本地精确 SHA 未对齐前不宣称 pushed。

## SS_VERIFY_EXTERNAL_GATE_MISSING

- 阶段：显式功能验收
- 含义：机器私有配置、主 provider 或 Grok2API 闸门缺失/校验失败。
- 检查：只看配置是否存在与校验结果，不读取密钥内容。
- 处理：补齐对应闸门后重新显式运行 `agent-infra sync verify smartsearch`。
- 停止条件：保留真实 pending live 状态；不用重复探针掩盖。

## SS_VERIFY_PROVIDER_ERROR

- 阶段：显式功能验收
- 含义：真实请求失败（一次验收最多一次恢复探针后仍失败），或 doctor 通过但固定的
  真实搜索用例失败（此时验收结果为 `activated`/diagnostic ready，不是 `live`）。
- 处理：请求/恢复类错误转入
  `skills/smart-search-cli/references/error-recovery.md` 的对应条目；本目录不复制。
- 停止条件：不循环重试。
