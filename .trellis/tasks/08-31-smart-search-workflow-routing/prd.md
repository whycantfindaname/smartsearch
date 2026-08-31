# Simplify Smart Search workflow routing and research depth

## Goal

Make smart-search-cli a progressive-disclosure router, replace the public quick research mode with focused, add honest modes help, move Research Workflow mechanics into references, remove platform-specific runtime snapshots from the governed Skill, and preserve advanced CLI compatibility boundaries.

## Requirements

- Expose two primary user workflows: immediate `search` and the Skill-level
  `Research Workflow`. Keep `deep`, `research`, and `research-run` available as
  advanced compatibility or kernel interfaces instead of presenting all CLI
  commands as peer product modes.
- Replace the public research depth `quick` with `focused` everywhere the value
  belongs to the product-mode contract. Do not retain `quick` as a hidden alias.
  Unrelated uses of the English word `quick`, such as a lightweight diagnostic
  probe, are outside this rename.
- Define `focused`, `standard`, and `deep` by observable Research Workflow
  differences: Claim scope, source discovery, delegation, document mining,
  cross-validation, replanning, and stopping. A shallower depth may reduce
  coverage but must not weaken evidence eligibility.
- Add a read-only, offline `smart-search modes` command with JSON, Markdown, and
  content output. It must separate public workflows, research depth presets,
  and advanced CLI interfaces, include defaults and invocation surfaces, and
  describe the existing compact `research` executor honestly. It must not run
  provider, configuration, Skill-activation, or Preview-readiness probes.
- Refactor `skills/smart-search-cli/SKILL.md` into a progressive-disclosure
  router. Keep only purpose, decision path, shared invariants, and conditional
  Reference selection in the entrypoint. Put Research Workflow mechanics in
  `references/research-workflow.md` and architecture/data contracts in
  `references/agentic-research-architecture.md`.
- Remove platform- or machine-specific runtime snapshots from the governed
  Skill. In particular, do not describe an OPPO Linux host, private path,
  current machine model, or current provider availability as a universal
  Skill contract.
- Remove redundant Reference indirection once `SKILL.md` owns routing. Preserve
  stable cross-platform mechanisms in their actual owning References instead
  of deleting unique operational contracts.
- Keep the public Skill tree and npm-packaged Skill tree byte-identical.
- Implement first on `preview/multi-source-agentic-research`, verify it, then
  integrate into `lwj_dev` without modifying Smart Search `main` or discarding
  branch-specific work.
- Sync the governed personal `smart-search-cli` package main-first and merge it
  into `macos`, `oppo_windows`, and `oppo_linux` with the package-aware workflow.
  Refresh and verify macOS activation. Native Windows/Linux runtime acceptance
  remains deferred to those machines.
- Do not modify CPA, CLIProxyAPI, provider credentials, or unrelated dirty
  changes. Do not push, tag, publish, or release.

## Acceptance Criteria

- [ ] `smart-search modes --format json` returns a stable structured contract
      with `public_workflows`, `research_depths`, and `advanced_entrypoints` and
      performs no network or configuration probe.
- [ ] Markdown/content output explains that `search` is immediate retrieval,
      while `Research Workflow` creates a caller-held, evidence-backed research
      run; delegation is a mechanism, not the mode definition.
- [ ] CLI parsers, planner contracts, ResearchFrame validation, tests, READMEs,
      current design documents, public Skill, and packaged Skill accept
      `focused|standard|deep` and no product-mode surface accepts `quick`.
- [ ] `focused` preserves the former bounded planner behavior: no more than two
      decomposition items and four planned steps, while retaining at least one
      fetch step when Claim-level conclusions require evidence.
- [ ] Help and References explicitly state that `research --budget` currently
      changes its generated plan/metadata but does not turn the compact executor
      into the Root-led multi-agent Workflow or guarantee matching runtime call
      caps.
- [ ] `SKILL.md` contains no Research Workflow procedure, role walkthrough,
      architecture diagram, OPPO/Linux snapshot, private runtime path, or model
      deployment snapshot; every conditional Reference is reachable from its
      routing table.
- [ ] `references/research-workflow.md` owns the named trigger and complete
      focused/standard/deep execution and stopping contract.
- [ ] Public and packaged Skill trees are byte-identical; removed References do
      not remain in either tree or in dangling links/tests.
- [ ] Full Python tests, focused CLI tests, Skill validation/parity, package-data
      checks, tarball smoke, Trellis check, and `git diff --check` pass, or a
      pre-existing unrelated global validator failure is isolated with evidence.
- [ ] Preview and `lwj_dev` commits are reported separately; Smart Search main
      remains unchanged.
- [ ] Personal Skills main/macOS/Windows/Linux commits and macOS source/cache/
      Codex/Claude hashes are reported separately.
- [ ] Final report states explicitly that no push, tag, publish, or release was
      executed.

## Notes

- `budget` is retained as the legacy CLI flag name; user-facing documentation
  calls its values research depth presets.
- This task documents the compact `research` executor's current budget boundary
  but does not redesign its live candidate-fetch pipeline. A future behavior
  change must define actual request, source, and stopping limits before coding.
