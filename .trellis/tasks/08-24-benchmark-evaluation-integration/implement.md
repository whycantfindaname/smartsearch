# Benchmark Evaluation Implementation Plan

本任务当前只完成计划。未获用户确认前不得启动模型、下载数据集、调用真实 Provider
或 Judge，也不得产生 Benchmark 分数。

## Phase 0 — Freeze Experiment Inputs

- [ ] 记录 Smart Search、四种 Harness、Qwen3.8、SGLang 与 Benchmark 的固定版本。
- [ ] 记录 Linux、8×A100 的显存 SKU、Driver、CUDA 与容器环境。
- [ ] 明确可用 Provider、现有 Entitlement、禁止自动充值和失败策略。
- [ ] 固定 canonical Agent YAML、Root Prompt Wrapper 和相同 Qwen reasoning 配置。
- [x] Benchmark 与 Judge 已由用户确认（2026-08-31）：首轮 Pilot 为 BrowseComp
      小样本（约 20 题）+ LiveResearchBench 子集（约 5 题）；Judge 使用本地
      Qwen，结果标记 benchmark-derived internal，不声称官方排行榜名次。
- [ ] Case IDs 与执行上限（每题超时、并发、Provider 用量上限）在 Pilot 启动前
      另行冻结。

### Phase 0 冻结进展（2026-08-31，Mac 本机核查，未启动实施）

- Smart Search 锚点：分支 `preview/multi-source-agentic-research`，本机 HEAD
  `eadcf57`（含 Stage G 证据包 `1fe0068` 的后代）；Linux 实施时以实际 checkout
  的 commit 为准重新冻结。
- Canonical Agent YAML 已核实：`skills/smart-search-cli/agents/{search_scout,
  source_curator,evidence_miner}.yaml` 为角色权威（`src/smart_search/assets/`
  下同名文件是打包镜像，`.codex/agents/*.toml` 是 Codex 投影）。注意
  `deployment_defaults.model` 当前为托管模型 `gpt-5.6-luna`：Benchmark 运行时
  HarnessDriver 必须用固定 Qwen 端点覆盖该默认值，模型身份漂移按 Phase 2 要求
  显式失败。
- Root Prompt Wrapper 在产品代码中尚不存在，属 Phase 2 待建物；Phase 0 只冻结
  其内容边界（Benchmark 问题、模式、Workspace 目录、答案格式）。
- Provider configured 快照（脱敏，可达性与 Entitlement 未实测，不做真实调用）：
  AnySearch（含 fallback key）、Tavily、Exa、Firecrawl、Jina、SciVerse、
  Context7、本地 OpenAI-compatible 网关（`127.0.0.1:8000/v1`）、SiliconFlow
  intent router（Qwen3-Embedding-8B + Qwen2.5-7B-Instruct）。配置源：
  `~/.config/smart-search/config.json`。Linux 侧需复制同等 Provider 配置并保留
  失败可见策略。
- Harness 版本参考（Mac 本机，非冻结值）：codex-cli 0.150.1、Claude Code
  2.1.251；pi 与 opencode 本机未安装，Linux 侧安装后冻结版本。

## Phase 1 — SGLang Protocol Preflight

- [ ] 部署两个 TP=4 的 Qwen3.8-27B SGLang worker 和 HTTP Model Gateway。
- [ ] 验证 OpenAI-compatible streaming/non-streaming、Tool Call 与 Tool Result 循环。
- [ ] 验证 Claude Code 所需 Anthropic Messages、多工具流和长会话；若失败，只允许
      加入同一 Qwen 后端上的协议兼容层，不得更换模型。
- [ ] 用服务端日志证明 Root 与所有项目 Agent 均命中固定 Qwen revision，且无托管模型回退。
- [ ] 把通过的端点、SGLang commit、parser、上下文上限和已知限制写入 Manifest 模板。

## Phase 2 — Harness-Neutral Runtime and Trace

- [ ] 在仓库级 `evaluation/` 实现 HarnessRunSpec、HarnessRunResult、Manifest、
      CaseAttempt 与 CaseScore Schema。
- [ ] 从 canonical Agent YAML 生成 Codex、Claude Code、Pi、OpenCode 的原生角色投影；
      Harness 配置不得成为第二份角色语义权威。
- [ ] 实现每题、每 Harness、每模式独立进程与独立 Home/Session/Artifact Root。
- [ ] 为四种 Harness 实现统一的启动、终态解析、取消、超时、非零退出和
      DelegateResult 校验边界。
- [ ] 保存 `native-events.jsonl`，并把白名单化的生命周期、Tool、Provider、Usage、
      Artifact 元数据归一化到现有 append-only Trace；不保存隐藏思维链。
- [ ] 扩展 Trace 事件，覆盖 Root plan/replan、Delegate request/start/end/failure、
      Tool start/end、Provider attempt、checkpoint、Claim derivation、Root decision、
      Citation verification 与 final synthesis。
- [ ] 保证无效 DelegateResult、事件缺失、孤儿事件和模型身份漂移都形成显式失败。

## Phase 3 — Harness Adapters and Compatibility Micro-suite

