import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_SKILL_DIR = ROOT / "skills" / "smart-search-cli"
PACKAGED_SKILL_DIR = ROOT / "src" / "smart_search" / "assets" / "skills" / "smart-search-cli"


def test_regression_does_not_create_repo_log_file():
    log_dir = ROOT / "logs"
    if not log_dir.exists():
        return
    assert not list(log_dir.glob("smart_search_*.log"))


def test_smart_search_skill_contract_enforces_cli_first():
    skill_dir = Path.home() / ".codex" / "skills" / "smart-search-cli"
    if not skill_dir.exists():
        return
    skill_files = [
        p
        for p in skill_dir.rglob("*")
        if p.is_file() and p.suffix in {".md", ".yaml", ".yml"}
    ]
    if not skill_files:
        return

    text = "\n".join(
        p.read_text(encoding="utf-8")
        for p in skill_files
    )

    forbidden_text = [
        "mcp__smart-search__",
        "get_sources",
        "get_config_info",
        "toggle_builtin_tools",
        "native web search fallback",
        "silently fallback",
    ]
    for phrase in forbidden_text:
        assert phrase not in text

    assert "native `web_search` is disabled" in text or "native web search is disabled" in text
    assert "do not silently fall back" in text


def _read_skill_tree(path: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted(path.rglob("*"))
        if p.is_file() and p.suffix in {".md", ".yaml", ".yml"}
    )


def _read_reference_tree(path: Path) -> str:
    return "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((path / "references").rglob("*"))
        if p.is_file() and p.suffix == ".md"
    )


def _skill_text_files(path: Path) -> dict[str, str]:
    return {
        p.relative_to(path).as_posix(): p.read_text(encoding="utf-8")
        for p in sorted(path.rglob("*"))
        if p.is_file() and p.suffix in {".md", ".yaml", ".yml"}
    }


def test_deep_research_skill_contract_public_and_packaged_assets_match():
    public_text = _read_skill_tree(PUBLIC_SKILL_DIR)
    packaged_text = _read_skill_tree(PACKAGED_SKILL_DIR)
    required_markers = [
        "Deep Research Mode",
        "深度搜索",
        "深度调研",
        "deep search",
        "deep research",
        "research_plan",
        "capability-based orchestration",
        "intent_signals",
        "capability_plan",
        "gap_check",
        "fetch_before_claim",
        "smart-search skills status",
        "smart-search skills update",
        "Do not treat Exa as the universal second hop",
        "Prefer Context7 before Exa",
        "smart-search deep",
        "decomposition",
        "usage_boundary",
        "search`, `exa-search`, `exa-similar`, `zhipu-search`, `context7-library`, `context7-docs`, `fetch`, and `map`",
        "`doctor` is a `preflight` action",
        "fixed topic recipe",
        "深度搜索一下最近的比特币行情",
        "platform temporary directory",
        "tempfile.gettempdir()/smart-search-evidence",
        "mock-full plus live-limited",
        "public planner entrypoint",
        "public live executor entrypoint",
        "not an executor",
        "does not change default `smart-search search`",
        "does not depend on an MCP session",
        "SMART_SEARCH_RESEARCH_PREFERRED_PROVIDERS",
        "provider advantage routing",
        "smart-search route",
        "Intent Routing Diagnostics",
        "SMART_SEARCH_INTENT_ROUTER=hybrid|rules|off",
        "INTENT_EMBEDDING_API_URL",
        "INTENT_CLASSIFIER_API_URL",
        "required_capabilities",
        "Classifier output cannot select providers",
    ]
    for marker in required_markers:
        assert marker in public_text
        assert marker in packaged_text


