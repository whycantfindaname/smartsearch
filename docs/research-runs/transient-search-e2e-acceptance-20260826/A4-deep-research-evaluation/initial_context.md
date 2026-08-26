# Initial Context

## User Question

在 2025-08-26 至 2026-08-26 的首次发布窗口内，哪些论文、评测集、benchmark 或开源实现实质涉及 source coverage、evidence faithfulness、citation correctness 或 fault recovery？请区分 paper、benchmark、dataset 与 repository，并判断直接证据是否真正评估了 source coverage 或 DRA fault recovery。

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
    "claim_spec_id": "claim-a4-dream-date",
    "decision_criteria": [],
    "statement": "DREAM: Deep Research Evaluation with Agentic Metrics 的首次发布时间为 2026-02-21。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-date",
    "decision_criteria": [],
    "statement": "LiveResearchBench: A Live Benchmark for User-Centric Deep Research in the Wild 的首次发布时间为 2025-10-16。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-metrics-inventory",
    "decision_criteria": [],
    "statement": "DREAM 的 Source Quality 指标包括 Factuality 与 Citation Integrity。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-paper-metrics",
    "decision_criteria": [],
    "statement": "LiveResearchBench 论文提出的 DeepEval 覆盖 coverage、presentation、citation accuracy、citation association、consistency 与 analysis depth，未列出 DRA fault recovery。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-verification-pipelines",
    "decision_criteria": [],
    "statement": "DREAM 的 Citation Integrity 使用 Claim Attribution 与 Citation Faithfulness 的调和平均。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-factuality-independent",
    "decision_criteria": [],
    "statement": "DREAM 的 Factuality 独立于给定引用检索外部证据。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-kic-boundary",
    "decision_criteria": [],
    "statement": "DREAM 的 Key-Information Coverage 将关键点转成时效性的 yes/no checklist，用于发现遗漏或过时内容，而不是测量来源集合覆盖率。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-taxonomy",
    "decision_criteria": [],
    "statement": "DREAM 将 Deep Research Evaluation 组织为 Presentation Quality、Task Compliance、Analytical Depth 与 Source Quality 四个 vertical。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-framework",
    "decision_criteria": [],
    "statement": "DREAM 把评测本身做成具有工具调用能力的 agentic framework。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-static-metrics",
    "decision_criteria": [],
    "statement": "DREAM 的静态指标包括 Writing Quality、Factuality、Citation Integrity 与 Domain Authoritativeness。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-adaptive-kic",
    "decision_criteria": [],
    "statement": "DREAM 的 Key-Information Coverage 通过检索最新来源并识别必要事实来构造可核验问题。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-reasoning-quality",
    "decision_criteria": [],
    "statement": "DREAM 的 Reasoning Quality 使用 query-specific questions 与 structured validation plans 评估推理。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-dream-factuality-boundary",
    "decision_criteria": [],
    "statement": "DREAM 论文指出 citation alignment 不足以完成 factuality evaluation。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-paper-scale",
    "decision_criteria": [],
    "statement": "LiveResearchBench 论文将其定义为覆盖日常生活、企业和学术场景的 100 个专家策划任务的 benchmark。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-paper-systems",
    "decision_criteria": [],
    "statement": "LiveResearchBench 论文报告了对 17 个 frontier deep research systems 的评估。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-dataset-fields",
    "decision_criteria": [],
    "statement": "LiveResearchBench dataset 页面列出 question_with_checklist subset。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-dataset-question-only",
    "decision_criteria": [],
    "statement": "LiveResearchBench dataset 页面列出 question_only subset。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-dataset-checklist",
    "decision_criteria": [],
    "statement": "LiveResearchBench dataset 页面提供用于 coverage evaluation 的 checklist 字段。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-repo-identity",
    "decision_criteria": [],
    "statement": "LiveResearchBench repository 同时包含 LiveResearchBench benchmark 与 DeepEval evaluation framework。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-resume",
    "decision_criteria": [],
    "statement": "LiveResearchBench repository 的 README 说明评分中断后重新运行同一命令会自动继续。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-live-incremental",
    "decision_criteria": [],
    "statement": "LiveResearchBench repository 会把已评分报告立即保存到按 criterion 区分的 JSONL 文件。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-excluded-browsecomp",
    "decision_criteria": [],
    "statement": "Improving and Evaluating Open Deep Research Agents 提出 BrowseComp-Small，属于主题相关的 benchmark adaptation。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-excluded-date",
    "decision_criteria": [],
    "statement": "Improving and Evaluating Open Deep Research Agents 的首次发布时间为 2025-08-13，早于本次窗口。",
    "terms_scope": {},
    "time_boundary": {}
  },
  {
    "claim_spec_id": "claim-a4-excluded-updated",
    "decision_criteria": [],
    "statement": "Improving and Evaluating Open Deep Research Agents 的当前版本更新时间为 2026-01-08，不能替代首次发布时间。",
    "terms_scope": {},
    "time_boundary": {}
  }
]
```
