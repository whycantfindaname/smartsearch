# Stage G 架构复盘

> 复盘对象：隔离 Preview 环境中的 `deep` 研究运行 `run-stage-g-seq-20260823T191412Z`
> 证据时点：2026-08-24
> 结论边界：本复盘只判断哪些项目架构应保留、修改或暂不实施。它不证明一套完整公共架构，也不选择、运行或评分任何 Benchmark。
> 文档索引：[Stage G 研究索引与 References](stage-g-research-index.md)

## 结论

保留 Root 作为唯一语义规划与综合控制面，以及 Scout 发现、Curator 提案、Miner 文档内取证、Smart Search 确定性校验与存储的分工。当前运行已经证明这些角色可以通过稳定任务 ID、候选 ID、受控 artifact、typed locator 和结构化结果完成一条可审计的局部闭环；公开材料也分别支持“主 Agent 统筹并复核子任务”“清晰任务边界”“文档内检索—展开—导航—读取”等设计。不过，公开证据只覆盖各局部，架构 Claim 在本次 dossier 中仍为 `weakly_supported`，不能声称 Root/Scout/Curator/Miner、动态重规划、Claim 反向追踪和反馈循环组成的完整公共架构已经得到证明。

需要修改的重点有三项：把 Root 发给子角色的 brief 扩展为包含已知事实、已读集合、任务边界和期望引用的完整上下文；把每次补搜、重试、降级、选文和停止的公开决策摘要写入 dossier/Trace；把角色发现的覆盖缺口、重复劳动和系统改进建议纳入正式反馈字段。暂不增加独立 Review Agent、系统升级 Agent、自动恢复工作流或统一证据分数。

## 本次运行事实

- 运行汇总为 113 个 `DiscoveryCandidate` 与 113 个 `CandidateCard`。Root 将其交给两个互不重叠的 Curator shard：academic shard 输入 50 个候选，multisource shard 输入 63 个候选；两份 `KeySourceProposal` 分别返回保留、延后、淘汰及理由。它们是选源提案，不是已核验事实，也不替 Root 作最终选择。
- 结构化委派共 7 组：2 个 Search Scout、2 个 Source Curator、3 个 Evidence Miner，均返回成功结果。Scout 负责扩展发现；Curator 只处理 Root 指定的候选 ID；Miner 只读取登记过的 artifact，并按 `claim_spec_id` 返回 locator-backed evidence、缺口和建议。
- `deep` 对 Firecrawl、Tavily、Exa、Jina 发起了四次独立 Provider Research Agent 尝试：Exa 成功，7 次搜索、6.163 agent compute units、总成本 **$0.6493**；Tavily 返回 **HTTP 432**，原因是套餐用量上限；Firecrawl 与 Jina 均超时。单项失败没有终止研究，后续 Scout、索引搜索、fetch、Curator 和 Miner 仍继续执行。这证明的是失败隔离和运行记录，不是四家 Provider 具有同等质量或稳定性。
- 动态调整在执行层有真实记录：Firecrawl Developer Index 首次因响应 Schema 对可选字段要求过严而失败，修复适配器后重试成功；文档 phrase grep 未命中微信公众号正文后，Root 改用已知字符范围 `read` 并成功取证。验收还发现词法模式曾把“未请求 MinerU”和“未启用 Embedding”错误记为失败；修复后复跑只记录受控 loader、Search Toolkit ingestion 与 SQLite FTS5 的真实成功尝试，不再产生虚假失败。当前 `root_next_decision` 为空，因此这些动作证明了重试与降级路径，尚不足以证明每次语义重规划都被 Root 明确记录。
- 最终 dossier 含 16 个 `EvidenceItem`、2 个 `KeySourceProposal` 和 2 个 `ClaimRecord`。引用验证 `ok=true`，16/16 条引用均可反向回到 ClaimRecord、ClaimSpec、EvidenceItem、任务、执行尝试、artifact、snapshot 与原始文件引用。

## 信息交换：保留角色，收紧协议

保留下面的单向任务创建与双向结果返回：

```text
Root
  ├─ SearchTask / DelegateRequest → Scout → candidates + gaps + suggestions
  ├─ candidate shard             → Curator → keep/defer/reject proposal + reasons
  └─ EvidenceMiningTask          → Miner → EvidenceItem[] + not-found/parsing gaps

Smart Search：校验身份与 Schema，归一化并只追加保存 artifact、attempt、evidence 和 Trace
Root：跨分片复核、选择关键文档、更新 Claim、补充任务或停止
```

这一方向与 Anthropic 的 orchestrator-worker 实践一致：lead agent 负责分解并协调并行的专门子任务，且任务必须说明目标、输出格式、工具/来源和边界；其公开案例也显示，过短 brief 会造成误解和重复搜索。[A1] SearchSwarm 进一步指出，子 Agent 在全新上下文中运行时，brief 是上下文输入的唯一通道，而主 Agent 才拥有跨子任务全局视图；子结果若不附直接来源 URL，主 Agent 无法可靠复核。[A3]

