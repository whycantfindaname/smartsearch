# Research Log: Review the architecture of a multi-source agentic research system and identify worthwhile public benchmarks for later evaluation. Focus on Root/Scout/Curator/Miner information exchange, dynamic replanning, key-document selection, document-internal mining, Claim synthesis, trace/provenance, feedback loops, benchmark scoring, dependencies, reproduction cost, freshness and contamination. Cover papers, official documentation, open-source repositories, engineering articles and public cases. Seed sources include Mistral Agentic Search, Mistral Search Toolkit, Firecrawl Developer Index, SearchSwarm arXiv 2606.09730, and https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ.

## Phase 1: Initialization

- Run `run-stage-g-seq-20260823T191412Z` initialized in `deep` mode.
- Root supplied 2 claims and 16 initial/current search tasks.
- Capability snapshot observed at `2026-08-23T19:10:12.680234Z`.

## Phase 2: Discovery

- Observed 63 execution attempts and retained 113 normalized candidates.
- Task `task-main-architecture` / `main_search` via `smart-search`: `success`.
- Task `task-main-benchmarks` / `main_search` via `smart-search`: `success`.
- Task `task-provider-research` / `provider_research` via `firecrawl`: `timeout`.
- Task `task-provider-research` / `provider_research` via `tavily`: `failed`.
  - Public error: HTTP 432: {"detail": {"error": "This request exceeds your plan's set usage limit. Please upgrade your plan or contact support@tavily.com"}}
- Task `task-provider-research` / `provider_research` via `exa`: `success`.
- Task `task-provider-research` / `provider_research` via `jina`: `timeout`.
- Task `task-academic-index` / `academic_search` via `firecrawl`: `success`.
- Task `task-developer-index` / `developer_search` via `firecrawl`: `failed`.
  - Public error: Firecrawl developer_search response requires object coverage and boolean reranked
- Task `task-developer-index-retry` / `developer_search` via `firecrawl`: `success`.
- Task `task-scout-architecture` / `search_scout` via `search_scout`: `success`.
- Task `task-scout-benchmarks` / `search_scout` via `search_scout`: `success`.
- Task `task-fetch-anthropic` / `web_fetch` via `tavily`: `success`.
- Task `task-fetch-mistral` / `web_fetch` via `tavily`: `success`.
- Task `task-fetch-browsecomp-plus` / `web_fetch` via `tavily`: `success`.
- Task `task-fetch-deepresearch-bench` / `web_fetch` via `tavily`: `success`.
- Task `task-mine-architecture` / `document_tool` via `mineru`: `failed`.
- Task `task-mine-architecture` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-architecture` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-architecture` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-architecture` / `document_tool` via `openai_compatible_embedding`: `degraded`.
  - Public error: EMBEDDING_FAILED
- Task `task-mine-architecture` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-architecture` / `document_tool` via `mineru`: `failed`.
- Task `task-mine-architecture` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-architecture` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-architecture` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-architecture` / `document_tool` via `openai_compatible_embedding`: `degraded`.
  - Public error: EMBEDDING_FAILED
- Task `task-mine-architecture` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `mineru`: `failed`.
- Task `task-mine-benchmarks` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `openai_compatible_embedding`: `degraded`.
  - Public error: EMBEDDING_FAILED
- Task `task-mine-benchmarks` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `mineru`: `failed`.
- Task `task-mine-benchmarks` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-benchmarks` / `document_tool` via `openai_compatible_embedding`: `degraded`.
  - Public error: EMBEDDING_FAILED
