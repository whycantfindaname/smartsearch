using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Windows.Storage.Pickers;
using WinRT.Interop;
using static SmartSearch.Desktop.Localization;

namespace SmartSearch.Desktop;

public sealed partial class MainWindow
{
    private ContentControl? _nativeCliState;
    private bool _cliFirstStep;
    private bool CliBlocked => _cliManager.Busy || _cliManager.Checking || AppInstallBlocked;

    private ContentControl BuildNativeCliPanel(bool firstStep = false)
    {
        _cliFirstStep = firstStep;
        _nativeCliState = new ContentControl { HorizontalContentAlignment = HorizontalAlignment.Stretch };
        RenderCliState();
        return Card(_nativeCliState);
    }

    private void RenderCliState()
    {
        if (_nativeCliState is null) return;
        var state = new StackPanel { Spacing = 12 };
        var actions = new List<UIElement>();
        if (_cliManager.Npm is null && _cliManager.Selected is null)
            actions.Add(ActionButton(L("安装 Node.js"), async () =>
                { await Windows.System.Launcher.LaunchUriAsync(new Uri("https://nodejs.org/en/download")); }, primary: true));
        else if (_cliManager.CanInstall && (_cliManager.Selected?.Compatible != true || _cliManager.UpdateAvailable))
            actions.Add(ActionButton(CliInstallTitle(), () => ManageNativeCliAsync(remove: false), primary: true,
                operationKey: "native-cli-install", busyText: L("处理中…"), enabled: () => !CliBlocked && !CliReleaseUnavailable));
        if (!_backend.IsConnected)
            actions.Add(ActionButton(L("重新检测"), ConnectAsync, operationKey: "connect", enabled: () => !CliBlocked));
        actions.Add(ActionButton(L("环境详情…"), ShowCliSettingsAsync));
        if (_cliManager.Selected?.Compatible != true)
        {
            actions.Add(new HyperlinkButton { Content = L("手动下载 CLI"), NavigateUri = new Uri("https://github.com/konbakuyomu/smartsearch/releases/latest") });
            actions.Add(ActionButton(L("选择已有 CLI…"), ChooseCliAsync, enabled: () => !CliBlocked));
        }
        state.Children.Add(StepHeader(_cliFirstStep ? L("1. 准备本地环境") : L("本地环境"), CliStatus(), actions.ToArray()));
        state.Children.Add(Secondary(CliExplanation()));
        if (_cliManager.Checking || _cliManager.Busy) state.Children.Add(new ProgressBar { IsIndeterminate = true });
        if (_cliManager.Message.Length > 0) state.Children.Add(Secondary(_cliManager.Message));
        if (_cliManager.CheckError.Length > 0) state.Children.Add(Secondary(L("检查更新失败，请稍后重试。")));
        _nativeCliState.Content = state;
    }

