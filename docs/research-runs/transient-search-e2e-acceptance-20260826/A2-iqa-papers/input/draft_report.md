# 2026-07-28 至 2026-08-26 新发布 Image Quality Assessment 论文核验

## 结论

按 arXiv 官方 Atom 记录的 `published` 字段判定首次 arXiv 公开日期，本次在 2026-07-28 至 2026-08-26 的窗口内确认了 11 项与静态图像质量评估直接相关或紧邻的工作。[cite:a2-window-record]

最值得继续跟进的是三条不同的路线：`SciFigQual-Bench` 将全文上下文、模态证据收集与融合引入科学图表质量评测，属于明确的 agentic/workflow 型 IQA；[cite:a2-scifigqual] `MR-IQA-2` 以 actor–editor–judge 组织 reasoning–editing–reflection，属于多组件、多阶段的视觉反思；[cite:a2-mriqa2] LGE-MRI 工作把 VLM 质量报告与 GPT 临床可用性判断串成两阶段流程，属于 multi-stage clinical IQA。[cite:a2-lge-mri] 这三项都不能仅凭“有多个组件”被统称为 `multi-agent`。[cite:a2-scifigqual] [cite:a2-mriqa2] [cite:a2-lge-mri]

在给定检索预算和来源范围内，没有核验到一篇首次发布于该窗口、且原文明确自称 `multi-agent IQA` 的新论文；因此这里把 `agentic`、`workflow`、`multi-stage` 与 `multi-agent` 分开使用，而不把相邻概念合并成一个标签。[cite:a2-window-record]

## 范围、日期口径与证据状态

- 时间范围为 2026-07-28 00:00:00 至 2026-08-26（Asia/Shanghai 截止）；日期比较采用 arXiv `published` 的 UTC 日期，不采用 `updated` 作为首次公开日期。
- 纳入论文的主要研究对象必须包含静态图像的质量、保真度、感知偏好、缺陷/可用性评估，或服务于这些对象的 benchmark、dataset、metric、judge 或 assessment framework。
- 排除纯 Video Quality Assessment；只把 PSNR/SSIM 等作为下游指标的生成或恢复论文；以及首次发布早于窗口、但在窗口内更新的论文。
- “首次公开”在本文只证明“首次 arXiv 提交”。作者主页、会议网站、社交媒体或代码仓库是否曾更早公开，没有逐项建立全球最早事件链，因而这一更强主张保持 `unverified`。
- 标为 `verified` 的内容限于保存的 arXiv 官方摘要页或 Atom entry 能直接支持的题名、`published` 日期、研究对象和摘要级方法；全文实验设计、统计有效性、代码复现性和 SOTA 主张不在本轮核验范围。没有直接证据的 multi-agent 结论标为 `missing`，而不是把搜索摘要当成正面证据。[cite:a2-window-record]

本文的概念边界是：`agentic` 强调模型能否按任务需要规划、调用工具或组织证据；`workflow` 强调这些动作形成了可描述的处理流程；`multi-stage` 只表示存在明确串联的阶段；`multi-agent` 则要求原文明确以多个协作 agent 组织 IQA。因而一个 staged workflow 不自动等于 multi-agent。[cite:a2-window-record]

## 窗口内优先方向

### Agentic、workflow 与 multi-stage IQA

