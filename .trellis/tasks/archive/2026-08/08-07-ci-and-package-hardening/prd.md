# Harden CI and package release

## Goal

在发布前增加无副作用 PR CI、真实 tarball 安装验证和可预测的 prerelease/stable workflow。

## Requirements

- CI 在 pull_request、main push 和手动触发运行，但不得执行 publish。
- 矩阵固定为 Ubuntu Node18/Python3.10、Ubuntu Node24/Python3.12、Windows Node22/Python3.12。
- CI 执行 npm test、regression、mock smoke、pack dry-run、tarball install smoke、skill parity、diff check。
- publish workflow 增加 concurrency；stable version 相对 first parent 变化时 main push 跳过自动 beta。
- 版本同步为 `0.1.15`，增加 beta/stable notes，并保持 tag stable -> npm latest。

## Acceptance Criteria

- [ ] workflow YAML 可解析，静态契约 tests 覆盖 triggers、matrix、no-publish、concurrency、stable change detection。
- [ ] 本机执行与 CI 相同的 npm/package gates 全绿。
- [ ] tarball 只包含声明资产，安装后 version/regression/mock smoke 通过。
- [ ] `0.1.15-beta.1` 和 `0.1.15` registry availability 在远程动作前回读。

## Out Of Scope

- 不升级 actions major 或引入 Python lockfile；另立依赖维护任务。
