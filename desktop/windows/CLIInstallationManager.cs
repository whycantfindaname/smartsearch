using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;
using static SmartSearch.Desktop.Localization;

namespace SmartSearch.Desktop;

internal sealed record CLIInstallation(string Id, string Executable, string[] Arguments, string Version, string Source,
    bool Compatible, string[] Manager, string Prefix, Dictionary<string, string> Environment,
    string Note = "", string[]? ManagerOptions = null)
{
    internal bool CanManage => Source is "npm" or "mise" && Manager.Length > 0;
    public string Title => $"{Source} · {Version} · {Id}";
}

internal sealed record NpmEnvironment(string NpmPath, string NodePath, string Version, string Prefix, string Modules,
    string[] Command, Dictionary<string, string> Environment)
{
    internal string Identity => NodePath + "|" + string.Join("|", Command) + "|" + Prefix;
}

internal sealed class CLIInstallationManager
{
    private const string Package = "@konbakuyomu/smart-search";
    private static readonly JsonSerializerOptions JsonOptions = new() { PropertyNamingPolicy = JsonNamingPolicy.CamelCase };
    private readonly string? _searchPath;
    private readonly string _stateFile;
    private readonly Func<Task<string>>? _versionLoader;
    private readonly Func<DateTimeOffset> _clock;
    private bool _checkedAtLaunch;
    private sealed record UpdateRecord(string Identity = "", string LatestVersion = "", bool SupportsBinary = false,
        DateTimeOffset? CheckedAt = null, DateTimeOffset? AttemptedAt = null, bool AutomaticallyChecks = true, string ManualNpmPath = "",
        string SelectedId = "", string ManualCliPath = "");
    private UpdateRecord _update = new();

