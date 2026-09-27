# App、CLI 与 Skill 的职责

App 只分发原生界面和原生安装管理器，不携带搜索引擎、Python 或 CLI。App 的版本更新由 Sparkle / Velopack 独立管理：启动和每 24 小时检查，允许跳过指定版本，手动检查可重新发现。

CLI 通过用户系统中的 npm 独立安装。首页第一步选择并连接 npm 管理的 CLI，之后配置服务商和 Skills。自动查找 npm 支持常见目录及 mise/nvm/Volta，允许手动指定；无效手动路径不回退。App 只读取所选 npm 的全局目录，不扫描或接管 PATH 中的 pip/uv 开发版。

App 在 CLI 缺失、损坏或协议不兼容时仍可通过选定的 npm 安装、修复、更新和卸载 CLI。绑定配套 Node.js 和原全局 prefix；更换或卸载 CLI 前停止 App 拥有的协议进程，保留配置和 Skills。App 不下载运行环境、不提权、不改全局 npm 配置或 PATH。

Skill 的目标清单、正文、状态、安装、备份和移除由 CLI 提供。安装的 Skill 使用稳定入口，完整使用说明通过 `smart-search agent-guide` 从当前 CLI 获取。自动维护仅针对用户已接入的目标，遇到个人修改保留文件并报告；CLI 升级后的首次使用与日常检查均不依赖 App。

App 与 CLI 通过 `--desktop-capabilities` 和 JSON 行协议协商兼容性，不比较两者产品版本是否相同。

npm 主包通过精确版本 optionalDependencies 选择 macOS / Windows / Linux 的 x64 或 arm64 平台包。平台包携带冻结后的 Python 解释器、依赖及资源；启动器隔离外部 Python/venv/Conda/PyInstaller 环境。没有 postinstall，不回退到系统 Python。构建管线先验证六个平台包的真实 npm 安装，再发布平台包，最后发布主包；新平台包需配置 npm 发布权限。Linux 要求 glibc 2.35+。

CLI 默认启动时及每 24 小时检查 npm latest，只提示更新。成功时间、失败重试间隔、开关和 npm 环境身份独立持久化。更换 npm 环境清空旧检查缓存；失败不抹掉最近成功结果。正式 npm 0.1.24 尚为旧 Python 安装包，新版发布前 App 不会安装该旧流程。

自动维护回执还记录目标原先选择的 CLI 安装与配置目录。其他 CLI 副本不会改绑已接入的 Skill；切换绑定必须显式同步。
