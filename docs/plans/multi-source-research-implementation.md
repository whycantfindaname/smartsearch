# Smart Search 多源研究全流程实现计划

> 状态：实施前设计已部分确认
>
> 目标分支：`preview/macos-multisource-search`
>
> 首发范围：仅 macOS Preview
>
> 最后更新：2026-08-23

本文档是 Smart Search 多源研究改造的实现依据。后续新增决策只更新本文档，不以聊天记录或流程图中的隐含含义作为实现依据。

## 1. 目标

把 Smart Search 从“单次搜索命令与单一 Research 路径”扩展为统一的多源研究系统：同一个 Planner 根据问题、研究强度、可用能力和成本约束生成执行计划；Smart Search 内部搜索、Native Research API 与外部 Skill 以混合方式执行；所有结果进入统一证据管线，完成来源回读、实体去重、冲突记录和带引用综合。

最终用户仍只需要选择研究目标和强度，不需要手工编排各搜索引擎。

## 2. 已确认的产品决策

### 2.1 只保留一个 Planner

- 不新建第二套互相竞争的 Planner。
- 在现有 `build_deep_research_plan` 基础上演进为 Multi-Research Planner。
- 保留两个入口：
  - `deep`：只生成并展示计划，不执行网络请求。
  - `research`：生成计划并执行。
- 研究强度只保留 `quick`、`standard`、`deep`，不增加 `max`。

### 2.2 采用混合执行边界

- Smart Search 进程负责：内部 Provider、可直接调用的 Native Research API、统一数据结构、归一化、去重、证据处理和最终综合。
- Agent 负责：理解并调用外部 Skill，尤其是 AnySearch Skill。
- AnySearch 不重新作为 Smart Search 内部 Provider 实现。
- Agent 调用 AnySearch 后，必须把结构化结果交回 Smart Search 的公共合并管线，不能绕过证据处理直接拼接最终答案。

### 2.3 各研究强度的执行策略

| 模式 | 默认执行范围 | Native Research 限制 |
| --- | --- | --- |
| `quick` | Smart Search 基础搜索 | 不调用 |
| `standard` | Smart Search 基础搜索；Planner 判断有必要时委派 AnySearch | 不调用 |
| `deep` | 始终执行 Smart Search Research；Planner 从当前可用的 Native Research 中选择 | 最多并行 2 个 |

- 超过 2 个 Native Research 只在用户显式指定时执行。
- Provider 数量不是质量目标；Planner 应按问题类型和互补性选择来源。
- 某一执行单元不可用时记录降级，不阻断仍可产生可信结果的其他执行单元。

### 2.4 Native Research 的可用性门槛

只有同时满足以下条件的能力才能进入 Planner 的候选集合：

1. 当前机器存在对应 API Key。
2. 最小 live 请求成功。
3. 返回结果符合 Smart Search 适配契约。
4. 当前套餐、余额或 credits 确实允许调用。

仅有 Key 不代表能力可用。无余额的智谱 Key 只能作为备用配置，不能被 Planner 当作当前可执行能力。付费功能若未通过 live entitlement 验证，也不能进入默认计划。

首批 Native Research 候选包括 Firecrawl Agent、Jina DeepSearch、Exa Agent 和 Tavily Research；最终启用清单以实施时重新执行的 live capability probe 为准。

### 2.5 AnySearch 的管理和调用规则

- Smart Search 仓库保留一份完整、原样的 AnySearch Skill 快照。
- 快照首选来源固定为 `jason-liao-skills/main/skill-packages/anysearch`。
- 只有首选仓库中不存在该包时，才允许从 AnySearch 官方仓库获取。
- 不读取本地开发目录作为自动同步来源。
- Smart Search 仓库内的同步脚本只管理内置快照，不修改全局 Skill。
- 全局 AnySearch Skill 继续由 Skills 工作区自己的全局安装流程管理。
- Smart Search 内置快照优先于全局安装；内置快照缺失或损坏时才尝试全局 AnySearch Skill。
- Smart Search 只向 Agent 说明何时适合委派 AnySearch，以及 AnySearch 已具备的能力；不硬编码 Agent 必须调用某个具体子命令，由模型阅读 Skill 后自行选择。
- 若运行环境没有可用 AnySearch Skill，则记录委派不可用并继续其他搜索路径。
- `ANYSEARCH_API_KEY` 随内置快照的私有 `.env` 提供，同时保持 Git、npm 包和 wheel 中不包含明文密钥。

## 3. 目标执行流程

