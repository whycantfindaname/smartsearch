using System.Text.Json;
using SmartSearch.Desktop;

Console.OutputEncoding = new System.Text.UTF8Encoding(false);
if (args[0] == "--discover")
{
    var live = new CLIInstallationManager(Path.GetFullPath(args[1]));
    await live.DiscoverAsync();
    Console.WriteLine(JsonSerializer.Serialize(new { live.Message, npm = live.Npm?.NpmPath, selected = live.Selected?.Id,
        installations = live.Installations.Select(item => new { item.Id, item.Source, item.Version, item.Compatible, item.CanManage, item.Note }) }));
    return;
}
if (Environment.GetEnvironmentVariable("SMART_SEARCH_MISE_FIXTURE") is { } fixture && args[0] is "which" or "ls" or "config" or "use")
{
    var package = Path.Combine(fixture, "mise tool", "node_modules", "@konbakuyomu", "smart-search");
    var node = Path.Combine(fixture, "npm 2 & space", "node.exe");
    if (args[0] == "which") Console.WriteLine(args.Contains("--plugin") ? "npm:@konbakuyomu/smart-search" : args.Last() == "node" ? node : Path.Combine(package, "npm", "bin", "smart-search.js"));
    if (args[0] == "ls") Console.WriteLine(JsonSerializer.Serialize(new[] { new { version = "1.2.3", requested_version = "1.2.3", active = true, installed = true, install_path = Path.Combine(fixture, "mise tool"), source = new { type = "mise.toml", path = Path.Combine(fixture, "global.toml") } } }));
    if (args[0] == "config") Console.WriteLine("version = \"1.2.3\"\nallow_low_downloads = \"true\"");
    if (args[0] == "use")
    {
        File.WriteAllText(Path.Combine(fixture, "mise-operations.json"), JsonSerializer.Serialize(args));
        var manifest = Path.Combine(package, "package.json");
        File.WriteAllText(manifest, File.ReadAllText(manifest).Replace("1.2.3", "1.2.4"));
    }
    return;
}
var root = Path.GetFullPath(args[0]);
var first = Path.Combine(root, "npm 1 & space");
var second = Path.Combine(root, "npm 2 & space");
var now = DateTimeOffset.UtcNow;
var checks = 0;
var fail = false;
Task<string> Load() { checks++; return fail ? Task.FromException<string>(new IOException("offline")) : Task.FromResult("1.2.4"); }
var manager = new CLIInstallationManager(Path.Combine(root, "state"), first + Path.PathSeparator + second, Load, () => now);
await manager.DiscoverAsync();
Check(manager.Npm?.Prefix == first && manager.Selected is { Compatible: false, CanManage: true }, "Legacy installation detection");
Check(manager.Installations.Count == 2, "Discover all npm prefixes without silently replacing first selection");
Check(!File.Exists(Path.Combine(root, "legacy-executed")), "Must not run legacy Python wrapper");
manager.SelectInstallation(manager.Installations.Single(item => item.Prefix == second).Id);
await manager.DiscoverAsync();
Check(manager.Npm?.Prefix == second && manager.Selected?.Compatible == true, "Selecting an installation also selects its original npm environment");
manager.SetNpmPath(Path.Combine(root, "missing", "npm.cmd"));
await manager.DiscoverAsync();
Check(manager.Npm is null && manager.Selected is null, "Manual invalid path must not auto-fallback");
manager.SetNpmPath(Path.Combine(second, "npm.cmd"));
await manager.DiscoverAsync();
Check(manager.Npm?.Prefix == second && manager.Selected?.Compatible == true, "Manual path with spaces and ampersand must use trusted npm JS without cmd.exe");
await manager.CheckAutomaticallyAsync(onLaunch: true);
await manager.CheckAutomaticallyAsync(onLaunch: true);
Check(checks == 1 && manager.UpdateAvailable, "Startup/update notification");
now = now.AddSeconds(86399);
await manager.CheckAutomaticallyAsync();
Check(checks == 1, "Early periodic check");
now = now.AddSeconds(1);
await manager.CheckAutomaticallyAsync();
Check(checks == 2, "24 hour check");
var success = manager.CheckedAt;
fail = true;
now = now.AddHours(24);
await manager.CheckAutomaticallyAsync();
await manager.CheckAutomaticallyAsync();
Check(checks == 3 && manager.CheckedAt == success && manager.CheckError.Length > 0, "Failure cache and retry backoff");
manager.SetAutomaticChecks(false);
now = now.AddHours(24);
await manager.CheckAutomaticallyAsync();
Check(checks == 3, "Disabled preference");
fail = false;
await manager.CheckVersionAsync();
await manager.InstallOrRepairAsync("1.2.4");
Check(manager.Selected is { Compatible: true, Version: "1.2.4" }, "Postinstall verification");
var restored = new CLIInstallationManager(Path.Combine(root, "state"), first + Path.PathSeparator + second, Load, () => now);
await restored.DiscoverAsync();
Check(restored.ManualNpmPath == manager.ManualNpmPath && !restored.AutomaticallyChecks && restored.CheckedAt == manager.CheckedAt, "Persisted preferences");
await manager.UninstallAsync();
var arguments = JsonSerializer.Deserialize<string[]>(File.ReadAllText(Path.Combine(second, "operations.json")))!;
Check(arguments.SequenceEqual(["uninstall", "--global", "--prefix", second, "@konbakuyomu/smart-search"]), "Scoped uninstall arguments");
Check(File.Exists(Path.Combine(first, "node_modules", "@konbakuyomu", "smart-search", "package.json")), "Other npm installation changed");

