# Implementation Plan: Smart Search-owned AnySearch activation

## Phase 0: isolate and protect state

- [ ] 回读 Smart Search 与个人 Skills 各目标 worktree 的 `AGENTS.md`、`CLAUDE.md` 及链接拓扑。
- [ ] 记录所有目标分支 HEAD、upstream、ahead/behind 和既有脏文件；不复用含无关修改的 worktree。
- [ ] 为 Smart Search `lwj_dev`、preview 和个人 Skills `main`、`macos`、`oppo_windows`、
  `oppo_linux` 使用隔离 worktree；Smart Search `main` 只读核对。
- [ ] 建立不含密钥值的泄漏扫描模式和测试 fixture 约束。

## Phase 1: implement on Smart Search `lwj_dev`

- [ ] 在 public 与 packaged bundled AnySearch 中加入完全一致的
  `smart_search_anysearch.py`，复用现有 Python CLI 而不修改四套上游运行时。
- [ ] 实现配置路径解析、严格双字段校验、显式参数优先和单次备用密钥尝试。
- [ ] 实现 fail-closed 鉴权：缺少显式或中央主密钥时零网络请求，禁止 `.env`、环境变量和匿名回退。
- [ ] 仅对 HTTP `401`、`403`、`429` 切换；为超时、连接错误、畸形响应、`5xx`、参数和
  schema 错误保持单次失败。
- [ ] 屏蔽错误数据中的密钥字段，不自动保存 `auto_registered` 返回值。
- [ ] 修改 `smart-search-cli/SKILL.md`：bundled 为唯一入口，删除全局 `$anysearch` 回退，
  明确配置、错误和 parked 边界；同步 packaged Skill。
- [ ] 更新 `sync_anysearch_skill.py`，证明上游刷新会保留 Smart Search-owned adapter 与
  `runtime.conf`，且不会复制任何私有配置。
- [ ] 补充 adapter 单元测试、stub HTTP 行为测试、batch item 测试、配置路径测试、文档/包
  parity 测试和 sync-preservation 测试；stub 只断言非空 Bearer 头和主/备用身份序号，不记录值。
- [ ] 运行 Smart Search focused tests、完整 suite、Trellis check 和 secret scan；修复所有失败。
- [ ] 提交 `lwj_dev`，不修改或合并到 Smart Search `main`。

## Phase 2: integrate Smart Search preview

- [ ] 将已验证的 `lwj_dev` commit 合入隔离的
  `preview/multi-source-agentic-research` worktree。
- [ ] 保留 preview 的研究系统、Agent 定义和独有修改；逐文件处理冲突，不整树覆盖。
- [ ] 重跑 focused tests、完整 suite、Skill parity、Trellis check 和 secret scan。
- [ ] 提交 preview；记录两个 Smart Search 开发分支 commit。

## Phase 3: personal Skills main-first baseline

- [ ] 从已提交且干净的 Smart Search 开发分支更新
  `skill-packages/smart-search-cli`，更新来源 commit 和本地修改说明。
- [ ] 保留 `skill-packages/anysearch`、catalog 和 upstream registry；把
  `profiles/macos.yaml`、`profiles/oppo_windows.yaml`、`profiles/oppo_linux.yaml` 中 AnySearch
  tier 改为 `parked`，刷新由 profile 生成的兼容投影。
- [ ] 更新结构/迁移说明，明确 bundled 是唯一全局入口、parked 包用于项目恢复。
- [ ] 运行 package audit、profile validation 和 secret scan，提交个人 Skills `main`。

## Phase 4: macOS gate

- [ ] 对 `macos` 运行 scoped package-aware merge，仅处理 `smart-search-cli` 与 `anysearch`。
- [ ] 保留 macOS 适配；移动实体包到 `skills_parked/anysearch`，移除 Codex/Claude 的全局
  AnySearch 投影，为 bundled adapter 配置 macOS `runtime.conf`。
- [ ] 在 `~/.config/smart-search/config.json` 原子写入已获授权的两个不同密钥，保留其他字段和
  `0600` 权限；所有输出只报告字段存在性和掩码。
