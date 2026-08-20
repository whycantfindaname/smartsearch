# smartsearch 结构与维护边界

本文描述 `Skills/5-knowledge/smartsearch` 当前 checkout 的可核验结构。它是
Infra 的 companion repository，不是另一个本地运行时状态目录。目录、远端、
分支或发布入口发生变化时，应先重新检查 `git ls-files`、`package.json`、
`pyproject.toml` 和入口代码，再更新本文；不要把本机缓存或凭证写成仓库事实。

## 1. 在 Infra/Skills 中的角色

- Infra companion manifest 的 ID 是 `smartsearch`，工作区路径是
  `Skills/5-knowledge/smartsearch`，组件名是 `smart-search`，消费者是
  `smart-search-cli`。macOS profile 声明以 packaged checkout install 的方式
  提供原生 `smart-search` 命令，并由后续激活和 consumer probe 分别验证。
- 个人 fork 是 `whycantfindaname/smartsearch`，上游是
  `konbakuyomu/smartsearch`。本 checkout 的远端角色是：`fork` 指向个人 fork，
  `origin` 指向上游。
- 当前分支是 `lwj_dev`，跟踪个人 fork 的 `fork/lwj_dev`。本地提交、ahead/behind
  和远端同步状态必须在每次维护时通过 Git 回读，不能由本文推断。
- 本仓库负责可分发源码、npm/Python 包装、CLI、Skill 内容、测试和发布检查。
  Infra profile 负责把 reviewed checkout 安装到本机；用户级
  `~/.config/smart-search/config.json`、环境变量、Provider 凭证和已安装运行时
  不属于 Git 源码所有权。

### Fork 与上游同步

1. 同步前先读取本仓库 `AGENTS.md`、适用的 `.trellis/spec/`，检查 `git status`
   和当前远端角色；保留未提交的用户/并发改动。
2. 显式 fetch 后分别比较 `origin/main`、`origin` 上游分支、个人 fork 分支和
   本地 `lwj_dev` 的提交图；不能把个人提交误认为上游基线，也不能仅凭远端
   分支名判断内容已经同步。
3. 只在获准的同步任务中 merge/rebase 上游；不使用 reset、强制覆盖或删除本地
   改动。同步完成后重新检查 capability fallback、CLI 输出和 Skill 双份镜像。
4. 若分支、远端角色、Infra manifest 的 commit pin、consumer 或包发布入口改变，
   同时更新 Infra manifest/profile 和本文；本文只记录当前仓库能够验证的事实。
5. 供应商/路由合同变化还必须按 `.trellis/spec/backend/provider-capability-contract.md`
   更新实现与测试。单纯文档结构变更不改变该合同。

## 2. 顶层结构（以 `git ls-files` 为准）

| 路径 | 作用与边界 |
| --- | --- |
| `.codestable/` | Codestable 的 requirements、reference、feature/issue 记录、gates 和维护工具；其中已有部分文件是 tracked 历史/治理资料，不是运行时包内容。`.gitignore` 同时忽略未来本地 Codestable 内容。 |
| `.github/` | CI、npm 发布 workflow，以及版本发布说明；不参与 CLI 运行时。 |
| `.trellis/` | Provider capability spec、归档 task 和 workspace journal；它是开发治理资料，不会被 npm 包发布。现有 tracked 文件保留，新的本地 Trellis 内容被 `.gitignore` 忽略。 |
| `npm/` | npm 命令入口和 Node.js 安装、版本同步、测试、Skill parity、打包 smoke 脚本。 |
| `scripts/` | 仓库外层辅助检查；当前包括 `rebuild-mise-venv.ps1` 和 `test-jina-capability.ps1`。不包含 Python Provider 实现。 |
| `skills/smart-search-cli/` | 对外的 repo-local `smart-search-cli` Skill，含 `SKILL.md`、`agents/openai.yaml` 和 `references/*.md`。 |
| `src/smart_search/` | Python 包源码。`cli.py` 是 CLI 编排/渲染入口；`service.py` 是能力、Provider 和研究流程编排；`config.py` 管理配置；`intent_router.py` 管理能力路由；`providers/` 是各上游适配器；`skill_installer.py` 管理 Skill 安装；`assets/skills/` 是随包分发的 Skill 镜像。 |
| `tests/` | pytest 测试，包括 CLI、配置、intent router、各 Provider、service、smoke、回归、Skill/发布契约。测试通过 `tests/conftest.py` 把 `src` 加入 import path，并隔离配置文件。 |

重要根文件：