1. 接收用户问题和 `quick | standard | deep` 模式。
2. Multi-Research Planner 分解检索意图、问题类型、时间范围、来源偏好和成本边界。
3. Planner 生成三类执行单元：
   - Smart Search 内部搜索或抓取；
   - Native Research API；
   - Agent 执行的外部 Skill 委派。
4. 各执行单元返回统一 `ProviderRun`，其发现结果分别归一化为 `DiscoveryCandidate` 或 `ResearchArtifact`。
5. 合并候选，并按 URL、DOI、代码仓库、论文和事件实体去重。
6. 对关键候选读取原始网页、论文、文档或代码来源，生成 `EvidenceItem`。
7. 将待回答的事实主张登记到 `Claim Ledger`，关联支持证据、反驳证据、不确定性和时间信息。
8. 对冲突来源进行显式记录和权重判断。
9. 一次性生成带引用的综合结论，不分别输出互不协调的 Provider 摘要。

对应架构图：

- [`docs/architecture/multi-source-search-flow-anysearch.drawio`](../architecture/multi-source-search-flow-anysearch.drawio)
- [`docs/architecture/multi-source-search-flow-anysearch.png`](../architecture/multi-source-search-flow-anysearch.png)

Skill 正文中的 Mermaid 必须与本计划和 Draw.io 的逻辑一致，但可以压缩视觉细节。

## 4. 统一数据契约

以下结构是跨 Provider、Native Research 和外部 Skill 合并的最小公共语言。字段可在实现时细化，但不得绕开这些边界直接拼接结果。

### 4.1 `ProviderRun`

记录一次执行单元的运行事实：

- `run_id`、`step_id`
- `provider`、`capability`
- `execution_kind`：`internal | native_research | delegated_skill`
- `status`：`planned | running | awaiting_delegate | succeeded | partial | failed | skipped`
- 开始时间、结束时间、耗时
- 请求参数摘要、用量或成本摘要
- 原始产物引用
- 错误与降级原因

### 4.2 `DiscoveryCandidate`

表示搜索阶段发现、但尚未完成证据核验的候选来源：

- 标题、URL、摘要、发布日期和来源类型
- DOI、仓库地址或其他稳定实体标识
- 来源 Provider 与原始排名
- 与查询的初始相关性信息

### 4.3 `ResearchArtifact`

表示 Native Research 或外部 Skill 返回的研究产物：

- 执行单元和来源标识
- 研究摘要或结构化发现
- 引用列表及其原始定位信息
- Provider 自带的置信度或限制说明
- 原始响应产物引用

`ResearchArtifact` 不是最终证据；其中的关键引用仍需尽可能回读原始来源。

### 4.4 `EvidenceItem`

表示已读取并可用于支撑结论的证据：

- 规范化来源标识和可访问 URL
- 证据摘录或忠实转述
- 来源发布时间、读取时间和来源类型
- 支持或反驳的 Claim 标识
- 证据质量、时效性和直接性信息

### 4.5 `Claim Ledger`

以主张为中心保存：

- `claim_id` 和规范化主张
- 支持证据与反驳证据
- 冲突类型
- 当前判断、置信度和保留意见
- 最终答案中的引用映射

## 5. 分阶段实现

### 阶段 A：公共契约与持久运行目录

- 定义上述核心模型及 JSON 序列化格式。
- 为每次 Research 建立可恢复的运行目录，保存计划、状态、原始产物和合并产物。
- 先以契约测试固定输入输出，再迁移现有 Research 结果。

### 阶段 B：统一 Planner

- 在现有 Planner 上加入执行单元类型、能力探测、模式预算和最多 2 个 Native Research 的约束。
- 保持 `deep` 只规划、`research` 规划后执行。
- Planner 输出必须可解释：说明为何选择或跳过某项能力。

### 阶段 C：Native Research 适配器

- 为通过 live capability probe 的 Firecrawl、Jina、Exa、Tavily 能力实现适配器。
- 统一超时、状态、原始响应保存和 `ResearchArtifact` 转换。
- 不为未通过套餐验证的功能编写默认执行路径。

### 阶段 D：Agent 委派与恢复执行

- Planner 输出 AnySearch 委派步骤和输入契约。
- Smart Search 在需要 Agent 执行时进入可恢复的等待状态。
- Agent 自主选择 AnySearch Skill 功能并写回符合契约的产物。
- Smart Search 恢复该次运行，把 AnySearch 结果送入同一合并管线。

### 阶段 E：证据合并与综合

