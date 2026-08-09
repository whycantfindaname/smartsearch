---
doc_type: requirement
slug: sciverse-academic-search
pitch: 需要查论文时，可以按学术字段和引用关系拿到更可靠的文献证据
status: current
last_reviewed: 2026-07-06
implemented_by:
  - 2026-07-06-sciverse-academic-provider
tags: [academic, provider, evidence]
---

# 学术文献检索与引用关系查询

## 用户故事

- 作为一个要做文献综述的人，我希望按作者、年份、期刊、DOI 这类学术字段找论文，而不是只拿网页搜索的相关度结果。
- 作为一个要核论文脉络的人，我希望看到一篇论文引用了谁、又被谁引用，而不是自己在多个页面之间来回查。
- 作为一个让 AI 辅助科研的人，我希望它能读取可用的论文正文片段并给出证据，而不是只根据标题和摘要猜。

## 为什么需要

普通网页搜索适合发现线索，但学术研究常常需要更窄、更可核验的证据：字段过滤、开放获取状态、引用关系、正文片段。没有这类能力时，AI 很容易把“找到一篇相关网页”误当成“掌握了论文证据”。

## 怎么解决

提供一个明确的学术检索入口。用户主动调用它时，可以先查可用字段，再做结构化论文检索或语义检索；拿到论文标识后，可以继续读取正文片段或分页查看引用关系。

## 边界

- 不替代通用网页搜索，也不默认接管所有包含“论文”的普通搜索。
- 不负责生成论文结论；它只提供可核验的学术证据和关系数据。
- 不承诺每篇论文都有全文可读；是否能读取正文取决于来源数据和当前授权。
- 第一版不处理论文中的图片、表格等多模态资源。

## 变更日志

- 2026-07-06：`2026-07-06-sciverse-academic-provider` 落地第一版 explicit-only Sciverse 学术 provider，提供 `sciverse-catalog`、`sciverse-search`、`sciverse-semantic`、`sciverse-read`、`sciverse-relations`。该能力仍不进入 `docs_search`，不满足 `standard` minimum profile，不加入默认 `search` / `research` fallback。