- `AGENTS.md` 是本仓库 Codex/Trellis 入口规则；适用的 Provider 合同在
  `.trellis/spec/backend/provider-capability-contract.md`。
- `package.json` 声明 npm 包 `@konbakuyomu/smart-search`、`smart-search` bin、
  `files` 白名单和 npm scripts；`package-lock.json` 锁定 npm 依赖及包版本。
- `pyproject.toml` 声明 Python 包 `smart-search`、Python `>=3.10`、依赖、包数据，
  以及 `smart-search = "smart_search.cli:main"` 入口。
- `README.md` 与 `README.zh-CN.md` 是用户可见的英文/中文架构、安装、Provider、
  Deep Research 和发布说明；新增 CLI/Provider/Skill 合同时应保持两份说明一致。
- `LICENSE` 是 MIT 许可；`.gitignore` 定义生成物、虚拟环境、缓存、凭证和本机
  工具目录的边界。
- `STRUCTURE.md`（本文）只描述结构、接口所有权和维护边界，不存放机器上的
  endpoint、API key、运行结果或临时路径。

## 3. npm/Python/Skill 的分层接口

### 安装与 CLI 入口

`npm/bin/smart-search.js` 是 npm 的 `smart-search` wrapper。它：

1. 从包根目录定位 `.smart-search-python` 的隔离 Python runtime；runtime 缺失时
   调用 `npm/scripts/postinstall.js` 尝试修复。
2. 以调用者当前目录作为 CLI 的 `cwd`，通过 `SMART_SEARCH_PACKAGE_ROOT` 传递包根，
   再执行 `python -m smart_search.cli ...`，并设置 UTF-8 环境。
3. 不读取本机全局 Skill 作为包内资产，也不把 npm 包目录当作默认 Skill 安装根。

`npm/scripts/postinstall.js` 要求 Python 3.10 或更新版本，创建隔离 venv 并用 pip
安装当前包；`pyproject.toml` 的 `project.scripts` 是 Python 直接调用入口。包的
`files` 白名单控制要发布的业务文件：`npm/`、Python `src/smart_search/**/*.py`、
public/packaged `smart-search-cli` Skill、`pyproject.toml`、README 和 LICENSE；npm
自身还会包含必需的 `package.json` 元数据。测试、治理资料、本地配置、凭证和虚拟
环境不属于 npm tarball。

### CLI 命令边界

命令解析和输出渲染属于 `src/smart_search/cli.py`；Provider 网络调用和研究阶段
属于 `src/smart_search/service.py`。当前入口按用途分组如下：

- 主流程：`search`、`route`、`fetch`、`map`、`deep`/`dr`、`research`/`rs`、
  `route-calibrate`。
- 文档/网页 Provider：`exa-search`、`exa-similar`、`context7-library`、
  `context7-docs`、`zhipu-search`、`zhipu-mcp-search`、`zhipu-mcp-reader`，以及
  `zhipu-mcp-search-doc`、`zhipu-mcp-repo-structure`、`zhipu-mcp-read-file`。
- 实验性垂直 Provider：`anysearch-domains`、`anysearch-search`、
  `anysearch-extract`、`anysearch-batch`，以及显式的 `sciverse-catalog`、
  `sciverse-search`、`sciverse-semantic`、`sciverse-read`、`sciverse-relations`。
- 配置、诊断和维护：`doctor`、`diagnose openai-compatible`、`setup`、
  `config path|list|set|unset`、`model current|set`、`skills status|update`、
  `smoke` 和 `regression`。

`cli-core.md` 是命令签名、别名、JSON/Markdown/content 输出字段和退出码的
集中参考；`--format json` 是 Agent/脚本的机器接口。CLI 负责参数校验、格式化、
退出码、配置读写入口和 smoke/regression 调度，不应在 Skill 内复制 Provider
网络逻辑或自行增加重试。

### Skill 边界与镜像

- `skills/smart-search-cli/**` 是源码树中的 public Skill；
  `src/smart_search/assets/skills/smart-search-cli/**` 是安装包内的 runtime asset。
  两棵树必须保持路径和内容一致，`npm run check:skill-parity` 与回归测试会检查
  这一点。修改 Skill 或其 reference 时必须同时修改两份。
- Skill 只是告诉 AI 工具何时、如何调用 PATH 中的 `smart-search`，以及如何理解
  routing、fallback 和证据字段；它本身不提供搜索访问、不保存 Provider key、
  不创建 Trellis/hooks/agents/commands，也不替代 CLI 的配置和错误分类。
