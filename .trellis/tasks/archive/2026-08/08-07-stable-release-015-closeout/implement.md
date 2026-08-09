# Implementation

1. 汇总子任务 diff 和验收结果。
2. 运行 full pytest/regression/mock smoke/npm/package/tarball/secret gates。
3. 运行已配置 provider live-limited checks。
4. 回读 npm/GitHub availability 和本机 mise 状态。
5. 输出 commit/remote release plan，停在 owner gate。
