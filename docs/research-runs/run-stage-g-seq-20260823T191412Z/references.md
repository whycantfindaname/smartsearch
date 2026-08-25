# Stage G Reference Register

This register binds report-style reference IDs to the saved discovery and evidence records. `CandidateCard` means the source entered discovery; `EvidenceItem` means the source was mined with a saved snapshot and typed locator.

## Architecture References

| ID | Source | Saved identity | Evidence status |
| --- | --- | --- | --- |
| A1 | [Anthropic multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | CandidateCard `cand_65ade4bac10bbac004649282` | `evidence-architecture-anthropic-orchestrator`, `evidence-architecture-anthropic-boundaries`, `evidence-architecture-anthropic-duplicate-risk` |
| A2 | [Mistral Agentic Search](https://docs.mistral.ai/studio/search/agentic-search) | CandidateCard `cand_5107102d22f06e3185838d0d` | `evidence-architecture-mistral-retrieval-loop`, `evidence-architecture-mistral-read-set-navigation` |
| A3 | [SearchSwarm](https://arxiv.org/html/2606.09730) | CandidateCard `cand_14ada9dbe5277b11a3cb16e1` | `evidence-delegation-searchswarm-brief-context`, `evidence-delegation-searchswarm-root-judgment`, `evidence-delegation-searchswarm-citations` |
| A4 | [MultiAgent public case](https://mp.weixin.qq.com/s/Osm8jzocOBNvkxIXSgdiNQ) | Direct known-URL artifact; no CandidateCard | `evidence-delegation-wechat-feedback-protocol`, `evidence-delegation-wechat-role-separation` |
| A5 | [Mistral Search Toolkit documentation](https://docs.mistral.ai/studio/search-toolkit) | Implementation provenance | No independent EvidenceItem |
| A6 | [`mistralai-search-toolkit` package](https://pypi.org/project/mistralai-search-toolkit/) | Version and dependency provenance | No independent EvidenceItem |
| A7 | [`konbakuyomu/smartsearch`](https://github.com/konbakuyomu/smartsearch) | Upstream provenance | No independent EvidenceItem |
| A8 | [`whycantfindaname/smartsearch`](https://github.com/whycantfindaname/smartsearch) | Current implementation repository | No independent EvidenceItem |

## Benchmark References

| ID | Source | Saved identity | Evidence status |
| --- | --- | --- | --- |
| B1 | [DevDex](https://www.firecrawl.dev/benchmarks/devdex), [harness](https://github.com/firecrawl/benchmark-devdex) | CandidateCard `cand_91d38a21584dd4314594e98b`, `cand_0495c5d9da69713e829c1989` | Candidate only |
| B2 | [BrowseComp](https://openai.com/index/browsecomp/) | CandidateCard `cand_85939b9a7a062cf72b92cad9` | Candidate only |
| B3 | [BrowseComp-Plus](https://texttron.github.io/BrowseComp-Plus/) | CandidateCard `cand_bfd494130f6eaf8f076dd16a` | `evidence-miner-benchmarks-browsecomp-discrimination`, `evidence-miner-benchmarks-browsecomp-table-caveat`, `evidence-miner-benchmarks-browsecomp-metrics` |
| B4 | [LiveResearchBench](https://github.com/SalesforceAIResearch/LiveResearchBench) | CandidateCard `cand_dbb4f44d4140e24875c28170` | Candidate only |
| B5 | [LiveDRBench](https://github.com/microsoft/livedrbench) | CandidateCard `cand_5f22d728c373fe49030acdc6` | Candidate only |
| B6 | [QASPER](https://huggingface.co/datasets/allenai/qasper) | CandidateCard `cand_902623fc3396b0f60ba22bdf` | Candidate only |
| B7 | [MMLongBench-Doc](https://mayubo2333.github.io/MMLongBench-Doc/) | CandidateCard `cand_e96046df2347264f2a09e26b` | Candidate only |
| B8 | [ALCE](https://github.com/princeton-nlp/ALCE/) | CandidateCard `cand_cc8b1cf12a24eed3d271dd8a` | Candidate only |
| B9 | [DeepResearch Bench](https://deepresearch-bench.github.io/) | CandidateCard `cand_34d246b318eba3e034e49647` | `evidence-miner-benchmarks-deepresearch-complement`, `evidence-miner-benchmarks-deepresearch-race`, `evidence-miner-benchmarks-deepresearch-fact` |
| B10 | [Smart Search Stage G engineering gate](../../acceptance/stage-g-engineering-gate.md) | Project-internal run evidence | [Citation verification](evidence/citation_verification.json) |

The complete source records are [CandidateCard JSONL](evidence/candidate_cards.jsonl) and [EvidenceItem JSONL](evidence/evidence_items.jsonl). Final Claim backtraces are authoritative in [citation verification](evidence/citation_verification.json).
