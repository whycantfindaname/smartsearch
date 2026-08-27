# smartsearch：结构、接口与维护边界

本文面向维护 `Skills/5-knowledge/smartsearch` checkout、Infra 配套仓库清单
（companion manifest）和 `smart-search-cli` 消费者的 Agent 与维护者。它回答四个问题：
源文件在哪里、每一层负责什么、npm/Python/Skill/Provider 的边界是什么，以及什么变化
需要重新核验。

本文的事实来源按以下顺序使用：

1. Git 中的 tracked source（受版本控制的源码，用 `git ls-files` 确认）；
2. `package.json`、`package-lock.json`、`pyproject.toml`、入口代码、测试和 Skill
   reference；
3. Infra 的 companion manifest/profile（负责仓库身份、checkout 与消费者关系）；
4. 本文仅保留能够由上述材料回读的结构和维护约定。

术语在本文中保持以下边界：`source`（源码）是 Git 中的可分发文件，`cache`（缓存）是
本机生成的缓存或安装状态，`runtime`（运行时）是已安装包、隔离 Python 环境和用户配置
的执行面，`live`（在线状态）是实际 Provider 网络调用或 consumer probe 的结果。`live`
状态不由本文推断，也不写入本文。

## 导航

| 需要回答的问题 | 读取位置 |
| --- | --- |
| Infra 配套仓库、fork、upstream 和同步边界是什么？ | 第 1 节；身份事实见 Infra manifest |
| 顶层目录和根文件分别拥有哪类内容？ | 第 2 节；目录清单以 `git ls-files` 为准 |
| npm wrapper、Python 入口和 Skill 镜像怎样分层？ | 第 3 节；实现见 `npm/`、`src/smart_search/` 和 `skills/` |
| Provider、capability、fallback 和证据边界是什么？ | 第 4 节；实现见 `src/smart_search/service.py` 和 `src/smart_search/intent_router.py` |
| 改动应落在哪个文件，哪些内容不能进入 source（源码）？ | 第 5、6 节 |
| 怎样验证以及何时更新本文？ | 第 7、8 节 |

相关入口：[`AGENTS.md`](AGENTS.md)、[Provider capability contract](.trellis/spec/backend/provider-capability-contract.md)、[英文 README](README.md)、[中文 README](README.zh-CN.md)、[Stage G 研究索引与 References](docs/acceptance/stage-g-research-index.md)。
命令与 Provider 参考：[CLI contract](skills/smart-search-cli/references/cli-core.md)、[Provider routing](skills/smart-search-cli/references/provider-routing.md)、[Deep Research](skills/smart-search-cli/references/deep-research-mode.md)、[Setup and config](skills/smart-search-cli/references/setup-config.md)。

## 1. Infra 配套仓库（companion）、fork 与 upstream

- Infra companion manifest 的 ID 是 `smartsearch`，workspace path（工作区路径）是
  `Skills/5-knowledge/smartsearch`，component（组件）是 `smart-search`，consumer
  （消费者）是 `smart-search-cli`。macOS profile 负责记录 reviewed checkout（已审查
  checkout）的安装、激活与 consumer verification contract（消费者验证契约）；具体
  branch、commit 和 `live` 结果以 profile 与对应 receipt 为准。
- fork 是 `https://github.com/whycantfindaname/smartsearch.git`，upstream 是
  `https://github.com/konbakuyomu/smartsearch.git`。本 checkout 的约定是：`fork`
  用于个人仓库，`origin` 指向 upstream；remote role 变化时必须重新读取 Git 和
  Infra manifest，不能由本文推断。
- 本仓库拥有可分发 source、npm/Python 包装层、CLI、Skill source、测试和发布检查。
  Infra profile 拥有 reviewed checkout 的本机安装与消费验证；用户级
  `~/.config/smart-search/config.json`、环境变量、Provider credentials 和已安装
  runtime 不属于 Git source 的所有权。

### fork 与 upstream 的同步边界

1. 同步前读取本仓库 [`AGENTS.md`](AGENTS.md) 和适用的 [Provider capability contract](.trellis/spec/backend/provider-capability-contract.md)，检查 `git status` 与 remote role，并保留用户或并发产生的未提交改动。
2. 显式 fetch 后分别比较 upstream 基线、fork 目标分支和本地工作分支的提交图；不能把个人提交误认为 upstream 基线，也不能只凭远端分支名判断已经同步。
3. 只有获准的同步任务才能 merge/rebase upstream；不使用 reset、强制覆盖或删除本地改动。同步后重新检查 capability fallback、CLI 输出和 public/packaged Skill parity（一致性）。
4. 若 branch、remote role、Infra manifest 的 commit pin、consumer 或 package 发布入口改变，同时更新 Infra manifest/profile 和本文；本文只记录当前 source 与 manifest 能够验证的事实。
5. Provider/routing contract 变化还必须按 `.trellis/spec/backend/provider-capability-contract.md` 更新实现与测试；单纯的文档结构变化不改变该 contract。

