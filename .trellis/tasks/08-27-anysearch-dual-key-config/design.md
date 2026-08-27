# Design: Smart Search-owned AnySearch activation

## Audience and purpose

本文供实现与审查 Agent 使用，定义 bundled AnySearch 的唯一激活入口、双密钥读取边界和
跨机器 profile 迁移方式。实现不得依赖会话历史或密钥明文。

## Final architecture

```text
/smart-search-cli
  -> read bundled-skills/anysearch/SKILL.md
  -> read bundled runtime.conf when present
  -> run smart_search_anysearch.py
  -> explicit --api_key, or Smart Search private config
  -> existing AnySearch Python CLI transport

skills_parked/anysearch
  -> governed and recoverable
  -> absent from global activation manifests
```

AnySearch 仍是 Agent 级 bundled Skill，不进入 Smart Search provider registry，也不新增
`smart-search anysearch`、兼容命令或 provider fallback。`smart-search-cli/SKILL.md` 是集成
规则的唯一权威；bundled AnySearch 的原始命令和垂直检索参数继续由其自身 `SKILL.md` 拥有。

## Portable adapter

在 Smart Search 的 public Skill 与 packaged Skill 中各保存一份完全一致的
`bundled-skills/anysearch/scripts/smart_search_anysearch.py`。适配器：

1. 保留原 AnySearch CLI 的参数和输出；
2. 显式 `--api_key` 优先，且禁用备用密钥；
3. 未显式传参时，严格读取 Smart Search 私有配置中的主、备用字段；
4. 主密钥成功时只请求一次；HTTP `401`、`403` 或 `429` 时最多用备用密钥再请求一次；
5. 连接错误、超时、畸形响应、`5xx`、本地参数错误和 schema 错误不切换；
6. 不打印、记录或写回密钥，也不持久化响应中的 `auto_registered.api_key`；
7. 配置缺失时在网络调用前失败；不回退 `.env`、环境变量或匿名访问。

所有 AnySearch 操作均为只读检索或提取；备用密钥尝试只发生在同一次只读调用内，不构成
Smart Search 搜索任务的逻辑重放。批量搜索按单个 item 约束最多一次备用尝试，不修改全局密钥。

## Config resolution

适配器只读解析配置，不创建目录：

1. 非空 `SMART_SEARCH_CONFIG_DIR`：读取其下 `config.json`，失败时不探测其他路径；
2. Windows 且未覆盖：优先 `%LOCALAPPDATA%/smart-search/config.json`；
3. 其他平台：`~/.config/smart-search/config.json`；
4. Windows 首选文件不存在时，允许读取既有 home legacy 路径。

两个字段必须是不同的非空字符串。格式错误只返回不含值的配置错误。Smart Search 现有配置
写回必须继续保留未知字段；本任务不把 AnySearch 注册进 provider schema、doctor 或 setup。
测试 HTTP stub 必须记录请求是否存在非空 Bearer 认证头，但不得保存或输出头部值。

## Packaging and sync

- Smart Search `main` 保持不变。
- 在隔离 worktree 中先实现 `lwj_dev`，再合入
  `preview/multi-source-agentic-research`，保留 preview 的研究系统修改。
- `sync_anysearch_skill.py` 将适配器文件列为 Smart Search-owned overlay；刷新官方 AnySearch
  快照时不得删除它，原始四套 CLI 仍由上游快照管理。
- `skills/smart-search-cli` 与 packaged asset 必须完全一致。
- 个人 Skills 使用 main-first：更新 `skill-packages/smart-search-cli` 和三份 profile tier，提交
  portable baseline 后再做 package-aware merge。
- 独立 `skill-packages/anysearch` 和 catalog/upstream 登记保留；三个 profile 的 tier 改为
  `parked`。机器分支把实体目录从 `skills/anysearch` 移到
  `skills_parked/anysearch`，并从全局激活投影移除。

## Platform adaptations

- `macos`：先配置 bundled `runtime.conf` 使用可用的 Python 3，并刷新 Codex/Claude 激活。
- `oppo_windows`：macOS 验收通过后合并，保留 Windows 路径、`python` 启动方式和现有清单。
- `oppo_linux`：最后合并，保留 Linux 路径及 Codex/Claude/Cursor 投影。
- 私密配置不跨分支同步。当前用户授权的两个密钥只写当前 macOS 配置；其他机器只获得读取能力。

## Safety and rollback

- 所有仓库、任务文档、测试 fixture、命令输出和 commit diff 使用合成占位值。
- 写入 macOS 配置前创建权限受限的本地备份，原子替换后保持 `0600`。
- 回滚激活时可把 `skills_parked/anysearch` 恢复到 active tier，并恢复原激活清单；无需恢复密钥副本。
- 不 push、tag、release，不修改 CPA、CLIProxyAPI 或任何 Smart Search `main` worktree。

## Evidence source

跨运行时、配置路径和错误结构审计见
[`research/anysearch-cross-runtime-contract.md`](research/anysearch-cross-runtime-contract.md)。
