# Smart Search 桌面构建

脚本默认构建未签名测试产物；Windows 显式使用 `-SigningMode Required` 时生成自签名产物，签名失败即停止。不创建 GitHub Release、不修改 PATH，也不会读取或删除共享配置、用户结果或外部 npm CLI。每次执行都会在 `.desktop-artifacts/` 新建独立目录；失败现场保留供排查。

Python 后端固定为 PyInstaller `onedir`：`smart-search.exe`（Windows）或 `smart-search`（macOS），并验证 `smart_search/assets` 全量存在、`smart-search` 包元数据存在。`--smoke` 仅发送本机 `initialize` 与 `shutdown` 协议消息，使用本次运行目录中的空配置目录，不发真实服务商请求。

## Windows

在仓库根目录执行：

```powershell
.\desktop\scripts\Build-Windows.ps1 -PythonPath .\.venv\Scripts\python.exe -Architecture x64
```

脚本先构建并验证后端，再把 `desktop/windows` 的源文件阶段化到本次 artifact 目录中执行 `dotnet publish --self-contained true`，最后把完整 onedir 后端复制到 `publish\backend\smart-search.exe`。阶段化会跳过工作树已有的 `bin`、`obj` 和 `.desktop-artifacts`，因此每次构建不依赖或清空旧中间文件。Windows x64 与 ARM64 必须在对应架构的 Windows 上分别构建和运行；脚本会拒绝 Python 架构与目标不一致的 PyInstaller 交叉构建。本机 x64 的成功不能代表 ARM64 已验证。

脚本会查找本机已存在的 Inno Setup 6 `ISCC.exe`，但绝不安装它。找到后会额外生成仅当前用户的未签名安装包，安装目录为 `%LOCALAPPDATA%\Programs\Smart Search`；卸载只处理该应用目录，不移除 `%LOCALAPPDATA%\smart-search` 的共享配置或用户结果，也不改 PATH。未找到时 `result.json` 会标为 `not-built`，可先使用 `publish` 测试包；需要强制生成安装包时加 `-InstallerMode Required`，或用 `-InnoSetupPath` 指定已安装的编译器。

若本机已有 `innounp`，可显式加 `-BootstrapInnoSetup`。它只把固定版本的官方 Inno Setup 6.7.3 下载到本次 `.desktop-artifacts` 构建目录，核对固定 SHA-256、Pyrsys B.V. 的 Authenticode 签名与安装归档完整性，再本地解压 `ISCC.exe`；不会运行安装器、写注册表或改变 PATH。缺少 `innounp`、下载/签名/哈希/解压任一失败都会停止并保留该次目录。

更新前需要用户先处理 Smart Search 自有任务并退出 App。安装器与 App 共享 `Local\SmartSearch.Desktop` mutex，且显式禁用自动关闭、自动重启；检测到正在运行的 App 时不能原地覆盖其后端或资源。

Windows 签名覆盖自有 App EXE/DLL、后端、Setup 和卸载器，使用固定公开证书、SHA-256 和 RFC3161 时间戳。私钥从 GitHub Secrets 导入当前用户 `My`，不会导入 Root/TrustedPublisher；本地备份位于仓库外，密码受当前用户 DPAPI 保护。验签分别检查 CMS 签名、PE 内容摘要、固定证书链和时间戳，第三方文件保持原字节。说明及操作见 [Windows 签名](../docs/windows-signing.md)。

## macOS

在目标架构的 macOS 13+ 机器上执行：

```bash
bash desktop/scripts/build-macos.sh --architecture arm64 --python python3
```

脚本要求 Python、宿主机和目标架构一致，避免把 PyInstaller 的原生二进制误当成交叉编译产物。它用独立 SwiftPM scratch 目录构建 `desktop/macos` 的 `SmartSearchDesktop`，将后端放入 `Smart Search.app/Contents/Resources/backend/smart-search`，并生成同目录的未签名、未公证 DMG。Intel 构建使用 `--architecture x86_64`。

## CI 与发布边界

`.github/workflows/desktop-build.yml` 在 pull request 或普通手动触发时构建四个平台的未签名测试产物，不向 PR 提供签名 Secrets。手动开启 `sign_windows` 可生成不发布版本的自签名候选；填写已有稳定 `release_tag` 时，Windows 签名强制开启。在临时 Windows runner 安装 Inno Setup，生成两种 Windows 安装器和两种 DMG；全部构建、验签及版本/文件名校验成功后，才向已有 Release 上传包和 `SHA256SUMS.txt`。不创建 Release/Tag、不推送提交，默认不覆盖已上传附件。macOS 不签名或公证。

签名 CI 运行错误密码/证书、内容/签名/时间戳篡改及签名失败检查；在可丢弃 runner 静默安装候选并验签实际落盘的 App、后端与卸载器，不启动 GUI。结果记录在 `result.json`、`installed-signatures.json` 和签名检查结果中，随候选 artifact 提供。CI 不自动修改用户信任库；构建、验签和静默安装不能代替实机 GUI、完整升级/卸载或 SmartScreen 提示验收。

