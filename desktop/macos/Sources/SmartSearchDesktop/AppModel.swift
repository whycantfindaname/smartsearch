import AppKit
import Foundation
import SwiftUI

@MainActor
final class AppModel: ObservableObject {
    enum ExitChoice {
        case background
        case stopAndQuit
        case `return`
    }

    enum ConnectionState: Equatable {
        case disconnected
        case connecting
        case ready
        case failed

        var title: String {
            switch self {
            case .disconnected: return L("未连接")
            case .connecting: return L("正在连接")
            case .ready: return L("已连接")
            case .failed: return L("后端失联")
            }
        }

        var symbol: String {
            switch self {
            case .disconnected: return "circle"
            case .connecting: return "arrow.triangle.2.circlepath"
            case .ready: return "checkmark.circle.fill"
            case .failed: return "exclamationmark.triangle.fill"
            }
        }
    }

    @Published var selectedDestination: Destination = .overview
    @Published private(set) var connection: ConnectionState = .disconnected
    @Published private(set) var state: DesktopState?
    @Published private(set) var lastStateRefresh: Date?
    @Published private(set) var activityRuns: [ActivityRun] = []
    @Published private(set) var activityErrors: [String] = []
    @Published private(set) var currentResult: JSONValue?
    @Published private(set) var currentResultCommand: String?
    @Published private(set) var activityDetails: JSONValue?
    @Published private(set) var activityResultRunID: String?
    @Published private(set) var activityResult: JSONValue?
    @Published var selectedActivity: ActivityRun?
    @Published private(set) var cliStatus: JSONValue?
    @Published private(set) var skillStatuses: [String: String] = [:]
    @Published private(set) var skillsState: JSONValue?
    private var skillSelectionInitialized = false
    @Published private(set) var updateResult: JSONValue?
    @Published private(set) var environmentState: JSONValue?
    @Published var errorMessage: String?
    @Published var noticeMessage: String?
    @Published private(set) var isBusy: Set<String> = []
    private var operations = OperationState()

    @Published var configDraft: [String: String] = [:]
    @Published var clearSecretKeys: Set<String> = []
    @Published private(set) var configPreview: JSONValue?
    @Published var selectedCommandID: String?
    @Published var commandValues: [String: String] = [:]
    @Published var commandBooleans: [String: Bool] = [:]
    @Published var selectedSkillTargets: Set<String> = []
    @Published var activityEnabled = true
    @Published var observedDirectories: [String]
    @Published var backendPathOverride: String
    @Published var requestTimeoutSeconds: Double
    @Published private(set) var languagePreference: String

    private let backend = BackendClient()
    private var eventTask: Task<Void, Never>?
    private var ownedActiveRunIDs: Set<String> = []
    @Published private var ownedRunResults = OwnedRunResultStore(capacity: 100)
    private var selectedBusinessRunID: String?
    private var intentionalShutdown = false

    private enum DefaultsKey {
        static let backendPath = "SmartSearchDesktop.backendPathOverride"
        static let timeout = "SmartSearchDesktop.requestTimeoutSeconds"
        static let observedDirectories = "SmartSearchDesktop.observedDirectories"
    }

    init() {
        let savedLanguage = UserDefaults.standard.string(forKey: Localization.preferenceKey) ?? "auto"
        let validLanguage = ["auto", "zh", "en"].contains(savedLanguage)
        languagePreference = validLanguage ? savedLanguage : "auto"
        backendPathOverride = UserDefaults.standard.string(forKey: DefaultsKey.backendPath) ?? ""
        let storedTimeout = UserDefaults.standard.double(forKey: DefaultsKey.timeout)
        requestTimeoutSeconds = storedTimeout == 0 ? 30 : min(max(storedTimeout, 5), 300)
        observedDirectories = UserDefaults.standard.stringArray(forKey: DefaultsKey.observedDirectories) ?? []
        Task {
            await connect()
            if !validLanguage { noticeMessage = L("无法读取已保存的显示偏好，已使用默认设置。原配置文件未修改。") }
        }
    }

    deinit {
        eventTask?.cancel()
    }

    var hasOwnedActiveRuns: Bool { !ownedActiveRunIDs.isEmpty }
    var isUpdatingCLI: Bool { isBusy.contains("cli.update") || updateResult?["cli_update"]?["status"]?.stringValue == "running" }
    var environmentBusy: Bool { isBusy.contains("environment.request") || environmentState?["busy"]?.boolValue == true }
    var skillsBusy: Bool { isBusy.contains("skills.sync") || skillsState?["busy"]?.boolValue == true }
    var skillsChecking: Bool { isBusy.contains("skills.check") || isBusy.contains("skills.catalog") || skillsState?["checking"]?.boolValue == true }
    var environmentActions: [String] {
        (environmentState?["plan"]?.arrayValue ?? []).map(\.displayString)
    }
    var environmentActionLabel: String {
        guard environmentState?["plan_id"]?.stringValue?.isEmpty == false else { return L("安装缺少的组件") }
        if environmentActions.isEmpty { return L("环境已就绪") }
        return (environmentState?["plan"]?.arrayValue ?? []).isEmpty ? L("配置所选 AI 接入") : L("按清单准备环境")
    }

