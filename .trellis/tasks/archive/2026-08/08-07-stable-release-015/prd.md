# Prepare smart-search v0.1.15 stable release

## Goal

把 `origin/main` 的 beta.8 可靠性修复、本地三个 provider 提交和 PR #21 的有效改动整合为可审计、可安装、可发布的 `v0.1.15`。先发布 `0.1.15-beta.1` 做精确安装与 live 验证，再在单独授权后发布 npm `latest` 和 GitHub `v0.1.15`。

## Confirmed Baseline

- `origin/main=667c465`，包含 OpenAI-compatible stream/non-stream、model fallback、breaker 和 telemetry。
- 本地待整合提交为 `18f4611`、`e5357cf`、`ebc8ce5`；PR #21 提交为 `6a30a9a`。
- 发布实现使用独立工作树 `D:\Dev\20_Software\21_Mine\smartsearch-release-0.1.15` 和分支 `codex/release-0.1.15`，原工作树既有 `.codestable` / `.gitattributes` 脏改动不得被修改或提交。
- 当前可 live 验证 OpenAI-compatible、Exa、Context7、AnySearch、Tavily、Jina、Firecrawl 和意图路由。
- `XAI_API_KEY`、`ZHIPU_MCP_API_KEY`、`SCIVERSE_API_TOKEN` 缺失；对应功能仅做 offline contract 验收。普通 Zhipu Web Search 当前 HTTP 429，记录为外部限流降级。
- `0.1.15-beta.1` 与 `0.1.15` 当前均未在 npm registry 发布。

## Requirements

### R1. Unified Release Baseline

- 从 `origin/main` 建立发布分支，按顺序整合本地三个提交和 PR #21，保留 contributor authorship。
- 冲突解决必须同时保留 beta.8 的 OpenAI fallback、Zhipu MCP session、Context7/AnySearch 和 Sciverse explicit-only 契约。
- PR #21 只接收当前分支缺失的 `--param`、extract 本地截断和相应测试/文档，不覆盖已 live 通过的 `get_sub_domains` 请求形状。

### R2. Context7 And AnySearch

- Context7 自动选库不得硬编码易漂移的 React library id；必须要求查询主体词与候选 title/id 有明确重合，description/trust/benchmark 仅用于加权或同分排序。
- 自动选库低置信度时回退 Exa；显式 `context7-library` 候选列表和 `context7-docs LIBRARY_ID` 保持兼容。
- `anysearch-search` 新增 repeatable `--param KEY=VALUE`；先解析 `--sub-domain-params` JSON，再由 `--param` 覆盖同名键。
- `anysearch-extract --max-length` 只在本地截断成功结果，不把 `max_length` 发给上游；非正数表示不截断。

### R3. Truthful Controls And Diagnostics

- `TAVILY_ENABLED=false` 时，Tavily 不得出现在 capability configured 列表、自动路由、doctor/live smoke 或任何网络请求中；显式 Tavily-only 命令返回 `config_error`。
- 统一 HTTP/transport 分类：400/422=`parameter_error`，401/403=`auth_error`，408/timeout=`timeout`，429=`rate_limited`，5xx/transport=`network_error`，非法 JSON=`parse_error`，MCP/tool failure=`provider_error`。
- Tavily/Firecrawl 失败必须记录为 provider attempt error，不能伪装成正常 empty；正常空结果仍保持 empty。
- live smoke 新增 `status=healthy|degraded|failed`、`skipped_cases`。存在同能力 fallback 的 provider 故障保持 `ok=true`/exit 0，但 Markdown/content 必须显示 degraded；critical failure 保持非零退出。

### R4. Optional Provider Boundaries

- Zhipu MCP 和 Sciverse 随稳定版发布，但保持 optional、experimental、explicit-only，不进入 standard profile 或默认 search/research fallback。
- 缺 key 时禁止网络请求并报告 skipped/not_configured，不得报告 live passed。
- PR #15 fastCRW 不进入本版本。

### R5. CI, Packaging And Release Safety

- 新增无密钥 PR CI：Ubuntu Node 18/Python 3.10、Ubuntu Node 24/Python 3.12、Windows Node 22/Python 3.12。
- CI 覆盖 `npm ci`、`npm test`、CLI regression、mock smoke、package dry-run、skill parity、clean tarball install smoke 和 `git diff --check`，且绝不发布。
- 发布 workflow 增加 concurrency；检测 `package.json` 从父提交变为新的稳定版本时，main push 跳过自动 beta，避免 beta.2 竞态。
- 统一 `package.json`、`package-lock.json`、`pyproject.toml` 为 `0.1.15`，同步 README、public/packaged skills、Trellis contract、beta/stable release notes。

### R6. Release Lane

- 全部源码和 package gates 通过后，手动从发布分支发布精确 `0.1.15-beta.1` 到 npm `next`。
- beta 必须通过 mise 精确安装、路径/版本回读、packaged regression、mock smoke 和可用 provider live probes。
- commit、push、PR/merge、tag、npm stable publish、GitHub stable release、远程 Issue/PR 状态变更分别保留 owner gate；本任务本轮只实施代码、测试和本地发布准备，未获后续授权不得越过远程门槛。

## Acceptance Criteria

- [ ] 发布分支包含 `667c465`、`18f4611`、`e5357cf`、`ebc8ce5` 和 PR #21 的有效行为。
- [ ] Context7 React/useEffect、React Native、无关高信任候选和低置信度 fallback 测试通过。
- [ ] AnySearch `--param` precedence、无效参数、extract 上游 payload 与本地截断测试通过。
- [ ] `TAVILY_ENABLED=false` 的 capability、routing、doctor、smoke、direct-call no-network 测试通过。
- [ ] provider error taxonomy 覆盖 auth、rate limit、parameter、server、timeout、network、parse 和 empty。
- [ ] live smoke 的 healthy/degraded/failed/skipped JSON、Markdown、content 和退出码契约通过。
- [ ] full pytest、regression、mock smoke、`npm test`、pack/publish dry-run、clean tarball install、skill parity、secret scan、`git diff --check` 全部零失败。
- [ ] PR CI 三组矩阵定义有效，release workflow 的 stable-bump/concurrency 测试通过。
- [ ] 缺失三个可选 key 明确报告 skipped/not_configured；Zhipu 429 明确记录为 degraded。
- [ ] 原工作树既有 dirty paths 未被修改或纳入发布分支。
- [ ] beta 发布前停在 owner 授权门槛，并提供精确命令、版本、测试和剩余 live blocker 清单。

## Out Of Scope

- 获取或替换三个缺失 key，解决 Zhipu 账户额度，加入 fastCRW，启用 Sciverse 默认路由。
- 无关依赖体系迁移、大规模重构、批量清理或改动原工作树 CodeStable runtime 文件。

## Key Decisions

- 版本为 `v0.1.15`；先 `0.1.15-beta.1` 再稳定版。
- Zhipu MCP 与 Sciverse 随版本发布，但缺 key 时只做 offline contract 验收。
- live degraded 保持兼容退出码 0，但增加顶层状态，避免被显示成完全健康。
- 发布实现使用独立工作树，父任务只负责跨子任务验收，不直接承载产品代码。