def test_deep_research_cli_contract_documents_plan_and_smoke_matrix():
    public_contract = _read_reference_tree(PUBLIC_SKILL_DIR)
    packaged_contract = _read_reference_tree(PACKAGED_SKILL_DIR)
    required_markers = [
        "Deep Research Skill Contract",
        "`smart-search deep` is the public offline planner command",
        "`smart-search research` is the public live executor command",
        "must not change default `smart-search search` behavior",
        "`mode`: always `deep_research`",
        "`query_mode`: always `deep`",
        "`question`: the user's research question",
        "`trigger_source`: usually `explicit_cli`",
        "`difficulty`: `standard` or `high`",
        "`intent_signals`: dimensional signals",
        "`decomposition`: subquestions for complex research",
        "`capability_plan`: the selected capability needs",
        "`evidence_policy`: default `fetch_before_claim`",
        "`preflight`: `doctor` guidance",
        "`steps`: ordered CLI command steps",
        "`gap_check`: how the agent verifies",
        "`final_answer_policy`: how to cite fetched evidence",
        "`usage_boundary`: user-facing distinction",
        "Allowed `tool` values are `search`, `exa-search`, `exa-similar`, `zhipu-search`, `context7-library`, `context7-docs`, `fetch`, and `map`",
        "`doctor` is a `preflight` action, not a `steps[]` item",
        "must not require fixed topic recipe ids",
        "fixed topic recipe ids are not required schema",
        "Mock-full coverage should cover trigger phrases",
        "research provider advantage routing",
        "`research --fallback auto` permits same-capability fallback",
        "Live-limited coverage should run `doctor`, one broad `search`, one `exa-search`, and one `fetch`",
        "`smart-search skills status --targets codex,claude,cursor,hermes --format json`",
        "`smart-search skills update --targets codex,claude,cursor,hermes --format json`",
        "Status values are `missing`, `up_to_date`, `stale`, `extra_files`, and",
        "must not change provider keys, run setup",
        "Prefer `skills status` and",
        "rerun the affected smoke until it passes or is proven to be an external provider blocker",
        "Budget limits must not break evidence policy",
        "Even `--budget focused` plans must retain at least one `fetch` step",
        "`steps[].command` and `steps[].output_path` are one contract",
        "Prefer PowerShell-safe quoted commands",
        "`tempfile.gettempdir()`",
        "explicit examples only, not the runtime default",
        "`smart-search route QUERY",
        "Route diagnostic output includes",
        "`intent_router_mode`",
        "`required_capabilities`",
        "`SMART_SEARCH_INTENT_ROUTER` accepts `hybrid`, `rules`, and `off`",
        "`INTENT_EMBEDDING_API_URL`",
        "`INTENT_CLASSIFIER_API_URL`",
        "`INTENT_ROUTER_TIMEOUT_SECONDS` defaults to `8`",
        "`deep` remains an offline planner",
    ]
    for marker in required_markers:
        assert marker in public_contract
        assert marker in packaged_contract