    internal CLIInstallationManager(string? toolsDirectory = null, string? searchPath = null,
        Func<Task<string>>? versionLoader = null, Func<DateTimeOffset>? clock = null)
    {
        _searchPath = searchPath;
        _stateFile = Path.Combine(toolsDirectory ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SmartSearchTools"), "cli-npm-state.json");
        _versionLoader = versionLoader;
        _clock = clock ?? (() => DateTimeOffset.UtcNow);
        try
        {
            if (File.Exists(_stateFile)) _update = JsonSerializer.Deserialize<UpdateRecord>(File.ReadAllText(_stateFile), JsonOptions) ?? new();
        }
        catch (Exception error) when (error is IOException or JsonException or UnauthorizedAccessException) { }
    }

    internal List<CLIInstallation> Installations { get; private set; } = [];
    internal CLIInstallation? Selected => _update.SelectedId.Length > 0
        ? Installations.FirstOrDefault(item => item.Id.Equals(_update.SelectedId, StringComparison.OrdinalIgnoreCase)) : Installations.FirstOrDefault();
    internal NpmEnvironment? Npm { get; private set; }
    internal string ManualNpmPath => _update.ManualNpmPath;
    internal string ManualCliPath => _update.ManualCliPath;
    internal bool CanInstall => Selected is { } selected ? selected.CanManage : Npm is not null && _update.SelectedId.Length == 0;
    internal string LatestVersion => _update.LatestVersion;
    internal bool LatestSupportsBinary => _update.SupportsBinary;
    internal DateTimeOffset? CheckedAt => _update.CheckedAt;
    internal bool AutomaticallyChecks => _update.AutomaticallyChecks;
    internal bool UpdateAvailable => Selected is { } selected && ValidVersion(selected.Version)
        && ValidVersion(LatestVersion) && Version.Parse(LatestVersion) > Version.Parse(selected.Version);
    internal bool Checking { get; private set; }
    internal string CheckError { get; private set; } = "";
    internal bool Busy { get; private set; }
    internal string Message { get; private set; } = "";

    internal void SetNpmPath(string path)
    {
        _update = _update with { ManualNpmPath = Environment.ExpandEnvironmentVariables(path.Trim().Trim('"')), SelectedId = "", ManualCliPath = "" };
        SaveUpdateState();
    }

    internal void SelectInstallation(string id)
    {
        if (!Installations.Any(item => item.Id == id)) throw new InvalidOperationException(L("所选安装已不可用，请重新检测。"));
        _update = _update with { SelectedId = id };
        SaveUpdateState();
    }

    internal void SetCliPath(string path)
    {
        path = Environment.ExpandEnvironmentVariables(path.Trim().Trim('"'));
        _update = _update with { ManualCliPath = path, SelectedId = path };
        SaveUpdateState();
    }

    internal async Task DiscoverAsync()
    {
        if (Busy || Checking) return;
        Busy = true;
        Installations = [];
        Npm = null;
        Message = "";
        try
        {
            var searchPath = _searchPath ?? string.Join(Path.PathSeparator,
                Environment.GetEnvironmentVariable("PATH"), Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.User),
                Environment.GetEnvironmentVariable("PATH", EnvironmentVariableTarget.Machine));
            var paths = ManualNpmPath.Length > 0 ? [ManualNpmPath] : NpmCandidates(searchPath);
            var seen = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var npmEnvironments = new List<NpmEnvironment>();
            foreach (var path in paths)
            {
                try
                {
                    var npm = await ResolveNpmAsync(path, searchPath);
                    Npm ??= npm;
                    if (seen.Add(npm.Identity)) { npmEnvironments.Add(npm); await AddInstallationAsync(npm); }
                }
                catch (Exception error) when (error is IOException or InvalidOperationException or TimeoutException or System.ComponentModel.Win32Exception)
                { if (ManualNpmPath.Length > 0) Message = error.Message; }
            }
            if (ManualNpmPath.Length == 0) await DiscoverMiseAsync(searchPath);
            if (ManualCliPath.Length > 0) await DiscoverManualAsync();
            if (_update.SelectedId.Length > 0 && Selected is null)
                Message = L("所选安装已不可用，请重新检测或选择其他安装。");
            if (_update.SelectedId.Length == 0 && Selected is { } first) SelectInstallation(first.Id);
            if (Selected is { } chosen)
                Npm = npmEnvironments.FirstOrDefault(item => chosen.Source == "npm"
                    ? item.Prefix == chosen.Prefix && item.Command.SequenceEqual(chosen.Manager)
                    : item.NodePath == chosen.Executable) ?? Npm;
            if (Npm is not { } selectedNpm)
            {
                if (Message.Length == 0 && Selected is null) Message = L("未找到可用的 npm。请先安装 Node.js，或手动指定 npm 路径。");
                return;
            }
            if (_update.Identity != selectedNpm.Identity)
            {
                _update = _update with { Identity = selectedNpm.Identity, LatestVersion = "", SupportsBinary = false, CheckedAt = null, AttemptedAt = null };
                _checkedAtLaunch = false;
                CheckError = "";
                SaveUpdateState();
            }
        }
        finally { Busy = false; }
    }

