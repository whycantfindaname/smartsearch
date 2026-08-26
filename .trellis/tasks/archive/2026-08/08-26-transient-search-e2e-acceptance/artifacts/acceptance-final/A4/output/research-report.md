# 结论

在 2025-08-26 至 2026-08-26 的首次发布窗口内，本次检索取得两个有直接来源支持、且与 Deep Research Agent 评估相关的目标：DREAM 与 LiveResearchBench。DREAM 是论文与 agentic evaluation framework；LiveResearchBench 同时包含论文、benchmark、dataset 与开源 repository。两者都直接覆盖 citation correctness / citation faithfulness 或报告内容 coverage，但当前直接证据都不足以把它们描述为严格评估 `source coverage`（检索来源覆盖率）的工作；也没有证据表明它们把 agent 的 `fault recovery` 作为被测指标。

| 目标 | 类型 | 首次发布日期 | 与筛选维度的关系 | 证据状态 |
| --- | --- | --- | --- | --- |
| DREAM: Deep Research Evaluation with Agentic Metrics | 论文；agentic evaluation framework | [2026-02-21](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152) | Citation Integrity、Citation Faithfulness、Factuality、Key-Information Coverage；不含已核验的 fault-recovery 指标。[原始论文](https://arxiv.org/html/2602.18940v1) | `verified` |
| LiveResearchBench: A Live Benchmark for User-Centric Deep Research in the Wild | 论文；benchmark；dataset；开源 repository | [2025-10-16](https://export.arxiv.org/api/query?id_list=2510.14240) | Coverage、Citation Accuracy、Citation Association；repository 支持中断后继续评分，但这不是对 DRA fault recovery 的评测。[原始论文](https://arxiv.org/html/2510.14240v1) | `verified` |
| Improving and Evaluating Open Deep Research Agents | 论文；benchmark adaptation；open-source agent improvement | [2025-08-13](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152) | 标题与主题相关，但首次发布早于窗口起点；2026-01-08 是更新日期，不改变排除结论。[arXiv abstract](https://arxiv.org/abs/2508.10152) | `verified` |

DREAM 的 arXiv 官方元数据给出的首次发布时间为 2026-02-21T19:14:31Z，位于要求窗口内。[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152) `published` 字段，`arxiv:2602.18940v1`。

LiveResearchBench 的 arXiv 官方元数据给出的首次发布时间为 2025-10-16T02:49:16Z，也位于窗口内。[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2510.14240) `published` 字段，`arxiv:2510.14240v1`。

# 范围与方法

目标读者是需要机器验收研究过程的人，以及需要复核来源的 Deep Research Agent 研究人员。截止日为 2026-08-26；纳入标准是工作首次发布于 2025-08-26 至 2026-08-26，且属于论文、评测集、benchmark 或开源实现，并实质涉及 source coverage、evidence faithfulness、citation correctness 或 fault recovery 中至少一个相邻维度。

关键概念按以下边界使用：`citation faithfulness` 指引用来源是否支持相邻主张；`citation correctness` 是更宽的引用正确性概念；`Key-Information Coverage` 或 checklist coverage 指报告是否覆盖必要内容，不自动等同于检索来源的 `source coverage`；`fault recovery` 指 agent 在工具、检索或执行故障后恢复任务的能力，不把评测代码的断点续跑机制混入该概念。

研究首先按 Skill 指定的 Exa date-filtered source-first 路线检索。该路线失败后，依据结构化错误恢复规则，依次尝试显式学术与 broad discovery 路线；没有重试已经失败的 provider，也没有使用复合 `research`。Broad discovery 只用于生成候选 URL；随后通过 `fetch` 打开 arXiv 原始论文、arXiv 官方 API、Hugging Face 官方 dataset page 与 GitHub 官方 repository page。只有这些直接来源支持的 Claim 才标记为 `verified`。

# 关键发现

## DREAM

DREAM 把 Deep Research Evaluation 分成 Presentation Quality、Task Compliance、Analytical Depth 与 Source Quality 四个 vertical，并采用 tool-calling agent 创建或执行部分评测协议。其静态指标包括 Writing Quality、Factuality、Citation Integrity 与 Domain Authoritativeness；自适应指标包括 Key-Information Coverage 与 Reasoning Quality。[DREAM 原始论文](https://arxiv.org/html/2602.18940v1) §2 表 1、§3 “Static Metrics” 与 “Adaptive Metrics”。

DREAM 的 Citation Integrity 是 Claim Attribution 与 Citation Faithfulness 的调和平均；Citation Faithfulness 会读取每条引用 URL 的内容并判断其是否支持对应 Claim。Factuality 则独立于给定引用检索外部证据，以检测“引用与错误主张彼此对齐、但主张在现实中仍为假”的情况。[DREAM 原始论文](https://arxiv.org/html/2602.18940v1) §3 “Workflow Evaluator”、Appendix C.3、§4.4。

DREAM 的 Key-Information Coverage 由 agent 检索最新来源，将必要事实转成可核验的 yes/no 问题，再检查报告是否覆盖这些事实。因此它是 query-specific information coverage，而不是对候选来源空间覆盖程度的直接测量。[DREAM 原始论文](https://arxiv.org/html/2602.18940v1) §3 “Adaptive Metrics”、Appendix C.5。

论文还对 DeepResearch Bench、LiveResearchBench 与 ResearchRubrics 上的三个开源 DRA 进行统一评测，并指出这些系统的 Citation Integrity 普遍较低。这是论文中的实验结论，不应外推为所有 Deep Research Agent 的总体性质。[DREAM 原始论文](https://arxiv.org/html/2602.18940v1) §5 “Benchmarking Leading DRAs”、Figures 8–9。

## LiveResearchBench

LiveResearchBench 提供 100 个专家策划、要求实时网页检索和多源综合的任务，并用 DeepEval 评估 coverage、presentation、citation accuracy and association、consistency 与 analysis depth；论文报告对 17 个 frontier deep research systems 进行了评估。[LiveResearchBench 原始论文](https://arxiv.org/html/2510.14240v1) Abstract。

官方 dataset page 明确给出 `question_with_checklist` 与 `question_only` 两个 subset，并展示每个问题的 checklist 用于 coverage evaluation；它还链接原始论文与官方源码仓库。[LiveResearchBench dataset](https://huggingface.co/datasets/Salesforce/LiveResearchBench) “Dataset Overview”、“Dataset Fields” 与 “Quick Links”。

官方 repository 包含 `liveresearchbench`、`configs`、`data/reference_reports`、`scripts` 与 `tests` 等实现表面，并在 README 中说明评分结果按 criterion 增量保存，重新运行时自动加载未完成状态继续评分。[LiveResearchBench repository](https://github.com/SalesforceAIResearch/LiveResearchBench) repository tree 与 README 的 incremental grading / resume grading 说明。

上述断点续评属于 evaluator implementation 的运行恢复能力。当前直接来源没有把工具故障、检索失败或执行中断后的 DRA 恢复行为定义成 benchmark 指标，因此不能据此声称 LiveResearchBench 评估 `fault recovery`。[LiveResearchBench repository](https://github.com/SalesforceAIResearch/LiveResearchBench) README 的 grading recovery 说明；[LiveResearchBench 原始论文](https://arxiv.org/html/2510.14240v1) Abstract 所列 DeepEval 维度。

## 排除项

“Improving and Evaluating Open Deep Research Agents”提出 BrowseComp-Small，并改进 Open Deep Research 得到 ODR+；它与开源 DRA 和 benchmark 高度相关。[arXiv abstract page](https://arxiv.org/abs/2508.10152) 标题与 bibliographic metadata；[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152) abstract。

但其首次发布时间是 2025-08-13T19:32:01Z，早于窗口起点 2025-08-26。arXiv 当前版本更新时间为 2026-01-08T17:54:58Z；更新时间不能替代首次发布时间，因此本报告不把它列为窗口内成果。[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152) `published` 与 `updated` 字段，`arxiv:2508.10152v2`。

# 来源核验与证据状态

| Claim | 状态 | 直接来源与 locator |
| --- | --- | --- |
| DREAM 首次发布于 2026-02-21 | `verified` | [arXiv API](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152)，`arxiv:2602.18940v1` 的 `published` 字段 |
| DREAM 定义 Citation Integrity、Citation Faithfulness、Factuality、KIC | `verified` | [DREAM 原始论文](https://arxiv.org/html/2602.18940v1) §3、Appendix C.3、C.5 |
| DREAM 严格评估 source coverage | `missing` | KIC 评估必要信息覆盖，未发现“来源集合覆盖率”的操作定义 |
| DREAM 评估 DRA fault recovery | `missing` | 已核验指标与实验章节未见该评测维度 |
| LiveResearchBench 首次发布于 2025-10-16 | `verified` | [arXiv API](https://export.arxiv.org/api/query?id_list=2510.14240)，`arxiv:2510.14240v1` 的 `published` 字段 |
| LiveResearchBench 评估 coverage 与 citation accuracy/association | `verified` | [原始论文](https://arxiv.org/html/2510.14240v1) Abstract；[dataset page](https://huggingface.co/datasets/Salesforce/LiveResearchBench) “Dataset Overview / Fields” |
| LiveResearchBench 有公开 dataset 与 source repository | `verified` | [Hugging Face dataset](https://huggingface.co/datasets/Salesforce/LiveResearchBench) “Quick Links”；[GitHub repository](https://github.com/SalesforceAIResearch/LiveResearchBench) tree / README |
| LiveResearchBench repository 可从增量结果继续评分 | `verified` | [GitHub README](https://github.com/SalesforceAIResearch/LiveResearchBench) 的 incremental grading / resume grading 说明 |
| LiveResearchBench 将 fault recovery 作为 DRA 指标 | `missing` | repository 的恢复机制属于 evaluator implementation，论文所列 DeepEval 维度不含该项 |
| Improving and Evaluating Open Deep Research Agents 首次发布于 2025-08-13，因此早于窗口起点 | `verified` | [arXiv API](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152)：`published=2025-08-13T19:32:01Z` |

# 限制

本次检索不是该时间窗的穷尽性系统综述。首选 Exa discovery 因公开的 provider billing 错误失败；Sciverse 的两个文档化筛选字段与服务端 schema 不一致；Zhipu 路线未配置。可用 broad discovery 返回三个候选，其中两个 URL 实际指向同一 DREAM 论文，另一个为窗口外论文。因而“当前确认两项”只表示本次安全路线取得并直接核验的集合，不表示窗口内绝对只有两项。

没有找到可直接核验、且在窗口内首次发布、专门把 DRA `fault recovery` 作为评测维度的工作。也没有找到对 `source coverage` 作严格来源集合覆盖率定义的入选工作。相关结论均保持为 `missing`，没有从相邻指标外推。

# 观察到的错误与恢复附录

1. Exa source-first 请求返回 `provider_error`，公开消息为 HTTP 402 / `payment_required`。依据 Exa channel 规则，不重试 Exa，改走显式学术路线。
2. Sciverse 首次请求返回 `parameter_error`，服务端拒绝 `year_from` 与 `year_to`（`extra_forbidden`）。按规则仅移除被拒字段，并把日期窗口保留在 query 中，提交一次修正请求。
3. 修正后的 Sciverse 请求又返回 `parameter_error`，服务端拒绝 `sort_by_year`（`extra_forbidden`）。因一次修正预算已用完，停止该 provider。
4. Zhipu explicit broad discovery 在网络请求前返回 `config_error`，原因是 provider 未配置。没有重试，也没有修改配置。
5. 主 `search` broad discovery 成功，`logical_attempts=1`、`logical_retry_used=false`。其 main answer 声称没有联网能力，但同一 JSON 的 `extra_sources` 与 `provider_attempts` 显示 Tavily / Firecrawl 返回候选。故忽略自相矛盾的 synthesis，只使用候选 URL，并通过后续 `fetch` 核验。
6. `doctor` 未被 structured recovery 要求，因此调用次数为 0。

# References

1. Ben Avraham, E. et al. “DREAM: Deep Research Evaluation with Agentic Metrics.” arXiv:2602.18940. [原始论文](https://arxiv.org/html/2602.18940v1)；[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152)。
2. Wang, J. et al. “LiveResearchBench: A Live Benchmark for User-Centric Deep Research in the Wild.” arXiv:2510.14240. [原始论文](https://arxiv.org/html/2510.14240v1)；[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2510.14240)。
3. Salesforce AI Research. “LiveResearchBench.” [Hugging Face dataset](https://huggingface.co/datasets/Salesforce/LiveResearchBench)；[GitHub repository](https://github.com/SalesforceAIResearch/LiveResearchBench)。
4. Allabadi, D., Bradbury, K., and Malof, J. “Improving and Evaluating Open Deep Research Agents.” arXiv:2508.10152. [arXiv abstract page](https://arxiv.org/abs/2508.10152)；[arXiv API metadata](https://export.arxiv.org/api/query?id_list=2602.18940,2508.10152)。仅用于说明时间窗排除。

# Execution Summary

- 执行了 1 次 Exa source-first discovery、2 次 Sciverse 显式学术请求（原请求与规程允许的一次修正）、1 次 Zhipu explicit broad discovery、1 次带规定 timeout / max-try 的 broad `search`，以及 8 次已知 URL `fetch`。
- Broad `search` 成功且只发生 1 个 logical attempt；没有 Agent 层重试循环，没有进入复合 `research`，没有调用 doctor。
- 直接核验表面包括 arXiv HTML、arXiv official API、Hugging Face dataset page 与 GitHub repository page。
- `native_web_used=false`；没有使用浏览器、curl、wget、其他联网 Skill 或裸 `smart-search`。
