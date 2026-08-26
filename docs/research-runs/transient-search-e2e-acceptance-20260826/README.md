# 瞬时搜索错误端到端验收调研包

这里把 2026-08-26 瞬时错误验收中的五项真实调研提升为持久、带引用验证的 Research Workspace。原 Trellis 归档保持不变，继续作为报告和命令材料的 provenance source；本目录只保存重写后的报告、机器可审计证据和脱敏导出。

五个 Workspace 均由 Smart Search commit `f3a30d4` 的 citation-backed Research Workspace 合约生成。读者报告使用相邻编号引用，`evidence/citation_verification.json` 和 `evidence/reference_register.json` 保存从显示引用反查 ClaimRecord、EvidenceItem、证据快照和 locator 的机器链路。

## 调研项

| Case | 调研目标 | Workspace |
| --- | --- | --- |
| A1 | Provider 错误与限流契约 | [`A1-provider-errors`](A1-provider-errors/) |
| A2 | 最近一个月的 IQA 论文，优先 agentic 与 workflow 方法 | [`A2-iqa-papers`](A2-iqa-papers/) |
| A3 | OpenAI Agents SDK、LangGraph 与 PydanticAI 的恢复能力 | [`A3-agent-workflows`](A3-agent-workflows/) |
| A4 | Deep Research Agent 论文、评测与开源实现 | [`A4-deep-research-evaluation`](A4-deep-research-evaluation/) |
| A5 | 截至验收日最新的 Mac mini 与 Mac Studio | [`A5-apple-desktops`](A5-apple-desktops/) |

## 迁移边界

- 原报告按“主张旁紧邻证据”和确定性 References 重写；可以收窄有来源的主张，不得增强原证据没有支持的结论。
- 来源标题、URL、日期、产品名、论文名、错误码和实测计数都是受保护字面量；只有保存的直接来源能够证明更正时才可修改。
- 每个正式引用必须有一段能在保存命令结果中精确回读的 excerpt。仅用于发现的候选保留在 search materials 中，不进入正式 References。
- 每个 Case 保存脱敏后的 command JSON、invocation、gateway event、run result 和 verdict。重复的 stdout/stderr 与被最终结果取代的失败尝试只保留在原 Trellis 归档。
- 生成器在导出时重写密钥、令牌、用户目录、用户名与私网 URL；原归档不被修改。
- 本次迁移不执行实时搜索、provider 诊断、凭据读取或 `doctor` 探针。

顶层 [`export_manifest.json`](export_manifest.json) 记录来源 commit、provenance 位置、纳入/排除范围和数量；[`REVISION_NOTES.md`](REVISION_NOTES.md) 记录写作与术语修订。

## 重新生成

在仓库根目录使用兼容当前 Smart Search dataclass 合约的 Python 运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3.12 \
  docs/research-runs/transient-search-e2e-acceptance-20260826/build_bundle.py
```

生成器只读取已保存的最终验收产物，并在写入持久目录时脱敏，不会连接 provider。应使用 Python 3.12 或其他与当前 Smart Search 运行时合约兼容的解释器。