    private async Task ShowCliSettingsAsync()
    {
        if (_dialogOpen) return;
        var blocked = CliBlocked;
        Func<Task>? pendingAction = null;
        var dialog = new ContentDialog
        {
            XamlRoot = DialogRoot, RequestedTheme = ((FrameworkElement)Content).ActualTheme,
            Title = L("本地环境"), CloseButtonText = L("完成")
        };
        Button DeferredAction(string title, Func<Task> action, bool enabled = true)
        {
            var button = new Button { Content = title, MinHeight = 36, IsEnabled = enabled };
            button.Click += (_, _) => { pendingAction = action; dialog.Hide(); };
            return button;
        }
        var content = new StackPanel { Spacing = 16 };
        content.Children.Add(Section(L("Smart Search CLI"), [Secondary(CliStatus()), ActionRow(
            DeferredAction(L("重新检测"), ConnectAsync, !blocked),
            DeferredAction(L("检查更新"), CheckCliVersionAsync, _cliManager.Npm is not null && !blocked))]));
        if (_cliManager.Installations.Count > 0)
        {
            var installations = new ComboBox { ItemsSource = _cliManager.Installations, DisplayMemberPath = "Title",
                SelectedItem = _cliManager.Selected, HorizontalAlignment = HorizontalAlignment.Stretch, IsEnabled = !blocked };
            content.Children.Add(Section(L("已发现的安装"), [installations,
                DeferredAction(L("使用所选安装"), async () =>
                {
                    if (installations.SelectedItem is CLIInstallation selected)
                    {
                        _cliManager.SelectInstallation(selected.Id);
                        await ConnectAsync();
                    }
                }, !blocked)]));
        }
        content.Children.Add(ActionRow(DeferredAction(L("选择已有 CLI…"), ChooseCliAsync, !blocked),
            new HyperlinkButton { Content = L("手动下载 CLI"), NavigateUri = new Uri("https://github.com/konbakuyomu/smartsearch/releases/latest") }));
        content.Children.Add(Secondary(L("独立下载包解压后选择 smart-search 可执行文件，并保留同目录的运行文件。手动安装由你自行更新。")));
        var environment = new StackPanel { Spacing = 8 };
        environment.Children.Add(SectionHeading(L("npm 环境")));
        if (_cliManager.Npm is { } npm)
        {
            environment.Children.Add(Secondary(L("npm {0} · {1}", npm.Version, npm.NpmPath)));
            environment.Children.Add(Secondary(L("安装目录：{0}", npm.Prefix)));
        }
        else environment.Children.Add(Secondary(L("未找到 npm")));
        var path = new TextBox { Text = _cliManager.ManualNpmPath, PlaceholderText = L("npm 路径（留空自动查找）"), IsEnabled = !blocked };
        environment.Children.Add(path);
        var choose = new Button { Content = L("选择文件…"), MinHeight = 36, IsEnabled = !blocked };
        choose.Click += async (_, _) =>
        {
            try
            {
                var picker = new FileOpenPicker();
                picker.FileTypeFilter.Add(".cmd");
                picker.FileTypeFilter.Add(".exe");
                InitializeWithWindow.Initialize(picker, _windowHandle);
                if (await picker.PickSingleFileAsync() is { } file) path.Text = file.Path;
            }
            catch (Exception error) { ShowNotice(L("操作未完成"), SafeMessage(error), InfoBarSeverity.Error); }
        };
        environment.Children.Add(ActionRow(choose,
            DeferredAction(L("应用路径"), () => SetNpmPathAsync(path.Text), !blocked),
            DeferredAction(L("自动查找"), () => SetNpmPathAsync(""), !blocked)));
        content.Children.Add(environment);
        var automatic = CompactSwitch(L("自动检查 CLI 更新"), _cliManager.AutomaticallyChecks);
        automatic.Toggled += (_, _) => _cliManager.SetAutomaticChecks(automatic.IsOn);
        content.Children.Add(SettingRow(L("自动检查 CLI 更新"), L("启动时及每 24 小时检查。"), automatic));
        if (_cliManager.CheckedAt is { } date)
            content.Children.Add(Secondary(L("上次检查：{0}", date.ToLocalTime().ToString("g"))));
        var maintenance = new List<UIElement>
        {
            DeferredAction(CliInstallTitle(), () => ManageNativeCliAsync(remove: false), _cliManager.CanInstall && !blocked && !CliReleaseUnavailable)
        };
        if (_cliManager.Selected?.Source == "npm")
            maintenance.Add(DeferredAction(L("卸载 CLI"), () => ManageNativeCliAsync(remove: true), !blocked && _cliManager.Selected.CanManage));
        content.Children.Add(ActionRow(maintenance.ToArray()));
        if (_cliManager.CheckError.Length > 0)
            content.Children.Add(Disclosure("cli-check-error", L("错误详情"), DataText(_cliManager.CheckError)));
        dialog.Content = new ScrollViewer { Content = content, MaxHeight = 540, HorizontalContentAlignment = HorizontalAlignment.Stretch,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled, VerticalScrollBarVisibility = ScrollBarVisibility.Auto };
        _dialogOpen = true;
        try { await dialog.ShowAsync(); }
        finally { dialog.Content = null; _dialogOpen = false; }
        if (pendingAction is not null) await pendingAction();
    }

    private async Task CheckCliVersionAsync()
    {
        var check = _cliManager.CheckVersionAsync();
        RenderCliState();
        await check;
        RenderCliState();
    }

    private bool CliReleaseUnavailable => _cliManager.LatestVersion.Length > 0 && !_cliManager.LatestSupportsBinary;

    private string CliStatus()
    {
        if (_cliManager.Busy || _connecting) return L("正在检测本地环境…");
        if (_cliManager.Selected is not { } installation)
            return _cliManager.Npm is null ? L("尚未找到 Node.js/npm 或可用的 Smart Search CLI") : L("Node.js/npm 已就绪，等待准备 Smart Search CLI");
        if (!installation.Compatible) return L("{0} · {1} · 需要更新或修复", installation.Source, installation.Version);
        if (_cliManager.UpdateAvailable) return L("{0} · 可更新至 {1}", installation.Version, _cliManager.LatestVersion);
        return _backend.IsConnected ? L("{0} · 已就绪", installation.Version) : L("{0} · 尚未连接", installation.Version);
    }

