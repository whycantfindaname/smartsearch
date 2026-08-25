# Stage G 研究索引与 References

> 运行：`run-stage-g-seq-20260823T191412Z`
> 模式：`deep`
> 搜索与取证时点：2026-08-23 至 2026-08-24
> 用途：把计划、实际搜索产物、复盘、推荐报告与后续 Benchmark 任务连接成一条可回溯文档链。

## 阅读入口

| 目的 | 文档 | 与实际搜索结果的关系 |
| --- | --- | --- |
| 掌握总体设计 | [交互式项目地图](../plans/multi-source-search-big-picture.html) | 展示目标架构与实现状态，不是运行产物 |
| 查看实现依据 | [完整实施计划](../plans/multi-source-research-implementation.md) | 记录里程碑、契约、实现与 Stage G 收尾 |
| 查看工程事实 | [Stage G 工程验收记录](stage-g-engineering-gate.md) | 汇总真实运行、测试、Provider 状态与修复 |
| 查看架构判断 | [Stage G 架构复盘](stage-g-architecture-review.md) | 主要使用 References `[A1]`–`[A4]` 对应的 EvidenceItem |
| 查看 Benchmark 候选 | [Stage G Benchmark 候选推荐](stage-g-benchmark-recommendations.md) | 使用 References `[B1]`–`[B10]`；其中 `[B3]`、`[B9]` 已深挖为 EvidenceItem |
| 跨机器追溯搜索证据 | [Portable Research Evidence Bundle](../research-runs/run-stage-g-seq-20260823T191412Z/README.md) | Git 管理的精简证据包，保留 Candidate、Evidence、Claim、Artifact metadata 与公开 Trace |
| 继续 Benchmark 实施 | [Benchmark Trellis 交接](../../.trellis/tasks/08-24-benchmark-evaluation-integration/HANDOFF.md) | 继承本次运行、报告和 References，不重复建立来源总账 |

## Research Workspace 与可移植证据包

完整的可执行运行保存在当前机器、被 Git 忽略的目录：

`.smart-search/research-runs/run-stage-g-seq-20260823T191412Z`

它包含原始网页快照、SQLite 索引、checkpoints、逐任务目录和 raw Trace，主要用于当前机器上的字符级 locator 重放与调试。

跨机器入口是 Git 管理的 [Portable Research Evidence Bundle](../research-runs/run-stage-g-seq-20260823T191412Z/README.md)：

- [Project Manifest](../research-runs/run-stage-g-seq-20260823T191412Z/project_manifest.json)
- [Export Manifest](../research-runs/run-stage-g-seq-20260823T191412Z/export_manifest.json)
- [最终 Dossier](../research-runs/run-stage-g-seq-20260823T191412Z/latest_dossier.json)
- [候选来源](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/candidates.jsonl)与 [CandidateCard](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/candidate_cards.jsonl)
- [KeySourceProposal](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/key_source_proposals.jsonl)
- [EvidenceItem](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/evidence_items.jsonl)与 [ClaimRecord](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/claim_records.json)
- [引用反向验证](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/citation_verification.json)
- [Artifact metadata](../research-runs/run-stage-g-seq-20260823T191412Z/artifacts.jsonl)与[公开 Trace](../research-runs/run-stage-g-seq-20260823T191412Z/public_trace.jsonl)

可移植证据包能够审计既有 References 和 Claim 回溯，但不包含原始网页 payload，因此不能在其他机器上离线重放字符级 locator 验证。完整 Workspace 仍保留在当前 Mac，作为本地调试来源。

## 引用规则

- `[A#]` 是架构复盘使用的来源；`[B#]` 是 Benchmark 推荐使用的来源。
- `CandidateCard` ID 证明该来源进入了发现结果，不代表正文已经核验。
- `EvidenceItem` ID 证明该来源已经进入文档深挖，并具有 snapshot 与 typed locator。
- References 没有列出 `EvidenceItem` 时，该来源仍属于候选或实现归属依据，不能表述为本次正式取证结论。
- 最终 Claim 的权威引用关系以 Workspace 中的 `citation_verification.json` 为准。

## Architecture References

