# Benchmark Evaluation Design

## Claims Under Test

实验只回答四个问题：

1. quick、standard、deep 是否在相同模型与 live search 条件下呈现可解释的质量差异？
2. 新增的多源发现、关键文档深挖与证据综合能否稳定生成可回溯的研究产物？
3. 这些结果与公开 Benchmark 或 Leaderboard 的协议有多大可比性？
4. 使用同一个 Qwen、同一问题和同一 Smart Search 模式时，Codex、Claude Code、
   Pi、OpenCode 能否稳定完成等价的 Root/项目 Agent 生命周期？

## System Boundary

    Benchmark Case
        -> isolated Harness Driver
        -> Codex | Claude Code | Pi | OpenCode
        -> Root Agent
        -> Smart Search quick | standard | deep
        -> project Search Scout / Source Curator / Evidence Miner
        -> live Smart Search Providers
        -> one ResearchWorkspace
        -> normalized public Agent Trace
        -> official or pinned scorer adapter
        -> BenchmarkCaseScore
        -> per-benchmark native summary

Benchmark 层负责选题、调度、记录和评分，不负责重新实现搜索、Trace、证据或引用。

## Compute and Model Serving

目标机器为 Linux、8×A100。第一版使用两个相同的 SGLang 副本：

    GPU 0-3 -> Qwen3.8-27B worker A, TP=4
    GPU 4-7 -> Qwen3.8-27B worker B, TP=4
                       -> SGLang HTTP Model Gateway
                       -> OpenAI-compatible and verified Anthropic-compatible endpoints
                       -> Codex | Claude Code | Pi | OpenCode

两个副本提高 Root/Subagent 并发能力；不把 27B 模型无依据地切到 8 卡。实际 A100
显存规格、并发、KV cache、上下文上限和镜像版本在 Preflight 实测后写入 Manifest。

Codex、OpenCode 和 Pi 优先使用 SGLang 的 OpenAI-compatible Responses 或 Chat
Completions 路径。Claude Code 使用 Anthropic Messages 语义，必须通过同一
SGLang/Qwen 后端的已验证兼容路径。模型服务、Root 和每个项目 Agent 均固定为同一
Qwen revision；任何本地模型错误都直接使 Attempt 失败，禁止回退到 OpenAI、
Anthropic 或其他托管模型。

## Harness Driver Boundary

四种 Harness 共用一个 Driver 协议：

    HarnessRunSpec
      -> native Harness launch
      -> canonical project Agent role
      -> native events and terminal output
      -> HarnessRunResult
      -> DelegateResult plus normalized Trace events

HarnessRunSpec 至少包含 harness_id、benchmark_case_id、mode、run_id、模型端点、
模型 ID、角色定义、问题、Workspace/Artifact 路径、超时与输出格式。

HarnessRunResult 至少包含状态、最终答案、DelegateResult、原生事件路径、stderr、
模型身份、用量、失败分类和 ResearchWorkspace 路径。

每次 Run 使用独立 Harness Home/配置，不读取或修改用户日常配置：

- Codex：run-local CODEX_HOME、Responses Provider 和 ephemeral JSON run；
- Claude Code：run-local settings/home、stream JSON 和 Anthropic Messages 端点；
- Pi：run-local settings/session、SDK/extension events 和项目 Agent；
- OpenCode：run-local config/session、custom Provider 和 session events。

canonical Agent YAML 是角色语义权威。各 Driver 只生成 Harness-native 投影，不复制
新的角色语义。Prompt Wrapper 只包含：

- Benchmark 问题；
- 指定的 quick、standard 或 deep；
- ResearchWorkspace 输出目录；
- Benchmark 要求的最终答案格式。

它不固定 Subagent 数量或 Provider 调用预算。Root Agent 根据任务复杂度和中间结果
自主规划、派发与重规划，Harness 只保留可观测边界。

### Claude Code Compatibility Gate

Claude Code 不是默认视为可用。它的 Anthropic Messages、多工具流、deferred tool
reference 和长会话必须在固定 SGLang/Qwen 版本上实测。若直接端点不兼容，可使用
仅做协议转换和流清理的 Compatibility Gateway，但底层模型仍必须是同一 Qwen
checkpoint，并在 Manifest 中记录。兼容性失败作为 Harness 结果，不允许换模型。

## Compatibility Gate

任何正式 Pilot 前必须依次证明：

1. SGLang readiness 与 model list 正常。
2. Responses 的 streaming 与 non-streaming 请求正常。
3. Qwen 可以发出 Function Call，并在下一轮接收 Tool Result。
4. 每种 Harness 能通过 SGLang 完成最小本地工具调用。
5. 每种 Harness 都能加载 Smart Search Skill。
6. 每种 Harness 都能启动 Search Scout、Source Curator、Evidence Miner 并返回
   一个有效 DelegateResult。
7. 每种 Harness 的取消、超时、非零退出和无效结构化输出能映射为显式失败。
8. 一个最小 Research Case 能产生完整 ResearchWorkspace、Trace、Artifact、
   最终答案与引用回溯。
9. Harness 与 SGLang 日志证明 Root 和全部 Subagent 只使用固定的本地 Qwen。

任一项失败都先修兼容性，不允许换服务端或静默简化研究流程。

## Live Provider Contract

Generation 在本地完成，搜索故意保持 live。运行前记录经过脱敏的 Provider 能力状态：
configured、reachable、entitled。运行中保存所有 Provider 尝试、错误、超时和用量。