    var selectedCommand: CommandCatalogEntry? {
        guard let selectedCommandID else { return nil }
        return state?.commands.first(where: { $0.id == selectedCommandID })
    }

    func connect() async {
        guard !isUpdatingCLI && !environmentBusy else { noticeMessage = L("环境操作或 CLI 更新正在进行，请等待完成。"); return }
        guard !isBusy.contains("connect") else { return }
        clearOperations()
        guard begin("connect") else { return }
        intentionalShutdown = false
        connection = .connecting
        errorMessage = nil
        do {
            let backendURL = try BackendLocator.resolvedURL(overridePath: backendPathOverride)
            await backend.setTimeout(seconds: requestTimeoutSeconds)
            try await backend.start(backendURL: backendURL)
            startEventListener()
            let snapshot = try await backend.initialize(enableUpdateChecks: backendPathOverride.isEmpty, language: Localization.language)
            applyState(snapshot)
            connection = .ready
            await refreshActivity()
            await refreshCLIStatus()
        } catch {
            connection = .failed
            present(error)
        }
        end("connect")
    }

    func reconnect() async {
        await connect()
    }

    func setLanguage(_ preference: String) async {
        guard !environmentBusy && !isUpdatingCLI && !isBusy.contains("language") else { return }
        guard begin("language") else { return }
        defer { end("language") }
        do {
            var snapshot: JSONValue?
            if connection == .ready {
                snapshot = try await backend.request(method: "language.set", params: .object(["lang": .string(Localization.resolve(preference))]))
            }
            UserDefaults.standard.set(preference, forKey: Localization.preferenceKey)
            languagePreference = preference
            errorMessage = nil
            noticeMessage = nil
            if let snapshot { applyState(snapshot) }
        } catch { present(error) }
    }

    func refreshState() async {
        guard connection == .ready else { return }
        guard begin("state") else { return }
        defer { end("state") }
        do {
            applyState(try await backend.request(method: "get_state"))
        } catch {
            present(error)
        }
    }

    func refreshActivity() async {
        guard connection == .ready, !isBusy.contains("activity") else { return }
        guard begin("activity") else { return }
        defer { end("activity") }
        var params: [String: JSONValue] = [:]
        let directories = Array(Set(([state?.configDirectory].compactMap { $0 }) + observedDirectories)).sorted()
        if !directories.isEmpty {
            params["directories"] = .array(directories.map(JSONValue.string))
        }
        params["limit"] = .number(1_000)
        do {
            let result = try await backend.request(method: "activity.list", params: .object(params))
            activityRuns = (result["runs"]?.arrayValue ?? []).compactMap(ActivityRun.init).sorted { lhs, rhs in
                (lhs.updatedAt ?? .distantPast) > (rhs.updatedAt ?? .distantPast)
            }
            activityErrors = (result["errors"]?.arrayValue ?? []).compactMap { item in
                let directory = item["config_dir"]?.displayString ?? ""
                let message = item["error"]?.displayString ?? L("活动记录不可读，当前状态未知。")
                return directory.isEmpty ? message : "\(directory)：\(message)"
            }
            activityEnabled = result["enabled"]?.boolValue ?? activityEnabled
            if result["ok"]?.boolValue == false {
                errorMessage = L("一个或多个配置目录的活动记录不可读；可读取的记录仍已显示，其他状态未知。")
            }
        } catch {
            present(error)
        }
    }

    func refreshCLIStatus() async {
        guard connection == .ready else { return }
        guard begin("cli.status") else { return }
        defer { end("cli.status") }
        do {
            cliStatus = try await backend.request(method: "cli.status")
        } catch {
            present(error)
        }
    }

    func refreshSkillStatus() async {
        await skillsAction("skills.catalog")
    }

    func skillsAction(_ method: String, params: JSONValue = .object([:])) async {
        guard connection == .ready, !skillsBusy else { return }
        guard begin(method) else { return }
        defer { end(method) }
        do {
            let result = try await backend.request(method: method, params: params)
            skillsState = result
            skillStatuses = Dictionary(uniqueKeysWithValues: (result["targets"]?.arrayValue ?? []).compactMap { value in
                guard let target = SkillTarget(value), let status = target.status else { return nil }
                return (target.id, status)
            })
        } catch {
            present(error)
        }
    }

    func enter(_ destination: Destination) async {
        switch destination {
        case .activity:
            await refreshActivity()
        case .integration:
            await refreshCLIStatus()
            await refreshSkillStatus()
        case .overview, .providers, .search, .settings:
            await refreshState()
        }
    }

    func applyTimeout() {
        requestTimeoutSeconds = min(max(requestTimeoutSeconds, 5), 300)
        UserDefaults.standard.set(requestTimeoutSeconds, forKey: DefaultsKey.timeout)
        Task { await backend.setTimeout(seconds: requestTimeoutSeconds) }
        noticeMessage = L("后续请求将使用 {0} 秒超时。", "\(Int(requestTimeoutSeconds))")
    }