1. **[A1] Anthropic.** [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system). CandidateCard `cand_65ade4bac10bbac004649282`; EvidenceItem `evidence-architecture-anthropic-orchestrator`, `evidence-architecture-anthropic-boundaries`, `evidence-architecture-anthropic-duplicate-risk`.
2. **[A2] Mistral AI.** [Agentic Search](https://docs.mistral.ai/studio/search/agentic-search). CandidateCard `cand_5107102d22f06e3185838d0d`; EvidenceItem `evidence-architecture-mistral-retrieval-loop`, `evidence-architecture-mistral-read-set-navigation`.
3. **[A3] SearchSwarm.** [Agentic Search with Multi-Agent Collaboration](https://arxiv.org/html/2606.09730). CandidateCard `cand_14ada9dbe5277b11a3cb16e1`; EvidenceItem `evidence-delegation-searchswarm-brief-context`, `evidence-delegation-searchswarm-root-judgment`, `evidence-delegation-searchswarm-citations`.
4. **[A4] 用户提供的 MultiAgent 公开案例.** [微信公众号原文](https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ). 已知 URL 直接登记为 artifact，未生成 CandidateCard；EvidenceItem `evidence-delegation-wechat-feedback-protocol`, `evidence-delegation-wechat-role-separation`.
5. **[A5] Mistral AI.** [Search Toolkit documentation](https://docs.mistral.ai/studio/search-toolkit). 实现归属依据；本次没有独立 EvidenceItem。
6. **[A6] Mistral AI.** [`mistralai-search-toolkit` 发行包](https://pypi.org/project/mistralai-search-toolkit/). 版本与依赖归属依据；本次没有独立 EvidenceItem。
7. **[A7] konbakuyomu.** [`smartsearch` 上游仓库](https://github.com/konbakuyomu/smartsearch). 发现阶段原始项目来源；本次没有独立 EvidenceItem。
8. **[A8] whycantfindaname.** [当前 `smartsearch` 分支仓库](https://github.com/whycantfindaname/smartsearch). 当前实现与验收载体；本次没有独立 EvidenceItem。

## Benchmark References

1. **[B1] Firecrawl.** [DevDex / Developer Retrieval Benchmark](https://www.firecrawl.dev/benchmarks/devdex) 与 [公开 harness](https://github.com/firecrawl/benchmark-devdex). CandidateCard `cand_91d38a21584dd4314594e98b`, `cand_0495c5d9da69713e829c1989`; 本次没有 EvidenceItem。
2. **[B2] BrowseComp.** [OpenAI BrowseComp](https://openai.com/index/browsecomp/). CandidateCard `cand_85939b9a7a062cf72b92cad9`; 本次没有 EvidenceItem。
3. **[B3] BrowseComp-Plus.** [Benchmark project page](https://texttron.github.io/BrowseComp-Plus/). CandidateCard `cand_bfd494130f6eaf8f076dd16a`; EvidenceItem `evidence-miner-benchmarks-browsecomp-discrimination`, `evidence-miner-benchmarks-browsecomp-table-caveat`, `evidence-miner-benchmarks-browsecomp-metrics`.
4. **[B4] Salesforce AI Research.** [LiveResearchBench](https://github.com/SalesforceAIResearch/LiveResearchBench). CandidateCard `cand_dbb4f44d4140e24875c28170`; 本次没有 EvidenceItem。
5. **[B5] Microsoft.** [LiveDRBench](https://github.com/microsoft/livedrbench). CandidateCard `cand_5f22d728c373fe49030acdc6`; 本次没有 EvidenceItem。
6. **[B6] AllenAI.** [QASPER](https://huggingface.co/datasets/allenai/qasper). CandidateCard `cand_902623fc3396b0f60ba22bdf`; 本次没有 EvidenceItem。
7. **[B7] MMLongBench-Doc.** [Benchmark project page](https://mayubo2333.github.io/MMLongBench-Doc/). CandidateCard `cand_e96046df2347264f2a09e26b`; 本次没有 EvidenceItem。
8. **[B8] Princeton NLP.** [ALCE](https://github.com/princeton-nlp/ALCE/). CandidateCard `cand_cc8b1cf12a24eed3d271dd8a`; 本次没有 EvidenceItem。
9. **[B9] DeepResearch Bench.** [Benchmark project page](https://deepresearch-bench.github.io/). CandidateCard `cand_34d246b318eba3e034e49647`; EvidenceItem `evidence-miner-benchmarks-deepresearch-complement`, `evidence-miner-benchmarks-deepresearch-race`, `evidence-miner-benchmarks-deepresearch-fact`.
10. **[B10] Smart Search Stage G.** [工程验收记录](stage-g-engineering-gate.md) 与 [引用反向验证](../research-runs/run-stage-g-seq-20260823T191412Z/evidence/citation_verification.json). 项目内部工程证据，用于补充公开 Benchmark 无法覆盖的 typed information exchange、失败隔离、Trace 和 Claim-to-artifact 回溯。

## 后续任务

Benchmark 接入任务以 [PRD](../../.trellis/tasks/08-24-benchmark-evaluation-integration/prd.md)、[技术设计](../../.trellis/tasks/08-24-benchmark-evaluation-integration/design.md)、[实施清单](../../.trellis/tasks/08-24-benchmark-evaluation-integration/implement.md)和[研究资料目录](../../.trellis/tasks/08-24-benchmark-evaluation-integration/research/current-evidence.md)为准。该任务当前仍为 `planning`，尚未选择或运行 Benchmark，也没有产生分数。