- `setup --install-skills` 是首次安装兼容路径；CLI 升级后的日常同步使用
  `skills status`（只读比较）和 `skills update`（只覆盖受管 Skill 文件）。这些
  操作不能改 Provider 配置或删除额外用户文件。

## 4. Provider、能力和路由边界

`src/smart_search/service.py` 中的 `PROVIDER_PROFILES`、
`RESEARCH_PROFILE_ORDER`、`get_capability_status()` 和
`validate_minimum_profile()` 是当前能力注册与最低配置的实现入口。各 Provider
文件只负责上游适配、响应归一化和 Provider 错误；不应在 Provider 内写用户配置、
安装 Skill 或决定跨能力 fallback。

| 能力 | 当前 Provider / fallback 顺序 | CLI/用途边界 |
| --- | --- | --- |
| `main_search` | `xai-responses` -> `openai-compatible` | `search` 的主回答与 synthesis；两者是独立配置的 peer，不能复用同一个 URL/key 假造 fallback。 |
| `docs_search` | `context7` -> `exa` | `context7-library/docs` 用于库/API/框架文档；Exa 用于官方域名、论文、产品页和低噪声发现。不能把它当普通新闻 fallback。 |
| `web_search` | `zhipu` -> `zhipu-mcp` -> `tavily` -> `firecrawl` | 中文/国内/当前或补充来源发现；Zhipu REST Web Search 与 Coding Plan Remote MCP 是两层独立适配。 |
| `web_fetch` | `tavily` -> `jina` -> `zhipu-mcp-reader` -> `firecrawl` | `fetch` 和已知 URL 的证据正文；Jina 是 fetch-only，配置 key 后才满足 standard 最低 profile。 |
| `vertical_search` | `anysearch`；Sciverse 在 capability status 中标记实验性且 `route_enabled=false` | AnySearch 仅 `anysearch-*`；Sciverse 仅显式 `sciverse-*` 学术命令，不能加入默认 `search`/`research` 或 `docs_search`。 |
| `site_map` | Tavily | `map` 只做站点结构发现，不成为其他能力的 fallback。 |
| `synthesis` | 当前成功的 `main_search` provider | `research` 的最终综合只接收已 fetch/read 的证据，不再偷偷调用 web Provider。 |

统一规则：

- fallback 只能发生在同一 capability 内；`IntentRouter` 只能输出
  `docs_search`、`web_search`、`web_fetch`、`vertical_search`，不能直接选择
  Provider ID。
- `search`/`research` 可以根据 intent 追加同能力的补充路径；`deep` 是离线
  planner，不调用 Provider、远程 embeddings 或 classifier。
- `SMART_SEARCH_MINIMUM_PROFILE=standard` 要求至少配置
  `main_search`、`docs_search`、`web_fetch`；vertical 能力是可选实验能力，不能
  让最低 profile 通过。`off` 只用于本地实验和测试。
- Provider 尝试必须通过 `provider_attempts` 暴露，`error`、`empty`、`timeout` 等
  分类不能被静默吞掉；`routing_decision`、`providers_used`、`fallback_used`、
  `primary_sources` 和 `extra_sources` 是 CLI 可观测接口。`extra_sources` 是候选，
  关键结论要先 `fetch` 正文。

## 5. 自定义改动的职责边界

当前个人分支相对本地可见的 `origin/main` 差异集中在 CLI/配置、xAI Responses
生命周期、service fallback、测试、Skill/reference 镜像、README 和打包 smoke。
这些改动的职责可以按文件归纳为：

- `src/smart_search/providers/xai_responses.py`：xAI Responses 的 request ID、
  status monitor、soft/hard deadline、明确的 pre-submission 重试，以及已提交但
  结果不确定时的 `XAIRequestOutcomeUnknown`/停止重放语义。
- `src/smart_search/cli.py`：`search --timeout`、`--max-try` 的命令契约；只对
  明确的终态 xAI HTTP 504 `upstream_server_error` 做 CLI logical retry，并把
  logical attempt 写入 `provider_attempts`。
- `src/smart_search/config.py` 与 `service.py`：xAI timeout 配置、独立的能力
  profile、同能力 fallback、最低 profile 和可观测输出；Provider 之间仍保持
  原有接口边界。
- `skills/smart-search-cli/**`、`src/smart_search/assets/skills/**`、README 和
  `.trellis/spec/`：对外命令/证据/路由/发布合同的同步说明；必须保持 public 与
  packaged Skill 镜像一致。
