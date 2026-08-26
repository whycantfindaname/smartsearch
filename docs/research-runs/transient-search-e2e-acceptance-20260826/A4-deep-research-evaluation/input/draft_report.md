# 一年发布窗口内的 Deep Research Agent 评测证据

## 结论

本报告的时间边界是 2025-08-26 至 2026-08-26，日期判断使用工作首次发布日，而不是后续版本更新时间。纳入对象必须属于论文、评测集、benchmark 或开源实现，并实质涉及 `source coverage`、`evidence faithfulness`、`citation correctness` 或 `fault recovery` 中至少一个相邻维度。

在这个窗口内，本次直接核验确认两项相关成果。DREAM（*Deep Research Evaluation with Agentic Metrics*）的 arXiv 首次发布时间为 2026-02-21T19:14:31Z。[cite:a4-dream-date] LiveResearchBench（*A Live Benchmark for User-Centric Deep Research in the Wild*）的 arXiv 首次发布时间为 2025-10-16T02:49:16Z。[cite:a4-live-date]

这两项工作都直接覆盖了报告内容覆盖或引用质量，但现有直接来源不足以把任何一项描述为严格的检索来源集合覆盖率（`source coverage`）评测，也不足以证明它们把 Deep Research Agent（DRA）在工具、检索或执行故障后的恢复能力作为被测指标。这里的结论是 `missing`，不是断言该时间窗内绝对不存在此类工作：DREAM 的指标清单把 Source Quality 具体列为 Factuality 与 Citation Integrity。[cite:a4-dream-metrics-inventory] LiveResearchBench 的 DeepEval 指标清单包含 coverage、citation accuracy 与 citation association 等维度，但没有列出 DRA fault recovery。[cite:a4-live-paper-metrics]

## 研究范围与判定边界

本报告把 `citation faithfulness` 定义为引用来源是否支持相邻主张，把 `citation correctness` 作为更宽的引用正确性概念；`evidence faithfulness` 在本文中沿用前者的可核验边界。DREAM 的 Source Quality 说明区分了 citation faithfulness（主张与引用内容的对齐）和 factual correctness（不依赖引用、面向外部世界的真实性）。[cite:a4-dream-verification-pipelines]

`Key-Information Coverage` 或 checklist coverage 只回答报告是否覆盖问题所需的关键事实，不能自动改写成候选来源空间的覆盖率。DREAM 的 KIC 做法是检索最新来源，把关键点改写为可核验的 yes/no 问题，并据此检查遗漏或过时内容。[cite:a4-dream-kic-boundary] 因此，本文将“报告覆盖了哪些必要信息”和“检索过程覆盖了多少潜在来源”视为两个不同的指标问题。

本文的 `fault recovery` 仅指 DRA 在工具、检索或执行失败后恢复研究任务的能力；评测程序自身能够从中断处继续运行，不等于 benchmark 已经测量了 DRA 的故障恢复。

## 关键发现

### DREAM：主动核验型评测框架

DREAM 将 Deep Research Evaluation 组织为四个 vertical：Presentation Quality、Task Compliance、Analytical Depth 和 Source Quality。[cite:a4-dream-taxonomy] 论文进一步把评测本身做成具有工具调用能力的 agentic framework。[cite:a4-dream-framework]

其静态指标包括 Writing Quality、Factuality、Citation Integrity 和 Domain Authoritativeness；其中 Citation Integrity 检查主张是否归因于来源且得到引用内容支持。[cite:a4-dream-static-metrics] 其自适应指标包括 KIC 与 Reasoning Quality：KIC 用问题相关、时效性的 checklist 检查必要事实。[cite:a4-dream-adaptive-kic] Reasoning Quality 则依据结构化验证计划检查推理的连贯性与有效性。[cite:a4-dream-reasoning-quality]

DREAM 的 Workflow Evaluator 将 Claim Attribution 与 Citation Faithfulness 的调和平均作为 Citation Integrity。[cite:a4-dream-verification-pipelines] Factuality 则独立于给定引用检索外部证据。[cite:a4-dream-factuality-independent] 这一区分很重要：论文的受控实验明确指出，仅验证引用与主张的对齐不足以完成事实性评估；看似有依据的错误主张仍需要外部世界知识来识别。[cite:a4-dream-factuality-boundary]

从而，DREAM 能证明 citation faithfulness、factuality、必要信息 coverage 和 reasoning quality 是可分开的评测面；它不能由 KIC 或 Citation Integrity 的存在推出 `source coverage` 已被严格定义，也不能由已列出的指标推出 DRA `fault recovery` 已被评估。[cite:a4-dream-kic-boundary]

### LiveResearchBench：论文、benchmark、dataset 与 repository 的分层对象

LiveResearchBench 的论文把它定义为覆盖日常生活、企业和学术场景的 100 个专家策划任务的 benchmark。[cite:a4-live-paper-scale] 同一论文提出 DeepEval，用于评估长篇研究报告的 coverage、presentation、citation accuracy、citation association、consistency 和 analysis depth。[cite:a4-live-paper-metrics] 论文还报告了对 17 个 frontier deep research systems 的评估。[cite:a4-live-paper-systems]