    private string[] NpmCandidates(string searchPath)
    {
        var directories = searchPath.Split(Path.PathSeparator).Where(Path.IsPathFullyQualified).ToList();
        if (_searchPath is null)
        {
            var local = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            directories.AddRange([Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "nodejs"), Path.Combine(local, "nodejs")]);
            var miseRoots = new[] { Environment.GetEnvironmentVariable("MISE_DATA_DIR"), Path.Combine(local, "mise") };
            foreach (var mise in miseRoots.Where(root => !string.IsNullOrEmpty(root)).Distinct())
            {
                directories.Add(Path.Combine(mise!, "shims"));
                var installs = Path.Combine(mise!, "installs", "node");
                if (Directory.Exists(installs)) directories.AddRange(Directory.GetDirectories(installs).OrderByDescending(VersionFromDirectory));
            }
            var nvm = Environment.GetEnvironmentVariable("NVM_HOME");
            if (!string.IsNullOrEmpty(nvm) && Directory.Exists(nvm))
                directories.AddRange(Directory.GetDirectories(nvm, "v*").OrderByDescending(VersionFromDirectory));
            var volta = Environment.GetEnvironmentVariable("VOLTA_HOME") ?? Path.Combine(local, "Volta");
            directories.Add(Path.Combine(volta, "bin"));
            var nvmLink = Environment.GetEnvironmentVariable("NVM_SYMLINK");
            if (!string.IsNullOrEmpty(nvmLink)) directories.Add(nvmLink);
        }
        // mise may expose native npm.exe shims; prefer them to .cmd.
        return directories.Distinct(StringComparer.OrdinalIgnoreCase)
            .SelectMany(directory => new[] { Path.Combine(directory, "npm.exe"), Path.Combine(directory, "npm.cmd") })
            .Where(File.Exists).ToArray();
    }

    private static Version VersionFromDirectory(string path) => Version.TryParse(Path.GetFileName(path).TrimStart('v'), out var version) ? version : new Version();

    private static async Task<NpmEnvironment> ResolveNpmAsync(string path, string searchPath)
    {
        if (!Path.IsPathFullyQualified(path) || !File.Exists(path)) throw new InvalidOperationException(L("npm 路径无效，请选择可执行的 npm 文件。"));
        var directory = Path.GetDirectoryName(path)!;
        var node = Path.Combine(directory, "node.exe");
        if (!File.Exists(node)) throw new InvalidOperationException(L("npm 同目录下未找到 Node.js，请选择完整的 Node.js 安装。"));
        var environment = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase) { ["PATH"] = directory + Path.PathSeparator + searchPath };
        var actualNode = (await CommandAsync([node, "-p", "process.execPath"], environment)).Trim();
        if (!Path.IsPathFullyQualified(actualNode) || !File.Exists(actualNode)) throw new InvalidOperationException(L("无法确认 Node.js 的实际路径。"));
        environment["PATH"] = Path.GetDirectoryName(actualNode) + Path.PathSeparator + searchPath;
        var nodeVersion = (await CommandAsync([actualNode, "-p", "process.versions.node"], environment)).Trim();
        if (!Version.TryParse(nodeVersion, out var parsed) || parsed.Major < 18) throw new InvalidOperationException(L("请使用 Node.js 18 或更新版本。"));
        string[] command;
        var bundledNpm = Path.Combine(Path.GetDirectoryName(actualNode)!, "node_modules", "npm", "bin", "npm-cli.js");
        if (File.Exists(bundledNpm) && !File.GetAttributes(bundledNpm).HasFlag(FileAttributes.ReparsePoint)) command = [actualNode, bundledNpm];
        else
        {
            // Do not run npm.cmd through cmd.exe. Fixed Node + trusted npm-cli.js
            // preserves paths with spaces, quotes, and metacharacters as argv.
            var script = Path.Combine(directory, "node_modules", "npm", "bin", "npm-cli.js");
            if (!Path.GetExtension(path).Equals(".cmd", StringComparison.OrdinalIgnoreCase) || !File.Exists(script) || File.GetAttributes(script).HasFlag(FileAttributes.ReparsePoint))
                throw new InvalidOperationException(L("无法找到与 Node.js 配套的 npm，请重新选择 npm 路径。"));
            command = [actualNode, script];
        }
        var version = (await CommandAsync([.. command, "--version"], environment)).Trim();
        var prefix = (await CommandAsync([.. command, "prefix", "--global"], environment)).Trim();
        var modules = (await CommandAsync([.. command, "root", "--global", "--prefix", prefix], environment)).Trim();
        if (!ValidVersion(version) || !Path.IsPathFullyQualified(prefix) || !Path.IsPathFullyQualified(modules) || prefix.Contains('\n') || modules.Contains('\n'))
            throw new InvalidOperationException(L("npm 返回了无效的版本或安装目录。"));
        return new(path, actualNode, version, prefix, modules, command, environment);
    }

    private async Task AddInstallationAsync(NpmEnvironment npm, string? packageRoot = null, string source = "npm",
        string[]? manager = null, string note = "", string[]? options = null)
    {
        var root = packageRoot ?? Path.Combine(npm.Modules, "@konbakuyomu", "smart-search");
        var manifest = Path.Combine(root, "package.json");
        if (!File.Exists(manifest)) return;
        try
        {
            using var package = JsonDocument.Parse(await File.ReadAllTextAsync(manifest));
            var metadata = package.RootElement;
            if (String(metadata, "name") != Package) return;
            var environment = new Dictionary<string, string>(npm.Environment, StringComparer.OrdinalIgnoreCase)
                { ["SMART_SEARCH_PACKAGE_ROOT"] = root, ["SMART_SEARCH_NODE_PATH"] = npm.NodePath };
            var installation = new CLIInstallation(root, npm.NodePath, [Path.Combine(root, "npm", "bin", "smart-search.js")], String(metadata, "version"), source, false, manager ?? npm.Command, npm.Prefix, environment, note, options);
            // Legacy wrappers can bootstrap Python as a side effect. Never probe them.
            if (metadata.TryGetProperty("smartSearchBinary", out var binary) && binary.ValueKind == JsonValueKind.True)
            {
                try
                {
                    using var result = JsonDocument.Parse(await CommandAsync([installation.Executable, .. installation.Arguments, "--desktop-capabilities"], environment, 45));
                    var info = result.RootElement;
                    installation = installation with { Compatible = String(info, "product") == "smart-search" && String(info, "version") == installation.Version
                        && info.TryGetProperty("desktop_protocol_version", out var protocol) && protocol.TryGetInt32(out var number) && number == 1 };
                }
                catch (Exception error) when (error is IOException or JsonException or InvalidOperationException or TimeoutException or System.ComponentModel.Win32Exception) { }
            }
            if (!installation.Compatible && installation.Note.Length == 0)
                installation = installation with { Note = L("已找到 Smart Search CLI，但此版本不支持当前 App。请更新 CLI，或选择兼容的独立下载版。") };
            Installations.RemoveAll(item => item.Id.Equals(root, StringComparison.OrdinalIgnoreCase));
            Installations.Add(installation);
        }
        catch (Exception error) when (error is IOException or JsonException or UnauthorizedAccessException) { Message = L("CLI 安装信息损坏，请更新或修复。"); }
    }

    private async Task DiscoverMiseAsync(string searchPath)
    {
        var mise = searchPath.Split(Path.PathSeparator).Where(Path.IsPathFullyQualified)
            .Select(directory => Path.Combine(directory, "mise.exe")).FirstOrDefault(File.Exists);
        if (mise is null) return;
        try
        {
            const string tool = "npm:" + Package;
            var env = new Dictionary<string, string> { ["PATH"] = searchPath };
            using var installed = JsonDocument.Parse(await CommandAsync([mise, "ls", "--global", "--json", tool], env));
            var rows = installed.RootElement.ValueKind == JsonValueKind.Array ? installed.RootElement : installed.RootElement.GetProperty(tool);
            if (rows.GetArrayLength() == 0) return;
            if ((await CommandAsync([mise, "which", "--plugin", "smart-search"], env)).Trim() != tool) return;
            var entry = (await CommandAsync([mise, "which", "smart-search"], env)).Trim();
            foreach (var row in rows.EnumerateArray())
            {
                if (!row.TryGetProperty("active", out var active) || active.ValueKind != JsonValueKind.True ||
                    !row.TryGetProperty("installed", out var present) || present.ValueKind != JsonValueKind.True) continue;
                var install = String(row, "install_path");
                if (!Path.IsPathFullyQualified(install) || !Path.IsPathFullyQualified(entry) ||
                    !Path.GetFullPath(entry).StartsWith(Path.GetFullPath(install) + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) continue;
                var node = (await CommandAsync([mise, "which", "node"], env)).Trim();
                if (!Path.IsPathFullyQualified(node) || !File.Exists(node)) continue;
                node = (await CommandAsync([node, "-p", "process.execPath"], env)).Trim();
                if (!Path.IsPathFullyQualified(node) || !File.Exists(node)) continue;
                var version = (await CommandAsync([node, "-p", "process.versions.node"], env)).Trim();
                if (!Version.TryParse(version, out var nodeVersion) || nodeVersion.Major < 18) continue;
                env["PATH"] = Path.GetDirectoryName(node) + Path.PathSeparator + searchPath;
                var owner = row.GetProperty("source");
                var global = Environment.GetEnvironmentVariable("MISE_GLOBAL_CONFIG_FILE") ?? Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".config", "mise", "config.toml");
                var owned = String(owner, "type") == "mise.toml" && Path.IsPathFullyQualified(String(owner, "path")) &&
                    Path.GetFullPath(String(owner, "path")).Equals(Path.GetFullPath(global), StringComparison.OrdinalIgnoreCase) &&
                    string.IsNullOrEmpty(Environment.GetEnvironmentVariable("MISE_CONFIG_FILE")) && string.IsNullOrEmpty(Environment.GetEnvironmentVariable("MISE_ENV"));
                var options = owned ? MiseOptions((await CommandAsync([mise, "config", "get", "--global", "tools." + tool], env)).Trim(), String(row, "requested_version")) : null;
                var modules = Path.Combine(install, "node_modules");
                var context = new NpmEnvironment("", node, "", install, modules, [], env);
                await AddInstallationAsync(context, Path.Combine(modules, "@konbakuyomu", "smart-search"), "mise", options is null ? [] : [mise],
                    options is null ? L("此 mise 安装有环境覆盖或复杂版本约束，请在原终端更新。") : "", options);
                // Prefer the active global mise tool over unrelated Node npm prefixes on first discovery.
                var match = Installations.FindIndex(item => item.Source == "mise");
                if (match >= 0) { var item = Installations[match]; Installations.RemoveAt(match); Installations.Insert(0, item); }
            }
        }
        catch (Exception error) when (error is IOException or JsonException or InvalidOperationException or TimeoutException or System.ComponentModel.Win32Exception or KeyNotFoundException or ArgumentException)
        { Message = L("mise 环境检测未完成，请重新检测或手动选择 CLI。") + "\n" + error.Message; }
    }

    internal static string[]? MiseOptions(string config, string requested)
    {
        if (!ValidVersion(requested) && requested != "latest") return null;
        if (config == requested || config == "\"" + requested + "\"") return [];
        var lines = config.Split('\n', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
        if (!lines.Contains("version = \"" + requested + "\"")) return null;
        var options = new List<string>();
        foreach (var line in lines.Where(line => !line.StartsWith("version = ")))
        {
            var match = Regex.Match(line, "^allow_low_downloads = (true|false|\"true\"|\"false\")$");
            if (!match.Success) return null;
            options.AddRange(["--tool-option", "allow_low_downloads=" + match.Groups[1].Value]);
        }
        return options.ToArray();
    }

    private async Task DiscoverManualAsync()
    {
        try
        {
            if (!Path.IsPathFullyQualified(ManualCliPath) || !File.Exists(ManualCliPath) || !Path.GetExtension(ManualCliPath).Equals(".exe", StringComparison.OrdinalIgnoreCase))
                throw new InvalidOperationException(L("请选择独立下载包中的 smart-search.exe。"));
            var root = Path.GetDirectoryName(ManualCliPath)!;
            using var manifest = JsonDocument.Parse(await File.ReadAllTextAsync(Path.Combine(root, "package.json")));
            if (String(manifest.RootElement, "name") != Package || !Directory.Exists(Path.Combine(root, "_internal")))
                throw new InvalidOperationException(L("请选择完整独立下载包中的 CLI，不要选择全局 shim 或脚本。"));
            using var result = JsonDocument.Parse(await CommandAsync([ManualCliPath, "--desktop-capabilities"], timeoutSeconds: 45));
            var info = result.RootElement;
            if (String(info, "product") != "smart-search" || String(info, "version") != String(manifest.RootElement, "version") ||
                !info.TryGetProperty("desktop_protocol_version", out var protocol) || !protocol.TryGetInt32(out var number) || number != 1)
                throw new InvalidOperationException(L("所选 CLI 与当前 App 不兼容。"));
            Installations.Add(new(ManualCliPath, ManualCliPath, [], String(info, "version"), "manual", true, [], "", []));
        }
        catch (Exception error) when (error is IOException or JsonException or InvalidOperationException or TimeoutException or System.ComponentModel.Win32Exception)
        { Message = error.Message; }
    }

    internal void SetAutomaticChecks(bool enabled)
    {
        _update = _update with { AutomaticallyChecks = enabled };
        SaveUpdateState();
    }

    internal async Task CheckAutomaticallyAsync(bool onLaunch = false)
    {
        if (!AutomaticallyChecks || Npm is null || Busy || Checking) return;
        if (!(onLaunch && !_checkedAtLaunch))
        {
            if (CheckedAt is { } checkedAt && _clock() - checkedAt < TimeSpan.FromHours(24)) return;
            if (_update.AttemptedAt is { } attemptedAt && _clock() - attemptedAt < TimeSpan.FromHours(1)) return;
        }
        _checkedAtLaunch = true;
        await CheckVersionAsync();
    }

    internal async Task CheckVersionAsync()
    {
        if (Npm is not { } npm || Busy || Checking) return;
        Checking = true;
        _update = _update with { AttemptedAt = _clock() };
        SaveUpdateState();
        try
        {
            string version;
            bool supportsBinary;
            if (_versionLoader is not null) { version = await _versionLoader(); supportsBinary = true; }
            else
            {
                using var metadata = JsonDocument.Parse(await CommandAsync([.. npm.Command, "view", Package + "@latest", "--json"], npm.Environment, 60));
                version = String(metadata.RootElement, "version");
                supportsBinary = metadata.RootElement.TryGetProperty("smartSearchBinary", out var binary) && binary.ValueKind == JsonValueKind.True;
            }
            if (!ValidVersion(version)) throw new InvalidOperationException(L("无法确认 CLI 的最新版本。"));
            _update = _update with { LatestVersion = version, SupportsBinary = supportsBinary, CheckedAt = _clock() };
            CheckError = "";
            SaveUpdateState();
        }
        catch (Exception error) { CheckError = error.Message; }
        finally { Checking = false; }
    }

    private void SaveUpdateState()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(_stateFile)!);
        var temporary = _stateFile + ".tmp";
        File.WriteAllText(temporary, JsonSerializer.Serialize(_update, JsonOptions));
        File.Move(temporary, _stateFile, overwrite: true);
    }

    internal async Task InstallOrRepairAsync(string expectedVersion)
    {
        if (Busy || Checking) return;
        var previous = Selected;
        await DiscoverAsync();
        if (previous is not null && (Selected is not { } current || previous.Id != current.Id || previous.Source != current.Source ||
            previous.Version != current.Version || !previous.Manager.SequenceEqual(current.Manager) ||
            !(previous.ManagerOptions ?? []).SequenceEqual(current.ManagerOptions ?? [])))
            throw new InvalidOperationException(L("CLI 来源或版本刚刚发生变化，请重新检查后再更新。"));
        if (!CanInstall) throw new InvalidOperationException(L("请在原管理器中更新，或选择其他安装。"));
        if (!ValidVersion(expectedVersion) || expectedVersion != LatestVersion || CheckError.Length > 0) throw new InvalidOperationException(L("请先成功检查 CLI 更新。"));
        if (!LatestSupportsBinary) throw new InvalidOperationException(L("npm 上尚未发布自带运行时的 CLI，请等待新版发布后再安装。"));
        Busy = true;
        Message = L("正在通过原管理器安装或更新 CLI…");
        try
        {
            var selected = Selected;
            if (selected?.Source == "mise")
            {
                await CommandAsync([.. selected.Manager, "use", "--global", "--pin", .. selected.ManagerOptions ?? [], "npm:" + Package + "@" + expectedVersion], selected.Environment, 1800);
                _update = _update with { SelectedId = "" };
            }
            else
            {
                var command = selected?.Manager ?? Npm!.Command;
                var prefix = selected?.Prefix ?? Npm!.Prefix;
                await CommandAsync([.. command, "install", "--global", "--prefix", prefix, "--include=optional", Package + "@" + expectedVersion], selected?.Environment ?? Npm!.Environment, 1800);
            }
            Busy = false;
            await DiscoverAsync();
            if (Selected?.Version != expectedVersion || Selected?.Compatible != true) throw new InvalidOperationException(L("CLI 已安装，但运行验证未通过，请更新或修复。"));
            Message = L("CLI 安装完成，正在重新连接。");
        }
        finally { Busy = false; }
    }

    internal async Task UninstallAsync()
    {
        if (Busy || Checking || Selected is not { CanManage: true, Source: "npm" } selected) return;
        Busy = true;
        try
        {
            await CommandAsync([.. selected.Manager, "uninstall", "--global", "--prefix", selected.Prefix, Package], selected.Environment, 600);
            Installations = [];
            _update = _update with { SelectedId = "" };
            SaveUpdateState();
            Message = L("CLI 已卸载，配置和 Skills 已保留。");
        }
        finally { Busy = false; }
    }

    private static bool ValidVersion(string version) => Regex.IsMatch(version, @"^[0-9]+\.[0-9]+\.[0-9]+$");
    private static string String(JsonElement value, string name) => value.ValueKind == JsonValueKind.Object && value.TryGetProperty(name, out var property) && property.ValueKind == JsonValueKind.String ? property.GetString() ?? "" : "";

    internal static async Task<string> CommandAsync(IEnumerable<string> arguments, Dictionary<string, string>? environment = null, int timeoutSeconds = 15)
    {
        var command = arguments.ToArray();
        var start = new ProcessStartInfo(command[0]) { UseShellExecute = false, CreateNoWindow = true,
            WorkingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile),
            RedirectStandardOutput = true, RedirectStandardError = true, RedirectStandardInput = true,
            StandardOutputEncoding = System.Text.Encoding.UTF8, StandardErrorEncoding = System.Text.Encoding.UTF8 };
        foreach (var argument in command.Skip(1)) start.ArgumentList.Add(argument);
        if (environment is not null) foreach (var (key, value) in environment) start.Environment[key] = value;
        using var process = Process.Start(start) ?? throw new InvalidOperationException(L("CLI 操作未完成，请检查 npm 或重试。"));
        process.StandardInput.Close();
        var output = process.StandardOutput.ReadToEndAsync();
        var diagnostics = process.StandardError.ReadToEndAsync();
        try { await process.WaitForExitAsync().WaitAsync(TimeSpan.FromSeconds(timeoutSeconds)); }
        catch { if (!process.HasExited) process.Kill(entireProcessTree: true); throw; }
        var detail = await diagnostics;
        if (process.ExitCode != 0) throw new InvalidOperationException(L("CLI 操作未完成，请检查 npm 或重试。") + "\n" + detail[^Math.Min(detail.Length, 2000)..]);
        return await output;
    }
}