不购买额度、不自动充值、不换未批准 Key。Provider 失败作为 Case 结果的一部分。
因此实验可以做到本地模型零 API 推理费，但不能宣称真实搜索绝对零外部成本。

## Experiment Matrix

先做每种 Harness 的 Protocol Micro-suite，再对同一组小样本使用相同模型、角色配置、
Provider 能力、超时、并发和评分器运行完整矩阵：

| Harness | quick | standard | deep |
| --- | --- | --- | --- |
| Codex | isolated | isolated | isolated |
| Claude Code | isolated | isolated | isolated |
| Pi | isolated | isolated | isolated |
| OpenCode | isolated | isolated | isolated |

每个 Cell 生成独立 Session、Artifact Root 和 ResearchWorkspace，并使用 Benchmark
原生评分。每个 Case 的 Harness/模式顺序随机打乱并记录。首次 Attempt 是主结果；
诊断重试另存 Attempt，不得覆盖第一次失败。完整运行前先执行预先声明的小样本 Pilot。

## Records

### ExperimentManifest

- run_id、时间和区域
- Smart Search commit 或 dirty-tree identity
- Harness 及其版本、Qwen、SGLang、Compatibility Gateway、CUDA、Driver 与 GPU inventory
- 角色配置与 Prompt Wrapper identity
- Benchmark commit、split、Case IDs 与模式顺序
- 脱敏 Provider capability snapshot
- Scorer/Judge identity、失败规则和超时

### CaseAttempt

- benchmark_case_id、harness_id、mode、attempt_id
- input、native Harness event stream、normalized Trace、stderr、final answer
- ResearchWorkspace path
- start/end time、latency、tool/provider/model usage
- status 与显式 failure classification

### BenchmarkCaseScore

- benchmark 与原生 metric
- scorer input/output
- item-level judgment 或 deterministic match evidence
- leaderboard_comparability: exact | benchmark-derived-internal
- 对应 CaseAttempt 与 ResearchWorkspace

## Storage Layout

输出默认位于源码仓库之外：

    <bench-root>/<run-id>/
      manifest.json
      cases/<case-id>/<quick|standard|deep>/
        <harness-id>/
          input.json
          native-events.jsonl
          stderr.log
          final-answer.md
          case-result.json
          research-workspace/
          scorer/input.json
          scorer/output.json
      index.json
      summaries/<benchmark>.json

仓库只保存适配器、Schema、Fixture 和说明，不提交模型、数据集、真实 Key 或大规模结果。

## Trace and Visualization

原生 Harness Trace 与公开 Research Trace 分层保存：

- native-events.jsonl 保留 Harness 原始事件，用于复现和调试，属于私有 Case Artifact；
- Smart Search 只导入经过类型校验和字段白名单过滤的生命周期、Tool、Provider、
  Usage 和 Artifact 元数据；
- 归一化事件追加到现有 Trace，不建立第二套 Evidence 或 workflow authority；
- public_trace.jsonl 不包含 hidden reasoning、system/developer prompt、Key 或未经授权
  的网页正文。

Trace 至少覆盖 Harness session、Root plan/replan、Delegate request/start/end/failure、
Tool start/end、Provider attempt、checkpoint、Claim derivation、Root decision、
Citation verification 和 final synthesis。

Benchmark Viewer 先展示 Case × Harness × Mode 索引，再打开现有 Research Workspace
页面。Workspace 页面必须：

- 显示当前 Harness 和 quick/standard/deep；
- 对三种模式使用同一页面与 API；
- 区分未选择阶段、等待、失败、降级和完成，不能把正常 quick 流程显示为残缺 deep；
- 提供 Root/Agent/Tool 时间线、失败、用量、Evidence、Claim 和最终报告；
- 让每个分数和错误反向链接到 CaseAttempt 与 Trace。

## Benchmark Adapters

### LiveResearchBench

输入公开研究问题，输出 Markdown 报告。保留 presentation、coverage、consistency、
citation association 和 depth 等官方维度。若不用官方 GPT-5 + Gemini Judge 组合，
结果标记为 benchmark-derived internal。

### BrowseComp

输入公开问题，输出 Explanation、Exact Answer、Confidence。保存逐题 grader 判断和
Accuracy。它最适合三种模式直接比较；使用本地 Qwen Judge 时不声称官方排行榜名次。

### Firecrawl DevDex

从输出引用提取前十个 URL，复用 canonical matching，保存 Recall@10、MRR@10 和各
Track 结果。由于生成 Driver 改为 Codex/Qwen 且搜索为多源，只作为内部诊断。

### BrowseComp-Plus

仅在需要固定语料控制实验时实现。必须使用官方 corpus、retriever contract 与
Qwen3-32B Judge 才可能严格对齐其 Leaderboard；它不属于首轮 live Pilot。

## Failure and Resume

- Case 粒度隔离，单题失败不终止整个 Run。
- timeout、Provider unavailable、credit exhausted、malformed DelegateResult、
  Harness protocol/tool error、model error、scorer error 分开记录。
- Resume 只补未完成 Case/Mode，不覆写已完成的首次 Attempt。
- 聚合分母遵守 Benchmark 官方规则；额外 Failure Summary 单独展示。
- 任何 Judge 失败都不伪装成零分或成功。

## Package Boundary

Benchmark Runner、Harness Driver 和 Run Index 放在仓库级 evaluation 目录。
Harness-neutral Trace ingestion、ResearchWorkspace 和 Visualizer 合同属于 Smart
Search 产品代码。删除 evaluation 目录和仓库外 Run 输出后，核心研究运行时、
Skill 与 Provider 配置保持可独立使用。