## 2. 顶层结构（以 `git ls-files` 为准）

| 路径 | 作用与边界 |
| --- | --- |
| `.github/` | CI、npm 发布 workflow 和 release notes；不参与 CLI 运行时。 |
| `.trellis/` | 本仓库唯一的 task/spec/workspace 治理系统，包含规范、任务、平台脚本和 workspace journal；属于 tracked 开发资料，不会被 npm 包发布。机器身份与 session runtime 由 `.trellis/.gitignore` 单独排除。 |
| `.agents/`、`.claude/`、`.codex/` | Trellis 为 Codex 和 Claude Code 提供的仓库级 Skill、Agent、hook 与平台配置投影；属于 tracked 开发工具，不进入 npm runtime。 |
| `npm/` | npm CLI wrapper、Node.js 安装、版本同步、测试、Skill parity 和打包安装 smoke 脚本。 |
| `scripts/` | 仓库外层辅助检查；当前 tracked 文件是 `rebuild-mise-venv.ps1` 和 `test-jina-capability.ps1`，不包含 Python Provider 实现。 |
| `skills/smart-search-cli/` | 仓库内 public `smart-search-cli` Skill，包含 `SKILL.md`、`agents/openai.yaml` 和 `references/*.md`。 |
| `src/smart_search/` | Python package source。`cli.py` 是 CLI 编排与渲染入口；`service.py` 编排 capability、Provider 和 research；`config.py` 管理配置；`intent_router.py` 管理 capability routing；`providers/` 保存上游适配器；`skill_installer.py` 管理 Skill 安装；`assets/skills/` 保存随 package 分发的 Skill 镜像。 |
| `tests/` | pytest 测试，覆盖 CLI、配置、intent router、Provider、service、smoke、regression、Skill parity 和 release contract。`tests/conftest.py` 将 `src` 加入 import path，并将测试配置隔离到临时目录。 |

重要根文件：

- [`AGENTS.md`](AGENTS.md) 是本仓库的 Codex/Trellis 入口规则；Provider contract 在
  `.trellis/spec/backend/provider-capability-contract.md`。
- `package.json` 声明 npm package `@konbakuyomu/smart-search`，当前 package version
  为 `0.1.16`，Node.js 版本要求为 `>=18`，bin 为 `smart-search`，并声明 `files`
  白名单与 npm scripts；`package-lock.json` 锁定相同 package metadata 与 lockfile
  依赖状态。
- `pyproject.toml` 声明 Python package `smart-search`，当前 version 为 `0.1.16`，
  `requires-python` 为 `>=3.10`，声明依赖、package data，以及
  `smart-search = "smart_search.cli:main"` 入口。
- [`README.md`](README.md) 与 [`README.zh-CN.md`](README.zh-CN.md) 是面向用户的英文/中文安装、架构、Provider、Deep Research 和发布说明；新增 CLI、Provider 或 Skill contract 时应保持两份说明一致。
- `LICENSE` 是 MIT 许可；`.gitignore` 定义生成物、虚拟环境、缓存、凭证和本机工具
  目录的边界。
- `STRUCTURE.md` 只描述结构、接口所有权和维护边界，不存放机器 endpoint、API key、
  live health 结果、运行日志或临时路径。

## 3. npm、Python 与 Skill 的分层接口

### 安装与 CLI 入口

`npm/bin/smart-search.js` 是 npm package 的 `smart-search` wrapper（命令包装层）：

1. 从 package root（包根目录）定位 `.smart-search-python` 隔离 Python runtime；runtime
   缺失时
   调用 `npm/scripts/postinstall.js` 尝试修复。
2. 以调用者的当前目录作为 CLI `cwd`，通过 `SMART_SEARCH_PACKAGE_ROOT` 传递 package
   root，再执行 `python -m smart_search.cli ...`，并设置 `PYTHONIOENCODING` 与
   `PYTHONUTF8` 的 UTF-8 默认值。
3. 不读取本机全局 Skill 作为 package asset，也不把 npm package 目录当作默认 Skill
   安装根目录。