    private string CliExplanation()
    {
        if (_cliManager.Selected is { Compatible: false } selected) return selected.Note +
            (CliReleaseUnavailable ? "\n" + L("npm 上尚未发布兼容版本。可手动下载独立 CLI，或稍后重新检查。") : "");
        if (_cliManager.Message.Length > 0) return _cliManager.Message;
        if (_cliManager.Selected is { Note.Length: > 0 } installation) return installation.Note;
        if (_connectionFailed) return L("Smart Search CLI 已找到，但连接失败。请重新检测；错误详情显示在上方。");
        if (CliReleaseUnavailable && _cliManager.Selected is null) return L("npm 上尚未发布兼容版本。可手动下载独立 CLI，或稍后重新检查。");
        return L("App 通过本机独立安装的 Smart Search CLI 读取配置并运行搜索，两者分别安装和更新。检测会复用已有的 mise 或 npm 安装。");
    }

    private async Task ChooseCliAsync()
    {
        if (CliBlocked) return;
        var picker = new FileOpenPicker();
        picker.FileTypeFilter.Add(".exe");
        InitializeWithWindow.Initialize(picker, _windowHandle);
        if (await picker.PickSingleFileAsync() is not { } file) return;
        _cliManager.SetCliPath(file.Path);
        await ConnectAsync();
    }

    private string CliInstallTitle()
    {
        if (_cliManager.Selected is null) return L("安装 CLI");
        return _cliManager.UpdateAvailable ? L("更新 CLI") : L("修复 CLI");
    }

    private async Task SetNpmPathAsync(string path)
    {
        if (CliBlocked) return;
        _managingCLI = true;
        await _backend.StopAsync();
        _state = null;
        _cliManager.SetNpmPath(path);
        _managingCLI = false;
        await ConnectAsync();
        await CheckCliAutomaticallyAsync(onLaunch: true);
    }

    private async Task CheckCliAutomaticallyAsync(bool onLaunch = false)
    {
        if (_managingCLI || _connecting || _shuttingDown || _dialogOpen) return;
        var check = _cliManager.CheckAutomaticallyAsync(onLaunch);
        RenderCliState();
        await check;
        RenderCliState();
        RefreshActionButtons();
    }

    private async Task ManageNativeCliAsync(bool remove)
    {
        if (CliBlocked) return;
        if (!remove)
        {
            await _cliManager.CheckVersionAsync();
            RenderCliState();
            if (_cliManager.LatestVersion.Length == 0 || _cliManager.CheckError.Length > 0)
            { ShowNotice(L("CLI 操作未完成"), _cliManager.CheckError, InfoBarSeverity.Error); return; }
            if (!_cliManager.LatestSupportsBinary)
            { ShowNotice(L("CLI 尚不可安装"), L("npm 上尚未发布自带运行时的 CLI，请等待新版发布后再安装。"), InfoBarSeverity.Informational); return; }
        }
        if (!await ConfirmAsync(remove ? L("卸载所选 CLI？") : L("安装或更新独立 CLI？"),
            (_cliManager.Selected?.Id ?? _cliManager.Npm?.Prefix ?? "") + (remove ? "" : "\n" + L("CLI 最新版本：{0}", _cliManager.LatestVersion)) + "\n\n" + L("只处理所选 CLI；配置和 Skills 保留。App 自身不会更新。"),
            remove ? L("卸载 CLI") : L("继续"))) return;
        _managingCLI = true;
        _activityTimer.Stop();
        await _backend.StopAsync();
        _state = null;
        RenderCurrentPage();
        Exception? failure = null;
        try
        {
            if (remove) await _cliManager.UninstallAsync();
            else await _cliManager.InstallOrRepairAsync(_cliManager.LatestVersion);
            ShowNotice(L("独立 CLI"), _cliManager.Message, InfoBarSeverity.Success);
        }
        catch (Exception error) { failure = error; }
        finally { _managingCLI = false; }
        await ConnectAsync();
        if (failure is not null) ShowNotice(L("CLI 操作未完成"), SafeMessage(failure), InfoBarSeverity.Error);
    }
}
