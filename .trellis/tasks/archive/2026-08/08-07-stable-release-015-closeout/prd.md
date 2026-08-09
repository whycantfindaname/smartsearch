# Close out smart-search v0.1.15 release

## Goal

完成跨子任务全量 QA、可用 provider live 验证、secret scan 和 beta 发布前证据包，并停在远程授权门槛。

## Requirements

- 前四个子任务均完成并通过各自验收后才启动。
- 运行源码、npm、tarball、skill parity、secret scan 和 live-limited 全量矩阵。
- 缺少三个 optional keys 必须记为未验证；Zhipu 429 记为外部 degraded。
- 准备 beta workflow inputs、安装命令、rollback 和 Issue/PR closeout 文案，但未经授权不执行远程 mutation。

## Acceptance Criteria

- [ ] 全部离线 gates 零失败，发布工作树 clean 或仅含明确待提交发布改动。
- [ ] live provider 结果已脱敏汇总，missing/degraded 边界明确。
- [ ] beta version 可用，发布 workflow target/ref/version/tag 参数精确。
- [ ] 给出 commit 分组和远程动作清单，等待 owner 单独确认。

## Out Of Scope

- 未获单独授权时不 commit、push、开 PR、merge、dispatch、tag、publish 或关闭 Issue/PR。