`npm/scripts/postinstall.js` 要求 Python 3.10 或更新版本，创建隔离 venv，并用 pip
安装 package root；`pyproject.toml` 的 `project.scripts` 是 Python 直接调用入口。
`package.json` 的 `files` 白名单控制 npm tarball 内容：`npm/`、Python
`src/smart_search/**/*.py`、Research Visualizer、Python 3.12 Sidecar、
`skills/smart-search-cli/**`、`src/smart_search/assets/skills/smart-search-cli/**`、
`pyproject.toml`、两份 README、`THIRD_PARTY_NOTICES.md` 和 `LICENSE`；npm 自身
还会包含必需的 `package.json` 元数据。测试、治理资料、本地配置、凭证、虚拟环境、
`__pycache__` 和编译后的 Python cache 文件不属于 npm tarball。

### CLI 命令边界

命令解析、参数校验、输出渲染和退出码属于 `src/smart_search/cli.py`；Provider 网络
调用和 research 编排属于 `src/smart_search/service.py`。当前入口按用途分组：

- 主流程：`search`、`route`、`fetch`、`map`、`deep`/`dr`、`research`/`rs`、
  `research-run`/`rr`、`research-view`/`rv`、`research-environment`/`research-env`/`renv`
  和 `route-calibrate`。后三项是 Agentic Research Preview 的 dossier 操作、只读
  Workspace 可视化和 Python 3.12 Sidecar 环境管理入口。
- 文档与网页 Provider：`exa-search`、`exa-similar`、`context7-library`、
  `context7-docs`、`zhipu-search`、`zhipu-mcp-search`、`zhipu-mcp-reader`，以及
  `zhipu-mcp-search-doc`、`zhipu-mcp-repo-structure`、`zhipu-mcp-read-file`。
- 实验性垂直能力：AnySearch 由 Agent 委托给 Smart Search Skill 内置快照或全局
  `$anysearch` Skill，不属于 CLI Provider；Sciverse 继续通过显式的
  `sciverse-catalog`、`sciverse-search`、`sciverse-semantic`、`sciverse-read`、
  `sciverse-relations` 命令提供。
- 配置、诊断与维护：`doctor`、`diagnose openai-compatible`、`setup`、
  `config path|list|set|unset`、`model current|set`、`skills status|update`、
  `smoke` 和 `regression`。

完整命令签名、别名、JSON/Markdown/content 字段和退出码以
`skills/smart-search-cli/references/cli-core.md` 为准；`--format json` 是
Agent 与脚本的机器接口。Skill 不得复制 Provider 网络逻辑或自行增加 retry loop。
`deep` 只生成 offline planner（离线计划）；`research` 才执行 live Deep Research；
两者都不能改变 `search` 的默认入口语义。

### Skill 边界与 public/packaged 镜像

- `skills/smart-search-cli/**` 是 source tree 中的 public Skill；
  `src/smart_search/assets/skills/smart-search-cli/**` 是 package 内的 packaged
  runtime asset。两棵树必须保持路径和内容一致，`npm run check:skill-parity` 与
  regression 会检查这一点；修改 Skill 或 reference 时必须同时修改两份。
- Skill 只说明 AI tool 何时、如何调用 PATH 中的 `smart-search`，以及如何理解
  routing、fallback 和 evidence 字段。它不提供搜索访问、不保存 Provider key、不
  创建 Trellis/hooks/agents/commands，也不替代 CLI 的配置和错误分类。
- Citation-backed final delivery 继续走既有 `research-run verify` 与 Workspace
  materialization：`final_synthesis.md` 内的 References 是读者投影，
  `evidence/reference_register.json` 是审计投影，`project_manifest.json` 的
  entrypoints 只是 Workspace 文档索引；结构化 Dossier、Trace、Artifact、
  EvidenceItem、ClaimRecord 与权威 `citation_verification.json` 的边界不变。
- `setup --install-skills` 是首次安装兼容路径；CLI 升级后的日常同步使用
  `skills status`（只读比较）和 `skills update`（只覆盖受管 Skill 文件）。这些
  操作不能修改 Provider 配置或删除额外的用户文件。

## 4. Provider、能力（capability）与路由（routing）边界

`src/smart_search/service.py` 中的 `PROVIDER_PROFILES`、`RESEARCH_PROFILE_ORDER`、
`get_capability_status()` 和 `validate_minimum_profile()` 是 capability 注册、路由
顺序和 minimum profile 的实现入口。各 `src/smart_search/providers/*.py` 文件只负责
上游适配、响应归一化和 Provider error；不应在 Provider 内写用户配置、安装 Skill 或
决定跨 capability fallback。

