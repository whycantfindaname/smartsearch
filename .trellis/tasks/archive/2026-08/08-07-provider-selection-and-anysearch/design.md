# Design

- 抽取稳定的 library subject tokens，停用词不参与匹配。
- 候选 eligibility 由 title/id overlap 决定，分数按 exact/title-id overlap、description、trust/benchmark 依次降低权重。
- auto research 和 supplemental docs 共用 selector；explicit CLI 保留原始候选透明度。
- AnySearch 参数 parser 先 JSON 后 repeatable pairs；extract 在 JSON normalization 后本地截断。
