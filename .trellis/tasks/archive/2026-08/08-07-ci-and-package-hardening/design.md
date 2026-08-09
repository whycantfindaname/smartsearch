# Design

- 使用 matrix include 明确三个受支持组合，避免无意义笛卡尔积。
- tarball smoke 安装到 runner temp prefix，不污染全局环境。
- CI 与 publish workflow 使用不同文件和 permissions；CI 只读 contents。
- stable-bump detection 比较当前 package version 与 first-parent version，同时保留旧 commit-subject 兼容逻辑。
- publish concurrency 按 package/release lane 串行，CI 按 ref 取消旧运行。
