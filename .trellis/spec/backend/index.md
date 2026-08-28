# Backend Development Guidelines

> The backend is the `src/smart_search` Python CLI package, its `sidecar/` companion project, and the `npm/` distribution layer. There is no frontend in this repository — the Research Workspace visualizer is a bundled single-page asset served by `src/smart_search/assets/research_visualizer/server.py`, so no frontend spec layer exists.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Provider Capability Contract](./provider-capability-contract.md) | Provider registry, capability routing, `route_enabled` semantics; asserted by `tests/test_regression.py` | Active |
| [Packaging Contract](./packaging-contract.md) | npm tarball / wheel / installed-skill-tree sync, bundled-asset coverage, version sync | Active |
| [Error Handling](./error-handling.md) | Provider error taxonomy, secret sanitization, `classify_provider_exception` usage | Active |
| [Quality Guidelines](./quality-guidelines.md) | Test isolation contract, fake-signature rule, gates, subprocess/asyncio conventions | Active |
| [Logging Guidelines](./logging-guidelines.md) | Single-logger architecture, level validation, file-logging behavior | Active |
| [Research Report Finalization Contract](./research-report-finalization-contract.md) | Citation-marked report rendering, reverse-trace validation, and Workspace projections | Active |

Repository structure is documented once, at the root [STRUCTURE.md](../../../STRUCTURE.md) — do not duplicate it here.

## House Rules

1. Specs describe the code as it is, with real file/line pointers; update them in the same change as the behavior.
2. A guideline that no longer matches the code is a bug — fix or delete it.
3. Templates that do not apply to this project get deleted, not left unfilled.
