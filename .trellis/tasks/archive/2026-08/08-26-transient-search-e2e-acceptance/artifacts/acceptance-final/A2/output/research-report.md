# 2026-07-28 至 2026-08-26 新发布 Image Quality Assessment 论文核验

## 结论

按 arXiv 官方 Atom 记录的 `published` 字段定义“首次公开日期”，本次检索确认时间窗内有 11 项与静态图像质量评估直接相关或紧邻的工作。最值得 Agentic IQA 研究继续跟进的是三项：`SciFigQual-Bench` 用 staged cross-modal `SFQ-Agent` 汇集并融合多模态证据；`MR-IQA-2` 采用 actor–editor–judge 的 reasoning–editing–reflection；LGE-MRI 工作将 VLM 质量报告与 GPT 临床可用性判断串成两阶段流程。它们分别代表 agent 化评测、多组件视觉反思和 multi-stage 临床 IQA，但原文没有足够依据把三者统称为“multi-agent”。[SciFigQual-Bench](https://arxiv.org/abs/2607.27084) [MR-IQA-2](https://arxiv.org/abs/2608.18579) [LGE-MRI IQA](https://arxiv.org/abs/2608.21180)

在该时间窗内，没有核验到一篇原文明确自称 multi-agent IQA 的新论文。最贴近该方向的 `AgenticIQA`、`MUSE`、`Tool-IQA` 和 `IQA-T1` 首次 arXiv 日期分别为 2025-09-30、2026-06-02、2026-06-15 和 2026-07-14，均早于窗口起点；不能因为近期更新或当前检索命中而纳入。[AgenticIQA](https://arxiv.org/abs/2509.26006) [MUSE](https://arxiv.org/abs/2606.03005) [Tool-IQA](https://arxiv.org/abs/2606.16082) [IQA-T1](https://arxiv.org/abs/2607.12375)

## 范围与方法

- 目标读者：从事 MLLM、IQA 与 Agentic System 研究、需要可复查选题清单的研究者。
- 时间范围：2026-07-28 00:00:00 至 2026-08-26（Asia/Shanghai 截止；日期判断采用 arXiv `published` 的 UTC 日期）。
- 纳入标准：论文的主要研究对象包含静态图像的质量、保真度、感知偏好、缺陷/可用性评估，或提出用于这些对象的 benchmark、dataset、metric、judge 或 assessment framework。
- 排除标准：只把 PSNR/SSIM 等作为下游指标的生成/恢复论文；纯 Video Quality Assessment；首次发布早于窗口、但在窗口内更新的论文。
- 关键概念：`Image Quality Assessment`、`Agentic IQA`、`tool-augmented`、`multi-stage`、`multi-agent`。本任务未发现项目或全局 termbase 对这些名称作出额外裁决，因此沿用论文英文名称，并用自然中文解释边界。
- 证据流程：先执行一次 broad `search`；失败后严格按 structured recovery 调用一次 `doctor` 和一次 fresh search。随后用 `exa-search` 做候选发现，再用指定启动器的 `fetch` 打开 arXiv 官方摘要页与官方 Atom API。标题、研究对象和方法取自论文摘要；日期取 `published`，不取 `updated`。

“首次公开”在本报告中只证明“首次 arXiv 提交”；是否曾在作者主页、会议网站或代码仓库更早公开，未逐项建立全球最早事件链，因此该更强主张保持 `unverified`。

## 关键发现

### 优先方向：Agentic、workflow、tool-augmented、multi-stage

| 首次 arXiv 日期 | 论文 | 研究对象 | 方法与方向判断 |
| --- | --- | --- | --- |
| 2026-07-29 | [SciFigQual-Bench: A Benchmark for Scientific Figure Quality Assessment with Full-Manuscript Context](https://arxiv.org/abs/2607.27084) | 带 caption、引用句和全文上下文的科学图表质量；维度包括 clarity、layout、caption fit、context relevance、misleading risk | 构建 6,308 图的 benchmark，并提出 staged cross-modal `SFQ-Agent` 收集、融合模态证据后评分。属于本窗口最明确的 agent/workflow 型 IQA。`verified`（arXiv Atom entry 的 `published` 与 `summary`）。 |
| 2026-08-19 | [MR-IQA-2: Faithful Image Quality Reflection via Fine-Grained Credit Assignment](https://arxiv.org/abs/2608.18579) | Blind IQA 中“评分正确但推理未必忠实”的问题 | actor 生成质量推理；editor 按推理编辑图像；frozen judge 比较原图与编辑图，形成视觉反思监督；用 fine-grained credit assignment 分开 reasoning 与 rating 奖励。是 multi-component、multi-stage visual reflection，不把它过度标成 multi-agent。`verified`（arXiv Atom `published`、`summary`）。 |
| 2026-08-21 | [Toward Vision Language Model-based Assessment of Clinical Quality and Usability of LGE-MR Images for Cardiac Ablation Planning](https://arxiv.org/abs/2608.21180) | 左心房 LGE-MRI 的图像质量及其是否足以支持消融规划 | 第一阶段由 fine-tuned VLM 生成五项 radiology-style 质量报告；第二阶段由 GPT reasoning module 生成结构化分数与临床可用性二分类。是明确的 two-stage clinical IQA。`verified`（arXiv Atom `published`、`summary`）。 |
| 2026-08-03 | [MIEScore: Human-Aligned Evaluation for Multi-Source Image Editing](https://arxiv.org/abs/2608.02059) | 多源图像编辑结果的 visual quality、instruction following 与 attribute preservation | 建立 MIE-Bench，并训练经 skill optimization 与 multi-dimensional SFT 增强的 MLLM evaluator。它是 MLLM-based image-editing quality assessment，但摘要未表明在线工具调用或多 Agent 协作。`verified`（arXiv Atom `published`、`summary`）。 |

### 其他窗口内直接相关工作

| 首次 arXiv 日期 | 论文 | 研究对象 | 方法 |
| --- | --- | --- | --- |
| 2026-07-28 | [Rethinking Clinical Relevance in Chest X-ray Machine Learning: How Evaluation References Define Performance](https://arxiv.org/abs/2607.26333) | 胸片分类与重建 IQA 中，不同 reference standard 如何改变性能估计和模型排序 | 收集专家图像/报告标签及诊断质量评分，对分类模型、VLM 与 IQA measures 做受控比较；指出 SSIM、PSNR 与诊断可用性可能不一致。它是“评价参考选择”研究，IQA 是核心并行分支而非唯一任务。`verified`。 |
| 2026-07-30 | [BlindPSNR: A No-Reference Fidelity Predictor for Low-Light Image Enhancement](https://arxiv.org/abs/2607.27628) | 无 ground-truth 时，为低光增强参数选择预测 PSNR | 将增强图与低光输入通过 windowed cross-attention 融合，以 heteroscedastic regression 估计 PSNR。作者明确区分 signal fidelity 与 perceptual NR-IQA，因此应列为边界型 fidelity assessment，而非普通主观 IQA。`verified`。 |
| 2026-07-31 | [CBCT-IQ: A Publicly Available Annotated Cone-Beam CT Dataset for Image Quality Assessment and Benchmarking](https://arxiv.org/abs/2607.29253) | Cone-Beam CT 医学图像质量 | 发布 1,764 个专家标注切片，三名临床专家用四级量表评价整体与 ROI 质量；benchmark 26 个 FR/NR IQA measures，并给出探索性 ranking。`verified`。 |
| 2026-08-02 | [Ranking Image Fusion the Way Humans Do: A Learned Pairwise Preference Measure for Infrared-Visible Fusion Assessment](https://arxiv.org/abs/2608.01301) | 红外—可见光融合结果的相对感知偏好 | LPIFM 同时观察两幅源图和两个融合候选，预测 A/B/Tie；以 dense pairwise preference corpus 学习并复现 tie-aware Bradley–Terry 排序。Atom 当前条目已更新到 v3，但 `published` 是 2026-08-02，不能把 2026-08-07 的 `updated` 当首次日期。`verified`。 |
| 2026-08-03 | [Estimating SSIM from MSE for DCT-Based Compressed Images via Modeling Local Error Statistics](https://arxiv.org/abs/2608.02549) | DCT 压缩图像中低成本近似 SSIM | 用参考图的局部 variance 或 standard deviation 将 global MSE 重分配为近似 local MSE，再估计 SSIM。Atom `updated` 为 2026-08-19，`published` 为 2026-08-03。`verified`。 |
| 2026-08-14 | [A Subjective Study on a New Sharpness Informed Class of Metrics](https://arxiv.org/abs/2608.13989) | 去模糊结果的锐度偏好与过度锐化惩罚 | 用四协议主观实验和带 DMOS 的均匀锐度增量数据，提出 Sharpness Informed IQA metrics，包括 SI-PSNR。`verified`。 |
| 2026-08-21 | [AGIDefect-4K: A Richly Annotated Dataset for AI-Generated Image Defect Detection, Localization and Explanation](https://arxiv.org/abs/2608.20713) | AI-generated image 的缺陷存在性、位置、解释与总体质量 | 4,000 图、15 个生成模型，提供 detection label、pixel mask、文本解释和 overall quality score；AGIDA 用 MLLM 联合完成缺陷理解与质量预测。它与 AIGC-IQA 高度相关，但主要标题和任务设计更偏 defect diagnosis。`verified`。 |

### 时间窗外但与优先方向高度相关

`AgenticIQA` 的 planner–executor–summarizer、`MUSE` 的 perception tools + verifier-guided repair、`Tool-IQA` 的 Magnifier/Gamma Corrector workflow，以及 `IQA-T1` 的 tool-generated visual evidence 都是优先方向的关键邻近工作；其首次 arXiv 日期分别为 2025-09-30、2026-06-02、2026-06-15、2026-07-14，所以本轮只作背景，不纳入窗口清单。[AgenticIQA](https://arxiv.org/abs/2509.26006) [MUSE](https://arxiv.org/abs/2606.03005) [Tool-IQA](https://arxiv.org/abs/2606.16082) [IQA-T1](https://arxiv.org/abs/2607.12375)

fresh search 曾生成“AGENT-IQA: An Agentic Multi-Agent Collaborative Workflow for No-Reference Image Quality Assessment，arXiv:2608.04567”的无来源答案。打开 arXiv 官方记录后，2608.04567 实际是 NLP 论文 `STRIVE: Probing Reasoning Limits in Graded Plausibility Generation and Evaluation`；该候选已否决，不能引用为 IQA 论文。[arXiv:2608.04567](https://arxiv.org/abs/2608.04567)

## 来源核验与证据状态

- `verified`：上表 11 项的题名、`published` 日期、研究对象和摘要级方法均从 arXiv 官方摘要页或 Atom entry 回读；LPIFM 与 SSIM-from-MSE 的首次日期专门按 `published` 与 `updated` 分离。
- `verified`：四项窗口外邻近工作及错误候选 2608.04567 均由 arXiv 官方 Atom entry 核验，不依赖搜索摘要。
- `unverified`：各论文在 arXiv 之前是否有作者主页、会议页面、社交媒体或仓库的更早公开事件。本报告不把“首次 arXiv 提交”扩大成“全球首次宣布”。
- `missing`：在给定检索预算和来源范围内，没有找到并直接核验一篇首次发布于窗口内、且原文明确自称 multi-agent IQA 的论文。

可回读 locator：`output/commands/fetch-arxiv-api-candidates.json`、`fetch-arxiv-api-secondary.json` 与 `fetch-arxiv-api-agentic-outside-window.json` 中各 entry 的 canonical `id`、`title`、`updated`、`summary`、`published`、`author`；各 `fetch-<paper>.json` 中的 arXiv title、subjects、cite-as 与 submission-history heading。

## 限制

1. 检索以 arXiv、OpenReview 候选发现和 arXiv 直接核验为主，没有覆盖所有出版社、会议 program、作者主页和代码仓库，因此不是全网穷尽性系统综述。
2. arXiv 摘要足以核验题名、日期、研究对象与方法主干，但不能替代阅读全文后的实验设计、统计有效性、代码可复现性或 SOTA 主张审查；本报告没有把摘要中的性能宣称扩写成结论。
3. `SciFigQual-Bench`、`AGIDefect-4K`、`MIEScore` 扩展了传统自然图像 IQA 的对象边界；已在表中明确其 scientific figures、AIGC defects、image-editing assessment 语境。
4. `CamWorldQA` 与 `CodecArena` 主要是 video/codec quality assessment，故未纳入静态图像清单；仅使用 IQA 指标的 restoration/generation 论文同样排除。

## 观察到的错误与恢复附录

1. broad `search` 返回 `ok:false`、`error_type:request_cancelled`、HTTP 499；`logical_attempts:1`、`fallback_used:false`，structured recovery 标记 `safe_to_replay:false`，要求等待 30 秒、确认无结果、最多调用一次 `doctor`，再在仍有需要时发起一次 fresh search。
2. 实际恢复：等待超过 30 秒；读取 `references/error-recovery.md`；用指定启动器调用一次 `doctor`，结果 `ok:true`；随后只发起一次改写后的 fresh search，结果 `ok:true`。
3. fresh search 的内容没有任何 source（`sources_count:0`），并合成了错误的 AGENT-IQA 条目。后续 `fetch` 官方 arXiv 记录证实 ID 2608.04567 属于 STRIVE，因此将该内容质量问题记录并剔除。
4. 两个 `exa-search` 曾因我尝试并发启动而被本地约束拒绝，公开错误为 `parallel Smart Search invocations are not permitted`。之后所有 Smart Search 命令均改为串行；没有对 provider 建立外层重试循环。
5. `doctor_calls` 总数为 1；未调用 native web、浏览器、直接 HTTP、`curl` 或 `wget`。

## References

1. Fytas et al. [Rethinking Clinical Relevance in Chest X-ray Machine Learning](https://arxiv.org/abs/2607.26333). arXiv:2607.26333.
2. Deng et al. [SciFigQual-Bench](https://arxiv.org/abs/2607.27084). arXiv:2607.27084.
3. Lyu et al. [BlindPSNR](https://arxiv.org/abs/2607.27628). arXiv:2607.27628.
4. Hatamikia et al. [CBCT-IQ](https://arxiv.org/abs/2607.29253). arXiv:2607.29253.
5. Liu et al. [Ranking Image Fusion the Way Humans Do](https://arxiv.org/abs/2608.01301). arXiv:2608.01301.
6. Xu et al. [MIEScore](https://arxiv.org/abs/2608.02059). arXiv:2608.02059.
7. Trudeau and Martini. [Estimating SSIM from MSE for DCT-Based Compressed Images](https://arxiv.org/abs/2608.02549). arXiv:2608.02549.
8. Aurangabadkar et al. [A Subjective Study on a New Sharpness Informed Class of Metrics](https://arxiv.org/abs/2608.13989). arXiv:2608.13989.
9. Li et al. [MR-IQA-2](https://arxiv.org/abs/2608.18579). arXiv:2608.18579.
10. Kundu et al. [Toward Vision Language Model-based Assessment of Clinical Quality and Usability of LGE-MR Images](https://arxiv.org/abs/2608.21180). arXiv:2608.21180.
11. Sheng et al. [AGIDefect-4K](https://arxiv.org/abs/2608.20713). arXiv:2608.20713.
12. Zhu et al. [AgenticIQA](https://arxiv.org/abs/2509.26006). arXiv:2509.26006.（窗口外背景）
13. Lu et al. [MUSE](https://arxiv.org/abs/2606.03005). arXiv:2606.03005.（窗口外背景）
14. Qin et al. [Tool-IQA](https://arxiv.org/abs/2606.16082). arXiv:2606.16082.（窗口外背景）
15. Wu et al. [IQA-T1](https://arxiv.org/abs/2607.12375). arXiv:2607.12375.（窗口外背景）

## Execution Summary

- 使用 `language-system` Writing mode 建立读者、范围、关键概念、Claim 与证据状态；全局术语查询对五个关键概念均无命中，因此未创建术语候选或修改任何术语库。
- 所有联网动作均通过指定启动器完成；保留 27 个 JSON 命令产物，其中包括 2 个 main search、9 个成功的 Exa discovery、1 个 doctor 与 15 个 fetch/direct-source 记录。
- 交付状态：研究答案完成；11 项窗口内工作已按首次 arXiv `published` 日期核验；1 个合成候选被直接来源证伪；仓库代码与已有 dirty worktree 均未修改。
