# Fix Review Findings (2026-08-28 repo review)

## Background
2026-08-28 对仓库做了全面 review（626 tests 全绿），发现 2 个 P1、7 个 P2、若干 P3 问题。用户指示"能解决的都解决一下"。本任务为轻量任务，修复清单即需求来源。

## Requirements（按 review 发现逐条）
1. P1: pyproject.toml package-data 缺 `bundled-skills/anysearch/CONTRACT.md`，wheel 安装路径丢失该文件；同时存在死 glob `anysearch/SKILL.md`（c605f18 已删除该文件）。
2. P1: `SMART_SEARCH_LOG_LEVEL` 无校验，无效值导致 logger.py import 时 AttributeError，brick 整个 CLI。
3. P2: `SSL_VERIFY=false` 仅在部分 provider/call-site 生效（exa/jina/context7/zhipu_mcp/sciverse/Tavily/Firecrawl/Jina/service 内多处、provider_capabilities、research_providers、document_sidecar 忽略）。
4. P2: document_sidecar Popen 无 `encoding="utf-8"`（Windows mojibake）；同步阻塞调用被 async 路径直接 await；cli.py `_sidecar_health` 同类编码问题。
5. P2: `_save_config_file` 无 0o600（存明文 API key）。
6. P2: `utils.format_extra_sources` Tavily 去重失效（检查后不 append）。
7. P2: `SMART_SEARCH_LOG_TO_FILE=true` 时文件日志实际不写（log_info 仅 debug 才写 logger）。
8. P2: THIRD_PARTY_NOTICES.md 未覆盖 bundled AnySearch。
9. P3: check-skill-parity.js 未排除 tarball 剔除的 config.json/.env。
10. P3: 删除 .codestable/ 空目录残留（未跟踪）。
11. P3: STRUCTURE.md 顶层表缺 docs/、sidecar/、.zcode/、.terminology/；scripts/ 与 skills/ 行过时。
12. P3: README.md / README.zh-CN.md Commands 表缺 skills 命令；research-run 子命令为意译名。
13. 评估项（可能不做）: service.py 与 intent_router.py 意图关键词双份实现 —— 若两组关键词语义不同则保留并记录，不做强制统一。

## Acceptance criteria
- 上述 1-12 全部修复或有明确的不修理由；13 有明确结论。
- 新增回归测试覆盖：log level 校验、package-data 对 assets 的覆盖完整性、Tavily 去重。
- 全量 pytest 通过；`npm run check:skill-parity` 通过；`npm run pack:dry` 成功。
- 不引入新依赖；不改变现有 CLI 行为语义（除 bug 修复本身）。

## Non-goals
- 不重构 intent routing 架构；不加新 feature；不 push 远端。
