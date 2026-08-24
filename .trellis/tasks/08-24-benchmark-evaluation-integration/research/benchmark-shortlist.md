# Benchmark Shortlist for Smart Search Multi-Source Research

> Evidence checked: 2026-08-24. Planning only: no dataset was downloaded, no benchmark or judge was run, no paid API was called, and the Trellis task was not started.

## Decision

Use a four-part shortlist, but do not pretend that all four produce the same kind of evidence.

| Priority | Benchmark | What it should decide | Live or frozen | Leaderboard status | Status for this exact Codex CLI + Qwen/Qwen3.8-27B + live Smart Search system |
| --- | --- | --- | --- | --- | --- |
| **Primary** | [LiveResearchBench](https://github.com/SalesforceAIResearch/LiveResearchBench) | End-to-end quality of citation-grounded research reports | Live prompts with date placeholders; an optional static rendering also exists | Active project-page leaderboard covering 17 systems, but no public submission protocol was found | **Representative, but exact leaderboard comparison requires the official external judges and access to the non-public 20 tasks. Zero-judge-spend runs are internal-only.** |
| **Secondary / best direct mode comparison** | [BrowseComp](https://openai.com/index/browsecomp/) | Whether quick, standard, and deep trade more search work for more correct hard-to-find answers | Frozen public questions and answers, answered against the live Web | No official OpenAI leaderboard. [Steel](https://leaderboard.steel.dev/leaderboards/browsecomp/) is an active third-party index of sourced and team-reported results | **Best no-new-generation-harness comparison across the three live modes, but not exactly comparable to Steel unless generation, tools, budgets, and grader all match a cited row.** |
| **Diagnostic** | [Firecrawl DevDex](https://github.com/firecrawl/benchmark-devdex) | Developer-document, repository, issue, and PR discovery | Frozen gold URLs against currently live indexes/pages | Active maintainer table with a documented PR/rerun submission path | **The public sample can be scored exactly, but replacing the official Claude Opus driver with Codex/Qwen makes the result internal-only relative to the published table.** |
| **Deferred controlled secondary** | [BrowseComp-Plus](https://github.com/texttron/BrowseComp-Plus) | Separate retrieval/evidence recall from answer correctness under a controlled corpus | Frozen approximately 100K-document corpus | Active [official Hugging Face leaderboard](https://huggingface.co/spaces/Tevatron/BrowseComp-Plus) with email submission | **Potentially leaderboard-comparable with the official Qwen3-32B judge, but not while using real live Smart Search providers; therefore defer rather than distort the live-provider requirement.** |

The primary scientific claim should come from LiveResearchBench. The first low-cost operational comparison should use BrowseComp because it can feed the same question to `quick`, `standard`, and `deep` through Codex CLI while keeping the generation model and live-provider environment fixed. Report each benchmark's native metrics separately; do not calculate a cross-benchmark score.

## Exact leaderboard comparability versus internal mode comparison

“Same benchmark” is not enough for leaderboard comparability. A result is **exactly leaderboard-comparable** only when the task split/version, generation driver, model, tool policy, budgets, failure handling, and official scorer/judge configuration match the leaderboard protocol. Keeping only the official metric formula does not repair a changed driver or judge.

Under the required setup, none of the live-provider candidates gives a zero-additional-spend, exact leaderboard submission:

- LiveResearchBench accepts report files independently of the generation harness, so Codex/Qwen can generate inputs. Its documented reproducible evaluation, however, uses both GPT-5 and Gemini 2.5 Pro and averages their results. Replacing them with local Qwen changes the judge and creates an internal result.
- BrowseComp's reference scorer is reusable, but the reference implementation receives a configurable `grader_model` rather than defining one immutable public leaderboard judge. Steel explicitly mixes independently benchmarked and team-reported system setups. A locally judged Qwen result is useful for comparing modes, not for claiming a Steel rank.
- DevDex's deterministic URL scorer can score Qwen outputs without a judge, but its published table fixes Claude Opus 4.8, one search tool per arm, the tool gate, and depth cap. The Qwen/Codex multi-source flow changes the tested system.
- BrowseComp-Plus is the only shortlisted benchmark with a current, explicit submission scorer: Qwen3-32B. Exact comparison also requires its fixed corpus/retriever interface, so routing cases to live Smart Search providers would change the benchmark.

## 1. LiveResearchBench — primary end-to-end benchmark

### Why it is primary

LiveResearchBench contains 100 expert-curated, open-ended tasks intended to require current Web research and multi-source synthesis. It evaluates the artifact that users actually see: a citation-grounded long report. This is the closest match to the complete Root plus project-agent flow and is the strongest external evidence for `deep`; it can also reveal where `quick` and `standard` stop covering a complex request.

### Official scoring path

The official [repository](https://github.com/SalesforceAIResearch/LiveResearchBench) preprocesses one Markdown report per query and applies DeepEval across presentation, coverage, factual/logical consistency, citation association, and analysis depth. Presentation and coverage use checklists, consistency and citation use pointwise additive error counting, and depth uses position-swapped pairwise comparison. The repository recommends running GPT-5 and Gemini 2.5 Pro and averaging their summaries. Native dimensions must remain separate even if the project page also displays an average.

The [project page](https://livedeepresearch.github.io/#leaderboard) currently displays a leaderboard for 17 evaluated systems. It is an active published ranking, but neither the repository README nor CONTRIBUTING file gives a public new-system submission procedure. Treat it as a published baseline table, not an open submission service.

### Split, access, license, and freshness

- Full benchmark: 100 tasks.
- Public Hugging Face release: 80 tasks in `question_only` and `question_with_checklist` forms. The remaining 20 require contacting the authors, according to the official [dataset documentation](https://github.com/SalesforceAIResearch/LiveResearchBench/blob/main/docs/DATASET.md).
- Realtime mode substitutes current-year/current-date placeholders at preprocessing time; static mode retains fixed rendered dates. It is therefore live in query framing and Web evidence, not a hidden continuously regenerated test set.
- Repository code is Apache-2.0 under the official [license](https://github.com/SalesforceAIResearch/LiveResearchBench/blob/main/LICENSE.txt). Before implementation, recheck the Hugging Face dataset card's data-license metadata separately; the repository license alone should not be silently applied to hosted task data.

### Compatibility and cost

Codex CLI can generate the required Markdown files with Qwen/Qwen3.8-27B and the unchanged Smart Search modes. No official generation driver has to be retained. Exact comparison to the displayed leaderboard nevertheless requires the same task coverage and official judge combination. The major costs are three live research generations per task for the mode comparison, live provider calls, long contexts, and two frontier-model judge passes across multiple dimensions. Using local Qwen/Qwen3.8-27B as judge removes API spend but is **internal mode-comparison only** and risks self-preference because generator and judge are the same model family and instance.

## 2. BrowseComp — secondary and best quick/standard/deep comparator

### Why it is the best direct mode comparison

BrowseComp has 1,266 difficult, short-answer questions designed to require persistent browsing. The final output is compact, so most run cost is attributable to search behavior rather than report length. The same public question can go through all three Smart Search modes with identical Codex CLI, Qwen3.8-27B, SGLang, provider availability, timeout policy, and final-answer format. Record native accuracy alongside search calls, provider/tool calls, wall time, failure rate, and observed provider cost; these operational measures are not part of BrowseComp accuracy.

This makes BrowseComp the cleanest first answer to “does deep buy enough correctness over standard, and does standard buy enough over quick?” It does **not** measure citation quality or long-report synthesis, so it cannot replace LiveResearchBench.

### Official scoring path

OpenAI's [reference evaluator](https://github.com/openai/simple-evals/blob/main/browsecomp_eval.py) decrypts each problem and answer using the row's canary, requires `Explanation`, `Exact Answer`, and `Confidence`, and asks an LLM grader for a binary correct/incorrect judgment. The native aggregate is accuracy. The full CSV is loaded from OpenAI's public blob; there is no separate public development split or hidden official test split in the reference implementation. OpenAI's [simple-evals repository](https://github.com/openai/simple-evals) is MIT-licensed and, since July 2025, deprecated for new results while retaining BrowseComp's reference implementation.

The grader is an injected sampler rather than one permanently pinned model. Therefore a local Qwen3.8-27B grader can support zero-API-spend internal comparison, but it is not an “official judge” that creates exact comparability with arbitrary published results. Save item-level grader outputs and manually audit a fixed disagreement sample.

### Leaderboard and freshness

OpenAI does not publish an official submission leaderboard for BrowseComp. Steel's [BrowseComp page](https://leaderboard.steel.dev/leaderboards/browsecomp/) is useful for locating reported results, but Steel itself states that some rows are independently benchmarked while others are team-reported, and that model-only and agent-with-tools rows are not directly comparable. Cite Steel only as a **third-party index**, never as evidence of a protocol-controlled official rank.

The questions/answers are frozen and fully public, while evidence is obtained from the live Web. Results can drift as pages and search rankings change, and public questions carry contamination risk. Every run therefore needs the dataset revision, date/time, region, provider observations, and a no-search baseline or explicit contamination caveat.

### Cost

There is no dataset fee and the local generator is already provided. The irreducible costs are live Smart Search provider usage and 3 × 1,266 generations for a full three-mode run. A predeclared pilot subset is appropriate before any full run. Local Qwen judging adds GPU time but no paid judge API; exact comparison to any external row remains unavailable unless that row's complete grader and tool protocol can be reproduced.

## 3. Firecrawl DevDex — deterministic discovery diagnostic

### Official scoring path and split

DevDex evaluates repository, issue/PR, and documentation discovery. Its [official repository](https://github.com/firecrawl/benchmark-devdex) scores the first ten cited URLs with deterministic canonical/reference matching and reports Recall@10 and MRR@10. Failed cases are misses. The combined result is the equal-weight mean of the three track means, with stratified-bootstrap confidence intervals; preserve the track metrics and do not substitute the combined value for them.

The full set has 1,179 cases: 393 repository, 400 issue/PR, and 386 documentation cases. The repository ships a 594-case public sample (198/195/201); the remainder is held back. Code, scorer, and public sample are MIT-licensed. Pages and search indexes are live, but questions and canonical golds are frozen and can drift when documentation or repository URLs move.

### Leaderboard and compatibility

The current maintainer table is active and has a documented [submission path](https://github.com/firecrawl/benchmark-devdex/blob/main/CONTRIBUTING.md): run the public half, open a PR with command/results, then provide valid provider credentials privately so maintainers can rerun the held-out half. Published rows fix Claude Opus 4.8, one search tool per arm, the same agent loop/tool gate/depth cap, and the same scorer.

Smart Search can expose a compatible HTTP MCP surface, and its citations can be deterministically scored. But the required Codex CLI + Qwen3.8-27B driver and multi-source mode semantics violate the published-table control. Do not submit or claim table rank without maintainer agreement on a new driver track. Use the public sample internally to diagnose whether quick/standard/deep improve canonical-source discovery.

### Cost

The scorer has no judge cost. The official README estimates approximately USD 0.28 per item and USD 165 for one official full public-sample arm, mainly because of the Claude driver and vendor search calls. Local Qwen removes the Claude charge but not provider usage; it also removes official-table comparability. DevDex is narrower than the product because it does not score synthesis, evidence support, or report quality.

## 4. BrowseComp-Plus — defer as a frozen-corpus control

BrowseComp-Plus contains 830 BrowseComp-derived queries and an approximately 100K-document curated corpus. It deliberately replaces the live Web with a fixed corpus so retriever and agent effects can be compared reproducibly. That strength is also why it cannot be the first benchmark for the stated live-provider system.

The [official runner and submission instructions](https://github.com/texttron/BrowseComp-Plus) report Accuracy, gold/evidence Recall, average search-tool calls, and Calibration Error; retrieval-only submissions additionally use TREC nDCG@10 and Recall@5/100/1000. Agent scoring uses a local Qwen3-32B judge. The maintainers explicitly moved future submissions away from GPT-4.1 to Qwen3-32B for reproducibility in the official [judge documentation](https://github.com/texttron/BrowseComp-Plus/blob/main/docs/llm_as_judge.md). Results can be emailed for addition to the official Hugging Face leaderboard.

The official judge is locally runnable in principle and therefore need not incur paid judge API calls. Its actual SGLang fit/performance on the available 8×A100 stack was not tested in this planning task. It is a **different fixed evaluation model** from the required Qwen/Qwen3.8-27B generation model; replacing it with Qwen/Qwen3.8-27B forfeits exact leaderboard comparison. Conversely, keeping real Smart Search providers instead of the fixed corpus/retriever also forfeits comparison. All 830 queries are presented as the evaluation set and no hidden submission split is documented. The code repository is MIT-licensed; dataset access may require Hugging Face authentication, and the data/corpus license is not stated in the repository README or MIT code license, so it remains an implementation gate to verify from the dataset cards before download.

The project warns that a full 830-query frontier-model reproduction can cost about USD 1,000. That estimate does not apply directly to local Qwen, but corpus/index storage, retrieval serving, 830 agent runs, and Qwen3-32B judging still make this a material GPU/engineering run. Use it later only if the team wants a controlled retrieval study distinct from live Smart Search evaluation.

## Demoted candidates

### LiveDRBench — do not include in the first suite

[LiveDRBench](https://github.com/microsoft/LiveDRBench) offers 100 claim-discovery tasks and native precision, recall, and F1, which is conceptually useful for Claim-level diagnosis. The repository says tasks were collected in May–June 2025 and that periodic updates are planned, but the available `v1-full` set is a versioned frozen release rather than a continuously refreshed live split. There is no active leaderboard or public submission route in the official repository.

Its official evaluation command requires an OpenAI API key and defaults to GPT-4o for semantic matching. Replacing that judge with Qwen changes the scorer; retaining it violates the no-additional-evaluation-spend preference. Code is MIT and the dataset is CDLA v2 according to the official README. Because it adds a paid judge without giving a useful ranking target, defer it until Claim-record evaluation becomes a specific gap not covered by internal Trace/Claim checks.

### DeepResearch Bench / DeepResearch Bench II — do not include in the first suite

[DeepResearch Bench II](https://github.com/imlrz/DeepResearch-Bench-II) now has an active official leaderboard, 132 expert-report-derived tasks, and 9,430 rubrics across information recall, analysis, and presentation. As of August 2026, its official evaluator is GPT-5.5; leaderboard submission requires a temporary GPT-5.5-capable key so maintainers can recompute scores. Code is Apache-2.0, while task data has per-item CC BY 4.0, CC BY-NC 4.0, or CC0 terms.

It is influential and well structured, but it is redundant with LiveResearchBench for the first end-to-end report study and directly conflicts with the no-paid-judge preference. The original [DeepResearch Bench](https://deepresearch-bench.github.io/) is also judge-heavy and less useful than selecting one current report benchmark. Reconsider Bench II only if an official long-report leaderboard submission becomes more important than zero added evaluation spend.

## Recommended interpretation contract for a later run

1. **Internal mode comparison:** Run the same predeclared cases through quick, standard, and deep with the same Codex CLI version, Qwen/Qwen3.8-27B checkpoint/quantization, SGLang configuration, Root/subagent model, provider entitlement, region, timeout, concurrency, and failure policy. This isolates mode behavior but does not manufacture leaderboard comparability.
2. **External ranking evidence:** Use only an official split and unchanged official scorer/judge/driver. If any component differs, label the result “benchmark-derived internal evaluation,” not a leaderboard score.
3. **Native metrics only:** Keep LiveResearchBench dimensions, BrowseComp accuracy, DevDex Recall@10/MRR@10, and BrowseComp-Plus answer/retrieval/calibration metrics separate. Operational latency, calls, failures, and observed cost are parallel measurements, not ingredients of a universal score.
4. **Failure accounting:** Timeouts, provider failures, malformed outputs, and incomplete reports remain denominator failures according to each benchmark's official behavior; never silently drop them.
5. **Live-run evidence:** Save run timestamp, provider observations, final outputs, cited URLs, accessible page snapshots or artifact references, judge identity/configuration, and item-level judgments. This is necessary to interpret drift, not to create a new benchmark metric.

## Bottom line

- **Best primary benchmark:** LiveResearchBench, because it most closely measures the complete user-facing research product.
- **Best direct quick/standard/deep comparison under live search:** BrowseComp, because it minimizes report-generation overhead and gives a clear native accuracy outcome across a large common question set. Under local judging it is internal-only.
- **Best low-cost diagnostic:** DevDex public sample, because scoring is deterministic; published-table rank is unavailable with the required Qwen/Codex driver.
- **Best exact leaderboard path if live search is relaxed:** BrowseComp-Plus with its fixed corpus and Qwen3-32B judge.
- **No honest zero-additional-spend exact live leaderboard path exists for the required setup.** The project must choose between internal mode-comparison validity and strict external leaderboard protocol rather than claiming both.