修复既有发行版的打包时，产品源码仍固定在 tag，后端打包脚本与 Windows 检查工程取工作流本次提交。只有显式开启 `replace_existing_assets` 才替换附件和校验清单。桌面后端携带固定路径的 `package.json` 版本清单，避免覆盖升级遗留的旧版 `dist-info` 干扰版本读回。

普通 Windows PR CI 仍只上传 self-contained `publish` 测试包。签名构建使用 `-signed.exe` 文件名，但始终明确属于 self-signed；未签名构建使用 `-unsigned-test.exe`。既有历史发行附件不会因源码更新而自动获得签名。

## App 和 CLI 更新

设置中的“版本与更新”分别展示 App/内置引擎与实际生效的独立 CLI。生产 App 默认启动后检查，之后每 24 小时最多检查一次，可关闭；没有后台服务。检查不会下载安装，只在点击后下载匹配平台架构的官方稳定包；新 npm 版本没有对应桌面附件时不会误报 App 可安装。

下载显示实际字节进度，可取消重试，写临时文件并验证大小和 SHA256 后才可打开。Windows 会先要求处理草稿和 App 自有任务，再退出并打开当前用户安装器；macOS 打开 DMG，由用户正常安装。下载完成和安装器启动都不等于安装完成，重新启动后核对实际版本。SHA256 不等同系统代码签名。

独立 CLI 只在确认属于普通全局 npm 或全局 mise npm 时可更新。点击前展示当前来源、路径和确切目标版本；执行仅针对 Smart Search，保留原管理器，并读回实际版本。复杂 mise 工具选项、项目范围、版本约束、未知或冲突来源保留手动说明，不改 PATH。管理器运行期间保持 App 打开，不强制取消外部任务。CLI 状态刷新会重新读取路径和版本，不执行可能自动修复运行环境的公开 wrapper。

## 环境准备与 App/CLI 解耦

“更新 Skills → 共用独立 CLI 环境”提供“检测环境 → 安装缺少的组件 → 验证可用性”。健康的 Node/npm、支持 venv/pip 的 Python 和明确来源的 CLI 优先复用。缺失时从 Node 官方 LTS 发行版和经校验的 uv/Astral CPython 准备运行环境，再安装锁定的 npm 稳定版 CLI；无需预装 mise，也不代装或登录 Codex/Claude Code。

新环境位于 `%LOCALAPPDATA%/SmartSearchTools` 或 `~/.local/share/smart-search-tools`，独立 npm prefix 在其 `cli` 子目录。它们不是 App 文件，关闭、更新或卸载 App 不会移除它们。AI 接入文件包含独立 Node 和 npm CLI 的绝对调用路径。Windows 为新安装补充自己的用户 PATH 项并提示重新打开 AI/终端；macOS 不修改 shell 配置，图形 AI 可以按技能中的完整路径调用。

“更新 Skills”统一列出所有 Agent 目标，区分 Skill 文件状态、独立 CLI 版本和实际 AI 调用。最新源是官方 npm 稳定包，下载通过 SHA512 与归档边界检查，只读取说明文件。默认每天检查并提示；用户选择目标、核对路径后才备份并更新。备份路径在结果中显示，额外文件、未选目标与历史副本保留。Codex 使用 `.agents/skills`，Claude 尊重 `CLAUDE_CONFIG_DIR`，也支持 Cursor、Copilot、Gemini、OpenCode、Cline、Roo Code 等注册目标。更新会刷新独立 CLI 的本机调用说明。离线缓存不能冒充本次最新检查成功；CLI 较旧时先在设置页更新。检查不发收费请求，AI 内调用仍由用户验证。

安装失败保留已成功组件，重新检测后补缺。只有下载可取消；包管理器写入期间保持 App 打开。实现检查必须使用隔离配置、环境和技能目录；Windows x64 的实测不代表 macOS/ARM64 或真实 AI 会话已经验证。

## 双语界面与手册

App 在设置页选择自动、简体中文或 English，偏好独立于 CLI 保存。
App 将当前语言传给私有后端；切换保留草稿与任务，环境写入或 CLI 更新期间暂不可切换。
CLI 通过 `SMART_SEARCH_LANGUAGE` 和单次 `--lang` 选择语言，命令名、机器字段及来源原文不翻译。
共享语言资源位于 `src/smart_search/assets/i18n/messages.json`，Windows 直接嵌入，macOS 资源副本须保持字节一致。

用户入口见[双语手册](../docs/guide/README.md)，命令和配置参考通过
`python scripts/generate_references.py` 从当前实现更新。环境准备与完整语言切换从 v0.1.21 起提供；本地构建脚本不会覆盖已安装的 App。