// Run the real manager against a native fake mise process, without touching global tools.
var fakeBin = Path.Combine(root, "mise bin");
Directory.CreateDirectory(fakeBin);
foreach (var file in Directory.GetFiles(AppContext.BaseDirectory, "CLIManagementCheck.*"))
    File.Copy(file, Path.Combine(fakeBin, Path.GetFileName(file)), overwrite: true);
File.Copy(Path.Combine(AppContext.BaseDirectory, "CLIManagementCheck.exe"), Path.Combine(fakeBin, "mise.exe"), overwrite: true);
var misePackage = Path.Combine(root, "mise tool", "node_modules", "@konbakuyomu", "smart-search");
var savedPackage = Path.Combine(second, "node_modules", "@konbakuyomu", "smart-search.uninstalled");
foreach (var file in Directory.GetFiles(savedPackage, "*", SearchOption.AllDirectories))
{
    var destination = Path.Combine(misePackage, Path.GetRelativePath(savedPackage, file));
    Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
    File.Copy(file, destination);
}
var manifestPath = Path.Combine(misePackage, "package.json");
File.WriteAllText(manifestPath, File.ReadAllText(manifestPath).Replace("1.2.4", "1.2.3"));
var oldGlobal = Environment.GetEnvironmentVariable("MISE_GLOBAL_CONFIG_FILE");
try
{
    Environment.SetEnvironmentVariable("SMART_SEARCH_MISE_FIXTURE", root);
    Environment.SetEnvironmentVariable("MISE_GLOBAL_CONFIG_FILE", Path.Combine(root, "global.toml"));
    var mise = new CLIInstallationManager(Path.Combine(root, "mise state"), fakeBin + Path.PathSeparator + second, Load);
    await mise.DiscoverAsync();
    Check(mise.Selected is { Source: "mise", Compatible: true, CanManage: true }, "Resolve active mise tool outside npm prefix: " + mise.Message + " " + JsonSerializer.Serialize(mise.Installations));
    Check(mise.Selected!.ManagerOptions!.SequenceEqual(["--tool-option", "allow_low_downloads=\"true\""]), "Preserve mise tool options");
    await mise.CheckVersionAsync();
    await mise.InstallOrRepairAsync("1.2.4");
    Check(mise.Selected is { Source: "mise", Version: "1.2.4", Compatible: true }, "Mise update and reconnect");
    var use = JsonSerializer.Deserialize<string[]>(File.ReadAllText(Path.Combine(root, "mise-operations.json")))!;
    Check(use.SequenceEqual(["use", "--global", "--pin", "--tool-option", "allow_low_downloads=\"true\"", "npm:@konbakuyomu/smart-search@1.2.4"]), "Mise owns updates");
    mise.SetCliPath(Path.Combine(root, "missing", "smart-search.exe"));
    await mise.DiscoverAsync();
    Check(mise.Selected is null && !mise.CanInstall && mise.Message.Length > 0, "Missing explicit CLI must not silently switch to mise/npm");
}
finally
{
    Environment.SetEnvironmentVariable("SMART_SEARCH_MISE_FIXTURE", null);
    Environment.SetEnvironmentVariable("MISE_GLOBAL_CONFIG_FILE", oldGlobal);
}
Check(CLIInstallationManager.MiseOptions("version = \"1.2.3\"\npostinstall = \"custom\"", "1.2.3") is null, "Complex mise options are read-only");
Check(CLIInstallationManager.MiseOptions("version = \"^1\"", "^1") is null, "Do not broaden mise constraints");
Console.WriteLine("PASS: npm/mise discovery and ownership, multiple installations, legacy isolation, explicit selection, startup/24h checks, failure backoff and persistence");
static void Check(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
