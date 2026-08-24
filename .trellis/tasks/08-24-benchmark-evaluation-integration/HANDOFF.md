# Smart Search Linux GPU Development Handoff

## 目标

在 Linux 8×A100 上继续完成 Smart Search 多源 Agentic Research 与 Benchmark
评测能力。当前执行清单是：

- `.trellis/tasks/08-24-benchmark-evaluation-integration/implement.md`

任务目前仍为 `planning`。用户确认计划并允许实施后，才可执行
`task.py start`、部署 SGLang、下载模型或数据集、调用真实 Provider/Judge。

## 当前进展

- CodeStable 有价值内容已迁移到 Trellis；迁移任务已归档。
- Smart Search 多源研究 Preview、Research contracts、caller-held runtime、
  Artifact Registry、Trace、ResearchWorkspace 和 Visualizer 已存在于当前工作树。
- 已完成面向 Codex、Claude Code、Pi、OpenCode 的代码级可移植性审计。
- 已把四 Harness、三产品模式、逐题 Workspace、归一化 Agent Trace 和 Benchmark
  Viewer 写入当前 Benchmark 任务的 PRD、Design 和 Implementation Plan。
- Trellis `task.py validate 08-24-benchmark-evaluation-integration` 已通过；没有启动
  Benchmark、模型服务、Provider 或 Judge。

详细计划与证据以这些文件为准，不在本交接文档重复维护第二份设计：

- 需求：`.trellis/tasks/08-24-benchmark-evaluation-integration/prd.md`
- 技术设计：`.trellis/tasks/08-24-benchmark-evaluation-integration/design.md`
- 实施顺序：`.trellis/tasks/08-24-benchmark-evaluation-integration/implement.md`
- Harness/可视化代码审计：
  `.trellis/tasks/08-24-benchmark-evaluation-integration/research/harness-portability-and-observability.md`
- Harness 网页来源与可复现查询：
  `.trellis/tasks/08-24-benchmark-evaluation-integration/research/harness-web-sources.md`
- Qwen/SGLang/Codex 环境设计：
  `.trellis/tasks/08-24-benchmark-evaluation-integration/research/qwen-sglang-codex-harness.md`
- Benchmark 候选、评分与复现成本：
  `.trellis/tasks/08-24-benchmark-evaluation-integration/research/benchmark-shortlist.md`

## 已确定方案

1. 当前准确边界是 `Harness-neutral research protocol + Codex-oriented deployment
   artifacts`，尚不是完整的多 Harness runtime。
2. `ResearchFrame`、`DelegateRequest/DelegateResult`、Evidence、Claim、Trace 和
   Workspace 可作为四种 Harness 的公共协议；各 Harness 仍需实现启动、模型注入、
   原生事件解析、取消/超时和终态映射。
3. Codex 是首个参考 Driver。OpenCode 与 Pi 预计可直接走 SGLang 的
   OpenAI-compatible 路径，但仍缺原生角色投影和事件适配器。
4. Claude Code 是实验性 Driver。它必须先通过 Anthropic Messages、多工具流、
   deferred tool、Subagent 和长会话门槛；允许加入只做协议转换的兼容层，但底层
   checkpoint 仍必须是同一个 Qwen，不允许回退到托管模型。
5. Root Agent 与 Search Scout、Source Curator、Evidence Miner 固定使用同一
   Qwen/Qwen3.8-27B revision 和相同模型推理配置。quick、standard、deep 是 Smart
   Search 产品模式，不是三个 Harness-specific reasoning_effort。
6. quick、standard、deep 在评测中必须统一走 Root-led `research-run --workspace`，
   每题、每 Harness、每模式生成独立 ResearchWorkspace。
7. Visualizer 必须对三种模式使用同一页面和 API，并区分 `not_selected`、`waiting`、
   `running`、`degraded`、`failed`、`completed`，不能把 quick 显示成残缺 deep。
8. 每个 Harness 的原生事件保存在 Case 私有 Artifact；Smart Search 只把白名单化的
   Agent、Tool、Provider、Usage、Artifact、Evidence、Claim、引用验证和综合生命周期
   追加到公开 Trace，不保存隐藏思维链、密钥或私有 Prompt。