因此修改 `DelegateRequest` 的语义要求，而不增加新角色：

- brief 除问题与范围外，还应携带与本任务有关的已确认事实、未决 Claim、已读 artifact/locator、重复工作禁区和停止条件；
- Scout 与 Curator 的重要判断必须绑定候选 ID 和直接 URL，Miner 的重要判断必须绑定 artifact、snapshot 与 typed locator；
- 所有角色继续只返回 `gaps`、`suggestions`、`uncertainties` 等建议，只有 Root 能把建议转成新任务；
- Curator 输入卡片应补足用于选文的摘要、发布日期/版本、来源类型、原始记录、与其他来源的关系及可获得性。两份 Curator 结果都指出，现有卡片主要只有标题、URL、类型和 raw ref，不足以独立判断权威性、版本与复现成本。

## 动态重规划、关键文档与反馈循环

保留“结果驱动、由 Root 决策”的动态重规划，不恢复固定任务数、Agent 数、候选阈值或 Provider 上限。四个 Provider 的不同结果、Developer Index 的失败后重试、文档 grep 转 read，以及按文档类型选择 MinerU、Embedding 或纯词法索引，都说明运行时路径不能在离线计划中写死。

本次最初把多个长时任务放进一次 `execute`，外部 Harness 在约三分钟后终止了进程；由于 dossier 由调用方持有，尚未返回的状态不能自动恢复。Root 随后改为逐个添加并执行任务、每步保存 dossier，完整走完同一研究目标。Preview 不因此增加自动恢复引擎，但 Skill 应把“长运行按步骤保存 dossier”写成推荐调用方式，并明确区分 Trace 中已发生的事件与调用方已经持久化的最新 dossier。

需要新增的是可审计的公开决策记录，而不是模型隐藏思维过程。每个关键转向都应记录：观察到的结果或缺口、选中的下一动作、被放弃的替代动作、成本/时间约束和停止理由。本次 dossier 保存了 attempts、gaps 与最终 stop reason，但 `root_next_decision` 为空；后续验收应能直接看出“为何补搜、为何重试、为何选择这份文档、为何停止”。

关键文档仍由 Root 从候选与 Curator 提案中选择。本次架构挖掘实际选取 Anthropic 多 Agent 工程文章、Mistral Agentic Search 文档、SearchSwarm 论文和用户提供的 MultiAgent 公开案例，均形成了正式 EvidenceItem。[A1–A4] 公开案例提出把各角色发现的改进点纳入正式通信协议，这一建议值得吸收到现有 `gaps/suggestions/uncertainties`，但不足以据此新增常驻架构迭代 Agent、旁路 Review Agent 或 SystemUpdater。

反馈循环建议固定为：角色报告局部缺口或改进观察 → Root 跨分片去重并判断是否影响当前 Claim → 必要时创建补搜、重选文档或再挖掘任务 → Smart Search 记录决定及结果。系统级改进只形成待人工审阅的建议，不在研究运行中自动修改架构或代码。

## 文档深挖与知识产权来源

保留 Search Toolkit 文档内挖掘路线。本次 Sidecar 健康结果为 Python 3.12、`mistralai-search-toolkit` 0.0.11，暴露 `ingest/search/open/navigate/read/grep`，不暴露 `delete`；实际运行未使用 Mistral API、Vespa 或 Docker。受控 loader 只接受登记过的 artifact，本次显式关闭 Embedding 后由 SQLite FTS5 完成取证；自动化测试也覆盖了 Embedding 探测失败时的同能力降级。Mistral Agentic Search 直接描述了 search → inspect → grep → navigate/read 循环及 `exclude_ids` 已读排除；Mistral Search Toolkit 文档与 `mistralai-search-toolkit` 发行包是实现与归属依据。[A2, A5, A6]

来源边界必须长期保留：

- 发现阶段的 CLI、Provider 路由、Search/Research/Fetch、来源处理与可观测性改编自 `konbakuyomu/smartsearch`，并在当前 `whycantfindaname/smartsearch` 分支继续演化；[A7, A8]
- 文档深挖的文档模型、locator、Pipeline、splitter、QueryEngine 与工具循环来自 Mistral Agentic Search / Search Toolkit；项目只在其周围实现受控 artifact、存储、Embedding、MinerU 与失败降级适配；
- `ResearchFrame`、角色委派合同、caller-held `ResearchRun`、Claim 生命周期、Trace 和引用完整性检查是本项目自有协议；
- 代码、锁定依赖、NOTICE、许可证和第三方来源清单必须继续保留 Smart Search 与 Mistral Search Toolkit 的版权和许可信息。不得把接口复用写成项目独立发明，也不得把本次兼容结果外推为未经验证的完整兼容承诺。