- Task `task-mine-benchmarks` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-fetch-searchswarm` / `web_fetch` via `tavily`: `success`.
- Task `task-fetch-wechat` / `web_fetch` via `tavily`: `success`.
- Task `task-curator-multisource` / `source_curator` via `source_curator`: `success`.
- Task `task-mine-architecture` / `evidence_miner` via `evidence_miner`: `success`.
- Task `task-mine-benchmarks` / `evidence_miner` via `evidence_miner`: `success`.
- Task `task-curator-academic` / `source_curator` via `source_curator`: `success`.
- Task `task-mine-delegation` / `document_tool` via `search-toolkit-sidecar`: `failed`.
  - Public error: The existing index identity differs from the configured identity; rebuild is required.
- Task `task-mine-delegation` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-delegation` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-delegation` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-delegation` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-delegation` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-delegation` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-delegation` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-delegation` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-delegation` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-delegation` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-delegation` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-delegation` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-delegation` / `document_tool` via `fetched_text_fallback`: `success`.
- Task `task-mine-delegation` / `document_tool` via `controlled_artifact_loader`: `success`.
- Task `task-mine-delegation` / `document_tool` via `search_toolkit_pipeline`: `success`.
- Task `task-mine-delegation` / `document_tool` via `sqlite_fts5`: `success`.
- Task `task-mine-delegation` / `evidence_miner` via `evidence_miner`: `success`.

## Phase 3: Source Curation

- Proposal `proposal-curator-multisource` retained 36, deferred 19, and rejected 8 candidates.
- Proposal `proposal-curator-academic` retained 27, deferred 21, and rejected 2 candidates.

## Phase 4: Evidence Mining

- Root assigned 3 evidence tasks; 16 EvidenceItem records are present.
- Evidence gap: Published systems rarely expose a complete typed DelegateRequest/DelegateResult and Claim-to-artifact reverse-trace contract.
- Evidence gap: No single benchmark measures retrieval, live-Web orchestration, document mining, evidence provenance and long-report citation quality together.
- Evidence gap: 没有单一候选同时覆盖 Root/Scout/Curator/Miner 的 typed information exchange、动态重规划、文档内挖掘、Claim-to-artifact 反向追踪和最终报告评分。
- Evidence gap: 现有 benchmark 候选分散在 live Web、固定语料检索、文档定位、引用生成和浏览器执行；缺少一个同时测 retrieval、freshness、document mining、provenance 与 long-form citation quality 的统一基准。
- Evidence gap: 候选卡未提供统一的 provider 独立性、失败隔离、预算/延迟、重复来源控制和反馈回路指标，无法仅凭本分片完成端到端架构验收。
- Evidence gap: 部分官方页面、仓库和基准的原始数据、隐藏测试、许可证、judge 实现与版本冻结信息仍需后续证据挖掘确认。
- Evidence gap: BrowseComp-Plus's full numeric table is not yet posted in the supplied snapshot; the table-caveat EvidenceItem captures this limitation.
- Evidence gap: candidate_cards 仅有标题、canonical_url、source_type 和 raw_record_ref；没有摘要、作者、版本、数据集规模、评分指标、代码/许可证、运行依赖或公开排行榜，因此无法仅凭本分片确认 public availability、scoring process 和 reproduction cost。
- Evidence gap: 本 academic shard 没有独立的官方 benchmark 文档、代码仓库或 leaderboard 卡片；Benchmark 推荐仍需 Root 结合其他分片和已登记 artifact 复核原始实现与评分协议。
- Evidence gap: 没有单个卡片直接证明完整的 typed Root↔Scout↔Curator↔Miner 信息交换、Claim-to-artifact reverse trace 和失败隔离契约；保留的 trajectory、trace、evidence 和 coordination 来源只能覆盖这些维度的局部。
- Evidence gap: 实时性、搜索时污染、长链证据、宽深覆盖和过程评分由不同候选分别覆盖，当前没有一个已确认同时满足全部维度的公开 Benchmark。
- Evidence gap: 多模态、企业、医学、地理定位和软件 Agent 候选未能从卡片确认其对 text-first preview_research_run 的迁移成本，暂不作为主推荐。
- Evidence gap: document sidecar unavailable for task-mine-delegation: INDEX_IDENTITY_MISMATCH

## Phase 5: Claim Assessment

- Claim `claim-architecture` is `weakly_supported` with 8 support, 0 contradiction, and 2 qualification records.
- Claim `claim-benchmarks` is `weakly_supported` with 5 support, 0 contradiction, and 1 qualification records.

## Phase 6: Root Decision

- Stop reason: Stage G has sufficient primary evidence for an architecture review and benchmark recommendation. Selecting or running a benchmark is intentionally deferred for user review.

## Phase 7: Citation Verification

- Supplied verification status: `True`; citation count: `16`.

## Phase 8: Document Index

- [Portable bundle index](README.md) connects the run, canonical reports, Evidence/Claim files, and follow-up Benchmark task.
- [Reference register](references.md) binds paper-style reference IDs to saved CandidateCard and EvidenceItem identities.