| Capability | Provider / fallback 顺序 | CLI 与用途边界 |
| --- | --- | --- |
| `main_search` | `xai-responses` -> `openai-compatible` | `search` 的主回答；两者是独立配置的 peer，不能复用同一个 URL/key 假造 fallback。 |
| `docs_search` | `context7` -> `exa` | `context7-library/docs` 用于库、API 和框架文档；Exa 用于官方域名、论文、产品页和低噪声发现，不是普通新闻 fallback。 |
| `web_search` | `zhipu` -> `zhipu-mcp` -> `tavily` -> `firecrawl` | 中文、国内、当前或补充来源发现；Zhipu REST Web Search 与 Coding Plan Remote MCP 是两层独立适配。 |
| `web_fetch` | `tavily` -> `jina` -> `zhipu-mcp-reader` -> `firecrawl` | `fetch` 和已知 URL 的证据正文；Jina 是 fetch-only，只有配置 key 才满足 standard minimum profile。 |
| `vertical_search` | bundled AnySearch Skill；Sciverse 在 capability status 中为 experimental 且 `route_enabled=false` | Agent 从 `bundled-skills/anysearch/SKILL.md` 读取并执行 AnySearch；它不是 Smart Search CLI 命令族。Sciverse 仅用于显式 `sciverse-*` 学术命令，不能加入默认 `search`/`research` 或 `docs_search`。 |
| `site_map` | `tavily` | `map` 只做站点结构发现，不成为其他 capability 的 fallback。 |
| `synthesis` | evidence-only synthesis | research 最终综合只接收已经 fetch/read 的证据，不再次调用 web Provider，也不把未抓取的 discovery candidate 当作证明。 |

统一规则：

- fallback 只能发生在同一 capability 内；`IntentRouter` 只能输出
  `docs_search`、`web_search`、`web_fetch`、`vertical_search`，不能直接选择
  Provider ID。
- `search`/`research` 可以根据 intent 追加同 capability 的 supplemental path；
  `deep` 是 offline planner，不调用 Provider、远程 embeddings 或 classifier。
- `SMART_SEARCH_MINIMUM_PROFILE=standard` 要求至少配置
  `main_search`、`docs_search`、`web_fetch`；vertical capability 是 optional
  experimental capability（可选实验能力），不能让 minimum profile 通过。`off` 只用于本地实验和测试。
- Provider attempt（尝试记录）必须通过 `provider_attempts` 暴露；`error`、`empty`、`timeout`
  等分类不能被静默吞掉。`routing_decision`、`providers_used`、`fallback_used`、
  `primary_sources` 和 `extra_sources` 是 CLI 可观测接口；`extra_sources` 是
  discovery candidate（发现候选），关键结论要先 `fetch` 正文。

## 5. 维护职责与变更边界

| 路径 | 负责内容 |
| --- | --- |
| `src/smart_search/providers/xai_responses.py` | xAI Responses 的 request ID、status monitor、soft/hard deadline、pre-submission retry，以及已提交但结果不确定时的 `XAIRequestOutcomeUnknown` 与停止重放语义。 |
| `src/smart_search/cli.py` | `search --timeout`、`--max-try` 的 CLI contract；仅对明确终态的 xAI HTTP 504 `upstream_server_error` 做 logical retry，并把 logical attempt 写入 `provider_attempts`。 |
| `src/smart_search/config.py` 与 `src/smart_search/service.py` | xAI timeout 配置、独立 capability profile、同 capability fallback、minimum profile 和可观测输出；Provider 之间保持既有接口边界。 |
| `skills/smart-search-cli/**`、`src/smart_search/assets/skills/**`、README 和 `.trellis/spec/` | 对外 command、evidence、routing 和 release contract 的同步说明；public 与 packaged Skill 镜像必须一致。 |
| `tests/`、`npm/scripts/` 和 `.github/workflows/` | 验证 xAI 生命周期、CLI UTF-8/wrapper、Provider fallback、Skill parity、tarball 内容和 release workflow。 |

本仓库的 source/doc 不应写入本机 relay、个人 model、私有 endpoint、账号导出或一次性
抓取结果；也不应借由 fork 改写 upstream 已确定的 CLI schema。若 contract 确实改变，
必须同步更新适用 spec、service、CLI、两份 Skill 和测试。

## 6. 源码（source）、缓存（cache）、虚拟环境、凭证与运行时（runtime）边界

### 应进入版本控制的内容

源码、测试、README、Skill 及其 reference、Provider spec、npm/Python 元数据、lockfile、
CI/release workflow 和经过审查的 release notes 才是可分发输入。用 `git ls-files` 判断
source 清单；`find` 看到的目录不能自动视为 source。