- [ ] 先完成 Codex Driver，验证 Skill、三个项目 Agent、自动回收结果和 Workspace。
- [ ] 完成 OpenCode Driver，验证 custom Provider、Agent 投影和 session event 归一化。
- [ ] 完成 Pi Driver/extension，验证 Skill、项目 Agent、session event 和结构化终态。
- [ ] 完成 Claude Code 实验 Driver；只有 Anthropic 协议门槛通过后才进入 live Pilot。
- [ ] 对每种 Harness 运行同一组离线协议 Fixture：单工具、多工具、Subagent、取消、
      超时、Malformed Result、最小 Research Case。
- [ ] 记录每种 Harness 的 capability result；某个 Harness 失败不阻塞其他 Harness，
      但不得伪装为已通过或切换到其他模型。

## Phase 4 — Mode-Independent Workspace and Visualization

- [ ] quick、standard、deep 统一通过 Root-led `research-run --workspace` 物化产物，
      不再让旧入口绕过 ResearchWorkspace/Trace。
- [ ] 将 Workspace 与 Visualizer 测试参数化覆盖三种模式，而不是只使用 deep Fixture。
- [ ] Visualizer 区分 `not_selected`、`waiting`、`running`、`degraded`、`failed`、
      `completed`，避免把正常 quick 流程显示为残缺 deep。
- [ ] 增加 Root/项目 Agent/Tool/Provider 时间线以及 Evidence、Claim、引用验证和最终报告视图。
- [ ] 为最终报告生成论文式 References，将来源 URL 绑定到 CandidateCard、Artifact、
      snapshot 和 EvidenceItem，并在 Viewer 中提供反向导航。
- [ ] 增加 Benchmark Run Index：按 Case × Harness × Mode 展示原生分数、状态、错误、
      用量，并可打开对应 ResearchWorkspace 与 Trace。
- [ ] 验证任一分数、失败和可视化节点都能反向定位到 CaseAttempt、事件和 Artifact。

## Phase 5 — Benchmark Adapters and Offline Verification

- [ ] 实现 BrowseComp 输入、输出格式与固定 Judge Adapter。
- [ ] 实现 LiveResearchBench 报告文件与维度评分 Adapter。
- [ ] 可选实现 DevDex 公共样本 URL 提取与 deterministic scorer Adapter。
- [ ] 暂不实现 BrowseComp-Plus，除非用户选择固定语料 Leaderboard 路径。
- [ ] 使用小型本地 Fixture 验证 Case 隔离、Resume、失败分母、Summary 和三模式 Viewer。
- [ ] 验证 Scorer 输入严格来自保存的最终答案/ResearchWorkspace。
- [ ] 验证 Manifest/Public Trace 不含 Key、隐藏思维链或未经授权正文，仓库不打包
      数据集、模型或 Run 输出。
- [ ] 验证报告只展示各 Benchmark 原生指标，不生成跨 Benchmark 总分。

## Phase 6 — User-Approved Cross-Harness Live Pilot

- [ ] 先对预先声明的小样本运行 Codex、Claude Code、Pi、OpenCode ×
      quick、standard、deep 的 4×3 矩阵；Case 内顺序打乱并尽量相近时间执行。
- [ ] 每个 Cell 保存独立 Workspace、原生事件、归一化 Trace、最终答案和 Scorer 结果。
- [ ] 报告 Benchmark 原生分数，并列报告完成率、有效 DelegateResult 比例、
      Tool Call 成功率、引用回溯率、Trace 完整率、时延、调用量、GPU 与 Provider 用量。
- [ ] 对 Harness 协议失败、产品流程失败、Provider 失败、模型失败和 Scorer 失败分别统计。
- [ ] 明确标记结果属于 exact leaderboard comparable 还是 benchmark-derived internal。
- [ ] 先向用户提交 Pilot 与逐题 Viewer，不自动扩大到全量。

## Phase 7 — Full Run or Leaderboard Path

只有用户看过 Pilot 后才创建后续执行任务：

- [ ] 选择是否运行完整公共 Split。
- [ ] 选择是否承担官方 Judge/Provider 成本。
- [ ] 选择是否为严格 Leaderboard 可比性改用官方固定 Driver/Judge/Corpus。
- [ ] 若选择 BrowseComp-Plus，单独规划固定 Corpus、Retriever 与 Qwen3-32B Judge。

## Planning Validation

- [x] task.py validate 通过。
- [x] 所有推荐 Benchmark 有官方来源、评分与复现成本说明。
- [x] SGLang、四种 Harness、Qwen、8×A100 和 live search 决策在 PRD/Design/Research 一致。
- [x] quick、standard、deep 的独立 Workspace、Trace 与逐题可视化要求已写入计划。
- [x] 当前实现的 Harness-neutral 核心与缺失的原生 Driver/事件适配边界已有代码审计记录。
- [x] Trellis task status 保持 planning。
- [x] 没有数据集、模型服务、Provider/Judge 调用或新分数。

## Rollback

用户批准前的变更仅限本 Trellis Task 文档。删除该任务目录不会改变 Smart Search
运行时、Skill、Provider 配置或已完成的 CodeStable 迁移。