- [ ] 刷新受管 immutable cache、`~/.codex/skills/smart-search-cli` 与
  `~/.claude/skills/smart-search-cli`；确认两个全局 AnySearch 链接均不存在。
- [ ] 用本地 stub 验证主成功、`401/403/429` 单次备用、非切换错误和显式参数；再运行一次
  低成本 live bundled AnySearch 查询。不得反复运行 doctor。
- [ ] 对比 source/cache/Codex/Claude 的 package 与关键文件哈希，运行 native validation，
  提交 `macos`。只有全部通过才进入下一阶段。

## Phase 5: remaining native branches

- [ ] 对 `oppo_windows` 从已提交的个人 `main` commit 运行 scoped package-aware merge；保留
  Windows 路径和清单，设置 Windows Python runtime，移动 AnySearch 到 parked，运行可在
  当前 macOS 上执行的静态/profile/package 测试并提交。
- [ ] 对 `oppo_linux` 执行同样流程，保留 Linux 的 Codex/Claude/Cursor 适配，运行静态/profile/
  package 测试并提交。
- [ ] 不把 macOS 私密配置复制到两个远端机器分支；若无法在对应主机执行 live test，明确报告为
  “分支静态验证通过，机器 live 激活未执行”，不得冒充部署成功。

## Phase 6: closeout

- [ ] 重跑 Trellis check、必要 spec 更新、所有受影响测试和全 workspace secret scan。
- [ ] 回读 PRD、design、implement、Skill 正文、profile、manifest 和 activation 结果，清除旧的
  global fallback 表述。
- [ ] 记录两个 Smart Search 开发分支 commit、个人 Skills 四个分支 commit、测试、macOS 激活与
  哈希、live 结果、Windows/Linux 验证边界，以及明确的 no-push/no-tag/no-release 状态。
- [ ] 仅在所有必需工作完成后运行 Trellis 任务收尾；保留用户既有脏改动和隔离 worktree 证据。

## Completion Record

- Smart Search `main` 保持不变；`lwj_dev` 提交为 `9b7db027fb25d1927b4272c143ccd1de3421ff5c`，preview 集成提交为 `cf68fe8d5c38124b8d0d4d2ff6df21e719c6fbbb`。
- 个人 Skills main-first 提交依次为：`main` `a9011c07770fb8bd753c9b7a409d146e536dcfb9`、`macos` `084f4ec07958dfa9d18d018ba11cc7acad4b5ead`、`oppo_windows` `e594e73f64ec7eda69084f72faf270e5c03fdab9`、`oppo_linux` `eabdeb2568f51f92f77a6f0d8be1508297f6aa00`。
- Smart Search 完整测试为 `623 passed, 3 skipped`；public/package parity 为 30 个文件；AnySearch focused suite 为 62 passed；Ruff 与 `git diff --check` 通过。
- adapter stub 覆盖主密钥成功、401/403/429 单次备用、超时/连接/畸形响应/5xx 不切换、显式单 key、无 key 零网络及每次请求非空 Bearer。
- macOS 私有配置原子写入两个不同且非空的 key 槽，模式 `0600`；证据不含值。一次 live bundled AnySearch 查询成功返回 1 条结果；未运行 doctor。
- macOS source/cache/Codex/Claude 的 `SKILL.md` SHA-256 均为 `35d9ca07edd7299f7cd5cdd43946fbfde2e3c90d81c90d244a306239aa706128`，cache commit 为 `084f4ec07958dfa9d18d018ba11cc7acad4b5ead`；Codex/Claude 的独立 AnySearch 激活均不存在。
- Windows 与 Linux 已完成 package-aware merge、active-to-parked 迁移、激活清单清理和静态测试；按用户决定，真实机器激活与 live 查询留到各自平台执行，不宣称已部署。
- 全程未 push、未 tag、未 release；未修改 CPA 或 CLIProxyAPI；既有无关脏改动保持未暂存。