- **[SciFigQual-Bench: A Benchmark for Scientific Figure Quality Assessment with Full-Manuscript Context](https://arxiv.org/abs/2607.27084)（2026-07-29）**：面向带 caption、引用句和全文上下文的科学图表质量，评估 clarity、layout、caption fit、context relevance 和 misleading risk；数据包含 6,308 幅图，由领域专家在五个维度上评分并聚合为 gold-standard annotations。论文提出 staged cross-modal `SFQ-Agent`，通过收集和融合模态证据进行可审计、可细化的评分。[cite:a2-scifigqual] 这里的“agentic”描述证据组织和评测流程，原文摘要没有提供足以把它改称为 multi-agent 的依据。[cite:a2-scifigqual]

- **[MR-IQA-2: Faithful Image Quality Reflection via Fine-Grained Credit Assignment](https://arxiv.org/abs/2608.18579)（2026-08-19）**：针对 blind IQA 中“评分正确但推理未必忠实”的问题，提出 actor–editor–judge 框架。actor 为输入图像生成质量推理，editor 按识别出的质量因素编辑图像，冻结的 judge 比较原图与编辑图并为 actor 的推理提供反思监督；fine-grained credit assignment 将 reasoning 与 rating 的监督信号解耦。[cite:a2-mriqa2] 这是一种 multi-component、multi-stage visual reflection，不应直接标成 multi-agent。[cite:a2-mriqa2]

- **[Toward Vision Language Model-based Assessment of Clinical Quality and Usability of LGE-MR Images for Cardiac Ablation Planning](https://arxiv.org/abs/2608.21180)（2026-08-21）**：针对左心房 LGE-MRI 的图像质量及其是否足以支持心房颤动消融规划，第一阶段由 fine-tuned VLM 生成五项 radiology-style 质量报告，第二阶段由 GPT-based reasoning module 映射为结构化质量分数和临床可用性二分类。论文使用 20 名患者的 60 个 annotated image slice–text pairs，并报告了四种 VLM 的基准结果。[cite:a2-lge-mri] 这里的关键是清晰的 two-stage clinical IQA 流程，而不是 multi-agent 协作。[cite:a2-lge-mri]

- **[MIEScore: Human-Aligned Evaluation for Multi-Source Image Editing](https://arxiv.org/abs/2608.02059)（2026-08-03）**：面向多源图像编辑结果的 visual quality、instruction following 和 attribute preservation，建立 MIE-Bench，并训练经过 skill optimization 与 multi-dimensional SFT 增强的 MLLM evaluator。摘要给出 3,000 个 editing instances、16 个任务、36K 张编辑图和超过 108K 个 MOS；它是 MLLM-based image-editing quality assessment，但摘要没有表明在线工具调用或多 Agent 协作。[cite:a2-miescore]

## 窗口内其他直接相关工作

- **[Rethinking Clinical Relevance in Chest X-ray Machine Learning: How Evaluation References Define Performance](https://arxiv.org/abs/2607.26333)（2026-07-28）**：研究 pathology classification 与 IQA 中 evaluation reference 的选择如何改变性能估计和模型排序，并指出 SSIM、PSNR 等常用 IQA 指标可能与专家对诊断可用性的判断不一致。它是“评价参考选择”研究，IQA 是核心并行分支而非唯一任务。[cite:a2-cxr]

- **[BlindPSNR: A No-Reference Fidelity Predictor for Low-Light Image Enhancement](https://arxiv.org/abs/2607.27628)（2026-07-30）**：在没有 ground-truth 时预测低光增强结果的 PSNR，用 windowed cross-attention 融合增强图与低光输入，再通过 heteroscedastic regression 估计 PSNR。它明确区分 signal fidelity 与 perceptual NR-IQA，应作为边界型 fidelity assessment 阅读，而不是普通主观 IQA。[cite:a2-blindpsnr]

- **[CBCT-IQ: A Publicly Available Annotated Cone-Beam CT Dataset for Image Quality Assessment and Benchmarking](https://arxiv.org/abs/2607.29253)（2026-07-31）**：发布 1,764 个专家标注的 CBCT 图像切片；三名临床专家用四级量表评价整体质量与 ROI 质量，并将 26 个 full-reference/no-reference IQA measures 与专家标注进行基准比较。[cite:a2-cbct]

- **[Ranking Image Fusion the Way Humans Do: A Learned Pairwise Preference Measure for Infrared-Visible Fusion Assessment](https://arxiv.org/abs/2608.01301)（2026-08-02）**：`LPIFM` 同时观察两幅源图和两个融合候选，预测 A、B 或 Tie；监督数据覆盖 VIFB 的 21 个场景、25 个 fusion methods 的全部 6,300 个无序比较。Atom 当前记录的 `updated` 为 2026-08-07，但 `published` 仍是 2026-08-02，因此按首次 arXiv 日期纳入窗口。[cite:a2-lpifm]

- **[Estimating SSIM from MSE for DCT-Based Compressed Images via Modeling Local Error Statistics](https://arxiv.org/abs/2608.02549)（2026-08-03）**：在 DCT 压缩图像中，用 reference image 的 local statistics 将 global MSE 按 variance 或 standard-deviation weighting 重分配，从而近似 local MSE 和 SSIM。Atom 的 `updated` 为 2026-08-19，`published` 为 2026-08-03。[cite:a2-ssim]

- **[A Subjective Study on a New Sharpness Informed Class of Metrics](https://arxiv.org/abs/2608.13989)（2026-08-14）**：通过四协议主观实验研究去模糊结果的锐度偏好与过度锐化惩罚，提出带 DMOS 数据的 Sharpness Informed IQA metrics，包括 SI-PSNR；摘要报告 sharpness-aware loss 的图像在二值比较中平均有 67% 获得偏好。[cite:a2-sharpness]

- **[AGIDefect-4K: A Richly Annotated Dataset for AI-Generated Image Defect Detection, Localization and Explanation](https://arxiv.org/abs/2608.20713)（2026-08-21）**：提供来自 15 个生成模型的 4,000 张图像，包含 defect detection labels、pixel-level masks、文本解释和 overall quality score，并提出基于 MLLM 的 `AGIDA`，联合完成缺陷检测、定位、解释和质量预测。它与 AIGC-IQA 高度相关，但标题和任务设计更偏向 defect diagnosis。[cite:a2-agidefect]

## 窗口外但值得保留的背景

- **[AgenticIQA: An Agentic Framework for Adaptive and Interpretable Image Quality Assessment](https://arxiv.org/abs/2509.26006)** 首次 arXiv 日期为 2025-09-30；它把 IQA 拆成 distortion detection、distortion analysis、tool selection 和 tool execution，由 planner、executor、summarizer 协调，是 agentic IQA 的直接邻近工作，但早于窗口。[cite:a2-agenticiqa]

- **[MUSE: A Unified Agentic Harness for MLLMs](https://arxiv.org/abs/2606.03005)** 首次 arXiv 日期为 2026-06-02；它用可组合模块封装现成 MLLM，覆盖 task representation、visual processing、perception tool use、structured parsing、deterministic verification 和 verifier-guided repair，且不重新训练模型。它是通用 agentic harness，不是窗口内的新 IQA 论文。[cite:a2-muse]

- **[Tool-IQA: Augmenting Image Quality Assessment with Simple Tools](https://arxiv.org/abs/2606.16082)** 首次 arXiv 日期为 2026-06-15；它用 Magnifier 检查局部细节、用 Gamma Corrector 暴露可见性和隐藏伪影，并将 IQA 改写为 observation、tool-assisted inspection、final quantification 的 tool-augmented workflow。[cite:a2-tooliqa]

- **[IQA-T1: Tool-based Visual Evidence Reasoning for Image Quality Assessment](https://arxiv.org/abs/2607.12375)** 首次 arXiv 日期为 2026-07-14；它让 MLLM 调用分析工具生成 noise residual maps、gradient statistics 和 frequency spectra 等结构化视觉证据，并用 Q-Tool 保存 11k 条基于工具证据的多模态推理链。它早于窗口起点，不纳入窗口清单。[cite:a2-iqat1]

## 错误候选与证据边界

保存的 [fresh search 材料](../search-materials/commands/fresh-search-after-499.json) 曾生成“AGENT-IQA: An Agentic Multi-Agent Collaborative Workflow for No-Reference Image Quality Assessment”，但对应的 arXiv:2608.04567 官方记录实际是 **[STRIVE: Probing Reasoning Limits in Graded Plausibility Generation and Evaluation](https://arxiv.org/abs/2608.04567)**，属于 Computation and Language，不是 IQA 论文；因此该候选已剔除，不能作为 multi-agent IQA 证据。[cite:a2-strive]

本报告只把保存的 arXiv 官方摘要页和 Atom entry 中能直接回读的题名、日期、研究对象及摘要级方法标为 `verified`。搜索结果摘要只能作为候选线索；窗口外工作的排除日期是 `verified`，作者主页或会议网站是否更早公开属于 `unverified`，窗口内明确 self-described multi-agent IQA 的直接证据属于 `missing`。[cite:a2-window-record]

摘要级证据不能替代全文审查：本报告没有把摘要中的性能宣称扩写成 SOTA 结论，也没有审查实验设计、统计有效性或代码可复现性。`SciFigQual-Bench`、`AGIDefect-4K` 和 `MIEScore` 扩展了传统自然图像 IQA 的对象边界，分别对应 scientific figures、AIGC defects 和 image-editing assessment；主要针对 video/codec quality 的工作，以及只把 IQA 指标作为下游指标的 restoration/generation 论文，仍按排除规则处理。[cite:a2-window-record]

## 验收恢复附录

本地 acceptance 的 [broad search 记录](../search-materials/commands/broad-search.json) 曾返回 HTTP 499 `request_cancelled`；随后按恢复规则执行了单次 [doctor probe](../search-materials/commands/doctor.json) 和一次 fresh search，doctor 结果报告接口可用。两次 Exa 并发启动还触发了本地“parallel Smart Search invocations are not permitted”约束，后续记录改为串行；这些是执行路径事实，不是论文证据。fresh search 产生的无来源 AGENT-IQA 文本已由上面的官方 arXiv 记录纠正并排除。[cite:a2-strive]