## Claim、Evidence、Trace 与 provenance

保留 `ClaimSpec → EvidenceItem → ClaimRecord`。本次 16 条 EvidenceItem 均具有直接 URL、不可混淆的 artifact/snapshot identity、character-range locator、parser/chunker 标识、stance 与定性质量维度；两个 ClaimRecord 都是 `weakly_supported`，准确反映了“有局部直接证据，但完整体系尚缺公共证据”的状态。

执行 Trace 与证据 provenance 必须继续分开：

- **执行 Trace** 回答“系统做了什么”：任务、步骤、attempt、时间、Provider、状态、失败/降级、公开决策摘要和 artifact 引用。它是 run-local、append-only 的审计历史，不证明来源内容为真，也不承诺自动恢复。
- **证据 provenance** 回答“这项主张来自哪里”：canonical URL、artifact、snapshot、retrieved_at、parser/chunker、typed locator、摘录/转述、Claim 关联和 stance。它证明证据可定位与未被身份混淆，不单独证明编排过程正确。
- 两者通过 task/attempt/artifact 相交。当前引用反向验证已经从 16 条最终 citation 全部回到 Claim、Evidence、attempt、snapshot 和 raw ref；后续应继续以这一链路作为引用完整性条件，不能用“Trace 中出现过某 URL”替代 EvidenceItem。

## 决策清单

| 决策 | 内容 |
| --- | --- |
| 保留 | Root 唯一语义 Planner/Synthesizer；Scout/Curator/Miner 专职角色；Smart Search 确定性内核；四 Provider 独立失败隔离；Root 选关键文档；Search Toolkit 文档内循环；Claim/Evidence 生命周期；执行 Trace 与证据 provenance 双链；引用反向验证；来源和许可证归属。 |
| 修改 | brief 加入已知事实、read-set、边界与引用要求；CandidateCard 增加选文所需元数据；每次重规划与停止保存公开决策摘要；将 `gaps/suggestions/uncertainties` 正式纳入反馈循环；继续验证 embedding、MinerU 和 Provider 降级，不把一次成功当作稳定性证明。 |
| 暂不做 | 独立 Review/架构迭代/SystemUpdater 角色；子角色创建后代；自动暂停恢复或重放工作流；固定 Agent/任务/候选阈值；统一证据分数；声称完整公共架构已获证明；选择、运行或评分 Benchmark。 |

Stage G 的架构复盘到此停止。Benchmark 仍需用户审阅后另建任务；本文件不作选择，也没有运行任何 Benchmark。

## References

1. **[A1] Anthropic.** [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system). CandidateCard `cand_65ade4bac10bbac004649282`; EvidenceItem `evidence-architecture-anthropic-orchestrator`, `evidence-architecture-anthropic-boundaries`, `evidence-architecture-anthropic-duplicate-risk`.
2. **[A2] Mistral AI.** [Agentic Search](https://docs.mistral.ai/studio/search/agentic-search). CandidateCard `cand_5107102d22f06e3185838d0d`; EvidenceItem `evidence-architecture-mistral-retrieval-loop`, `evidence-architecture-mistral-read-set-navigation`.
3. **[A3] SearchSwarm.** [Agentic Search with Multi-Agent Collaboration](https://arxiv.org/html/2606.09730). CandidateCard `cand_14ada9dbe5277b11a3cb16e1`; EvidenceItem `evidence-delegation-searchswarm-brief-context`, `evidence-delegation-searchswarm-root-judgment`, `evidence-delegation-searchswarm-citations`.
4. **[A4] 用户提供的 MultiAgent 公开案例.** [微信公众号原文](https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ). 已知 URL 直接登记为 artifact；EvidenceItem `evidence-delegation-wechat-feedback-protocol`, `evidence-delegation-wechat-role-separation`.
5. **[A5] Mistral AI.** [Search Toolkit documentation](https://docs.mistral.ai/studio/search-toolkit). 实现归属依据，本次没有独立 EvidenceItem。
6. **[A6] Mistral AI.** [`mistralai-search-toolkit` 发行包](https://pypi.org/project/mistralai-search-toolkit/). 版本与依赖归属依据，本次没有独立 EvidenceItem。
7. **[A7] konbakuyomu.** [`smartsearch` 上游仓库](https://github.com/konbakuyomu/smartsearch). 发现阶段原始项目来源，本次没有独立 EvidenceItem。
8. **[A8] whycantfindaname.** [当前 `smartsearch` 仓库](https://github.com/whycantfindaname/smartsearch). 当前实现与验收载体，本次没有独立 EvidenceItem。