### 不属于 tracked source 的内容

`.gitignore` 排除以下本地状态：`.venv/`、`.smart-search-python/`、`node_modules/`、
`src/smart_search.egg-info/`、`__pycache__/`、`.pytest_cache/`、`dist/`、`build/`、
`.env`、`.smart-search/`、`logs/`、`*.tgz` 和本机 `.agent/`。仓库级 `.agents/`、
`.claude/`、`.codex/` 与 `.trellis/` 是 tracked 开发治理资料；其中机器身份、session
runtime 等私有状态由 `.trellis/.gitignore` 在目录内排除，不能当作 product source。

### configuration 与 credentials

- Configuration 优先级是进程 environment variable -> 用户 configuration file ->
  default。macOS/Linux 默认文件为 `~/.config/smart-search/config.json`；
  `SMART_SEARCH_CONFIG_DIR` 可为 CI/sandbox 指定绝对可写目录。`config list` 与
  `doctor` 必须 mask key。
- Runtime configuration 面包括 `XAI_*`、`OPENAI_COMPATIBLE_*`、`EXA_*`、
  `CONTEXT7_*`、`ZHIPU_*`、`JINA_*`、`TAVILY_*`、`FIRECRAWL_*`、`ANYSEARCH_*`、
  `SCIVERSE_*`、`SMART_SEARCH_*`、`INTENT_*` 和 `SSL_VERIFY`。实际 key、relay URL、
  日志与生成的 evidence 必须留在用户 runtime 或临时目录，不能写入 Git、Skill、
  test artifact 或 error string。
- `smart-search-cli` 可安装到用户级 AI-tool Skill 目录；例如 Codex、Claude Code
  和 Cursor 的默认相对目录分别是 `~/.codex/skills`、`~/.claude/skills` 和
  `~/.cursor/skills`。这些 installed Skill 与本仓库的 public/packaged Skill source
  是不同层次；不能把它们或本机 `.env` 当作该仓库的分发源。
- `live` provider health、installed command version、consumer probe 和本地日志属于
  runtime/Infra verification，不属于 source structure；需要记录时写入对应的
  profile/receipt，而不是本文。

## 7. 开发与验证入口

以下命令应在项目的隔离 Python/Node environment（环境）中执行，不依赖个人 shell 的隐式
PATH 或配置：

```bash
npm ci
npm test
node npm/bin/smart-search.js regression
node npm/bin/smart-search.js smoke --mock --format json
npm run check:skill-parity
npm run pack:dry
npm run smoke:tarball
git diff --check
```

`npm test` 会在 `.smart-search-python` 内安装 `.[dev]`、运行 pytest、验证 wrapper
repair/help、检查非 ASCII planner JSON，并执行 npm pack dry-run。source checkout 的
`regression` 运行 CLI、service、Provider、smoke、intent-router、regression 和 release
workflow 的选定 pytest 文件；packed install 没有 tests 时改跑内置 mock smoke，因此
packaged regression 是安装健康检查，不替代 source regression。

CI 当前覆盖 Ubuntu Node 18/Python 3.10、Ubuntu Node 24/Python 3.12 和 Windows Node
22/Python 3.12，并运行 source regression、mock smoke、Skill parity、tarball smoke 与
提交差异空白检查。涉及 Provider、routing 或 output contract 时，先更新适用 spec，
再补对应的 `tests/test_*.py`，至少运行 source pytest、
`smart-search smoke --mock --format json`、Skill parity 和 package/tarball 检查。
涉及真实 key 时，提交前还要针对 exact key 做定向 secret scan；本结构文档本身不需要
联网、安装或 live Provider call。

## 8. 何时更新本文

以下任一事实改变时，应在同一变更中更新 `STRUCTURE.md`：

- tracked 顶层目录、重要根文件、npm/Python entry point、package metadata 或发布
  allowlist 新增、删除或改变；
- capability/provider 注册、fallback 顺序、`search`/`research`/Skill contract 或
  public/packaged Skill mirror 关系改变；
- `.gitignore` 的 cache/credential/runtime 边界、configuration 所有权或 Infra
  consumer/ownership 改变；
- fork/upstream、remote role、branch、manifest pin 或本地安装方式改变。

更新时重新读取 `git ls-files`、`package.json`、`package-lock.json`、`pyproject.toml`、
入口代码、configuration/packaging scripts、Skill references 和 tests，删除已不成立的
陈述；不记录本机临时目录、当前 key、live health 结果、未跟踪 runtime artifact 或未经
批准的架构设想。