- 实现候选归一化和实体级去重。
- 回读 Native Research 和 AnySearch 引用的原始来源。
- 生成 `EvidenceItem` 和 `Claim Ledger`。
- 处理来源冲突、时效差异和证据缺口。
- 使用统一权重生成一次性带引用结论。

### 阶段 F：Benchmark 调研与评测设计

- 本阶段只能在阶段 A 至 E 全部实现并通过工程测试后启动。
- 冻结待验收的代码版本、配置、Provider 清单和模型版本，避免调研期间继续改变被测对象。
- 以 `max` 强度启动一次独立的 Benchmark 深度调研；这里的 `max` 表示验收调研的覆盖程度和证据要求，不是 Smart Search 面向用户的第四种运行模式。
- 全面调研各 Provider、搜索工具和 Deep Research 系统公开使用的 benchmark、数据集、评测脚本和指标。
- 工具范围至少覆盖 Smart Search 当前接入或计划接入的 AnySearch、Exa、Tavily、Firecrawl、Jina、Context7、Sciverse、主搜索模型及其 Native Research 能力；某个工具没有公开 benchmark 时也要记录“未找到”和检索范围。
- 记录每项公开结果的题集版本、样本数、任务类型、检索深度、驱动模型、Reader、Judge、时间、成本和厂商关系。
- 选择能够在统一 harness 中复现的公开题集，建立 Smart Search 自己的分轨评测套件。
- 分别运行无搜索、单一 Provider、简单多源并集、完整 Smart Search 和关键组件消融实验。
- 输出分轨能力表、质量—延迟—成本曲线、失败案例和置信区间，不用单一总分掩盖不同能力。

### 阶段 G：端到端工程验收与 macOS 激活

- 完成离线契约测试、Provider mock 测试和有限 live smoke test。
- 验证源码、wheel、npm 包及安装后运行行为。
- 验证私有 `.env` 不进入 Git 或发布包。
- 根据阶段 F 的调研结果完成 Benchmark 基线和发布候选运行，保存原始结果与复现实验命令。
- 在 Preview 分支验收通过后，替换 macOS 当前激活的 `smart-search-cli`。
- 稳定运行后再决定是否合并到 `lwj_dev` 并同步其他机器；本计划不授权自动 push 或跨机器部署。

## 6. Benchmark 调研与评测方案

### 6.1 调研产物

Benchmark 调研必须形成一张可追溯的对照表，每行记录：

- 工具与被测能力；
- benchmark 名称、版本、任务数和数据许可；
- 任务类型与 gold answer 的来源；
- 指标及其计算方式；
- 每题允许的搜索调用次数、返回结果数和停止条件；
- 固定的驱动 Agent、Reader、Judge 及其版本；
- 是否使用 LLM-as-a-Judge；
- 延迟、token、API 调用和费用的统计口径；
- 公开代码、数据和结果链接；
- 复现状态；
- 厂商自测、独立评测或学术评测；
- 已知偏差、数据污染风险和适用边界。

max 调研按五条独立路线执行：

1. 厂商路线：逐一核对各搜索工具自己的 benchmark、方法、代码和公开数据。
2. 独立路线：查找第三方 Search API 排行榜和 provider-swap 评测，识别与厂商自测不一致的结果。
3. 学术路线：调研通用检索、时效问答、多跳搜索、Agentic Search 和 Deep Research benchmark。
4. 复现路线：检查数据许可、脚本可运行性、费用、所需模型和潜在数据污染，确定哪些评测能够成为发布门禁。
5. 映射路线：把候选 benchmark 映射到 Smart Search 的发现、排序、证据、研究和工程效率五类能力，并设计单源、多源和组件消融实验。

各路线完成后由主 Agent 合并证据，再使用一个独立 Reviewer 检查厂商偏差、对照不匹配、指标误用、遗漏工具和无法复现的结论。调研报告通过审查后才进入实际 Benchmark 运行。

max 调研至少应核对以下 Benchmark 类型和公开入口；这些条目是调研范围，不代表当前已经完成核验或决定采用：