9. Benchmark Viewer 按 `Case × Harness × quick|standard|deep` 建立索引，每个分数、
   错误和运行指标都能回到 CaseAttempt、Workspace、Trace 与 Artifact。
10. 先跑四 Harness 的协议 Micro-suite，再跑同一小样本的 4×3 Pilot。原生
    Benchmark 分数与 Harness 完成率、DelegateResult 有效率、Tool Call 成功率、
    引用回溯率和 Trace 完整率分开报告，不合成万能总分。

## 未完成或未验证

- 尚无统一 HarnessDriver、Claude/Pi/OpenCode 项目 Agent adapter 或原生事件
  normalizer。
- 当前 `.codex/agents` 仍是 Codex 专属配置，并且可见配置不是 Linux Benchmark
  使用的本地 Qwen overlay。
- 旧 public `deep` / `research` 路径仍可能绕过新的 Workspace/Trace；当前
  Visualizer 测试主要使用 deep fixture。
- Claude Code 与 SGLang/Qwen3.8 的真实 Tool 协议兼容性尚未在目标 Linux 机器验证。
- A100 显存 SKU、SGLang commit、CUDA/Driver、上下文上限、并发和 KV cache 参数
  尚未在目标机器冻结。
- 尚未选择最终 Pilot Case IDs、Judge 和执行范围，也没有任何 Benchmark 分数。

## 未生效方案

- 仅把 Skill 复制到 Claude Code、Pi 或 OpenCode 目录不能证明 Harness 可移植；
  Skill 安装器不负责启动项目 Agent、约束模型、解析原生事件或导入 DelegateResult。
- 不能把 Codex 的 TOML/hooks 直接复制给其他 Harness；角色语义以 canonical Agent
  YAML 为权威，各 Driver 生成自己的运行时投影。
- 不能假设通过 OpenAI-compatible 端点的 Harness 也会让 Claude Code 通过；Claude
  Code 的 Anthropic Messages 路径必须独立实测。
- 不要在协议 Pilot 前直接把完整 Benchmark 扩大为 4×3 全量运行。

## Linux 上的后续步骤

1. 先确认 Mac 上本分支的目标改动已提交并推送，再在 Linux 拉取同一分支；当前
   Mac checkout 为 `preview/multi-source-agentic-research`，观察到的 HEAD 是
   `020b4dc904e2b19643aeece0c00b25d011eb1fc5`，但当前工作树包含大量未提交和
   未跟踪改动，不能把该 HEAD 当作本交接内容的远端版本。
2. 在 Linux 读取 `AGENTS.md`、`.trellis/workflow.md` 和本文件，验证
   `08-24-benchmark-evaluation-integration` 仍为 `planning`。
3. 用户确认实施后再运行：

   ```bash
   python3 .trellis/scripts/task.py start 08-24-benchmark-evaluation-integration
   ```

4. 严格按 `implement.md` Phase 0→7 推进：先冻结环境，再验证 SGLang 协议，随后
   实现 Harness-neutral runtime/Trace、四种 Driver、三模式 Viewer、Benchmark
   adapters，最后才启动用户批准的小规模 live Pilot。
5. 每完成一个实现阶段，使用 Trellis implement/check 流程验证；不要修改全局 Infra，
   Benchmark 的 Harness Home、模型配置和输出均使用 run-local 隔离目录。

## Suggested Agent Skills

- `codex-sdk`：实现 Codex Driver、isolated CODEX_HOME 和事件采集。
- `claude-code-sdk`：实现 Claude Code Driver 与 Anthropic 协议兼容门槛。
- `smart-search-cli`：验证 Smart Search 命令、Provider 和 ResearchWorkspace 行为。
- `skill-creator`：把 canonical 项目 Agent 角色投影到各 Harness，避免复制角色语义。
- `hugging-face:hf-cli`：在用户批准实施后管理 Linux 上的 Qwen 模型版本与落盘。

## 工作树边界

创建本文件时只新增/更新了规划和交接资料。当前仓库原有大量代码、文档、Trellis
初始化和 CodeStable 迁移改动；后续 Agent 必须先检查 live `git status`，不得清理、
覆盖或归因不明的现有改动。