    func saveBackendOverride(_ path: String) {
        backendPathOverride = path.trimmingCharacters(in: .whitespacesAndNewlines)
        UserDefaults.standard.set(backendPathOverride, forKey: DefaultsKey.backendPath)
    }

    func chooseBackendExecutable() {
        let panel = NSOpenPanel()
        panel.title = L("选择开发环境后端")
        panel.prompt = L("选择")
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        saveBackendOverride(url.path)
    }

    func chooseConfigDirectory() {
        let panel = NSOpenPanel()
        panel.title = L("选择 Smart Search 配置目录")
        panel.prompt = L("使用此目录")
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        Task { await selectProfile(url.path) }
    }

    func selectProfile(_ directory: String) async {
        guard connection == .ready else { return }
        guard configDraft.isEmpty && clearSecretKeys.isEmpty else {
            errorMessage = L("还有未保存的修改，请先保存或放弃，再切换配置目录。")
            return
        }
        guard begin("profile") else { return }
        defer { end("profile") }
        do {
            applyState(try await backend.request(method: "profile.select", params: .object(["config_dir": .string(directory)])))
            await refreshActivity()
        } catch {
            present(error)
        }
    }

    func addObservedDirectory() {
        let panel = NSOpenPanel()
        panel.title = L("添加要观察的配置目录")
        panel.prompt = L("添加")
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        guard !observedDirectories.contains(url.path) else { return }
        observedDirectories.append(url.path)
        persistObservedDirectories()
        Task { await refreshActivity() }
    }

    func removeObservedDirectory(_ directory: String) {
        observedDirectories.removeAll { $0 == directory }
        persistObservedDirectories()
        Task { await refreshActivity() }
    }

    func draftBinding(for field: ConfigField) -> Binding<String> {
        Binding(
            get: { self.configDraft[field.key] ?? "" },
            set: { self.setDraft($0, for: field) }
        )
    }

    func setDraft(_ value: String, for field: ConfigField) {
        guard !isEnvironmentReadOnly(field), !isBusy.contains("save") else { return }
        configPreview = nil
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty || (!field.isSecret && trimmed == state?.effectiveValue(for: field)) {
            configDraft.removeValue(forKey: field.key) // Empty secret input means KEEP.
        } else {
            configDraft[field.key] = value
            clearSecretKeys.remove(field.key)
        }
    }

    func clearSecret(_ field: ConfigField) {
        guard field.isSecret, !isEnvironmentReadOnly(field), !isBusy.contains("save") else { return }
        configDraft.removeValue(forKey: field.key)
        clearSecretKeys.insert(field.key)
    }

    func keepSecret(_ field: ConfigField) {
        guard !isBusy.contains("save") else { return }
        clearSecretKeys.remove(field.key)
        configDraft.removeValue(forKey: field.key)
    }

    func isEnvironmentReadOnly(_ field: ConfigField) -> Bool {
        state?.source(for: field) == "environment"
    }

    func draftStatus(for field: ConfigField) -> String {
        if isEnvironmentReadOnly(field) { return L("由环境变量提供，只读") }
        if clearSecretKeys.contains(field.key) { return L("将在保存时清除") }
        if configDraft[field.key]?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty == false {
            return field.isSecret ? L("将在保存时替换") : L("将在保存时更新")
        }
        return field.isSecret ? L("保持当前密钥") : L("未修改")
    }

    func resetConfigDraft() {
        configDraft.removeAll()
        clearSecretKeys.removeAll()
        configPreview = nil
    }

    func previewConfig() async {
        guard connection == .ready else { return }
        guard begin("preview") else { return }
        defer { end("preview") }
        let parameters = configMutationParameters(includeRevision: false)
        do {
            let preview = try await backend.request(method: "config.preview", params: parameters)
            if parameters == configMutationParameters(includeRevision: false) { configPreview = preview }
        } catch {
            present(error)
        }
    }

    func saveConfig() async {
        guard connection == .ready else { return }
        guard let revision = state?.revision else {
            errorMessage = L("没有可用的配置版本，请先刷新后再保存。")
            return
        }
        guard begin("save") else { return }
        defer { end("save") }
        var params = configMutationParameters(includeRevision: false).objectValue ?? [:]
        params["revision"] = revision
        do {
            let result = try await backend.request(method: "config.apply", params: .object(params))
            guard result["ok"]?.boolValue == true else {
                errorMessage = result["error_type"]?.stringValue == "conflict"
                    ? L("配置已被其他进程修改；你改的内容还在，请刷新后核对。")
                    : L("后端没有保存配置；你改的内容还在。")
                return
            }
            // config.apply returns a compact status snapshot; get_state restores the
            // metadata and command catalog that the native form needs.
            applyState(try await backend.request(method: "get_state"))
            resetConfigDraft()
            noticeMessage = L("配置已保存。后续新任务会使用新版本；正在运行的任务不受影响。")
        } catch {
            present(error)
        }
    }

