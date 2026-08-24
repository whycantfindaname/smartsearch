# Stage G Benchmark 候选推荐

> 日期：2026-08-24
> 边界：本报告只推荐候选和后续评分流程，不选择、不运行任何 Benchmark，也不生成分数。

## 结论

没有单一公开 Benchmark 能同时覆盖多源发现、代码与开发者资料检索、live Web 时效性、关键文档选择、文档内证据定位、Claim 综合、长报告质量、引用正确性以及 Root/Scout/Curator/Miner 的过程 Trace。Stage G 后续若进入实跑，应采用**分层组合**，并保留各 Benchmark 的原始指标，不能把异质指标压成一个总分。

候选组合按能力层展开如下：

| 能力层 | 优先研究候选 | 角色 |
| --- | --- | --- |
| 发现 / 代码检索 | [DevDex](https://www.firecrawl.dev/benchmarks/devdex)、[BrowseComp-Plus](https://texttron.github.io/BrowseComp-Plus/) | 前者测开发者资料检索，后者用固定语料拆开答案正确性与证据召回 |
| live Web | [LiveResearchBench](https://github.com/SalesforceAIResearch/LiveResearchBench)、[LiveDRBench](https://github.com/microsoft/livedrbench)；[BrowseComp](https://openai.com/index/browsecomp/) 可选 | 分别测实时长报告、Claim 发现和困难短答案搜索 |
| 文档挖掘 | [QASPER](https://huggingface.co/datasets/allenai/qasper) 或 [MMLongBench-Doc](https://mayubo2333.github.io/MMLongBench-Doc/) | 前者适合低成本文本证据定位，后者适合 PDF、跨页、表格和图表路径 |
| 报告与引用 | [DeepResearch Bench](https://deepresearch-bench.github.io/) | 联合评估长报告质量、信息获取和引用可信度 |
| 轻量引用单测 | [ALCE](https://github.com/princeton-nlp/ALCE/) | 对生成内容做引用完整性与引用支持关系回归 |

“优先研究”表示值得进入下一轮选型核验，不表示已经选定。尤其是数据许可、隐藏集访问、当前评测脚本、judge 模型和服务配额，仍需在实际建任务前按固定 commit 回读。

## 1. 发现 / 代码检索

### DevDex / Developer Retrieval Benchmark

- **测什么：** 面向技术问题，从开发者文档、README、仓库、Issue 和 PR 等资料中找回规范来源；最贴近 Search Scout 的代码与开发者资料发现，以及 Curator 对 canonical URL 的选择。
- **评分流程：** 在统一的 agent、搜索工具和每次返回 10 条结果的条件下，将前 10 个引用与 canonical URL gold 对齐，计算 Recall@10 与 MRR@10；空结果按未命中处理，不需要 LLM judge。公开实现见 [benchmark-devdex](https://github.com/firecrawl/benchmark-devdex)。
- **公开依赖与成本：** 依赖公开 harness、公开样本、被测搜索服务和 agent 模型；完整集合包含非公开部分。相对复现成本为**低至中**，主要变量是搜索 API、模型调用和 URL 规范化。
- **时效与污染：** no-search memorization gate 可排除模型不搜索也能答出的样本，但公开样本仍可能进入训练；开发者页面迁移、版本更新和 canonical URL 变化会造成时间漂移。
- **不能测什么：** 不测通用 live Web 覆盖、长文档内定位、长报告综合、引用对 Claim 的语义支持，也不能证明动态重规划或多 Agent 信息交换有效。

### BrowseComp-Plus

- **测什么：** 在约 100K 固定文档和 830 个查询上，同时观察答案正确性、gold evidence 召回、搜索调用量与置信度校准；适合区分“答案碰巧正确”和“确实找到了证据”。
- **评分流程：** 官方页面给出的四项指标是由 `gpt-4.1` 判定的 Accuracy、相对完整 evidence 集的 Recall、Search Calls 和 Calibration Error。运行时应分别报告四项，不合成总分。
- **公开依赖与成本：** 依赖固定语料、gold evidence / hard negatives、检索索引、agent 模型和 `gpt-4.1` judge。语料规模与 judge 调用使相对复现成本为**中至高**。
- **时效与污染：** 固定语料有利于可重复比较，却不测 freshness；公开问题、gold evidence 和语料会逐步产生训练污染。应固定数据版本，并增加 no-search 基线。
- **不能测什么：** 不测真实网页变化、跨站访问失败、完整长报告质量、Claim 级引用支持或内部角色 Trace。
- **当前限制：** 官方页面的结果表结构已经出现，但明确写明表格数据将稍后发布；因此截至本次材料快照，**BrowseComp-Plus 完整结果表尚未发布**，不能把页面上的示例结果当成完整 leaderboard。

## 2. Live Web

### LiveResearchBench

- **测什么：** 用户导向、需要最新网页信息的开放式长报告，覆盖动态检索、跨来源综合、内容覆盖、呈现质量和引用关系；它最接近 Smart Search `deep` 的最终用户产物。
- **评分流程：** 使用 DeepEval 对报告做多协议评估，维度包括 coverage、presentation、citation accuracy / association、consistency 和 analysis depth。后续运行应保留分维度结果，同时抽样人工复核 judge 分歧。
- **公开依赖与成本：** 依赖公开任务与评测仓库、实时 Web、搜索/抓取服务、报告生成模型和 LLM judge；相对复现成本为**高**，且一次运行包含生成与评测两类费用。
- **时效与污染：** live 任务减少单纯背题的价值，但网页更新、下线、地域差异和搜索排序变化会降低跨时间可比性。必须记录运行时间、地区、provider、抓取快照和 judge 版本。
- **不能测什么：** 最终报告得分不能单独定位是 Scout 漏搜、Curator 选错文档、Miner 漏证据还是 Synthesizer 写作失败，也不直接验收 typed locator 和内部 Trace。

### LiveDRBench

- **测什么：** 把 deep research 视为 Claim 发现问题，考察系统找出的关键 Claim 是否完整且准确；适合检查 Miner 到 Claim synthesis 的中间产物，而不只看最终文风。
- **评分流程：** 按官方仓库协议将系统 Claim 与参考 Claim 对齐，报告 precision、recall 和 F1。若对齐实现调用语义匹配模型或 judge，应锁定模型、提示词与阈值，并保存匹配明细供复核。
- **公开依赖与成本：** 依赖公开任务/Claim 数据、实时搜索与抓取、Claim 抽取和匹配实现；相对复现成本为**中**，若完整重跑 live research 则上升为中至高。
- **时效与污染：** Claim gold 与网页事实都可能随时间变化。固定旧 gold 会损害 freshness，动态更新 gold 又会降低重复性；应把任务版本和事实截止时间作为结果的一部分。
- **不能测什么：** 不测报告结构、叙述质量、引用呈现、文档内 locator 精度，也不能单独评价代码检索或 Root/Scout 的协作效率。

### BrowseComp（可选侧测）

- **测什么：** 困难、持续搜索型的 live-Web 短答案任务，适合给 Root 的查询改写、跨页追踪和停止决策施压。
- **评分流程：** 按官方协议对 1,266 个任务的短答案做规范化正确性判定，并单独记录失败、调用次数、耗时和成本；不要把短答案正确率替代引用或长报告指标。
- **公开依赖与成本：** 依赖任务访问、实时 Web、搜索/浏览工具和 agent 模型；相对复现成本为**中至高**，长尾任务的延迟和调用数可能较大。
- **时效与污染：** live Web 会漂移；公开题目也可能被训练或被网页直接收录。需要冻结题集版本、记录运行日期，并设置 no-search 对照。
- **不能测什么：** 不测 evidence recall、引用完整性、报告质量、文档内证据定位或多 Agent Trace。因此它只应是 live-Web 侧测候选，不是主验收基准。

## 3. 文档挖掘

### QASPER

- **测什么：** 1,585 篇论文上的 5,049 个问题及 evidence annotations，适合验证文本论文内的答案提取、不可回答判断和证据段选择。
- **评分流程：** 分别计算答案 token F1 与 evidence-selection F1；答案和证据必须保持分开，避免答案正确掩盖 locator 选错。
- **公开依赖与成本：** 依赖公开数据集、论文文本预处理和确定性 scorer，通常不需要在线搜索或 LLM judge；相对复现成本为**低至中**。
- **时效与污染：** 静态且已公开多年，重复性高但训练污染风险高。适合作为工程回归，不适合作为当前检索能力的唯一证据。
- **不能测什么：** 不测 live Web、多源发现、网页/仓库检索、复杂 PDF 视觉元素、长报告或外部引用正确性。

### MMLongBench-Doc（多模态文档路径）

- **测什么：** 135 篇长 PDF 上的 1,082 个专家问题，覆盖跨页、表格、图表和不可回答案例；更贴近 MinerU、PDF 解析与 typed locator 的联合路径。
- **评分流程：** 分开报告 answer 与 evidence-location 指标，并按问题类型拆分文本、表格、图表、跨页和不可回答结果。开放答案是否需要 judge，应以锁定 commit 的官方 scorer 为准。
- **公开依赖与成本：** 依赖公开 PDF/标注、PDF 渲染或 OCR/版面解析、多模态模型及评测脚本；相对复现成本为**高**，但能覆盖 QASPER 不具备的输入形态。
- **时效与污染：** 固定文档带来较强可重复性，也带来公开数据污染；解析器、渲染分辨率和模型视觉预处理变化会形成额外评测漂移。
- **不能测什么：** 不测 live Web、跨来源发现、引用到原始网页的可信度、长报告综合或多 Agent 协作。

QASPER 与 MMLongBench-Doc 是两条不同成本的候选路径，不应把后者的多模态负担强加给 text-first 回归，也不应以 QASPER 代替 PDF、表格和图表验收。

## 4. 报告与引用

### DeepResearch Bench

- **测什么：** 面向双语、博士级研究任务的长报告；RACE 关注报告质量，FACT 关注信息获取效果、有效引用和引用准确性。它是本候选集中最接近端到端报告验收的一项。
- **评分流程：** 先按 RACE 的自适应 criteria 和维度权重评价报告，再按 FACT 拆分 citation abundance / effectiveness 与 citation accuracy；两套框架互补，不能只保留一个总分。
- **公开依赖与成本：** 依赖公开任务/参考材料、实时来源回读、长报告生成和 evaluator/judge。相对复现成本为**高**；必须锁定 judge、prompt、引用抓取器和失败处理规则。
- **时效与污染：** 任务公开会产生污染；引用网页可能变化，RACE judge 也会发生版本漂移。应保存输入、报告、URL 快照、抓取失败和逐项 judge 输出。
- **不能测什么：** 端到端分数不能隔离检索器、Curator、Miner 或 Synthesizer 的因果贡献，也不直接证明内部 locator、失败隔离和 Root/Agent 信息交换符合项目契约。

## 5. 轻量引用单测

### ALCE

- **测什么：** 在 ASQA、QAMPARI、ELI5 等静态任务上检查长答案的正确性、流畅性、引用完整性以及引用是否真正支持相邻 Claim；适合做快速、频繁的 citation regression。
- **评分流程：** 使用官方 harness 分开计算任务正确性/覆盖、citation recall、citation precision 或 entailment 支持关系，并保留 fluency；不要把 NLI 判断当作网页来源权威性判断。
- **公开依赖与成本：** 依赖公开数据、候选 passages / 检索结果、生成模型和 NLI/评测模型；若复用固定候选而不跑 live search，相对复现成本为**低至中**。
- **时效与污染：** 数据静态且较旧，污染风险高、freshness 为零；优势是结果稳定，适合作为单测而不是产品级 live 结论。
- **不能测什么：** 不测实时发现、文档抓取、复杂 locator、搜索重规划、多 Agent 协作或完整研究报告的事实覆盖。

## 后续若实跑，统一评分流程

1. **冻结实验合同。** 固定 benchmark 版本/commit、公开或隐藏 split、模型、prompt、provider、工具权限、每题预算、并发、超时、地区、运行日期和 judge；先声明主指标与失败计分规则。
2. **保留分层原始结果。** 分别保存候选来源、canonical URL、文档快照、EvidenceItem/locator、Claim、最终答案/报告、Trace、调用次数、延迟、费用和失败原因；不只保存最终分数。
3. **官方 scorer 优先。** 确定性 URL、F1、evidence-location 指标先运行；需要 judge 时锁定实现并保存逐项判定，抽样人工复核，不能静默更换 judge。
4. **加入污染与时效对照。** 对公开静态集增加 no-search / no-tool 基线；对 live 集记录事实截止时间和网页快照。同一比较只改变待测能力，其余条件保持一致。
5. **按 Benchmark 分别报告。** 同时报覆盖、准确性、引用、成本和失败率，但不跨 Benchmark 求统一总分。只有用户审阅本报告并明确选择后，才建立独立运行任务。

## 决策边界

这组候选仍不能直接测出 Root/Scout/Curator/Miner 的 typed information exchange、动态重规划质量、Provider 失败隔离、重复来源控制和 Claim-to-artifact 反向追踪。上述项目契约应继续由工程 E2E Gate 与项目自有 Trace/locator 测试负责；公开 Benchmark 只补充外部能力证据，不能替代内部验收。
