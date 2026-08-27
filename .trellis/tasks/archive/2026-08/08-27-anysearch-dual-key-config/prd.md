# Centralize dual AnySearch keys

## Goal

让 `smart-search-cli` 成为 AnySearch 的唯一激活入口：Smart Search 在内部加载并执行
`bundled-skills/anysearch`，独立 AnySearch 从各机器 profile 的 `skills/` 移到
`skills_parked/`。bundled AnySearch 从 Smart Search 的机器私有配置读取两个有顺序的密钥，
且凭据不进入 Git、Skill 正文、Trellis 文档、缓存证据或日志。

## Confirmed Facts

- macOS 上 Codex 与 Claude 的激活目录均来自受管的 `jason-liao-skills/macos` 缓存投影。
- 全局 AnySearch 和 Smart Search 内置 AnySearch 当前均未设置 `runtime.conf`。
- AnySearch 已将 `runtime.conf` 定义为机器侧命令覆盖入口，无需新增兼容命令。
- Smart Search 配置文件权限为 `0600`；其写回逻辑会保留未由 CLI 管理的 JSON 字段。
- 用户已授权写入两个不同的 AnySearch 密钥；密钥值不得进入版本控制或验收输出。

## Requirements

- 在各平台的 Smart Search 私有配置中使用两个有顺序的字段：`ANYSEARCH_API_KEY` 为主密钥，
  `ANYSEARCH_API_KEY_FALLBACK` 为备用密钥。
- `smart-search-cli` 必须直接读取相对路径 `bundled-skills/anysearch/SKILL.md` 并执行其 CLI；
  不等待、提示或回退到全局 `/anysearch`。
- macOS、`oppo_windows` 和 `oppo_linux` 都把独立 AnySearch 从 `skills/` 移到
  `skills_parked/`，保留可恢复副本但不再写入 Codex、Claude 或 Cursor 的激活清单。
- 先在 macOS 完成配置、激活与行为验证；通过后再用 package-aware merge 将同一便携基线
  合并到 `oppo_windows` 和 `oppo_linux`，保留各平台的路径、运行时和清单适配。
- 配置路径优先使用 `SMART_SEARCH_CONFIG_DIR/config.json`，未设置时使用 Smart Search
  在当前平台既有的默认配置目录。
- 主密钥仅在服务端明确返回鉴权、权限、限流或配额拒绝时切换到备用密钥一次。
- 超时、连接错误、响应无法解析、服务端 `5xx`、本地参数或 schema 错误不得切换密钥。
- 显式传入 `--api_key` 时把它视为调用方的一次性单密钥覆盖，不读取或尝试备用密钥。
- bundled AnySearch 禁止匿名请求：没有显式 `--api_key` 且中央配置没有有效主密钥时，必须在
  发起网络请求前返回脱敏配置错误；不得回退 `.env`、环境变量或匿名访问。
- 优先保持 AnySearch 官方 Python、Node、Bash、PowerShell CLI 不变；平台适配器只复用已有
  CLI 或其结构化错误接口，不把 AnySearch 注册成 Smart Search provider。
- 不恢复 AnySearch provider 或兼容命令，不修改 Smart Search `main`，不 push、tag 或 release。

## Acceptance Criteria

- [ ] 私有配置恰好包含两个不同且非空的 AnySearch 密钥槽，文件权限为 `0600`；所有证据脱敏。
- [ ] macOS 的 Codex 与 Claude 只激活 `smart-search-cli`，不再存在可调用的全局 AnySearch；
  parked 副本仍可由管理流程定位和恢复。
- [ ] `smart-search-cli` 能从自身相对路径加载 bundled AnySearch，并读取 Smart Search 私有配置。
- [ ] 模拟主密钥成功时只发起一次请求。
- [ ] 模拟明确鉴权或配额拒绝时只依次尝试主密钥和备用密钥各一次。
- [ ] 模拟超时、连接失败、畸形响应和 `5xx` 时不切换密钥。
- [ ] 显式 `--api_key` 时不切换到配置中的备用密钥。
- [ ] 缺少中央主密钥时零网络请求并明确失败；所有实际 bundled 请求都带非空
  `Authorization: Bearer …`，测试和日志不暴露其值。
- [ ] 受管源码、不可变缓存、Codex 激活和 Claude 激活的对应内容哈希一致。
- [ ] macOS 验证通过后，`oppo_windows` 与 `oppo_linux` 完成 package-aware merge；各分支的
  active/parked 目录、激活清单和平台适配一致且验证通过。
- [ ] 仓库、Trellis 产物、测试输出和 Git diff 中不存在密钥值。

## Out of Scope

- 不把 AnySearch 接入 Smart Search provider、doctor 或 setup wizard。
- 不做轮询、并发竞速或自动持久化新注册密钥。
- 不删除 AnySearch 的 package catalog、上游来源登记或 parked 副本。

## Rollout Decision

- 先完成并验证 macOS；只有 macOS 通过后才继续 `oppo_windows` 与 `oppo_linux`。
- 独立 AnySearch 在三个机器分支均进入 `skills_parked/`，bundled AnySearch 成为唯一运行副本。

## Rollout Result

- macOS 已完成私有双 key 配置、受管激活、四层哈希核对和一次真实 bundled 查询。
- Windows 与 Linux 分支已完成便携基线合并和平台适配；真实机器验收由用户在对应平台执行。
- 任何网络请求均由 adapter 在发送前验证非空 Bearer；缺失双 key 的测试路径在本地失败且网络调用次数为零。