    func testProvider(_ provider: String) async {
        guard connection == .ready, let state else { return }
        guard begin("test:\(provider)") else { return }
        defer { end("test:\(provider)") }
        let providerKeys = Set(state.fields.filter { $0.provider == provider }.map(\.key))
        var overrides = configDraft.reduce(into: [String: JSONValue]()) { partial, item in
            if providerKeys.contains(item.key), !item.value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                partial[item.key] = .string(item.value)
            }
        }
        // An explicit Clear is a draft value too; an empty string is never a masked placeholder.
        for key in clearSecretKeys where providerKeys.contains(key) {
            overrides[key] = .string("")
        }
        do {
            let result = try await backend.request(method: "provider.test", params: .object([
                "provider": .string(provider),
                "overrides": .object(overrides),
            ]))
            guard result["ok"]?.boolValue == true, let runID = result["run_id"]?.stringValue else {
                errorMessage = L("后端未能开始测试；配置没有改变。")
                return
            }
            ownedActiveRunIDs.insert(runID)
            ownedRunResults.register(runID: runID, kind: .providerTest, label: L("测试 {0}", "\(provider)"))
            trackRun(runID, key: "test:\(provider)")
            await recoverRun(runID)
            await refreshActivity()
        } catch {
            present(error)
        }
    }

    func selectCommand(_ id: String?) {
        selectedCommandID = id
        commandValues.removeAll()
        commandBooleans.removeAll()
        guard let command = selectedCommand else { return }
        for field in command.fields {
            if field.isBoolean {
                commandBooleans[field.name] = field.defaultValue?.boolValue ?? false
            } else if let defaultValue = field.defaultValue?.stringValue, !defaultValue.isEmpty {
                commandValues[field.name] = defaultValue
            }
        }
    }

    func commandBinding(for field: CommandField) -> Binding<String> {
        Binding(
            get: { self.commandValues[field.name] ?? "" },
            set: { self.commandValues[field.name] = $0 }
        )
    }

    func booleanBinding(for field: CommandField) -> Binding<Bool> {
        Binding(
            get: { self.commandBooleans[field.name] ?? false },
            set: { value in
                self.commandBooleans[field.name] = value
                if value, field.name == "stream" { self.commandBooleans["no_stream"] = false }
                if value, field.name == "no_stream" { self.commandBooleans["stream"] = false }
            }
        )
    }

    func startSelectedCommand() async {
        guard connection == .ready, let command = selectedCommand else { return }
        let missing = CommandArgumentBuilder.missingRequired(for: command, values: commandValues, booleans: commandBooleans)
        guard missing.isEmpty else {
            errorMessage = L("请填写必填项：{0}。", "\(missing.map(\.label).joined(separator: "、"))")
            return
        }
        guard begin("run:\(command.id)") else { return }
        defer { end("run:\(command.id)") }
        do {
            let arguments = CommandArgumentBuilder.arguments(for: command, values: commandValues, booleans: commandBooleans)
            let result = try await backend.request(method: "run.start", params: .object([
                "command": .string(command.id),
                "arguments": .array(arguments.map(JSONValue.string)),
            ]))
            guard result["ok"]?.boolValue == true, let runID = result["run_id"]?.stringValue else {
                errorMessage = L("后端未能开始此操作。")
                return
            }
            ownedActiveRunIDs.insert(runID)
            ownedRunResults.register(runID: runID, kind: .business, label: command.label)
            trackRun(runID, key: "run:\(command.id)")
            selectedBusinessRunID = runID
            currentResult = nil
            currentResultCommand = command.label
            noticeMessage = L("操作已开始，进度会显示在活动页。")
            await recoverRun(runID)
            await refreshActivity()
        } catch {
            present(error)
        }
    }

    func cancel(_ run: ActivityRun) async {
        guard ownedActiveRunIDs.contains(run.runID), run.isActive, connection == .ready else { return }
        guard begin("cancel:\(run.runID)") else { return }
        defer { end("cancel:\(run.runID)") }
        do {
            let result = try await backend.request(method: "run.cancel", params: .object(["run_id": .string(run.runID)]))
            if result["ok"]?.boolValue == true {
                if ownedActiveRunIDs.contains(run.runID) { trackRun(run.runID, key: "cancel:\(run.runID)") }
                await recoverRun(run.runID)
                noticeMessage = L("已请求取消，等待后端确认最终状态。")
            } else {
                errorMessage = L("后端未接受取消请求；任务仍保持原状态。")
            }
        } catch {
            present(error)
        }
    }

    func canCancel(_ run: ActivityRun) -> Bool {
        ownedActiveRunIDs.contains(run.runID) && run.isActive
    }

    func showActivityDetails(_ run: ActivityRun) async {
        selectedActivity = run
        activityDetails = nil
        activityResultRunID = nil
        activityResult = nil
        guard connection == .ready else { return }
        guard begin("details:\(run.runID)") else { return }
        defer { end("details:\(run.runID)") }
        var params: [String: JSONValue] = ["run_id": .string(run.runID)]
        if let directory = run.configDirectory { params["config_dir"] = .string(directory) }
        do {
            // activity.details carries only protocol-approved, redacted metadata.
            let result = try await backend.request(method: "activity.details", params: .object(params))
            activityDetails = result.redacted()
        } catch {
            present(error)
        }
    }

    func environmentAction(_ method: String, params: JSONValue = .object([:])) async {
        guard connection == .ready, !isUpdatingCLI else { return }
        if environmentBusy && method != "environment.cancel" { return }
        guard begin("environment.request") else { return }
        defer { end("environment.request") }
        do { environmentState = try await backend.request(method: method, params: params) }
        catch { present(error) }
    }

    func prepareEnvironment() async {
        guard !environmentBusy, !environmentActions.isEmpty, environmentState?["can_install"]?.boolValue == true,
              let planID = environmentState?["plan_id"]?.stringValue else { return }
        let targets: [String] = []
        let replace = false
        let plan = environmentActions.joined(separator: "\n")
        let alert = NSAlert()
        alert.messageText = L("准备独立 CLI")
        alert.informativeText = plan + L("\n接入目标：") + (targets.isEmpty ? L("只准备独立 CLI") : targets.joined(separator: "、")) +
            L("\n独立安装目录：") + (environmentState?["tools_dir"]?.displayString ?? "") + "\n" +
            (replace ? L("内容不同的接入文件将先备份再替换。") : L("已有个人修改将保留。")) + L("\n关闭或卸载 App 后，独立 CLI 仍可使用。")
        alert.addButton(withTitle: L("开始准备"))
        alert.addButton(withTitle: L("取消"))
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        await environmentAction("environment.install", params: .object([
            "confirm": .bool(true), "plan_id": .string(planID), "targets": .array(targets.map(JSONValue.string)),
            "replace_modified": .bool(replace)]))
    }

    func copyEnvironmentTest() {
        guard let command = environmentState?["invocation"]?.stringValue, !command.isEmpty else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(L("请使用 Smart Search 技能，先运行以下命令并报告实际版本，不要仅检查文件，也先不要联网搜索：\n") + command + L(" --version\n如果技能未出现，请重新打开 AI。配置目录：") + (environmentState?["config_dir"]?.displayString ?? ""), forType: .string)
        noticeMessage = L("已复制指引；请在 AI 内执行，本机检查不代表 AI 已调用成功。")
    }

    func installSelectedSkills() async {
        guard !environmentBusy, !isUpdatingCLI, !skillsBusy, !skillsChecking,
              !selectedSkillTargets.isEmpty, skillsState?["can_sync"]?.boolValue == true else { return }
        let targets = selectedSkillTargets.sorted()
        let plan = skillsState?["plan_id"]?.stringValue ?? ""
        let paths = (skillsState?["targets"]?.arrayValue ?? []).filter { targets.contains($0["target"]?.stringValue ?? "") }
            .map { ($0["label"]?.displayString ?? "") + "\n" + ($0["path"]?.displayString ?? "") }.joined(separator: "\n\n")
        let alert = NSAlert()
        alert.messageText = L("更新所选 Skills")
        alert.informativeText = L("来源版本：{0}\n{1}\n将同步所选目标的托管文件；不同内容先备份，额外文件保留。", skillsState?["source"]?["version"]?.displayString ?? "", paths)
        alert.addButton(withTitle: L("备份并更新"))
        alert.addButton(withTitle: L("取消"))
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        await skillsAction("skills.sync", params: .object(["targets": .array(targets.map(JSONValue.string)), "confirm": .bool(true), "plan_id": .string(plan)]))
    }

    func enableBundledCLI() async {
        guard !environmentBusy else { return }
        guard connection == .ready else { return }
        guard begin("cli.enable") else { return }
        defer { end("cli.enable") }
        do {
            let result = try await backend.request(method: "cli.enable", params: .object(["confirm": .bool(true)]))
            if result["ok"]?.boolValue == true {
                noticeMessage = result["message"]?.displayString ?? L("已启用内置 CLI，请重新打开终端。")
                await refreshCLIStatus()
            } else {
                errorMessage = L("内置 CLI 未启用；已有同名外部 CLI 不会被覆盖。")
            }
        } catch {
            present(error)
        }
    }

    func setActivityEnabled(_ enabled: Bool) async {
        guard connection == .ready else { return }
        guard begin("activity-setting") else { return }
        defer { end("activity-setting") }
        let priorValue = activityEnabled
        activityEnabled = enabled
        do {
            let result = try await backend.request(method: "activity.enabled", params: .object(["enabled": .bool(enabled)]))
            if result["ok"]?.boolValue != true {
                activityEnabled = priorValue
                errorMessage = L("活动记录设置没有改变。")
            }
        } catch {
            activityEnabled = priorValue
            present(error)
        }
    }

    func clearActivityHistory() async {
        guard connection == .ready else { return }
        guard begin("clear-activity") else { return }
        defer { end("clear-activity") }
        do {
            let result = try await backend.request(method: "activity.clear")
            if result["ok"]?.boolValue == true {
                noticeMessage = L("已清除已结束任务的活动元数据；配置和用户导出未受影响。")
                await refreshActivity()
            } else {
                errorMessage = L("活动历史没有被清除。")
            }
        } catch {
            present(error)
        }
    }

    func checkForUpdates() async {
        guard connection == .ready else { return }
        guard begin("update") else { return }
        defer { end("update") }
        do {
            updateResult = try await backend.request(method: "app.update-check")
        } catch {
            present(error)
        }
    }

    func updateAction(_ method: String, params: JSONValue = .object([:])) async {
        if environmentBusy && ["cli.update", "updates.installer"].contains(method) { return }
        guard connection == .ready, begin(method) else { return }
        defer { end(method) }
        do { updateResult = try await backend.request(method: method, params: params) }
        catch { present(error) }
    }

    func updateCLI() async {
        guard !isUpdatingCLI && !environmentBusy, let version = updateResult?["cli"]?["latest_version"]?.stringValue else { return }
        let alert = NSAlert()
        alert.messageText = L("更新独立 CLI")
        alert.informativeText = L("来源：{0}\n生效路径：{1}\n{2} → {3}\n只更新 Smart Search。请先结束其他终端中的 CLI 调用，更新期间保持 App 打开。", "\(cliStatus?["manager_label"]?.displayString ?? L("未知"))", "\(cliStatus?["resolved_path"]?.displayString ?? cliStatus?["external_path"]?.displayString ?? L("未知"))", "\(cliStatus?["external_version"]?.displayString ?? L("未知"))", "\(version)")
        alert.addButton(withTitle: L("更新 CLI"))
        alert.addButton(withTitle: L("取消"))
        guard alert.runModal() == .alertFirstButtonReturn else { return }
        await updateAction("cli.update", params: .object(["confirm": .bool(true), "version": .string(version)]))
    }

    func openDownloadedUpdate() async {
        guard configDraft.isEmpty && clearSecretKeys.isEmpty && !hasOwnedActiveRuns && !isUpdatingCLI && !environmentBusy else {
            noticeMessage = L("请先处理未保存配置，并等待 App 自有任务完成。"); return
        }
        guard begin("updates.installer") else { return }
        defer { end("updates.installer") }
        do {
            let ready = try await backend.request(method: "updates.installer")
            guard let path = ready["path"]?.stringValue, path.hasPrefix("/"), path.hasSuffix(".dmg") else { return }
            if NSWorkspace.shared.open(URL(fileURLWithPath: path)) {
                noticeMessage = L("已打开校验过的 DMG，尚未安装。请退出 App 后按正常方式安装，再重新打开核对版本；系统代码签名尚未验证。")
            } else { errorMessage = L("无法打开 DMG，请从下载目录手动打开。") }
        } catch { present(error) }
    }

    func revealDownloadedUpdate() {
        guard let path = updateResult?["download"]?["path"]?.stringValue else { return }
        NSWorkspace.shared.activateFileViewerSelecting([URL(fileURLWithPath: path)])
    }

    func copyCLIUpdateCommand() {
        guard let command = updateResult?["cli"]?["command"]?.stringValue else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(command, forType: .string)
        noticeMessage = L("已复制此安装的单工具更新命令。")
    }

    func copyCurrentResult() {
        guard let currentResult else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(currentResult.redacted().prettyPrinted(), forType: .string)
        noticeMessage = L("已复制脱敏的结构化结果。")
    }

    func exportCurrentResult() {
        guard let currentResult else { return }
        let panel = NSSavePanel()
        panel.title = L("导出结果")
        panel.nameFieldStringValue = "smart-search-result.json"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        do {
            let data = try JSONEncoder().encode(currentResult.redacted())
            try data.write(to: url, options: .atomic)
            noticeMessage = L("已导出脱敏结果。")
        } catch {
            errorMessage = L("无法写入所选导出文件。")
        }
    }

    func copyBundledCLIPath() {
        guard let status = cliStatus, let path = status["bundled_path"]?.stringValue else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(path, forType: .string)
        noticeMessage = L("已复制内置 CLI 路径。")
    }

    func shutdownForQuit() async {
        intentionalShutdown = true
        eventTask?.cancel()
        for runID in ownedActiveRunIDs {
            _ = try? await backend.request(method: "run.cancel", params: .object(["run_id": .string(runID)]))
        }
        ownedActiveRunIDs.removeAll()
        clearOperations()
        await backend.shutdown()
        connection = .disconnected
    }

    func displayLabel(for run: ActivityRun) -> String {
        ownedRunResults.descriptor(for: run.runID)?.label
            ?? state?.commands.first { $0.id == run.command }?.label
            ?? ["provider.test": L("服务商测试"), "version": L("版本查询"), "skills.install": L("安装 / 更新 Skills")][run.command]
            ?? L("其他任务")
    }

    func hasOwnedResult(for run: ActivityRun) -> Bool {
        ownedRunResults.result(for: run.runID) != nil
    }

    func activityResult(for run: ActivityRun) -> JSONValue? {
        guard activityResultRunID == run.runID else { return nil }
        return activityResult
    }

    func showOwnedResult(_ run: ActivityRun) {
        guard let descriptor = ownedRunResults.descriptor(for: run.runID),
              let result = ownedRunResults.result(for: run.runID) else { return }
        activityResultRunID = run.runID
        activityResult = result
        if descriptor.kind.updatesSearchResult {
            selectedBusinessRunID = run.runID
            currentResult = result
            currentResultCommand = descriptor.label
        }
    }

    func presentWindowCloseChoice(for window: NSWindow) {
        presentExitChoice(for: window) { [weak self] choice in
            guard let self else { return }
            switch choice {
            case .background:
                NSApp.hide(nil)
            case .stopAndQuit:
                Task {
                    await self.shutdownForQuit()
                    NSApp.terminate(nil)
                }
            case .return:
                break
            }
        }
    }

    func presentQuitChoice(completion: @escaping (ExitChoice) -> Void) {
        presentExitChoice(for: nil, completion: completion)
    }

    private func configMutationParameters(includeRevision: Bool) -> JSONValue {
        var params: [String: JSONValue] = [
            "set": .object(configDraft.compactMapValues { value in
                value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : .string(value)
            }),
            "unset": .array(clearSecretKeys.sorted().map(JSONValue.string)),
        ]
        if includeRevision, let revision = state?.revision { params["revision"] = revision }
        return .object(params)
    }

    private func applyState(_ raw: JSONValue) {
        let snapshot = raw["state"]?.objectValue == nil ? raw : (raw["state"] ?? raw)
        guard let parsed = DesktopState(snapshot) else {
            errorMessage = L("后端状态格式无法读取；没有使用旧状态覆盖它。")
            return
        }
        state = parsed
        updateResult = snapshot["updates"]
        cliStatus = snapshot["cli"]
        environmentState = snapshot["environment"]
        skillsState = snapshot["skills"]
        lastStateRefresh = Date()
        if !parsed.activityRuns().isEmpty {
            activityRuns = parsed.activityRuns()
        }
        if selectedCommandID == nil || !parsed.commands.contains(where: { $0.id == selectedCommandID }) {
            selectCommand(parsed.commands.first?.id)
        }
        if !skillSelectionInitialized {
            selectedSkillTargets = Set(parsed.skillTargets.filter(\.isDefault).map(\.id))
            skillSelectionInitialized = true
        }
    }

    private func startEventListener() {
        eventTask?.cancel()
        eventTask = Task { [weak self, backend] in
            let stream = await backend.eventStream()
            for await event in stream {
                guard !Task.isCancelled else { break }
                await self?.receive(event)
            }
        }
    }

    private func receive(_ event: BackendEvent) {
        switch event.name {
        case "skills":
            if skillsState?["checking"]?.boolValue == true, event.data["checking"]?.boolValue == false,
               event.data["error"]?.stringValue == "", (event.data["targets"]?.arrayValue ?? []).contains(where: { $0["status"]?.stringValue == "stale" }) {
                noticeMessage = L("发现内容不同的 Smart Search Skill，请到“更新 Skills”页选择目标。")
            }
            skillsState = event.data
        case "environment":
            environmentState = event.data
            if let installed = event.data["cli"] { cliStatus = installed }
        case "updates":
            updateResult = event.data
            if let installed = event.data["cli_update"]?["cli"] { cliStatus = installed }
        case "activity":
            Task { await reconcileRuns() }
            // Backend push events cover its active profile.  With user-added directories,
            // refresh the explicitly scoped aggregate instead of silently dropping rows.
            if !observedDirectories.isEmpty {
                Task { await refreshActivity() }
                return
            }
            if let runs = event.data["runs"]?.arrayValue {
                activityRuns = runs.compactMap(ActivityRun.init).sorted { lhs, rhs in
                    (lhs.updatedAt ?? .distantPast) > (rhs.updatedAt ?? .distantPast)
                }
                activityErrors = event.data["errors"]?.arrayValue?.compactMap { item in
                    let directory = item["config_dir"]?.displayString ?? ""
                    let message = item["error"]?.displayString ?? L("活动记录不可读，当前状态未知。")
                    return directory.isEmpty ? message : "\(directory)：\(message)"
                } ?? []
                activityEnabled = event.data["enabled"]?.boolValue ?? activityEnabled
            } else if let run = ActivityRun(event.data) {
                upsert(run)
            }
        case "run":
            guard let runID = event.data["run_id"]?.stringValue, ownedActiveRunIDs.contains(runID) else { return }
            let status = event.data["status"]?.stringValue ?? "unknown"
            if event.data["command"] != nil, let run = ActivityRun(event.data) { upsert(run) }
            if ["finished", "failed", "cancelled", "stale", "interrupted"].contains(status) {
                ownedActiveRunIDs.remove(runID)
                operations.finish(runID)
                isBusy = operations.busyKeys
                let descriptor = ownedRunResults.descriptor(for: runID)
                if let result = event.data["result"], result != .null,
                   let descriptor = ownedRunResults.cache(result.redacted(), for: runID) {
                    if descriptor.kind.updatesSearchResult, selectedBusinessRunID == runID {
                        currentResult = result.redacted()
                        currentResultCommand = descriptor.label
                    }
                }
                if descriptor?.kind == .providerTest {
                    // get_state carries only this backend's in-memory draft check map;
                    // applying it leaves the user's unsaved native draft and destination intact.
                    Task { await refreshProviderChecks() }
                }
                if descriptor?.kind == .skillsInstall { Task { await refreshSkillStatus() } }
                Task { await refreshActivity() }
            }
        case "backend.exited":
            clearOperations()
            environmentState = .object(["busy": .bool(false), "message": .string(L("连接已断开，安装结果尚未确认；重新连接后请检测环境。"))])
            if intentionalShutdown {
                connection = .disconnected
            } else {
                connection = .failed
                errorMessage = L("后端进程已退出；上次状态保留时间标记，不再表示当前正常。")
            }
        case "backend.protocol-error":
            clearOperations()
            environmentState = .object(["busy": .bool(false), "message": .string(L("连接异常，安装结果尚未确认；请重新检测环境。"))])
            connection = .failed
            errorMessage = L("后端输出不符合桌面协议；没有把它当作正常状态读取。")
        default:
            break
        }
    }

    private func upsert(_ run: ActivityRun) {
        if let index = activityRuns.firstIndex(where: { $0.runID == run.runID }) {
            activityRuns[index] = run
        } else {
            activityRuns.insert(run, at: 0)
        }
        activityRuns.sort { ($0.updatedAt ?? .distantPast) > ($1.updatedAt ?? .distantPast) }
    }

    private func persistObservedDirectories() {
        UserDefaults.standard.set(observedDirectories, forKey: DefaultsKey.observedDirectories)
    }

    var configOperationBusy: Bool { !isBusy.isDisjoint(with: ["state", "save", "preview", "profile"]) }

    private func begin(_ identifier: String) -> Bool {
        if ["state", "save", "preview", "profile"].contains(identifier), configOperationBusy { return false }
        guard operations.begin(identifier) else { return false }
        isBusy = operations.busyKeys
        return true
    }

    private func end(_ identifier: String) {
        operations.endRequest(identifier)
        isBusy = operations.busyKeys
    }

    private func trackRun(_ runID: String, key: String) {
        operations.track(runID, key: key)
        isBusy = operations.busyKeys
    }

    private func clearOperations() {
        operations.reset()
        isBusy = []
        ownedActiveRunIDs.removeAll()
    }

    private func recoverRun(_ runID: String) async {
        guard connection == .ready, ownedActiveRunIDs.contains(runID) else { return }
        let generation = state?.generation
        if let result = try? await backend.request(method: "run.result", params: .object(["run_id": .string(runID)])),
           state?.generation == generation {
            receive(BackendEvent(name: "run", data: result, generation: generation))
        }
    }

    private func reconcileRuns() async {
        guard begin("reconcile") else { return }
        defer { end("reconcile") }
        for runID in Array(ownedActiveRunIDs) { await recoverRun(runID) }
    }

    private func refreshProviderChecks() async {
        guard connection == .ready else { return }
        let directory = state?.configDirectory
        let generation = state?.generation
        do {
            let result = try await backend.request(method: "get_state")
            guard state?.configDirectory == directory, state?.generation == generation,
                  result["config_dir"]?.stringValue == directory,
                  var snapshot = state?.raw.objectValue else { return }
            snapshot["provider_checks"] = result["provider_checks"]
            snapshot["provider_health"] = result["provider_health"]
            // Probe completion must not silently adopt another process's config revision.
            state = DesktopState(.object(snapshot))
        } catch { present(error) }
    }

    func providerTestLabel(_ provider: String) -> String {
        let keys = Set(state?.fields.filter { $0.provider == provider }.map(\.key) ?? [])
        let changed = keys.contains { configDraft[$0] != nil || clearSecretKeys.contains($0) }
        if state?.raw["probe_kinds"]?[provider]?.stringValue == "presence" {
            return changed ? L("检查未保存的配置") : L("检查配置")
        }
        return changed ? L("用未保存的修改测试") : L("测试")
    }

    private func present(_ error: Error) {
        errorMessage = (error as? LocalizedError)?.errorDescription ?? L("操作未完成。")
    }

    private func presentExitChoice(for window: NSWindow?, completion: @escaping (ExitChoice) -> Void) {
        let alert = NSAlert()
        alert.messageText = L("仍有 Smart Search 任务在运行")
        alert.informativeText = L("这些任务属于本 App。你可以让它们继续在后台运行，取消后退出，或返回继续查看。")
        alert.addButton(withTitle: L("继续在后台"))
        alert.addButton(withTitle: L("取消任务并退出"))
        alert.addButton(withTitle: L("返回"))
        let resolve: (NSApplication.ModalResponse) -> Void = { response in
            switch response {
            case .alertFirstButtonReturn: completion(.background)
            case .alertSecondButtonReturn: completion(.stopAndQuit)
            default: completion(.return)
            }
        }
        if let window {
            alert.beginSheetModal(for: window, completionHandler: resolve)
        } else {
            resolve(alert.runModal())
        }
    }
}
