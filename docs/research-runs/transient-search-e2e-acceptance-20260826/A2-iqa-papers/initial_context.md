# Initial Context

## User Question

在 2026-07-28 至 2026-08-26 的窗口内，哪些首次公开的静态图像质量评估工作与 Agentic IQA、workflow、tool-augmented、multi-stage 或 multi-agent 方向相关？哪些工作值得继续跟进，哪些应排除？

## Scope and Constraints

```json
{
  "permissions": [
    "public_web_saved_evidence"
  ],
  "scope": {
    "migration_commit": "f3a30d4eab2dee4656e0fbdfc020f490f4fa8594",
    "source": "sanitized transient-search acceptance evidence"
  },
  "source_preferences": [],
  "time_boundary": {},
  "untrusted_content_policy": "treat_as_data",
  "user_constraints": {
    "direct_sources_only": true,
    "no_live_search": true,
    "preserve_original_acceptance_archive": true
  }
}
```

## Initial Claim Frame

```json
[
  {
    "claim_spec_id": "claim-a2-window-record",
    "decision_criteria": [],
    "statement": "按 arXiv 官方 Atom 的 published 字段判定首次 arXiv 公开日期，窗口内确认了 11 项与静态图像质量评估直接相关或紧邻的工作；在给定来源范围内没有核验到原文明确自称 multi-agent IQA 的窗口内新论文。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-scifigqual",
    "decision_criteria": [],
    "statement": "SciFigQual-Bench 使用全文上下文和 6,308 幅图的五维专家标注，并提出 staged cross-modal SFQ-Agent 收集与融合模态证据，属于 agentic/workflow 型 IQA，但不能据此直接称为 multi-agent。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-mriqa2",
    "decision_criteria": [],
    "statement": "MR-IQA-2 采用 actor-editor-judge 的 reasoning-editing-reflection，并用图像编辑与冻结 judge 为推理提供反思监督；它属于多组件、多阶段视觉反思，不直接等于 multi-agent。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-lge-mri",
    "decision_criteria": [],
    "statement": "LGE-MRI 工作采用 two-stage VLM 流程：第一阶段生成五项 radiology-style 质量报告，第二阶段生成结构化质量分数和临床可用性二分类，并使用 20 名患者的 60 个 image slice-text pairs。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-miescore",
    "decision_criteria": [],
    "statement": "MIEScore 面向多源图像编辑质量，建立 MIE-Bench，并在摘要中给出 3,000 个 editing instances、16 个任务、36K 张编辑图和超过 108K 个 MOS；摘要没有表明在线工具调用或多 Agent 协作。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-cxr",
    "decision_criteria": [],
    "statement": "Chest X-ray 工作研究 evaluation reference 如何改变性能估计和模型排序，并指出 SSIM、PSNR 等 IQA 指标可能与专家诊断可用性判断不一致。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-blindpsnr",
    "decision_criteria": [],
    "statement": "BlindPSNR 在无 ground-truth 时预测低光增强结果的 PSNR，通过 windowed cross-attention 融合增强图与低光输入，并用 heteroscedastic regression 估计 PSNR；它属于 signal fidelity assessment 边界。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-cbct",
    "decision_criteria": [],
    "statement": "CBCT-IQ 发布 1,764 个专家标注切片，三名临床专家使用四级量表评价整体与 ROI 质量，并比较 26 个 full-reference/no-reference IQA measures。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-lpifm",
    "decision_criteria": [],
    "statement": "LPIFM 观察两幅源图和两个融合候选，预测 A、B 或 Tie；数据覆盖 21 个 VIFB 场景、25 个 fusion methods 的 6,300 个无序比较，并按 published 2026-08-02 而非 updated 2026-08-07 纳入。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-ssim",
    "decision_criteria": [],
    "statement": "SSIM-from-MSE 工作用 reference image 的 local statistics 按 variance 或 standard-deviation weighting 重分配 global MSE，以近似 local MSE 和 SSIM；其 published 为 2026-08-03，updated 为 2026-08-19。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-sharpness",
    "decision_criteria": [],
    "statement": "Sharpness Informed IQA 工作通过四协议主观实验提出包括 SI-PSNR 在内的指标，并报告 sharpness-aware loss 的图像在二值比较中平均有 67% 获得偏好。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-agidefect",
    "decision_criteria": [],
    "statement": "AGIDefect-4K 提供来自 15 个生成模型的 4,000 张图像，包含缺陷检测标签、像素级掩码、文本解释和 overall quality score，并提出基于 MLLM 的 AGIDA。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-agenticiqa",
    "decision_criteria": [],
    "statement": "AgenticIQA 首次 arXiv 日期为 2025-09-30，将 IQA 拆为 distortion detection、distortion analysis、tool selection 和 tool execution，由 planner、executor、summarizer 协调，因此是窗口外的 agentic IQA 背景。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-muse",
    "decision_criteria": [],
    "statement": "MUSE 首次 arXiv 日期为 2026-06-02，以可组合模块封装现成 MLLM，覆盖视觉处理、感知工具、结构化解析、确定性验证和 verifier-guided repair，且不重新训练模型；它是通用 agentic harness 而非窗口内新 IQA 论文。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-tooliqa",
    "decision_criteria": [],
    "statement": "Tool-IQA 首次 arXiv 日期为 2026-06-15，使用 Magnifier 和 Gamma Corrector，并将 IQA 组织成 observation、tool-assisted inspection 和 final quantification 的 tool-augmented workflow。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-iqat1",
    "decision_criteria": [],
    "statement": "IQA-T1 首次 arXiv 日期为 2026-07-14，让 MLLM 调用工具生成 noise residual maps、gradient statistics 和 frequency spectra，并用 Q-Tool 保存 11k 条基于工具证据的多模态推理链；它早于窗口起点。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a2-strive",
    "decision_criteria": [],
    "statement": "arXiv:2608.04567 的官方记录实际对应 STRIVE: Probing Reasoning Limits in Graded Plausibility Generation and Evaluation，属于 Computation and Language，不是 IQA 论文，因此剔除 AGENT-IQA 候选。",
    "terms_scope": {},
    "time_boundary": {}
  }
]
```