- `tests/`、`npm/scripts/` 和 `.github/workflows/`：验证 xAI 生命周期、CLI
  UTF-8/wrapper、Provider fallback、Skill parity、tarball 内容和发布 workflow。

后续维护不应把本机 relay、个人模型、私有 endpoint、账号导出或一次性抓取结果
写进这些源码/文档；也不应借由本 fork 改写上游已确定的 CLI schema，除非同时更新
spec、service、CLI、两份 Skill 和测试。

## 6. 源码、缓存、虚拟环境、凭证和运行时

### 应该进入版本控制的内容

源码、测试、README、Skill 及其 reference、Provider spec、npm/Python 元数据、
lockfile、CI/release workflow 和经过审查的 release notes 才是可分发输入。用
`git ls-files` 判断来源清单；`find` 看到的目录不能自动视为源码。

### 不属于 tracked source 的内容

`.gitignore` 明确排除以下本地状态：`.venv/`、`.smart-search-python/`、
`node_modules/`、`src/smart_search.egg-info/`、`__pycache__/`、`.pytest_cache/`、
`dist/`、`build/`、`.env`、`.smart-search/`、`logs/`、`*.tgz` 以及本机的
`.agent/`、`.agents/`、`.claude/`、`.codex/`。当前检查还看到 `.venv/`、
`src/smart_search.egg-info/` 和 Python cache 被 Git 标记为 ignored；它们不是本次
结构清单或发布输入。`.codestable/` 和 `.trellis/` 虽有少量历史 tracked 文件，
其新的本地内容同样不应当被当成产品源码。

### 配置与凭证

- 配置优先级是进程环境变量 -> 用户配置文件 -> 默认值。macOS/Linux 默认配置
  文件为 `~/.config/smart-search/config.json`；`SMART_SEARCH_CONFIG_DIR` 可为
  CI/sandbox 指定绝对可写目录。`config list`/`doctor` 应保持 key masked。
- `XAI_*`、`OPENAI_COMPATIBLE_*`、`EXA_*`、`CONTEXT7_*`、`ZHIPU_*`、`JINA_*`、
  `TAVILY_*`、`FIRECRAWL_*`、`ANYSEARCH_*` 和 `SCIVERSE_*` 是运行时配置面；实际
  key、relay URL、日志和生成的 evidence 必须留在用户级运行时或临时目录，不能
  写入 Git、Skill、测试 artifact 或错误字符串。
- `smart-search-cli` 安装到用户级 AI-tool Skill 目录；它与本仓库的 public/packaged
  Skill 源文件是不同层次。不要把 `~/.codex/skills`、全局 shell wrapper 或本机
  `.env` 当作该仓库的分发源。

## 7. 开发与验证入口

以当前项目的孤立 Python/Node 环境执行，不要依赖个人 shell 的隐式 PATH 或配置：

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
repair/help、检查非 ASCII planner JSON，并执行 npm pack dry-run。源码 checkout 的
`regression` 执行 pytest 选定回归文件；打包安装没有 tests 时只运行内置 mock smoke，
因此 packaged regression 是安装健康检查，不替代源码回归门禁。CI 还覆盖 Ubuntu
Node 18/Python 3.10、Ubuntu Node 24/Python 3.12 和 Windows Node 22/Python 3.12，
并运行 source regression、mock smoke、Skill parity、tarball smoke 与提交差异空白
检查。

涉及 Provider/路由/输出合同时，先更新适用 spec，再补对应的 `tests/test_*.py`，
然后至少运行 source pytest、`smart-search smoke --mock --format json`、Skill parity
和 package/tarball 检查。涉及真实 key 时，提交前还要针对 exact key 做定向 secret
scan；本仓库结构文档本身不需要联网、安装或 live Provider 调用。

## 8. 何时更新本文

以下任一事实改变时，必须在同一变更中更新 `STRUCTURE.md`：

- 新增/删除 tracked 顶层目录、重要根文件、npm/Python 入口或发布白名单；
- capability/provider 注册、fallback 顺序、`search`/`research`/Skill 接口或
  public/packaged Skill 镜像关系改变；
- `.gitignore` 的缓存/凭证/运行时边界，配置文件归属或 Infra consumer/ownership
  改变；
- fork/upstream、remote role、分支、manifest pin 或本地安装方式改变。

更新时先用 `git ls-files`、`find`、入口代码、配置/打包脚本和测试核验，删除已不
成立的陈述；不记录本机临时目录、当前 key、live health 结果、工作树未跟踪产物或
未经批准的架构设想。