- [Firecrawl DevDex](https://www.firecrawl.dev/benchmarks/devdex)：代码仓库发现、Issue/PR 定位和文档检索；固定 gold URL，使用 Recall@10 与 MRR@10。
- [Exa Search Benchmarks](https://github.com/exa-labs/benchmarks)：WebCode、People、Company 和 Publication Retrieval 等分轨评测。
- [Tavily Search Evals](https://github.com/tavily-ai/tavily-search-evals)：SimpleQA 和文档相关性等统一搜索 API 评测。
- [AnySearch Accuracy Benchmark](https://anysearch.com/home)：FRAMES、FreshQA 和 WebWalkerQA；需要进一步核对可复现数据、脚本和完整方法。
- [Artificial Analysis Search API Methodology](https://artificialanalysis.ai/methodology/search-api)：固定 Agent、只替换 Search API 的 provider-swap 设计。
- [DeepResearch Bench](https://deepresearch-bench.github.io/)：面向研究报告的质量、引用和检索能力评测。
- [Deep Research Bench II](https://arxiv.org/abs/2601.08536)：使用专家报告生成的细粒度 rubric 评估信息召回、分析与表达。

max 调研需要核对每个入口的原始方法、代码、数据和许可证。厂商公布的分数不能直接横向合并，因为各评测的模型、查询集、调用预算、结果数、Reader、Judge 和运行时间可能不同。

### 6.2 Smart Search 的评测层级

Smart Search 需要分别回答五个问题：

| 能力层级 | 核心问题 | 主要指标 |
| --- | --- | --- |
| 发现能力 | 能否找到正确来源 | Recall@k、Success@k、覆盖率 |
| 排序能力 | 正确来源是否排在前面 | MRR@k、nDCG@k |
| 证据能力 | 来源是否真正支持主张 | Citation precision、Citation recall、引用完整率 |
| 研究能力 | 能否分解问题、补足缺口并形成可靠结论 | 答案准确率、Claim 覆盖率、冲突识别率、报告 rubric 得分 |
| 工程效率 | 提升是否值得额外资源 | P50/P95 延迟、每题成本、API 调用数、token、失败率 |

搜索能力和写作能力必须分开报告。检索到正确来源但综合模型答错，属于 Reader 或 synthesis 失败；没有检索到正确来源，才属于搜索失败。

### 6.3 计划采用的 Benchmark 组合

最终套件按能力分轨，不把所有任务压成一个排行榜：

1. **开发者检索**：优先复现 DevDex；补充 Exa WebCode 中可公开复现的文档与代码内容评测。
2. **一般事实检索**：使用 SimpleQA Verified 或同类固定答案集，测量搜索给固定 Reader 带来的准确率提升。
3. **时效性检索**：使用 FreshQA，并增加带明确采集日期的滚动题集；旧答案必须按运行日期重新核验。
4. **多跳和复杂检索**：使用 FRAMES、WebWalkerQA、BrowseComp 或 DeepSearchQA 中可合法、可复现的子集。
5. **学术检索**：使用 Publication Retrieval 或自建 DOI gold 集，覆盖已知论文、模糊回忆、方法追踪和引用关系。
6. **研究报告**：使用 DeepResearch Bench 类任务评估信息覆盖、引用正确性、分析和表达；该轨与纯检索分数分开。
7. **项目真实任务集**：从 Smart Search 的真实使用场景抽取代码、API 文档、论文、中文时效信息和综合研究任务，建立冻结测试集与后续滚动测试集。

公开 benchmark 只有在数据、脚本和许可证允许本地复现时才进入正式验收。只能看到排行榜、无法重跑的方法保留在调研报告中，不作为发布门禁。

### 6.4 统一对照实验

所有方案在匹配条件下运行：同一题集版本、同一 Agent/Reader/Judge、同一提示词、同一最大搜索次数、同一 top-k、同一超时、同一日期窗口和同一输出格式。每次运行保存模型版本、Provider 版本、配置、随机种子、原始检索结果和费用。

每个轨道至少比较：

1. `No Search`：测量模型记忆基线和题目污染。
2. 每个可用的单一 Provider 或 Native Research：测量单源能力。
3. `Naive Union`：多源结果简单合并，只测量增加来源数量的收益。
4. `Smart Search quick`。
5. `Smart Search standard`。
6. `Smart Search deep`。
7. `Smart Search deep` 的组件消融：分别关闭 Planner、AnySearch、Native Research、去重、原始来源回读和 Claim Ledger。

这组比较可以把三类增益分开：

- **来源增益**：最佳单源与 `Naive Union` 的差异；
- **编排增益**：`Naive Union` 与完整 Planner 的差异；
- **证据合并增益**：关闭与开启去重、来源回读、Claim Ledger 时的差异。

只有质量提高且额外成本、延迟和失败率处于可接受范围时，才认定多源方案带来有效增益。增加搜索次数本身不算能力提升。

### 6.5 结果判定

发布判断采用分轨门槛和 Pareto 比较：

- `quick` 关注低延迟与基础准确率，不能因多源调度显著变慢。
- `standard` 应在一般事实、时效性和项目真实任务上稳定优于最佳单源，或在相近质量下显著降低成本或失败率。
- `deep` 应在复杂检索和研究报告轨道上提高证据覆盖、引用正确性和 Claim 覆盖率；其延迟和成本单独报告。
- 任一总体提升都必须同时报告各任务轨道、95% 置信区间和失败案例，避免平均数掩盖代码、学术、中文或时效任务的退化。
- Planner 选择策略只有在相同题目上优于固定 Provider 组合，或以更低成本达到相近质量时才算有效。

正式阈值在完成 benchmark 全面调研和首轮基线后确定。当前不预先填写任意百分比，以免把没有经验依据的数字写成发布标准。

## 7. 验收标准

### 7.1 功能与工程验收

- `deep` 在无网络请求的情况下产出完整可执行计划。
- `quick` 不调用 Native Research 或 AnySearch。
- `standard` 只在 Planner 判断需要时委派 AnySearch，不调用 Native Research。
- `deep` 始终包含 Smart Search Research，默认最多并行 2 个已验证可用的 Native Research。
- AnySearch 始终作为外部 Skill 委派，不恢复为内部 Provider 或重复实现。
- AnySearch 不存在、Provider 失败或套餐不可用时，流程可降级并说明覆盖缺口。
- 所有执行结果都能追溯到 `ProviderRun` 和原始产物。
- Native Research 的摘要不能直接充当最终证据；关键结论需要尽可能回读原始引用。
- 重复 URL、DOI、仓库和同一事件不会被当作独立证据重复加权。
- 冲突结论在 `Claim Ledger` 中可追踪，最终答案说明冲突或不确定性。
- 最终输出是一次性综合结果，并包含可定位的引用。
- Git、npm 包和 wheel 均不泄露 API Key 或私有 `.env`。
- macOS 激活版本与 Preview 分支验收产物一致。

### 7.2 Benchmark 验收

- 阶段 A 至 E 已完成，发布候选版本及其配置已经冻结，随后才启动 max Benchmark 调研。
- 完成搜索工具 Benchmark 全面调研表，并回读公开方法、代码和数据，而不是只记录厂商宣传分数。
- 至少覆盖开发者检索、一般事实、时效、多跳、学术、研究报告和项目真实任务七个轨道。
- 同一 harness 中完成 No Search、单源、Naive Union、三种 Smart Search 模式和关键组件消融。
- 结果可复现到题目级，包含检索结果、最终答案、引用、延迟、token、API 调用和成本。
- 分别报告检索、证据、研究和工程效率，不用一个综合分数替代分轨判断。
- 完成统计不确定性、污染检查、失败案例和回归分析。
- 基线与发布候选的差异满足首轮评测后确定的分轨门槛；任何关键轨道退化必须在激活前解释和裁决。
- Benchmark 验收未完成前，不替换 macOS 当前激活版本。

## 8. 当前实现状态

### 已实现

- Preview 分支和 macOS 首发边界。
- 删除 Smart Search 内部 AnySearch Provider、配置和专属 CLI 命令。
- AnySearch 外部 Skill 委派的路由元数据。
- 内置 AnySearch Skill 快照、同步脚本、私有配置隔离和打包规则。
- Draw.io 流程图、Skill 中的 Mermaid 目标图。
- 最小 Preview 的单元测试、打包测试和 macOS 激活验证。

### 尚未实现

- Multi-Research Planner 的统一可执行调度。
- Native Research 的并行执行与 entitlement 动态筛选。
- Agent 委派的暂停、产物回传和恢复协议。
- `ProviderRun`、`DiscoveryCandidate`、`ResearchArtifact`、`EvidenceItem` 和 `Claim Ledger` 的完整代码实现。
- 实体去重、原始来源回读、冲突处理和统一加权综合。
- 整张流程图对应的端到端执行与验收。
- Benchmark 全面调研报告、统一 harness、基线结果和分轨发布门槛。

## 9. 尚待确认的关键问题

这些问题会改变接口或执行模型，必须在对应阶段编码前确认：

1. Agent 回传 AnySearch 结果的最简交互形式；当前不限定“运行目录 + 恢复命令”。
2. Native Research 的精确选择优先级，以及用户显式选择多个能力时的 CLI 表达方式。
3. 最终综合沿用当前 Smart Search 的合成模型，还是允许 Planner 独立选择合成 Provider。
4. Benchmark 全面调研完成后，各能力轨道的发布阈值和项目真实任务集权重。

第 1 项决定混合执行的接口，第 4 项决定最终发布门槛。两项都应以实际原型或基线数据为依据，不在当前阶段凭空确定。
