# Windows 签名与首次启动 / Signatures and first launch

## 下载与信任 / Download and trust

Windows 安装器文件名以 `-signed.exe` 结尾时，使用 Smart Search 的**自签名代码签名证书**。旧 `-unsigned-test.exe` 包没有因此变成已签名；请以对应版本的文件和验签结果为准。macOS 不属于这套 Windows 签名流程，仍未签名、未公证。

Windows 默认不信任自签名证书。请从[官方 GitHub Releases](https://github.com/konbakuyomu/smartsearch/releases)下载并核对来源。如果 SmartScreen 显示提示，且系统策略提供“更多信息 → 仍要运行”，可以在确认来源后自行选择；这只是运行选择，不是永久信任证书。不保证只提示一次，受管理设备也可能禁止继续。无需关闭 SmartScreen，也不要为使用 App 自动导入根证书。

Windows installers ending in `-signed.exe` use Smart Search's **self-signed code-signing certificate**. Older `-unsigned-test.exe` files remain unsigned. macOS is outside this Windows signing workflow and remains unsigned and unnotarized.

Windows does not trust this certificate by default. Download from the official Releases page and verify the source. If SmartScreen offers **More info → Run anyway**, decide whether to continue after checking the source. This is a run choice, not permanent certificate trust; future downloads may prompt again, and managed devices may prohibit it. Do not disable SmartScreen or automatically import a root certificate.

## 公开身份 / Public identity

- Subject: `CN=Smart Search`
- [公开证书 / Public certificate](../desktop/packaging/windows/smart-search.cer)
- [指纹与到期时间 / Fingerprint and expiry](../desktop/packaging/windows/smart-search.json)
- SHA-256: `9BECD07F73FF0B9ECB10D9C7D6D9B2E48584FBC6FA3D4759BF6661892DBBB35B`

公开 CER 不含私钥。可用 PowerShell 读取安装器的签名者指纹（将路径替换为实际下载文件）：

The public CER contains no private key. Read the installer signer's fingerprint in PowerShell, replacing the path with your downloaded file:

```powershell
$signature = Get-AuthenticodeSignature -LiteralPath 'C:\Downloads\SmartSearch-version-win-x64-Setup-signed.exe'
$signature.SignerCertificate.GetCertHashString([Security.Cryptography.HashAlgorithmName]::SHA256)
$signature.Status
```

指纹一致只确认签名者身份；完整性与时间戳仍须单独验证。自签名在未信任机器上可能显示 `NotTrusted` 或 `UnknownError`，不能仅凭这些文字判断文件完整，也不能忽略所有同名错误。发布构建使用项目验签脚本同时检查 CMS 签名、PE 内容、固定证书和时间戳，只有未信任自签名根这一限制被明确区分。

A matching fingerprint identifies the signer; it does not replace integrity or timestamp checks. Self-signed files may show `NotTrusted` or `UnknownError` on an untrusted machine. Do not treat every such error as harmless. The build verifier checks CMS signatures, PE contents, the pinned certificate and timestamps separately.

## 维护者：生成与保管 / Maintainers: identity storage

首次生成使用 PowerShell 7；已有证书时脚本拒绝覆盖。Windows x64 与 ARM64 共用同一身份，不在每次 CI 中重新生成。

Generate once with PowerShell 7. The script refuses to replace an existing identity. Both Windows architectures reuse the same certificate across builds.

```powershell
./desktop/scripts/New-WindowsSigningIdentity.ps1
```

默认加密 PFX 位于 `%LOCALAPPDATA%/SmartSearch/signing/windows/smart-search.pfx`，目录仅当前用户可访问。`password.dpapi` 是当前 Windows 用户绑定的密码备份，不是可跨账户直接使用的明文密码；维护者迁移账户前应通过自己的安全凭据保管方式准备恢复材料。仓库只保留 CER 和公开元数据，禁止提交 PFX/P12、密码、Base64 私钥或把它们打包进 artifact。

The encrypted PFX is stored outside the repository in the current user's restricted directory. Its `password.dpapi` backup is bound to that Windows account. Prepare recovery material in your own secure credential store before migrating accounts. Only the CER and public metadata belong in Git; never commit or upload private containers/passwords as artifacts.

GitHub Actions Secrets（分别保存，不在日志回显 / separate values, never print them）：

- `SMART_SEARCH_WINDOWS_PFX_BASE64`: 加密 PFX 的 Base64 / Base64 of the encrypted PFX.
- `SMART_SEARCH_WINDOWS_PFX_PASSWORD`: PFX 导出密码 / PFX export password.

## 维护者：构建与验收 / Maintainers: build and verification

`Import-WindowsSigningIdentity.ps1` 从上述环境变量导入并核对公开 CER、用途、期限和私钥，仅写入 `CurrentUser/My`。导入后清除该进程中的秘密环境变量，构建子进程无需密码。不会修改 Root 或 TrustedPublisher。

The import script validates the identity and imports it into `CurrentUser/My`, then clears secret environment variables in that process. It does not modify trusted roots or publishers.

```powershell
./desktop/scripts/Import-WindowsSigningIdentity.ps1
./desktop/scripts/Build-Windows.ps1 -PythonPath .venv/Scripts/python.exe -Architecture x64 -InstallerMode Required -SigningMode Required
```

`Required` 缺密钥、签名失败、验签失败时均停止；默认 `Skip` 仅生成未签名测试物。签名覆盖 App EXE/DLL、冻结后端、安装器与卸载器。其他文件逐一核对 SHA-256，防止误签第三方库。Inno 临时卸载器的签名副本和记录保存在独立构建目录。签名用 SHA-256 和 DigiCert RFC3161 时间戳；核验时间戳签名及其 CA 链，不把文件 SHA256 清单当作代码签名。

`Required` fails if keys, signing or verification fail; the default `Skip` builds unsigned tests. Signing covers the App EXE/DLL, frozen backend, installer and uninstaller. Other files retain their hashes. The verifier checks the RFC3161 timestamp's signature and CA chain; checksums are not code signatures.

在 **Actions → Desktop packages → Run workflow** 开启 `sign_windows`、保持 `release_tag` 为空，即可构建不发布版本的候选。PR 不读取 Secrets。填写 `release_tag` 会强制 Windows 签名，并在全部平台成功后上传到已有 Release，属于显式发布操作。CI runner 会移除导入的签名私钥，并静默安装候选检查实际安装文件的签名；不会启动 App 界面。查看签名 artifact 的 `result.json`、`installed-signatures.json` 与 14 项签名负面检查记录。

In **Actions → Desktop packages → Run workflow**, enable `sign_windows` and leave `release_tag` empty for candidates without publishing. PRs receive no signing secrets. A nonempty `release_tag` requires Windows signatures and uploads to the existing Release only after all platforms succeed. CI removes its imported private key and silently installs the candidate to verify installed signatures without opening the App. Inspect the signing artifacts; CI success does not prove device GUI acceptance or remove SmartScreen warnings.