def test_search_error_recovery_catalog_is_the_single_instruction_source():
    catalog_relative_path = Path("references/error-recovery.md")
    public_skill = (PUBLIC_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    packaged_skill = (PACKAGED_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    public_catalog = (PUBLIC_SKILL_DIR / catalog_relative_path).read_text(encoding="utf-8")
    packaged_catalog = (PACKAGED_SKILL_DIR / catalog_relative_path).read_text(encoding="utf-8")

    entrypoint_markers = [
        "## Decision Path",
        "references/error-recovery.md",
        "before retrying, replaying, falling back, probing, or stopping",
        "Change code, tests, and specifications only when machine classification",
    ]
    contract_markers = [
        "single extensible decision catalog",
        "concurrency_limit_exceeded",
        "request_cancelled",
        "doctor_max_attempts",
        "`doctor` is a diagnostic probe, not a repair operation",
        "documentation-only operator response belongs here alone",
    ]

    for marker in entrypoint_markers:
        assert marker in public_skill
        assert marker in packaged_skill
    for marker in contract_markers:
        assert marker in public_catalog
        assert marker in packaged_catalog

    status_specific_markers = [
        "concurrency_limit_exceeded",
        "request_cancelled",
        "safe_to_replay",
        "doctor_max_attempts",
    ]
    for skill_dir in (PUBLIC_SKILL_DIR, PACKAGED_SKILL_DIR):
        for path, text in _skill_text_files(skill_dir).items():
            if path == catalog_relative_path.as_posix():
                continue
            for marker in status_specific_markers:
                assert marker not in text, f"{marker!r} must be owned by {catalog_relative_path}, not {path}"


def test_deep_research_readme_documents_capability_orchestration():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    english_markers = [
        "Deep Research is not a fixed topic recipe system",
        "smart-search research",
        "`route_policy_version`",
        "provider-advantage",
        "`intent_signals`",
        "`decomposition`",
        "`capability_plan`",
        "`gap_check`",
        "`usage_boundary`",
        "smart-search deep",
        "`exa-similar`",
        "`context7-library`",
        "smart-search skills status",
        "smart-search skills update",
        "`doctor` is preflight, not a research step",
        "smart-search route",
        "`intent_router_mode`",
        "`required_capabilities`",
        "degraded_reason",
        "Unsupported key claims must be fetched or downgraded to unverified candidates",
    ]
    chinese_markers = [
        "Deep Research 不是固定题材配方",
        "smart-search research",
        "`route_policy_version`",
        "provider 优势",
        "`intent_signals`",
        "`decomposition`",
        "`capability_plan`",
        "`gap_check`",
        "`usage_boundary`",
        "smart-search deep",
        "`exa-similar`",
        "`context7-library`",
        "smart-search skills status",
        "smart-search skills update",
        "`doctor` 只是配置预检",
        "smart-search route",
        "`intent_router_mode`",
        "`required_capabilities`",
        "degraded_reason",
        "没有 fetch 的来源标为未验证候选",
    ]
    for marker in english_markers:
        assert marker in readme
    for marker in chinese_markers:
        assert marker in readme_zh


def test_readme_language_split_and_provider_links_are_documented():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    package_json = (ROOT / "package.json").read_text(encoding="utf-8")

    assert "[简体中文](README.zh-CN.md) | English" in readme
    assert "简体中文 | [English](README.md)" in readme_zh
    assert "## 中文" not in readme
    assert "## English" not in readme
    assert "README.zh-CN.md" in package_json

    provider_markers = [
        "https://docs.x.ai/docs",
        "https://console.x.ai/team/default/api-keys",
        "https://platform.openai.com/docs",
        "https://platform.openai.com/api-keys",
        "https://docs.exa.ai/",
        "https://dashboard.exa.ai/api-keys",
        "https://context7.com/docs",
        "https://docs.bigmodel.cn/cn/guide/tools/web-search",
        "https://open.bigmodel.cn/usercenter/apikeys",
        "https://docs.tavily.com/",
        "https://app.tavily.com/home",
        "https://docs.firecrawl.dev/",
        "https://www.firecrawl.dev/app/api-keys",
    ]
    for marker in provider_markers:
        assert marker in readme
        assert marker in readme_zh


def test_deep_research_shared_skill_files_are_synchronized():
    assert _skill_text_files(PUBLIC_SKILL_DIR) == _skill_text_files(PACKAGED_SKILL_DIR)
    for skill_dir in (PUBLIC_SKILL_DIR, PACKAGED_SKILL_DIR):
        assert not (skill_dir / "references" / "current-search-flow.md").exists()
        assert not (skill_dir / "references" / "cli-contract.md").exists()


def test_agentic_research_project_agents_are_packaged_and_match():
    expected = {
        "search_scout.yaml": ("search_scout", ["DelegateRequest", "SearchTask"]),
        "source_curator.yaml": ("source_curator", ["DelegateRequest", "SearchTask", "CandidateCard[]"]),
        "evidence_miner.yaml": ("evidence_miner", ["DelegateRequest", "EvidenceMiningTask"]),
    }

    for filename, (agent_id, input_contracts) in expected.items():
        public_path = PUBLIC_SKILL_DIR / "agents" / filename
        packaged_path = PACKAGED_SKILL_DIR / "agents" / filename
        assert public_path.is_file()
        assert packaged_path.is_file()
        assert public_path.read_bytes() == packaged_path.read_bytes()

        definition = yaml.safe_load(public_path.read_text(encoding="utf-8"))
        assert definition["schema_version"] == "1"
        assert definition["id"] == agent_id
        assert definition["contracts"]["inputs"] == input_contracts
        assert definition["contracts"]["output"] == "DelegateResult"
        assert definition["deployment_defaults"] == {
            "model": "gpt-5.6-luna",
            "reasoning_effort": "max",
            "service_tier": "priority",
        }
        assert definition["permissions"]["may_create_tasks"] is False
        assert definition["permissions"]["may_spawn_descendants"] is False
        assert "registered artifact_id" in definition["instructions"]
        assert "final synthesis" in definition["instructions"]

    package_config = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert '"assets/skills/smart-search-cli/agents/*.yaml"' in package_config


def test_agentic_research_skill_uses_confirmed_architecture_and_terms():
    public_documents = {
        path.relative_to(PUBLIC_SKILL_DIR).as_posix(): path.read_text(encoding="utf-8")
        for path in PUBLIC_SKILL_DIR.rglob("*")
        if path.is_file()
        and path.suffix in {".md", ".yaml", ".yml"}
        and "bundled-skills/anysearch/"
        not in path.relative_to(PUBLIC_SKILL_DIR).as_posix()
    }
    text = "\n".join(public_documents.values())

    for deprecated in ("Native Research", "Multi-Research Planner"):
        assert deprecated not in text
    assert not re.search(
        r"focused\s*(?:/|\|)\s*standard\s*(?:/|\|)\s*deep\s*(?:/|\|)\s*max",
        text,
        flags=re.IGNORECASE,
    )

    required_markers = [
        "Root Agent is the sole semantic planner and synthesizer",
        "Provider Research Agents",
        "Firecrawl Agent",
        "Jina DeepSearch",
        "Exa Agent",
        "Tavily Research",
        "Search Scout",
        "Source Curator",
        "Evidence Miner",
        "A child may return gaps and suggestions in `DelegateResult`",
        "bundled-skills/anysearch/CONTRACT.md",
        "scripts/smart_search_anysearch.py",
        "Root may read all candidates or create any number of Curator shards",
        "ClaimSpec -> EvidenceItem -> ClaimRecord",
        "run-local and append-only",
        "registered `artifact_id` values only",
        "does not require a Mistral API key or credits",
        "does not use Vespa or Docker",
        "final citation -> ClaimRecord -> EvidenceItem",
        "[cite:<citation_id>]",
        "reference_register.json",
        "Workspace document index",
        "CandidateCard-only",
        "smart-search research-run",
        "smart-search research-environment",
    ]
    for marker in required_markers:
        assert marker in text


def test_research_workflow_mode_is_discoverable_and_packaged():
    relative_reference = Path("references/research-workflow.md")
    public_skill = (PUBLIC_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    packaged_skill = (PACKAGED_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    public_reference = (PUBLIC_SKILL_DIR / relative_reference).read_text(encoding="utf-8")
    packaged_reference = (PACKAGED_SKILL_DIR / relative_reference).read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")

    for skill_text in (public_skill, packaged_skill):
        assert "## Decision Path" in skill_text
        assert "使用 smart-search-cli 的 Research Workflow 调研 <GOAL>" in skill_text
        assert "references/research-workflow.md" in skill_text
        assert "This file is a router" in skill_text
        assert "## Multi-Source Research Flow" not in skill_text
        assert "OPPO" not in skill_text
        assert "Linux" not in skill_text
        assert "/home/" not in skill_text
        assert len(skill_text.splitlines()) < 100

    assert public_reference == packaged_reference
    for user_document in (readme, readme_zh):
        assert "使用smart-search-cli的Research Workflow调研" in user_document
        assert "not a CLI subcommand" in user_document or "不是 CLI 子命令" in user_document
    reference_markers = [
        "This short request is the complete activation surface",
        "Use `standard` when the user does not choose a depth",
        "## Research depth effects",
        "Subagents are optional execution resources",
        "not a PATH-resolved global package",
        "node <repo>/npm/bin/smart-search.js",
        "research-run capabilities --format json",
        "Do not put an entire long workflow into one `execute` call",
        "language-system",
        "error-recovery.md",
    ]
    for marker in reference_markers:
        assert marker in public_reference


def test_opencode_skill_path_contract_is_synchronized():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    public_contract = _read_reference_tree(PUBLIC_SKILL_DIR)
    packaged_contract = _read_reference_tree(PACKAGED_SKILL_DIR)
    required_markers = [
        "~/.config/opencode/skills/smart-search-cli",
        "~/.opencode/skills/smart-search-cli",
        "legacy_locations",
        "synthetic home",
    ]

    for marker in required_markers:
        assert marker in readme
        assert marker in public_contract
        assert marker in packaged_contract

    for marker in [
        "~/.config/opencode/skills/smart-search-cli",
        "~/.opencode/skills/smart-search-cli",
        "legacy_locations",
    ]:
        assert marker in readme_zh


def test_zhipu_setup_contract_public_and_packaged_assets_match():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    public_text = _read_skill_tree(PUBLIC_SKILL_DIR)
    packaged_text = _read_skill_tree(PACKAGED_SKILL_DIR)
    public_contract = _read_reference_tree(PUBLIC_SKILL_DIR)
    packaged_contract = _read_reference_tree(PACKAGED_SKILL_DIR)
    required_markers = [
        "--zhipu-api-url",
        "--zhipu-search-engine",
        "ZHIPU_API_URL",
        "ZHIPU_SEARCH_ENGINE",
        "search_std",
        "search_pro",
        "search_pro_sogou",
        "search_pro_quark",
        "Web Search API",
        "TAVILY_API_URL",
        "does not proxy Zhipu",
        "not Zhipu Chat Completions",
        "not the MCP Server",
    ]
    for marker in required_markers:
        assert marker in readme
        assert marker in public_text
        assert marker in packaged_text
    zh_required_markers = [
        "--zhipu-api-url",
        "--zhipu-search-engine",
        "ZHIPU_API_URL",
        "ZHIPU_SEARCH_ENGINE",
        "search_std",
        "search_pro",
        "search_pro_sogou",
        "search_pro_quark",
        "Web Search API",
        "TAVILY_API_URL",
        "不会代理智谱",
        "不是 Chat Completions",
        "不是 MCP Server",
    ]
    for marker in zh_required_markers:
        assert marker in readme_zh
    for marker in ["--zhipu-api-url", "--zhipu-search-engine"]:
        assert marker in public_contract
        assert marker in packaged_contract


def test_jina_and_zhipu_mcp_contract_public_and_packaged_assets_match():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    public_text = _read_skill_tree(PUBLIC_SKILL_DIR)
    packaged_text = _read_skill_tree(PACKAGED_SKILL_DIR)
    public_contract = _read_reference_tree(PUBLIC_SKILL_DIR)
    packaged_contract = _read_reference_tree(PACKAGED_SKILL_DIR)

    required_markers = [
        "JINA_API_KEY",
        "JINA_READER_API_URL",
        "JINA_RESPOND_WITH",
        "Jina Reader is `web_fetch` only",
        "Anonymous Jina Reader calls",
        "ZHIPU_MCP_API_KEY",
        "ZHIPU_MCP_SEARCH_API_URL",
        "ZHIPU_MCP_READER_API_URL",
        "ZHIPU_MCP_ZREAD_API_URL",
        "web_search_prime",
        "webReader",
        "search_doc",
        "get_repo_structure",
        "read_file",
        "Remote MCP",
        "Do not route it through the existing `/paas/v4/web_search`",
        "Coding Plan entitlement",
        "does not affect the standard minimum profile",
    ]
    for marker in required_markers:
        assert marker in public_text
        assert marker in packaged_text
        assert marker in public_contract
        assert marker in packaged_contract

    readme_markers = [
        "JINA_API_KEY",
        "Zhipu Coding Plan Remote MCP",
        "zhipu-mcp-search",
        "zhipu-mcp-reader",
        "not mixed into the existing `/paas/v4/web_search`",
        "Jina Reader is not a general search provider",
        "A normal `ZHIPU_API_KEY` for Web Search API does not prove `zhipu-mcp-search` or zread access",
    ]
    for marker in readme_markers:
        assert marker in readme

    zh_markers = [
        "JINA_API_KEY",
        "智谱 Coding Plan Remote MCP",
        "zhipu-mcp-search",
        "zhipu-mcp-reader",
        "不会混进现有 `/paas/v4/web_search`",
        "Jina Reader 不是通用搜索 provider",
        "普通 `ZHIPU_API_KEY` 能用 Web Search API，不代表能用 `zhipu-mcp-search` 或 zread",
    ]
    for marker in zh_markers:
        assert marker in readme_zh


def test_streaming_and_internal_anysearch_contract_public_and_packaged_assets_match():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    provider_contract = (ROOT / ".trellis/spec/backend/provider-capability-contract.md").read_text(encoding="utf-8")
    public_text = _read_skill_tree(PUBLIC_SKILL_DIR)
    packaged_text = _read_skill_tree(PACKAGED_SKILL_DIR)
    public_contract = _read_reference_tree(PUBLIC_SKILL_DIR)
    packaged_contract = _read_reference_tree(PACKAGED_SKILL_DIR)

    required_markers = [
        "OPENAI_COMPATIBLE_STREAM",
        "--stream",
        "--no-stream",
        "ANYSEARCH_API_KEY",
        "bundled-skills/anysearch/CONTRACT.md",
        "not a separately discoverable Skill",
        "bundled snapshot",
        "scripts/smart_search_anysearch.py",
        "SCIVERSE_API_TOKEN",
        "SCIVERSE_API_URL",
        "SCIVERSE_TIMEOUT_SECONDS",
        "sciverse-catalog",
        "sciverse-search",
        "sciverse-semantic",
        "sciverse-read",
        "sciverse-relations",
        "--retrieval",
        "--mode",
        "FILTER_OP_GTE",
        "no `collection` selector",
        "vertical_search",
        "not a registered provider",
        "not `docs_search`",
        "not required by the `standard` minimum profile",
    ]
    for marker in required_markers:
        assert marker in readme
        assert marker in public_text
        assert marker in packaged_text
        assert marker in public_contract
        assert marker in packaged_contract

    provider_contract_markers = [
        "SCIVERSE_API_TOKEN",
        "sciverse-catalog",
        "sciverse-relations",
        "--retrieval",
        "deprecated bridge",
        "no `collection` selector",
        "explicit-only",
        "Do not insert Sciverse into `docs_search`",
        "not required by and must not satisfy the `standard` minimum",
    ]
    for marker in provider_contract_markers:
        assert marker in provider_contract

    zh_required_markers = [
        "OPENAI_COMPATIBLE_STREAM",
        "ANYSEARCH_API_KEY",
        "bundled-skills/anysearch/CONTRACT.md",
        "Smart Search 私有配置",
        "SCIVERSE_API_TOKEN",
        "SCIVERSE_API_URL",
        "SCIVERSE_TIMEOUT_SECONDS",
        "sciverse-catalog",
        "sciverse-search",
        "sciverse-relations",
        "--retrieval",
        "--mode",
        "vertical_search",
        "不是 Smart Search provider",
        "不是 `docs_search`",
        "不是 `standard` 最低配置要求",
    ]
    for marker in zh_required_markers:
        assert marker in readme_zh


def test_anysearch_internal_contract_coexists_with_explicit_cli_commands():
    explicit_cli_commands = [
        "anysearch-domains",
        "anysearch-search",
        "anysearch-extract",
        "anysearch-batch",
    ]

    for skill_root in (PUBLIC_SKILL_DIR, PACKAGED_SKILL_DIR):
        bundled_contract = skill_root / "bundled-skills" / "anysearch" / "CONTRACT.md"
        assert bundled_contract.is_file()
        assert list(skill_root.rglob("SKILL.md")) == [skill_root / "SKILL.md"]

        instruction_files = [skill_root / "SKILL.md"]
        instruction_files.extend(sorted((skill_root / "references").glob("*.md")))
        instruction_files.extend(sorted((skill_root / "agents").glob("*.yaml")))
        instruction_text = "\n".join(
            path.read_text(encoding="utf-8") for path in instruction_files
        )

        assert "bundled-skills/anysearch/CONTRACT.md" in instruction_text
        assert "scripts/smart_search_anysearch.py" in instruction_text
        assert "$" + "anysearch" not in instruction_text
        assert "do not wait for or request a separately installed `/anysearch` Skill" in instruction_text
        for command in explicit_cli_commands:
            assert command in instruction_text


def test_openai_compatible_fallback_is_fail_over_not_time_slice():
    public_contract = _read_reference_tree(PUBLIC_SKILL_DIR)
    packaged_contract = _read_reference_tree(PACKAGED_SKILL_DIR)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    markers = [
        "fail-over after a hard primary-model failure, not a time slice",
        "remaining shared main-search budget",
    ]
    for marker in markers:
        assert marker in public_contract
        assert marker in packaged_contract
    assert "fail-over, not a time slice" in readme
    assert "失败后接力，不是时间片" in readme_zh


def test_openai_compatible_responses_mode_contract_is_documented_and_packaged():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    readme_zh = (ROOT / "README.zh-CN.md").read_text(encoding="utf-8")
    provider_contract = (ROOT / ".trellis/spec/backend/provider-capability-contract.md").read_text(encoding="utf-8")
    public_text = _read_skill_tree(PUBLIC_SKILL_DIR)
    packaged_text = _read_skill_tree(PACKAGED_SKILL_DIR)

    for marker in [
        "OPENAI_COMPATIBLE_API_MODE",
        "chat-completions",
        "responses",
        "named relay",
        "official",
    ]:
        assert marker in public_text
        assert marker in packaged_text
        assert marker in provider_contract

    assert "does not promise `/responses` support" in public_text
    assert "does not promise `/responses` support" in packaged_text
    assert "official protocol subset plus named relay acceptance" in provider_contract

    assert "OPENAI_COMPATIBLE_API_MODE=responses" in readme
    assert "official `model` + `instructions`/`input` request subset" in readme
    assert "OPENAI_COMPATIBLE_API_MODE=responses" in readme_zh
    assert "官方 `model` + `instructions`/`input` 请求子集" in readme_zh
