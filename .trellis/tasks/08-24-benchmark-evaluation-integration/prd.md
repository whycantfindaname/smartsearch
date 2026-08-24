# Smart Search Benchmark Evaluation Plan

## Goal

形成一份可直接进入实现阶段的实验计划：在 Linux 8×A100 上用
SGLang 托管同一个 Qwen/Qwen3.8-27B 模型，由 Codex CLI、Claude Code、
Pi 和 OpenCode 分别驱动同一套 Root Agent 与项目 Subagent，调用真实
Smart Search Provider，评测 quick、standard、deep 三种产品模式，并检验
研究流程对 Harness 的稳定性。

本任务只完成方案、数据协议、Benchmark 选择建议和复现边界；不启动模型，
不下载数据集，不调用 Provider 或 Judge，也不产生分数。

## Fixed Decisions

1. Codex CLI 是首个实现和完整 Benchmark 的基准 Harness；Claude Code、Pi、
   OpenCode 进入跨 Harness 稳定性 Pilot。
2. 模型服务器固定为 SGLang，不使用 vLLM。
3. Root Agent、Search Scout、Source Curator、Evidence Miner 使用同一个固定版本
   Qwen/Qwen3.8-27B 和相同 reasoning 配置。
4. 计算环境为 Linux、8×NVIDIA A100；首选两个 TP=4 的相同 SGLang 副本。
5. 搜索使用真实、当前可用且有权限的 Smart Search Provider；不购买额度，
   不自动充值，不用隐藏回退掩盖失败。
6. 自变量只有 Smart Search 的 quick、standard、deep。模型、问题、Harness、
   Provider 配置和评分器在同一比较内保持不变。
7. 每个问题、Harness 与模式使用独立会话和独立 ResearchWorkspace。
8. 保留各 Benchmark 的原生指标，不合成跨 Benchmark 的万能总分。
9. quick、standard、deep 在评测中统一经过 Root-led research-run 路径并物化
   ResearchWorkspace；可视化不是 deep 专属能力。
10. 保存各 Harness 原生事件，同时只把经过安全归一化的生命周期与工具元数据
    写入 Smart Search 现有 append-only Trace；不保存隐藏思维链。

## Benchmark Roles

- Primary: LiveResearchBench。评估引用支撑的长篇研究报告与端到端研究能力。
- Direct mode comparison: BrowseComp。用统一的困难短答案问题直接比较三种强度。
- Diagnostic: Firecrawl DevDex 公共样本。用确定性 URL 指标诊断代码、仓库、
  Issue/PR 与文档发现能力。
- Deferred controlled benchmark: BrowseComp-Plus。只有需要固定语料和较严格的
  官方排行榜可比性时才使用；它不代表真实 live search。

上述角色是实施建议，不等于声称本地结果可以直接进入公开排行榜。只有任务版本、
生成 Driver、工具策略、预算、失败规则和官方 Scorer/Judge 均与排行榜协议一致时，
才能称为排行榜可比结果。

## Requirements

1. 为每个 Benchmark 提供独立适配器，但复用现有 ResearchWorkspace、Trace、
   Artifact Registry、EvidenceItem、ClaimRecord 与引用回溯，不建立第二套证据权威。
2. 每个 Case 在 quick、standard、deep 下各执行一次；三种模式的执行顺序按 Case
   打乱，并尽量在相近时间完成，降低 live Web 漂移带来的固定偏差。
3. 保存固定版本与环境：Smart Search、Codex CLI、Qwen、SGLang、CUDA、Driver、
   Benchmark、角色配置和评分器。
4. 保存每题输入、对应 Harness 原生事件、stderr、最终答案、ResearchWorkspace、
   Scorer 输入输出和结构化 Case 结果。
5. Provider 超时、无额度、不可达、输出不合规和模型失败都作为可见结果保留，
   不从分母中静默删除。
6. 报告每个 Benchmark 的原生分数，并并列报告时延、Provider/工具调用数、
   本地模型 Token、GPU 资源和失败率；这些运行指标不混入原生分数。
7. 先运行预先声明的小规模 Pilot。完整数据集、官方付费 Judge 或排行榜提交
   必须另行获得用户批准。
8. 定义统一 Harness Driver：把 canonical Agent YAML、DelegateRequest 和任务输入
   映射到原生 Harness，并把终态输出转换成一个 DelegateResult。
9. 对 Codex、Claude Code、Pi、OpenCode 分别验证 Skill 加载、项目 Agent、
   多轮 Tool Call、取消/超时、结构化结果和同一 Qwen 模型身份。
10. 对每个 Case 保存原生 Harness Trace；公共可视化只读取归一化后的安全 Trace，
    并能展示 Root 重规划、Agent 生命周期、工具状态、失败和 Workspace checkpoint。
11. 提供 Benchmark Run 索引，使每个 Case × Harness × Mode 的分数和错误都能打开
    对应 ResearchWorkspace。

## Acceptance Criteria

- [ ] SGLang + 四种 Harness + Qwen 的部署拓扑、固定版本方式与兼容性门槛明确。
- [ ] quick、standard、deep 的逐题隔离、运行顺序与失败规则明确。
- [ ] Codex、Claude Code、Pi、OpenCode 共用的 Harness Driver、Agent 角色投影、
      事件归一化和兼容性门槛明确。
- [ ] 推荐 Benchmark 的官方来源、原生评分、Leaderboard 性质、复现成本、
      访问与 License 风险均有记录。
- [ ] 每个 Case 的输出可以追溯到独立 ResearchWorkspace 和逐题评分。
- [ ] quick、standard、deep 均有 Workspace/Trace/Visualizer 参数化测试计划。
- [ ] 每个 Harness 的原生 Trace 被保存，且安全归一化事件可在可视化器中按
      Root、Agent、Tool、Provider 和阶段查看。
- [ ] 明确区分内部模式比较、Benchmark 原生分数和严格排行榜可比分数。
- [ ] 实施顺序从离线 Fixture、最小兼容性验证到小规模 live Pilot，且需要用户
      决定后才进入完整运行。
- [ ] 本规划阶段没有下载模型或数据集，没有调用 Provider/Judge，没有产生分数。

## Out of Scope

- 本任务内运行 Benchmark 或声称排行榜名次。
- 未经 Pilot 直接在四种 Harness 上运行完整 Benchmark 数据集。
- 为追求 Benchmark 分数修改 Smart Search 产品架构。
- 购买 Provider/Judge 额度。
- 把 max 重新加入产品模式。
- 构造跨 Benchmark 的项目自定义总分。

## User Review Gate

后续最小 Pilot 建议同时覆盖：

1. 预先声明的 BrowseComp 小样本，用于比较 quick、standard、deep 的正确率与开销。
2. LiveResearchBench 公共样本中的小子集，用于检查长报告、引用和研究深度。
3. DevDex 公共样本仅作为可选发现能力诊断。
4. 同一小样本在 Codex、Claude Code、Pi、OpenCode × quick、standard、deep
   的矩阵中运行，用于判断 Harness 稳定性；完整 Benchmark 是否扩展到全部
   Harness 由 Pilot 结果决定。

在用户确认 Pilot Case、Provider 可用范围和 Judge 选择前，任务保持 planning，
不得启动 task.py start 或正式评测。
