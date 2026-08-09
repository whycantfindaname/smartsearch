# Design

- 使用独立 worktree，避免 stash、reset 或切换原工作树。
- 先 cherry-pick 三个本地提交，再 cherry-pick PR #21；冲突逐文件解决，不整分支 merge。
- 每次 cherry-pick 后检查状态和冲突集合；完成后用 focused tests 验证交叉契约。
