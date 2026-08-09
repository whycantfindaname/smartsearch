# Implementation

1. 核对 worktree HEAD 和原工作树 dirty snapshot。
2. 顺序 cherry-pick 四个提交并解决冲突。
3. 检查 commit graph、关键符号和 docs/skill 双份资产。
4. 运行 compileall、provider focused tests、diff check。
5. 输出统一基线 SHA 和未解决项。
