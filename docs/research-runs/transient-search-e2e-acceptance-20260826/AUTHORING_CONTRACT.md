# Citation-backed 重写合约

每个 Case 的 `input/` 包含带 citation marker 的 `draft_report.md` 和结构化 `migration_input.json`。本地确定性生成器把两者转换为一个 Smart Search Research Workspace。

## `migration_input.json`

```json
{
  "case_id": "A1",
  "run_id": "run-transient-a1-20260826",
  "question": "Research question",
  "mode": "standard",
  "claims": [
    {
      "claim_spec_id": "claim-example",
      "statement": "One report-level claim."
    }
  ],
  "sources": [
    {
      "source_id": "source-example",
      "citation_id": "citation-example",
      "claim_spec_id": "claim-example",
      "title": "Direct source title",
      "url": "https://example.com/source",
      "locator_label": "Section or heading checked in the source",
      "command_file": "relative command JSON filename",
      "excerpt": "Exact UTF-8 substring present in that command result"
    }
  ]
}
```

生成器会验证每段 excerpt 都能在对应保存命令中精确回读，然后注册不可变的摘录快照，创建 EvidenceItem 与 ClaimRecord，追加公开 Trace event，并调用 `f3a30d4` 的 `verify_final_citations` 和 `ResearchWorkspace.materialize`。URL 或 CandidateCard 本身不能证明一个主张。

## 写作规则

- 使用自然、准确、可核验的中文，保留官方英文 identity。
- 每个依赖来源的事实、数字、比较或结论后立即放置 `[cite:<citation_id>]`。
- 不手写 References；Smart Search 只在验证成功后追加该章节。
- 明确区分 `verified`、`unverified` 与 `missing`。搜索摘要和 discovery result 只是线索，不是 verified evidence。
- 验收机制只放在简短的方法或恢复附录中，正文仍应是一份可独立阅读的调研报告。
- 会改变结论边界的限制、排除项、零结果与被取代解释必须保留。
- 产品名、论文名、命令、URL、JSON 字段、错误码和 commit 等受保护字面量不翻译、不规范化。