这里需要保留对象层次：论文中的 LiveResearchBench 是研究与 benchmark 贡献；Hugging Face 页面是公开 dataset 表面，列出 `question_with_checklist`。[cite:a4-live-dataset-fields] 页面同时列出 `question_only`。[cite:a4-live-dataset-question-only] 页面还为条目提供用于 coverage evaluation 的 checklist。[cite:a4-live-dataset-checklist] GitHub 页面则是源码 repository；其 README 将项目描述为同时包含 LiveResearchBench benchmark 与 DeepEval evaluation framework。[cite:a4-live-repo-identity] 不能把论文、dataset 和 repository 合并成同一个证据对象，也不能把 dataset 的 checklist coverage 当成 source coverage。

repository 还提供评测器的中断续跑机制：README 说明，评分被中断后重新运行同一命令会自动从未完成位置继续。[cite:a4-live-resume] 它还说明每个已评分报告会立即保存到按 criterion 区分的 JSONL 文件中，重新运行时加载这些增量结果。[cite:a4-live-incremental] 这是 evaluator implementation 的运行恢复能力；论文列出的 DeepEval 维度仍是 coverage、citation accuracy/association、consistency、analysis depth 等，因此不能据此声称 LiveResearchBench 把 DRA `fault recovery` 作为 benchmark 指标。[cite:a4-live-paper-metrics]

### 窗口外排除项：Improving and Evaluating Open Deep Research Agents

*Improving and Evaluating Open Deep Research Agents* 提出 BrowseComp-Small（BC-Small），并围绕 Open Deep Research（ODR）及其改进版本展开实验，因此在主题上与 DRA、benchmark 和开源 agent 相关。[cite:a4-excluded-browsecomp] 但 arXiv API 给出的首次发布时间是 2025-08-13T19:32:01Z，早于本报告的窗口起点。[cite:a4-excluded-date] 当前版本的更新时间为 2026-01-08T17:54:58Z；更新时间不能替代首次发布时间，所以该工作不纳入窗口内成果。[cite:a4-excluded-updated]

## 证据状态与研究判断

- `verified`：DREAM 的首次发布时间、四类评测 vertical、Citation Integrity/Faithfulness/Factuality/KIC 等定义；LiveResearchBench 的首次发布时间、benchmark 规模、DeepEval 维度，以及 dataset 与 repository 的公开表面。
- `missing`：在本次直接核验的工作中，没有发现把检索来源集合覆盖率作为严格操作化指标的入选工作，也没有发现把 DRA fault recovery 作为评测维度的入选工作。LiveResearchBench repository 的 resume grading 只能证明评测器可以恢复评分进程，不能改变这一状态。[cite:a4-live-resume]

因此，最稳妥的结论是：DREAM 和 LiveResearchBench 可作为 citation/evidence quality 与报告内容 coverage 的相关评测材料，但不能被引用来证明已经解决了 `source coverage` 或 DRA `fault recovery` 评测。这个边界也避免把“引用与来源对齐”“报告覆盖 checklist”“评测脚本断点续跑”三个不同层次的问题混为一谈。[cite:a4-dream-factuality-boundary]

## 验收记录与恢复边界

为保留本次接受记录中的错误签名，[Exa source-first discovery](../search-materials/commands/exa-source-first.json) 返回 `provider_error`、HTTP 402 和 `payment_required`。[Sciverse 首次显式学术请求](../search-materials/commands/sciverse-discovery.json) 返回 HTTP 400 `INVALID_REQUEST`，拒绝 `year_from` 与 `year_to`，错误类型为 `extra_forbidden`。按记录提交的 [修正请求](../search-materials/commands/sciverse-discovery-corrected.json) 又因 `sort_by_year` 触发 `extra_forbidden`。[Zhipu explicit broad discovery](../search-materials/commands/zhipu-broad-discovery.json) 在请求前返回 `config_error`，提示 provider 未配置。

[Broad search 保存结果](../search-materials/commands/broad-search.json) 明确提醒，`extra_sources` 是并行取得的候选，不能自动用于验证生成内容；本报告因此只把后续直接抓取的原始论文、API、dataset page 和 repository page 用作证据。[接受结果](../search-materials/run-result.json) 还记录了 `doctor_calls=0` 和 `native_web_used=false`。这两项属于本次运行事实，不是研究结论。

## 核验方法与限制

本次检索先按 source-first 路线生成候选，再通过 arXiv 原始论文、arXiv 官方 API、Hugging Face dataset page 和 GitHub repository page 的直接抓取结果核验主张；候选摘要只用于发现 URL，不作为 `verified` 证据。研究结果是这条安全检索路线取得并直接核验的集合，不是该时间窗的穷尽性系统综述。

在接受记录中，失败的 provider 路线只影响候选发现和路线切换，不改变日期窗口、纳入/排除标准或“source coverage / fault recovery 尚无直接证据”的判断。正文因此保留研究结论、对象边界和负面发现，不把运行时重试逻辑写成新的研究结论。
