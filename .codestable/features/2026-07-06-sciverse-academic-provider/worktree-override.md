# Worktree Override

## reason

当前仓库已经在 repo-owned integration branch `codex/integrate-smartsearch-prs-beta` 上连续处理 #17、#19 和 #18 规划产物；#18 的 design / checklist / requirements 也已经在当前检出中形成 untracked 规划面。为了避免把未提交规划产物搬运到新 linked worktree 时制造重复 spec 或丢失上下文，本次 #18 在当前分支内继续执行。

## scope

仅限 `.codestable/features/2026-07-06-sciverse-academic-provider/` 关联的 Sciverse experimental vertical_search provider 实现、测试、文档、review、QA 与 acceptance 产物。不得借此扩大到 merge、deploy、push 或 commit；这些仍需按用户要求单独停下确认。

## approval

用户在 2026-07-06 明确授权自动继续执行 `cs-feat-impl -> cs-code-review -> cs-feat-qa -> cs-feat-accept`，并要求不要每个阶段都手动确认；仅在范围变更、架构决策、风险接受、无法验证、需要 merge/deploy/commit 时停下询问。本 override 只用于通过当前检出的 CodeStable start gate。
