import AppKit
import SwiftUI

struct ContentView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        NavigationSplitView {
            List {
                HStack(spacing: 10) {
                    Image(nsImage: NSApp.applicationIconImage)
                        .resizable().scaledToFit().frame(width: 36, height: 36)
                        .padding(3)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 6))
                        .accessibilityLabel(L("Smart Search 图标"))
                    Text("Smart Search").font(.headline)
                }
                Section("Smart Search") {
                    ForEach(Destination.allCases) { destination in
                        Button {
                            model.selectedDestination = destination
                        } label: {
                            HStack {
                                Label(destination.title, systemImage: destination.symbol)
                                Spacer()
                                if model.selectedDestination == destination {
                                    Image(systemName: "checkmark")
                                        .foregroundStyle(.tint)
                                }
                            }
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            .listStyle(.sidebar)
            .navigationTitle("Smart Search")
        } detail: {
            VStack(spacing: 0) {
                if let error = model.errorMessage {
                    MessageBanner(message: error, symbol: "exclamationmark.triangle.fill", tint: .red) {
                        model.errorMessage = nil
                    }
                }
                if let notice = model.noticeMessage {
                    MessageBanner(message: notice, symbol: "checkmark.circle.fill", tint: .green) {
                        model.noticeMessage = nil
                    }
                }
                destinationView
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button {
                        Task { await model.refreshState() }
                    } label: {
                        BusyLabel(text: L("刷新状态"), busyText: L("刷新中…"), busy: model.isBusy.contains("state"))
                    }
                    .disabled(model.connection != .ready || model.configOperationBusy)
                }
                ToolbarItem(placement: .automatic) {
                    ConnectionIndicator(state: model.connection)
                }
            }
        }
        .onChange(of: model.selectedDestination) { destination in
            Task { await model.enter(destination) }
        }
        .task {
            await model.enter(model.selectedDestination)
        }
    }

    @ViewBuilder
    private var destinationView: some View {
        switch model.selectedDestination {
        case .overview: OverviewView(model: model)
        case .providers: ProvidersView(model: model)
        case .search: SearchResearchView(model: model)
        case .activity: ActivityView(model: model)
        case .integration: IntegrationView(model: model)
        case .settings: SettingsAboutView(model: model)
        }
    }
}

private struct MessageBanner: View {
    let message: String
    let symbol: String
    let tint: Color
    let dismiss: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: symbol).foregroundStyle(tint)
            Text(message).fixedSize(horizontal: false, vertical: true)
            Spacer(minLength: 8)
            Button(action: dismiss) { Image(systemName: "xmark") }
                .buttonStyle(.borderless)
                .accessibilityLabel(L("关闭提示"))
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(tint.opacity(0.10))
    }
}

private struct ConnectionIndicator: View {
    let state: AppModel.ConnectionState

    var body: some View {
        Label(state.title, systemImage: state.symbol)
            .foregroundStyle(tint)
            .accessibilityLabel(L("后端状态：{0}", "\(state.title)"))
    }

    private var tint: Color {
        switch state {
        case .ready: return .green
        case .connecting: return .orange
        case .failed: return .red
        case .disconnected: return .secondary
        }
    }
}

private struct BackendUnavailableView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: model.connection == .failed ? "bolt.horizontal.circle" : "desktopcomputer")
                .font(.system(size: 42))
                .foregroundStyle(.secondary)
            Text(model.connection == .failed ? L("后端目前不可用") : L("正在连接本机后端"))
                .font(.title2.weight(.semibold))
            Text(L("页面没有显示模拟数据。连接后会读取当前配置、工具目录和活动记录。"))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button(L("重新连接")) { Task { await model.reconnect() } }
                .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}

private struct OverviewView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        guard let state = model.state else { return AnyView(BackendUnavailableView(model: model)) }
        return AnyView(ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("概览")).font(.largeTitle.weight(.bold))
                    Text(L("查看实际配置状态，决定下一步操作。打开此页不会发起服务商探针。"))
                        .foregroundStyle(.secondary)
                }

                GroupBox(L("首次配置")) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(L("主搜索用于回答问题；文档检索用于查库文档；网页抓取用于读取链接。配好之后请自己点一次测试，App 不会自动发起计费探针。"))
                            .foregroundStyle(.secondary)
                        if state.minimumProfileOK == true {
                            Label(L("基础能力已配置"), systemImage: "checkmark.circle.fill")
                                .foregroundStyle(.green)
                            Text(L("这表示后端已根据当前配置计算出基础条件；它不代表刚刚进行了真实服务商测试。"))
                                .foregroundStyle(.secondary)
                        } else if state.minimumProfileOK == false {
                            Label(L("还需要补齐配置"), systemImage: "exclamationmark.circle.fill")
                                .foregroundStyle(.orange)
                            if state.minimumMissing.isEmpty {
                                Text(L("后端未列出缺失能力。请在服务商页查看当前字段。"))
                                    .foregroundStyle(.secondary)
                            } else {
                                ForEach(state.minimumMissing, id: \.self) { item in
                                    Label(item, systemImage: "circle")
                                }
                            }
                            HStack {
                                Button(L("打开服务商配置")) { model.selectedDestination = .providers }
                                    .buttonStyle(.borderedProminent)
                                Button(L("选择配置目录")) { model.selectedDestination = .settings }
                            }
                        } else {
                            Text(L("后端尚未报告基础配置状态。"))
                                .foregroundStyle(.secondary)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                GroupBox(L("当前环境")) {
                    Grid(alignment: .leading, horizontalSpacing: 20, verticalSpacing: 10) {
                        GridRow {
                            Text(L("配置文件")).foregroundStyle(.secondary)
                            Text(state.configPath ?? L("后端未提供"))
                                .textSelection(.enabled)
                        }
                        GridRow {
                            Text(L("配置目录")).foregroundStyle(.secondary)
                            Text(state.configDirectory ?? L("后端未提供"))
                                .textSelection(.enabled)
                        }
                        GridRow {
                            Text(L("内置引擎")).foregroundStyle(.secondary)
                            Text(state.version ?? L("后端未提供"))
                        }
                        GridRow {
                            Text(L("协议 generation")).foregroundStyle(.secondary)
                            Text(state.generation ?? L("后端未提供"))
                                .textSelection(.enabled)
                        }
                        GridRow {
                            Text(L("最后读取")).foregroundStyle(.secondary)
                            Text(model.lastStateRefresh?.formatted(date: .abbreviated, time: .standard) ?? L("尚未读取"))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                if let capabilityStatus = state.capabilityStatus, let details = capabilityStatus.objectValue, !details.isEmpty {
                    GroupBox(L("能力状态")) {
                        VStack(alignment: .leading, spacing: 8) {
                            Text(L("此处是当前配置是否满足路由条件，不是刚刚完成的联网验证。"))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                            ForEach(details.keys.sorted(), id: \.self) { key in
                                CapabilityStatusRow(capability: key, status: details[key] ?? .object([:]))
                            }
                        }
                    }
                }
            }
            .padding(24)
            .frame(maxWidth: 940, alignment: .leading)
        })
    }
}

private struct ProvidersView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        guard let state = model.state else { return AnyView(BackendUnavailableView(model: model)) }
        let sections = Dictionary(grouping: state.fields.filter { $0.provider == nil || $0.provider == "" }, by: \.section)
        return AnyView(ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text(L("配置与服务商")).font(.largeTitle.weight(.bold))
                Text(L("先配齐主搜索、文档检索和网页抓取，每类任选一个；其余按需展开。"))
                    .foregroundStyle(.secondary)
                if let preview = model.configPreview { ConfigPreviewView(preview: preview) }
                ForEach(["main_search", "docs_search", "web_fetch"], id: \.self) { capability in
                    Text(capabilityName(capability)).font(.title2.weight(.semibold))
                    ForEach(state.providerGroups.filter { $0.primaryCapability == capability }) { group in
                        ProviderSection(model: model, state: state, section: group.id, title: group.id,
                                        blurb: "", fields: group.fields)
                    }
                }
                ForEach(state.providerGroups.filter { $0.primaryCapability == nil }) { group in
                    DisclosureGroup(L("更多服务商 · {0}", "\(group.id)")) {
                        ProviderSection(model: model, state: state, section: group.id, title: group.id,
                                        blurb: L("按需启用；测试可能产生计费请求。"), fields: group.fields)
                    }
                }
                ForEach(orderedSectionIDs(state: state, present: Set(sections.keys)), id: \.self) { section in
                    DisclosureGroup(state.sections.first { $0.id == section }?.label ?? section) {
                        ProviderSection(model: model, state: state, section: section,
                            title: state.sections.first { $0.id == section }?.label,
                            blurb: state.sections.first { $0.id == section }?.blurb ?? "", fields: sections[section] ?? [])
                    }
                }
                DisclosureGroup(L("冷却与路由详情")) {
                    ProviderHealthView(health: state.providerHealth)
                    ForEach(state.capabilityChains.keys.sorted(), id: \.self) { key in
                        KeyValueLine(label: capabilityName(key), value: state.capabilityChains[key, default: []].joined(separator: " → "))
                    }
                }
            }
            .padding(24)
            .frame(maxWidth: 980, alignment: .leading)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .safeAreaInset(edge: .bottom) {
            HStack(spacing: 12) {
                Button { Task { await model.saveConfig() } } label: {
                    BusyLabel(text: L("保存更改"), busyText: L("保存中…"), busy: model.isBusy.contains("save"))
                }
                .buttonStyle(.borderedProminent)
                .disabled(model.connection != .ready || model.configOperationBusy || (model.configDraft.isEmpty && model.clearSecretKeys.isEmpty))
                Button { Task { await model.previewConfig() } } label: {
                    BusyLabel(text: L("预览"), busyText: L("预览中…"), busy: model.isBusy.contains("preview"))
                }
                .disabled(model.connection != .ready || model.configOperationBusy)
                Text(L("未保存修改：{0} 项", "\(model.configDraft.count + model.clearSecretKeys.count)"))
                    .font(.caption).foregroundStyle(.secondary)
                Button(L("放弃修改")) { model.resetConfigDraft() }.disabled(model.isBusy.contains("save") || (model.configDraft.isEmpty && model.clearSecretKeys.isEmpty))
                Spacer(minLength: 0)
            }
            .padding(16)
            .background(.bar)
        })
    }
}

private func capabilityName(_ value: String) -> String {
    ["main_search": L("主搜索"), "docs_search": L("文档检索"), "web_fetch": L("网页抓取"),
     "web_search": L("网页搜索"), "vertical_search": L("垂直检索")][value] ?? value
}

/// Section ids in backend order, with anything the backend did not describe
/// appended alphabetically so a new section never vanishes from the page.
private func orderedSectionIDs(state: DesktopState, present: Set<String>) -> [String] {
    var ordered = state.sections.map(\.id).filter(present.contains)
    let described = Set(ordered)
    ordered.append(contentsOf: present.subtracting(described).sorted())
    return ordered
}

/// A button label that turns into a spinner while its operation runs. Without it
/// a 20-second probe looks identical to a click that did nothing.
private struct BusyLabel: View {
    let text: String
    let busyText: String
    let busy: Bool

    var body: some View {
        if busy {
            HStack(spacing: 6) {
                ProgressView().controlSize(.small)
                Text(busyText)
            }
        } else {
            Text(text)
        }
    }
}

private struct ConfigPreviewView: View {
    let preview: JSONValue

    var body: some View {
        GroupBox(L("配置检查")) {
            VStack(alignment: .leading, spacing: 6) {
                if preview.boolValue == false || preview["ok"]?.boolValue == false {
                    Label(L("这样还不够用，尚未保存。"), systemImage: "xmark.circle.fill")
                        .foregroundStyle(.red)
                } else if preview["minimum_profile_ok"]?.boolValue == true {
                    Label(L("这样配就够用了。"), systemImage: "checkmark.circle.fill")
                        .foregroundStyle(.green)
                } else {
                    Text(L("检查已完成；请根据还缺的能力决定是否保存。"))
                        .foregroundStyle(.secondary)
                }
                ForEach(preview["missing"]?.arrayValue?.map(\.displayString) ?? [], id: \.self) { item in
                    Text(item).foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct CapabilityStatusRow: View {
    let capability: String
    let status: JSONValue

    private var configuredProviders: [String] {
        status["configured"]?.arrayValue?.map(\.displayString).filter { !$0.isEmpty } ?? []
    }

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                Text(capabilityTitle).fontWeight(.medium)
                Text(configuredProviders.isEmpty ? L("没有已配置的服务商") : L("已配置：{0}", "\(configuredProviders.joined(separator: "、"))"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            Label(configurationLabel, systemImage: configurationSymbol)
                .foregroundStyle(configurationColor)
            if status["experimental"]?.boolValue == true {
                Text(L("实验性")).font(.caption).foregroundStyle(.orange)
            }
        }
        .padding(.vertical, 3)
    }

    private var capabilityTitle: String {
        switch capability {
        case "main_search": return L("主搜索")
        case "web_search": return L("网页搜索")
        case "docs_search": return L("文档检索")
        case "web_fetch": return L("网页抓取")
        case "vertical_search": return L("垂直检索")
        default: return capability
        }
    }

    private var configurationLabel: String {
        switch status["ok"]?.boolValue {
        case .some(true): return L("配置条件已满足")
        case .some(false): return L("缺少配置")
        case nil: return L("状态未报告")
        }
    }

    private var configurationSymbol: String {
        switch status["ok"]?.boolValue {
        case .some(true): return "checkmark.circle"
        case .some(false): return "exclamationmark.circle"
        case nil: return "questionmark.circle"
        }
    }

    private var configurationColor: Color {
        switch status["ok"]?.boolValue {
        case .some(true): return .green
        case .some(false): return .orange
        case nil: return .secondary
        }
    }
}

private struct ProviderHealthView: View {
    let health: JSONValue?

    var body: some View {
        GroupBox(L("服务商冷却状态")) {
            VStack(alignment: .leading, spacing: 9) {
                Text(L("冷却仅影响本机是否暂时跳过重试。无冷却不等于服务商刚刚联网成功。"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                if let providers = health?["providers"]?.arrayValue {
                    if providers.isEmpty {
                        Text(L("后端没有需要显示的冷却记录。"))
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(providers.indices, id: \.self) { index in
                            ProviderHealthRow(health: providers[index])
                        }
                    }
                } else {
                    Text(L("后端未报告冷却状态。"))
                        .foregroundStyle(.secondary)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct ProviderHealthRow: View {
    let health: JSONValue

    private var state: String { health["state"]?.stringValue ?? "unknown" }
    private var remainingSeconds: Double { health["cooldown_remaining_seconds"]?.numberValue ?? 0 }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline) {
                Text(health["provider"]?.displayString ?? L("未知服务商")).fontWeight(.medium)
                Spacer()
                if state == "cooldown" {
                    Label(L("冷却中（剩余 {0}）", "\(cooldownText)"), systemImage: "pause.circle")
                        .foregroundStyle(.orange)
                } else {
                    Label(L("无冷却"), systemImage: "minus.circle")
                        .foregroundStyle(.secondary)
                }
            }
            if health["configured"]?.boolValue == false {
                Text(L("当前配置未包含此服务商。"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if state == "closed" {
                Text(L("无冷却只表示当前不会因本机冷却被跳过，不代表联网验证成功。"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if let errorType = health["error_type"]?.stringValue, !errorType.isEmpty {
                Text(L("最近一次请求异常，可主动测试确认。"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if let message = health["error"]?.stringValue, !message.isEmpty {
                Text(message).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 3)
    }

    private var cooldownText: String {
        if remainingSeconds >= 60 { return L("{0} 分钟", "\(Int((remainingSeconds / 60).rounded(.up)))") }
        return L("{0} 秒", "\(Int(remainingSeconds.rounded(.up)))")
    }
}

private struct ProviderDraftChecksView: View {
    let checks: JSONValue?

    var body: some View {
        GroupBox(L("本 App 最近的测试")) {
            VStack(alignment: .leading, spacing: 9) {
                Text(L("只显示本 App 主动发起的测试。测试的是当前表单里的值，包含还没保存的修改；不写入冷却记录。"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
                let entries = checks?.objectValue ?? [:]
                if entries.isEmpty {
                    Text(L("本 App 还没测试过。"))
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(entries.keys.sorted(), id: \.self) { provider in
                        ProviderDraftCheckRow(provider: provider, check: entries[provider] ?? .object([:]))
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct ProviderDraftCheckRow: View {
    let provider: String
    let check: JSONValue

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .firstTextBaseline) {
                Text(provider).fontWeight(.medium)
                Spacer()
                Text(statusLabel).foregroundStyle(statusColor)
            }
            Text(L("时间：{0} · 来源：{1} · 范围：{2}", "\(checkedAtText)", "\(source)", "\(scope)"))
                .font(.caption)
                .foregroundStyle(.secondary)
            if let probe = check["probe"]?.stringValue, !probe.isEmpty {
                Text(L("方式：{0}", "\(["live": L("真实请求"), "main": L("主搜索请求"), "presence": L("仅检查已填写"), "shared": L("共用凭据")][probe] ?? L("本机检查"))")).font(.caption).foregroundStyle(.secondary)
            }
            if let message = check["message"]?.stringValue, !message.isEmpty {
                DisclosureGroup(L("技术详情")) { Text(message).font(.system(.caption, design: .monospaced)).textSelection(.enabled) }
            }
        }
        .padding(.vertical, 3)
    }

    private var status: String { check["status"]?.stringValue ?? "unknown" }
    private var source: String { check["source"]?.stringValue == "app" ? L("本次 App 会话") : L("本机测试") }
    private var scope: String { check["scope"]?.stringValue == "draft" ? L("未保存的修改") : L("当前有效配置") }

    private var statusLabel: String {
        switch status {
        case "ok": return L("测试通过")
        case "cancelled": return L("测试已取消")
        case "not_configured": return L("未配置")
        case "timeout": return L("测试超时")
        case "warning": return L("需要确认")
        case "configured": return L("已填写，未验证")
        default: return L("测试未通过")
        }
    }

    private var statusColor: Color {
        switch status {
        case "ok": return .green
        case "cancelled": return .secondary
        case "not_configured", "timeout", "warning", "configured": return .orange
        default: return .red
        }
    }

    private var checkedAtText: String {
        guard let seconds = check["checked_at"]?.numberValue else { return L("后端未提供") }
        return Date(timeIntervalSince1970: seconds).formatted(date: .abbreviated, time: .standard)
    }
}

private struct ProviderSection: View {
    @ObservedObject var model: AppModel
    let state: DesktopState
    let section: String
    let title: String?
    let blurb: String
    let fields: [ConfigField]

    private var provider: String? {
        let providers = Set(fields.compactMap(\.provider))
        return providers.count == 1 ? providers.first : nil
    }

    /// Of the 68 keys, 55 are advanced and 9 are essential. Showing them at equal
    /// weight is what makes this page read as a wall; `tier` was already parsed
    /// and simply never consulted.
    private var upfront: [ConfigField] { fields.filter { !$0.isAdvanced } }
    private var advanced: [ConfigField] { fields.filter(\.isAdvanced) }

    private var testKey: String { "test:" + (provider ?? section) }

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 14) {
                if !blurb.isEmpty {
                    Text(blurb).font(.caption).foregroundStyle(.secondary)
                }
                let visible = upfront
                ForEach(visible) { field in
                    ConfigFieldEditor(model: model, state: state, field: field)
                    if field.id != visible.last?.id { Divider() }
                }
                if !advanced.isEmpty {
                    DisclosureGroup(L("更多设置（{0}）", "\(advanced.count)")) {
                        VStack(alignment: .leading, spacing: 14) {
                            ForEach(advanced) { field in
                                ConfigFieldEditor(model: model, state: state, field: field)
                                if field.id != advanced.last?.id { Divider() }
                            }
                        }
                        .padding(.top, 8)
                    }
                }
                if let provider, let check = state.providerChecks?[provider] {
                    ProviderDraftCheckRow(provider: provider, check: check)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            HStack {
                Text(title ?? section)
                Spacer()
                if let provider {
                    Button {
                        Task { await model.testProvider(provider) }
                    } label: {
                        if model.isBusy.contains(testKey) {
                            HStack(spacing: 6) {
                                ProgressView().controlSize(.small)
                                Text(model.state?.raw["probe_kinds"]?[provider]?.stringValue == "presence" ? L("检查中…") : L("测试中…"))
                            }
                        } else {
                            Text(model.providerTestLabel(provider))
                        }
                    }
                    .disabled(model.connection != .ready || model.isBusy.contains(testKey))
                }
            }
        }
    }
}

private struct ConfigFieldEditor: View {
    @ObservedObject var model: AppModel
    let state: DesktopState
    let field: ConfigField

    var body: some View {
        VStack(alignment: .leading, spacing: 7) {
            HStack(alignment: .firstTextBaseline) {
                Text(field.label).fontWeight(.medium)
                if model.isEnvironmentReadOnly(field) {
                    Text(L("环境变量")).foregroundStyle(.secondary)
                }
                Spacer()
                Text(model.draftStatus(for: field)).foregroundStyle(.secondary)
            }

            if model.isEnvironmentReadOnly(field) {
                Text(state.effectiveValue(for: field).isEmpty ? L("后端未提供有效值") : state.effectiveValue(for: field))
                    .textSelection(.enabled)
            } else if field.isSecret {
                HStack {
                    SecureField(L("输入新值以替换；留空表示保持"), text: model.draftBinding(for: field))
                    if model.clearSecretKeys.contains(field.key) {
                        Button(L("保留")) { model.keepSecret(field) }
                    } else {
                        Button(L("清除 Key"), role: .destructive) { model.clearSecret(field) }
                    }
                }
            } else if !field.choices.isEmpty {
                Picker(field.label, selection: model.draftBinding(for: field)) {
                    Text(L("保持当前值")).tag("")
                    ForEach(field.choices, id: \.self) { choice in Text(choice).tag(choice) }
                }
                .labelsHidden()
            } else {
                TextField(field.placeholder.isEmpty ? field.label : field.placeholder, text: model.draftBinding(for: field))
            }

            VStack(alignment: .leading, spacing: 6) {
                Text(L("有效值：{0}", "\(state.effectiveValue(for: field).isEmpty ? "未设置" : state.effectiveValue(for: field))"))
                    .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                HStack {
                    Text(state.statusLabels[state.source(for: field)] ?? L("未知来源"))
                    if let docs = field.docsURL, let url = URL(string: docs) { Link(L("文档"), destination: url) }
                    if let keyURL = field.keyURL, let url = URL(string: keyURL) { Link(L("申请 Key"), destination: url) }
                }
                DisclosureGroup(L("来源详情")) {
                    Text(field.key).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    if state.savedValue(for: field) != state.effectiveValue(for: field) {
                        Text(L("配置文件：{0}", "\(state.savedValue(for: field).isEmpty ? "未设置" : state.savedValue(for: field))"))
                            .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    }
                }
            }
            .font(.caption).foregroundStyle(.secondary)
            if !field.help.isEmpty { Text(field.help).font(.caption).foregroundStyle(.secondary) }
        }
        .disabled(model.isBusy.contains("save"))
        .accessibilityElement(children: .contain)
    }
}

private struct SearchResearchView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        guard let state = model.state else { return AnyView(BackendUnavailableView(model: model)) }
        return AnyView(ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("搜索与研究")).font(.largeTitle.weight(.bold))
                    Text(L("工具目录和参数来自后端。实验性工具保持明确标注，结果先以可读内容和来源展示。"))
                        .foregroundStyle(.secondary)
                }

                if state.commands.isEmpty {
                    GroupBox(L("工具目录")) {
                        Text(L("后端尚未提供可运行的工具目录。"))
                            .foregroundStyle(.secondary)
                    }
                } else {
                    CommandFormView(model: model, commands: state.commands)
                }

                if let result = model.currentResult {
                    ReadableResultView(
                        result: result,
                        command: model.currentResultCommand,
                        copy: model.copyCurrentResult,
                        export: model.exportCurrentResult
                    )
                }
            }
            .padding(24)
            .frame(maxWidth: 980, alignment: .leading)
        })
    }
}

private struct CommandFormView: View {
    @ObservedObject var model: AppModel
    let commands: [CommandCatalogEntry]

    var body: some View {
        GroupBox(L("执行工具")) {
            VStack(alignment: .leading, spacing: 14) {
                Picker(L("工具"), selection: Binding(get: { model.selectedCommandID ?? "" }, set: { model.selectCommand($0) })) {
                    ForEach(commands) { command in
                        Text(command.experimental ? L("{0}（实验性）", "\(command.label)") : command.label).tag(command.id)
                    }
                }
                if let command = model.selectedCommand {
                    if !command.description.isEmpty { Text(command.description).foregroundStyle(.secondary) }
                    if command.experimental {
                        Label(L("实验性工具：只在明确选择后调用。"), systemImage: "flask")
                            .foregroundStyle(.orange)
                    }
                    let primaryFields = command.fields.filter { !$0.isAdvanced }
                    let advancedFields = command.fields.filter(\.isAdvanced)
                    ForEach(primaryFields) { field in CommandFieldEditor(model: model, field: field) }
                    if !advancedFields.isEmpty {
                        DisclosureGroup(L("高级参数")) {
                            VStack(alignment: .leading, spacing: 12) {
                                ForEach(advancedFields) { field in CommandFieldEditor(model: model, field: field) }
                            }
                            .padding(.top, 8)
                        }
                    }
                    HStack {
                        Button { Task { await model.startSelectedCommand() } } label: {
                            BusyLabel(text: L("开始 {0}", "\(command.label)"), busyText: L("运行中…"), busy: model.isBusy.contains("run:\(command.id)"))
                        }
                        .buttonStyle(.borderedProminent)
                        .disabled(model.connection != .ready || model.isBusy.contains("run:\(command.id)"))
                        Text(L("运行后可在活动页查看真实阶段并取消本 App 的任务。"))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct CommandFieldEditor: View {
    @ObservedObject var model: AppModel
    let field: CommandField

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            if field.isBoolean {
                Toggle(field.label, isOn: model.booleanBinding(for: field))
            } else if !field.choices.isEmpty {
                Picker(field.label, selection: model.commandBinding(for: field)) {
                    if !field.required { Text(L("未指定")).tag("") }
                    ForEach(field.choices, id: \.self) { choice in Text(choice).tag(choice) }
                }
            } else if field.acceptsMultipleValues {
                Text(field.label + (field.required ? L("（必填）") : ""))
                TextEditor(text: model.commandBinding(for: field))
                    .font(.body)
                    .frame(minHeight: 58)
                    .overlay(RoundedRectangle(cornerRadius: 5).stroke(.quaternary))
                Text(L("每行一个值。"))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                TextField(field.label + (field.required ? L("（必填）") : ""), text: model.commandBinding(for: field))
            }
            if !field.help.isEmpty { Text(field.help).font(.caption).foregroundStyle(.secondary) }
        }
    }
}

private struct ReadableResultView: View {
    let result: JSONValue
    let command: String?
    let copy: () -> Void
    let export: () -> Void

    var body: some View {
        GroupBox(command.map { L("结果：{0}", "\($0)") } ?? L("结果")) {
            VStack(alignment: .leading, spacing: 12) {
                if let text = result.readableText, !text.isEmpty {
                    Text(text).textSelection(.enabled)
                } else {
                    Text(L("后端返回了结构化结果，但没有可直接阅读的文本字段。可在高级详情查看脱敏结构。"))
                        .foregroundStyle(.secondary)
                }
                let sources = result.sourceLinks
                if !sources.isEmpty {
                    Divider()
                    Text(L("来源")).font(.headline)
                    ForEach(sources, id: \.absoluteString) { url in
                        Link(url.absoluteString, destination: url)
                            .lineLimit(1)
                    }
                }
                HStack {
                    Button(L("复制脱敏 JSON"), action: copy)
                    Button(L("导出脱敏结果"), action: export)
                    Spacer()
                }
                DisclosureGroup(L("高级 JSON")) {
                    Text(result.redacted().prettyPrinted())
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct ActivityView: View {
    @ObservedObject var model: AppModel
    @State private var confirmClear = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text(L("活动")).font(.largeTitle.weight(.bold))
                Text(L("显示本机当前配置目录和你主动添加目录中的真实活动。没有记录不代表外部 CLI 一定空闲。"))
                    .foregroundStyle(.secondary)
            }
            HStack {
                Button { Task { await model.refreshActivity() } } label: { BusyLabel(text: L("刷新"), busyText: L("刷新中…"), busy: model.isBusy.contains("activity")) }.disabled(model.isBusy.contains("activity"))
                Button(L("添加配置目录"), action: model.addObservedDirectory)
                Button(model.isBusy.contains("clear-activity") ? L("清除中…") : L("清除已结束历史"), role: .destructive) { confirmClear = true }.disabled(model.isBusy.contains("clear-activity"))
                Spacer()
                Toggle(model.isBusy.contains("activity-setting") ? L("正在更新…") : L("记录活动"), isOn: Binding(
                    get: { model.activityEnabled },
                    set: { value in Task { await model.setActivityEnabled(value) } }
                )).disabled(model.isBusy.contains("activity-setting"))
            }
            if !model.observedDirectories.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack {
                        ForEach(model.observedDirectories, id: \.self) { directory in
                            HStack(spacing: 5) {
                                Text(directory).lineLimit(1)
                                Button { model.removeObservedDirectory(directory) } label: { Image(systemName: "xmark.circle.fill") }
                                    .buttonStyle(.borderless)
                                    .accessibilityLabel(L("移除观察目录"))
                            }
                            .padding(.horizontal, 8).padding(.vertical, 4)
                            .background(.quaternary, in: Capsule())
                        }
                    }
                }
            }
            if !model.activityErrors.isEmpty {
                GroupBox(L("观察状态")) {
                    VStack(alignment: .leading, spacing: 5) {
                        ForEach(model.activityErrors, id: \.self) { error in
                            Label(error, systemImage: "exclamationmark.triangle.fill")
                                .foregroundStyle(.orange)
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
            GroupBox {
                if model.activityRuns.isEmpty {
                    VStack(spacing: 8) {
                        Image(systemName: "clock")
                            .font(.title2).foregroundStyle(.secondary)
                        Text(L("没有可显示的活动记录"))
                        Text(L("这可能是没有接入观测的新任务、记录被关闭，或当前目录没有历史；它不表示全部服务商正常。"))
                            .font(.caption).foregroundStyle(.secondary).multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity).padding(28)
                } else {
                    List(model.activityRuns) { run in
                        ActivityRow(model: model, run: run)
                    }
                    .frame(minHeight: 360)
                }
            }
        }
        .padding(24)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .task {
            while !Task.isCancelled {
                await model.refreshActivity()
                try? await Task.sleep(nanoseconds: 2_000_000_000)
            }
        }
        .alert(L("清除活动历史？"), isPresented: $confirmClear) {
            Button(L("取消"), role: .cancel) {}
            Button(L("清除已结束记录"), role: .destructive) { Task { await model.clearActivityHistory() } }
        } message: {
            Text(L("仅清除已结束任务的活动元数据，不会删除配置、研究证据或你导出的文件。"))
        }
        .sheet(item: Binding(get: { model.selectedActivity }, set: { if $0 == nil { model.selectedActivity = nil } })) { run in
            ActivityDetailView(model: model, run: run)
        }
    }
}

private struct ActivityRow: View {
    @ObservedObject var model: AppModel
    let run: ActivityRun

    var body: some View {
        HStack(alignment: .center, spacing: 12) {
            VStack(alignment: .leading, spacing: 3) {
                HStack {
                    Text(model.displayLabel(for: run)).fontWeight(.medium)
                    StatusTag(status: run.status, label: run.status == "stale" ? L("状态未更新") : model.state?.statusLabels[run.status])
                    Text(run.origin.uppercased()).font(.caption).foregroundStyle(.secondary)
                }
                Text([run.phase.map { model.state?.phaseLabel($0) ?? L("处理中") }, run.provider, run.model].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · "))
                    .font(.caption).foregroundStyle(.secondary)
                    .lineLimit(1)
                if let error = run.errorType { Text(model.state?.statusLabels[error] ?? L("任务异常")).font(.caption).foregroundStyle(.red) }
            }
            Spacer()
            Text(run.elapsedText).font(.caption.monospacedDigit()).foregroundStyle(.secondary)
            Button(model.isBusy.contains("details:\(run.runID)") ? L("读取中…") : L("详情")) { Task { await model.showActivityDetails(run) } }.disabled(model.isBusy.contains("details:\(run.runID)"))
            if model.canCancel(run) {
                Button(role: .destructive) { Task { await model.cancel(run) } } label: { BusyLabel(text: L("取消"), busyText: L("取消中…"), busy: model.isBusy.contains("cancel:\(run.runID)")) }.disabled(model.isBusy.contains("cancel:\(run.runID)"))
            }
        }
        .padding(.vertical, 4)
    }
}

private struct ActivityDetailView: View {
    @ObservedObject var model: AppModel
    let run: ActivityRun
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text(L("活动详情")).font(.title2.weight(.semibold))
                Spacer()
                Button(L("完成")) { dismiss() }
            }
            Text(model.displayLabel(for: run)).font(.headline)
            KeyValueLine(label: L("配置版本"), value: run.configRevision ?? L("活动记录未提供"))
            if model.hasOwnedResult(for: run) {
                Button(L("查看结果")) { model.showOwnedResult(run) }
            }
            if let result = model.activityResult(for: run) {
                ActivityResultView(result: result)
            }
            if let details = model.activityDetails {
                let events = details["events"]?.arrayValue ?? []
                if details["ok"]?.boolValue == false {
                    Text(details["error"]?.stringValue ?? L("活动详情当前不可读取。"))
                        .foregroundStyle(.red)
                } else if !events.isEmpty {
                    List(events.indices, id: \.self) { index in
                        ActivityEventRow(event: events[index], phaseLabel: model.state?.phaseLabel(events[index]["phase"]?.displayString ?? "") ?? L("未知阶段"))
                    }
                } else {
                    Text(L("后端没有返回额外的脱敏阶段元数据。"))
                        .foregroundStyle(.secondary)
                }
                DisclosureGroup(L("高级详情")) {
                    Text(details.redacted().prettyPrinted())
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                }
            } else {
                ProgressView(L("正在读取脱敏活动详情…"))
            }
            Spacer()
        }
        .padding(20)
        .frame(minWidth: 560, minHeight: 360)
    }
}

private struct ActivityResultView: View {
    let result: JSONValue

    var body: some View {
        GroupBox(L("任务结果")) {
            VStack(alignment: .leading, spacing: 8) {
                if let text = result.readableText, !text.isEmpty {
                    Text(text).textSelection(.enabled)
                } else {
                    Text(L("后端没有提供可直接阅读的结果文本。"))
                        .foregroundStyle(.secondary)
                }
                DisclosureGroup(L("高级 JSON")) {
                    Text(result.redacted().prettyPrinted())
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct ActivityEventRow: View {
    let event: JSONValue
    let phaseLabel: String

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(phaseLabel)
                Text([event["provider"]?.stringValue, event["model"]?.stringValue]
                    .compactMap { $0 }
                    .filter { !$0.isEmpty }
                    .joined(separator: " · "))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
            StatusTag(status: event["status"]?.displayString ?? "unknown")
        }
        .padding(.vertical, 3)
    }
}

private struct StatusTag: View {
    let status: String
    var label: String? = nil

    var body: some View {
        Text(label ?? ["running": L("运行中"), "finished": L("已完成"), "failed": L("失败"), "cancelled": L("已取消"), "cancelling": L("正在取消"), "stale": L("状态未更新"), "interrupted": L("已中断")][status] ?? L("状态未知"))
            .font(.caption.weight(.medium))
            .foregroundStyle(color)
            .padding(.horizontal, 8).padding(.vertical, 3)
            .background(color.opacity(0.12), in: Capsule())
    }

    private var color: Color {
        switch status {
        case "finished", "up_to_date": return .green
        case "failed", "interrupted": return .red
        case "running", "cancelling": return .orange
        case "cancelled", "stale": return .secondary
        default: return .secondary
        }
    }
}

private struct EnvironmentSetupView: View {
    @ObservedObject var model: AppModel
    private var environment: JSONValue { model.environmentState ?? .object([:]) }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            GroupBox(L("准备独立 CLI")) {
                VStack(alignment: .leading, spacing: 14) {
                    Text(environment["message"]?.displayString ?? L("先检测环境，再安装缺少的组件。"))
                        .textSelection(.enabled)
                    if model.environmentBusy, let total = environment["total"]?.numberValue, total > 0 {
                        ProgressView(value: environment["received"]?.numberValue ?? 0, total: total)
                    }
                    ForEach(environment["steps"]?.arrayValue ?? [], id: \.self) { step in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(step["name"]?.displayString ?? "").font(.headline)
                                Spacer()
                                Text(step["status_label"]?.displayString ?? L("待处理"))
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            Text(step["message"]?.displayString ?? "").foregroundStyle(.secondary)
                        }
                    }
                    if environment["plan_id"]?.stringValue?.isEmpty == false {
                        Text(model.environmentActions.isEmpty ? L("独立 CLI 已就绪。可返回上方检查并更新 Skills。") :
                            L("本次将执行：\n") + model.environmentActions.map { "• " + $0 }.joined(separator: "\n"))
                    } else { Text(L("检测后会在这里列出将要安装或配置的内容。")).foregroundStyle(.secondary) }
                    HStack {
                        Button { Task { await model.environmentAction("environment.check") } } label: {
                            BusyLabel(text: L("检测环境"), busyText: L("检测中…"), busy: model.environmentBusy && environment["operation"]?.stringValue == "check")
                        }
                            .disabled(model.skillsBusy || model.environmentBusy || model.isUpdatingCLI)
                        Button { Task { await model.prepareEnvironment() } } label: {
                            BusyLabel(text: model.environmentActionLabel, busyText: L("准备中…"), busy: model.environmentBusy && environment["operation"]?.stringValue == "install")
                        }
                            .buttonStyle(.borderedProminent)
                            .disabled(model.skillsBusy || model.environmentBusy || model.isUpdatingCLI || model.environmentActions.isEmpty || environment["can_install"]?.boolValue != true || environment["plan_id"]?.stringValue?.isEmpty != false)
                        Button { Task { await model.environmentAction("environment.verify") } } label: {
                            BusyLabel(text: L("验证可用性"), busyText: L("验证中…"), busy: model.environmentBusy && environment["operation"]?.stringValue == "verify")
                        }
                            .disabled(model.skillsBusy || model.environmentBusy || model.isUpdatingCLI)
                        if environment["can_cancel"]?.boolValue == true {
                            Button(L("取消下载")) { Task { await model.environmentAction("environment.cancel") } }
                        }
                    }
                    HStack {
                        Button(L("去配置服务商")) { model.selectedDestination = .providers }
                        Button(L("复制 AI 测试指引"), action: model.copyEnvironmentTest)
                            .disabled(environment["invocation"]?.stringValue?.isEmpty != false)
                    }
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            DisclosureGroup(L("安装位置与检查详情")) {
                VStack(alignment: .leading, spacing: 8) {
                    KeyValueLine(label: L("独立安装目录"), value: environment["tools_dir"]?.displayString ?? L("检测后显示"))
                    if let checked = environment["checked_at"]?.numberValue, checked > 0 {
                        KeyValueLine(label: L("检查时间"), value: Date(timeIntervalSince1970: checked).formatted())
                    }
                    KeyValueLine(label: "Node", value: environment["node"]?["path"]?.displayString ?? "")
                    KeyValueLine(label: "Python", value: environment["python"]?["path"]?.displayString ?? "")
                    KeyValueLine(label: L("独立调用"), value: environment["invocation"]?.displayString ?? "")
                    KeyValueLine(label: L("配置目录"), value: environment["config_dir"]?.displayString ?? "")
                    Text(L("缺失的 Python 使用 Astral CPython；App 只负责管理，独立 CLI 不依赖 App。"))
                        .font(.caption).foregroundStyle(.secondary)
                    Text(environment["log"]?.displayString ?? "").font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                    Text(environment["error"]?.displayString ?? "").foregroundStyle(.red)
                }.frame(maxWidth: .infinity, alignment: .leading).padding(.top, 8)
            }
        }.disabled(model.connection != .ready)
    }
}

private struct AgentSkillsView: View {
    @ObservedObject var model: AppModel
    private var skills: JSONValue { model.skillsState ?? .object([:]) }
    private var unavailable: Bool { model.connection != .ready || model.environmentBusy || model.isUpdatingCLI || model.skillsBusy || model.skillsChecking }

    private func status(_ value: JSONValue) -> String {
        switch value["status"]?.stringValue {
        case "missing": return L("未安装")
        case "stale": return L("内容不同，可同步")
        case "up_to_date", "extra_files": return L("与来源一致")
        case "error": return L("读取失败")
        default: return L("状态未知")
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            GroupBox(L("最新正式版 Skills")) {
                VStack(alignment: .leading, spacing: 12) {
                    if let version = skills["source"]?["version"]?.stringValue {
                        KeyValueLine(label: L("来源版本"), value: "npm " + version)
                        if let checked = skills["source"]?["checked_at"]?.numberValue {
                            KeyValueLine(label: L("最近成功检查"), value: Date(timeIntervalSince1970: checked).formatted())
                        }
                        if skills["cached"]?.boolValue == true { Text(L("显示上次缓存；请检查最新 Skills 后再更新。")) }
                    } else { Text(L("尚未获取正式版 Skills；当前文件仅与 App 内置副本比较。")) }
                    KeyValueLine(label: L("独立 CLI"), value: skills["cli_version"]?.displayString ?? L("未发现"))
                    Text(skills["error"]?.displayString ?? "").foregroundStyle(.red)
                    Text(skills["compatibility"]?.displayString ?? "").foregroundStyle(.secondary)
                    Toggle(L("每天自动检查 Skills，只提示，不写入"), isOn: Binding(
                        get: { skills["auto_check"]?.boolValue ?? true },
                        set: { enabled in Task { await model.skillsAction("skills.auto", params: .object(["enabled": .bool(enabled)])) } }))
                    HStack {
                        Button { Task { await model.skillsAction("skills.check") } } label: {
                            BusyLabel(text: L("检查最新 Skills"), busyText: L("检查中…"), busy: model.skillsChecking)
                        }
                        Button { Task { await model.refreshSkillStatus() } } label: { Text(L("刷新本机状态")) }
                    }.disabled(unavailable)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            GroupBox(L("选择 Agent")) {
                VStack(alignment: .leading, spacing: 12) {
                    Text(L("状态只表示 Smart Search Skill 内容。Codex 使用的 .agents/skills 也可能被其他兼容 Agent 读取。"))
                        .font(.callout).foregroundStyle(.secondary)
                    ForEach(skills["targets"]?.arrayValue ?? [], id: \.self) { target in
                        let id = target["target"]?.stringValue ?? ""
                        VStack(alignment: .leading, spacing: 4) {
                            Toggle((target["label"]?.displayString ?? id) + " · " + status(target), isOn: Binding(
                                get: { model.selectedSkillTargets.contains(id) },
                                set: { if $0 { model.selectedSkillTargets.insert(id) } else { model.selectedSkillTargets.remove(id) } }))
                                .disabled(model.skillsBusy)
                            Text(target["path"]?.displayString ?? "").font(.caption).textSelection(.enabled)
                            let changed = (target["stale_files"]?.arrayValue ?? []) + (target["missing_files"]?.arrayValue ?? [])
                            if !changed.isEmpty { Text(L("将同步：{0}", changed.map(\.displayString).joined(separator: ", "))).font(.caption).foregroundStyle(.secondary) }
                            ForEach(target["legacy_locations"]?.arrayValue ?? [], id: \.self) { legacy in
                                Text(L("历史副本，保留：{0}", legacy["path"]?.displayString ?? "")).font(.caption)
                            }
                            if let error = target["error"]?.stringValue { Text(error).foregroundStyle(.red) }
                        }
                    }
                    Button { Task { await model.installSelectedSkills() } } label: {
                        BusyLabel(text: L("更新所选 Skills"), busyText: L("更新中…"), busy: model.skillsBusy)
                    }.buttonStyle(.borderedProminent)
                        .disabled(unavailable || model.selectedSkillTargets.isEmpty || skills["can_sync"]?.boolValue != true)
                    ForEach(skills["result"]?["installed"]?.arrayValue ?? [], id: \.self) { receipt in
                        Text((receipt["target"]?.displayString ?? "") + L("：已同步"))
                        if let backup = receipt["backup"]?.stringValue, !backup.isEmpty {
                            Text(L("\n备份：{0}", backup)).font(.caption).textSelection(.enabled)
                        }
                    }
                    ForEach(skills["result"]?["failed"]?.arrayValue ?? [], id: \.self) { failure in
                        Text((failure["target"]?.displayString ?? "") + ": " + (failure["error"]?.displayString ?? "")).foregroundStyle(.red)
                    }
                    Text(L("不同内容会先备份；额外文件与未选目标保持原样。更新后重新打开 Agent 会话；Gemini 可运行 /skills reload。实际调用仍需在 Agent 中验证。"))
                        .font(.caption).foregroundStyle(.secondary)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }
}

private struct IntegrationView: View {
    @ObservedObject var model: AppModel
    @State private var confirmEnableCLI = false

    var body: some View {
        guard model.state != nil else { return AnyView(BackendUnavailableView(model: model)) }
        return AnyView(ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("更新 Skills")).font(.largeTitle.weight(.bold))
                    Text(L("为编程 Agent 安装或更新 Smart Search Skill。软件更新不会自动同步这些文件。"))
                        .foregroundStyle(.secondary)
                }

                AgentSkillsView(model: model)
                DisclosureGroup(L("共用独立 CLI 环境")) {
                    Text(L("所有 Agent 共用独立 CLI。此处只准备运行环境，Skills 在上方单独更新。"))
                    EnvironmentSetupView(model: model)
                    Button(L("去设置更新 CLI")) { model.selectedDestination = .settings }
                }

                DisclosureGroup(L("高级：App 内置入口（依赖 App）")) {
                    VStack(alignment: .leading, spacing: 10) {
                        KeyValueLine(label: L("内置路径"), value: model.cliStatus?["bundled_path"]?.displayString ?? L("尚未读取"))
                        KeyValueLine(label: L("外部路径"), value: model.cliStatus?["external_path"]?.displayString ?? L("未发现或尚未读取"))
                        KeyValueLine(label: L("内置版本"), value: model.cliStatus?["version"]?.displayString ?? L("尚未读取"))
                        HStack {
                            Button(L("复制内置路径"), action: model.copyBundledCLIPath)
                            Button { Task { await model.refreshCLIStatus() } } label: { BusyLabel(text: L("刷新 CLI 状态"), busyText: L("刷新中…"), busy: model.isBusy.contains("cli.status")) }.disabled(model.isBusy.contains("cli.status"))
                            Spacer()
                        }
                        Divider()
                        Text(L("内置入口随 App 卸载失效。上方的独立 CLI 接入不使用此入口；已有同名命令不会被覆盖。"))
                            .font(.caption).foregroundStyle(.secondary)
                        Button(model.isBusy.contains("cli.enable") ? L("启用中…") : L("启用内置 CLI…")) { confirmEnableCLI = true }
                            .disabled(model.connection != .ready || model.environmentBusy || model.isBusy.contains("cli.enable"))
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }


            }
            .padding(24)
            .frame(maxWidth: 900, alignment: .leading)
        }
        .alert(L("启用内置 CLI？"), isPresented: $confirmEnableCLI) {
            Button(L("取消"), role: .cancel) {}
            Button(L("确认启用")) { Task { await model.enableBundledCLI() } }
        } message: {
            Text(L("这会要求后端创建用户级 CLI 链接；它不会覆盖已存在的同名外部 CLI。"))
        })
    }
}

private struct SettingsAboutView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(L("设置与关于")).font(.largeTitle.weight(.bold))
                    Text(L("本页只调整 App 自身连接和观察范围；不会改写外部 npm 或 Python 安装。"))
                        .foregroundStyle(.secondary)
                }

                GroupBox(L("语言")) {
                    VStack(alignment: .leading, spacing: 10) {
                        Picker(L("界面语言"), selection: Binding(
                            get: { model.languagePreference },
                            set: { value in Task { await model.setLanguage(value) } })) {
                            Text(L("跟随系统")).tag("auto")
                            Text(L("简体中文")).tag("zh")
                            Text("English").tag("en")
                        }
                        .disabled(model.skillsBusy || model.environmentBusy || model.isUpdatingCLI || model.isBusy.contains("language"))
                        Text(L("App 与独立 CLI 分别保存语言选择。环境写入期间请等待操作完成。"))
                            .font(.caption).foregroundStyle(.secondary)
                    }.frame(maxWidth: .infinity, alignment: .leading)
                }

                GroupBox(L("当前配置目录")) {
                    VStack(alignment: .leading, spacing: 10) {
                        Text(model.state?.configDirectory ?? L("后端尚未提供"))
                            .textSelection(.enabled)
                        Button(model.isBusy.contains("profile") ? L("切换中…") : L("选择配置目录…"), action: model.chooseConfigDirectory)
                            .disabled(model.connection != .ready || model.configOperationBusy)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                GroupBox(L("后端连接")) {
                    VStack(alignment: .leading, spacing: 10) {
                        HStack {
                            TextField(L("开发环境后端路径（可选）"), text: $model.backendPathOverride)
                            Button(L("选择…"), action: model.chooseBackendExecutable)
                            Button(L("使用内置后端")) { model.saveBackendOverride("") }
                        }
                        Text(L("发布包默认使用 Contents/Resources/backend/smart-search。仅显式选择时才会使用开发路径。"))
                            .font(.caption).foregroundStyle(.secondary)
                        HStack {
                            Stepper(L("请求超时：{0} 秒", "\(Int(model.requestTimeoutSeconds))"), value: $model.requestTimeoutSeconds, in: 5...300, step: 5)
                            Button(L("应用超时"), action: model.applyTimeout)
                            Button(model.isBusy.contains("connect") ? L("连接中…") : L("重新连接")) { model.saveBackendOverride(model.backendPathOverride); Task { await model.reconnect() } }.disabled(model.isBusy.contains("connect"))
                        }
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                }

                UpdatesView(model: model)
            }
            .padding(24)
            .frame(maxWidth: 900, alignment: .leading)
        }
    }
}

private struct KeyValueLine: View {
    let label: String
    let value: String

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(label).foregroundStyle(.secondary).frame(minWidth: 90, alignment: .leading)
            Text(value).textSelection(.enabled)
            Spacer(minLength: 0)
        }
    }
}

private struct UpdatesView: View {
    @ObservedObject var model: AppModel
    private var app: JSONValue? { model.updateResult?["app"] }
    private var cli: JSONValue? { model.updateResult?["cli"] }
    private var download: JSONValue? { model.updateResult?["download"] }
    private var checking: Bool { model.updateResult?["checking"]?.boolValue == true || model.isBusy.contains("update") }
    private var cancelling: Bool { download?["status"]?.stringValue == "cancelling" || model.isBusy.contains("updates.cancel") }
    private var downloading: Bool { download?["status"]?.stringValue == "downloading" || cancelling }
    private var ready: Bool { download?["status"]?.stringValue == "ready" }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            GroupBox(L("版本与更新")) {
                VStack(alignment: .leading, spacing: 10) {
                    Toggle(L("自动检查，每 24 小时一次，点击才下载"), isOn: Binding(
                        get: { model.updateResult?["auto_check"]?.boolValue ?? true },
                        set: { value in Task { await model.updateAction("updates.auto", params: .object(["enabled": .bool(value)])) } }))
                    HStack {
                        Button { Task { await model.checkForUpdates() } } label: {
                            BusyLabel(text: L("检查更新"), busyText: L("检查中…"), busy: checking)
                        }.disabled(checking || model.connection != .ready)
                        Button(L("刷新已安装版本")) { Task { await model.refreshState() } }.disabled(model.isBusy.contains("state"))
                    }
                    if let error = model.updateResult?["error"]?.stringValue, !error.isEmpty { Text(error).foregroundStyle(.red) }
                    if let timestamp = app?["checked_at"]?.numberValue {
                        Text(L("App 检查时间：{0}", "\(Date(timeIntervalSince1970: timestamp).formatted())")).font(.caption).foregroundStyle(.secondary)
                    }
                    Text(L("App 和内置引擎一起更新；独立 CLI 使用原管理器更新。")).font(.caption).foregroundStyle(.secondary)
                }.frame(maxWidth: .infinity, alignment: .leading)
            }
            appCard
            cliCard
        }
    }

    private var appCard: some View {
        GroupBox(L("App 与内置引擎")) {
            VStack(alignment: .leading, spacing: 10) {
                KeyValueLine(label: "App", value: app?["current_version"]?.displayString ?? L("尚未读取"))
                KeyValueLine(label: L("内置引擎"), value: model.state?.version ?? L("尚未读取"))
                KeyValueLine(label: L("可安装稳定版"), value: app?["latest_version"]?.displayString ?? L("尚未检查"))
                if app?["package_pending"]?.boolValue == true { Text(L("较新的发行版尚未提供本平台完整安装包。")).foregroundStyle(.orange) }
                if downloading {
                    let received = download?["received"]?.numberValue ?? 0
                    let total = max(download?["total"]?.numberValue ?? 1, 1)
                    ProgressView(value: received, total: total)
                    Text(L("已下载 {0} / {1} MiB", "\(Int(received / 1048576))", "\(Int(total / 1048576))")).monospacedDigit()
                }
                if ready { Text(L("已下载并校验，尚未安装。")).foregroundStyle(.green) }
                if cancelling { Text(L("正在取消下载…")).foregroundStyle(.secondary) }
                if let error = download?["error"]?.stringValue, !error.isEmpty { Text(error).foregroundStyle(.orange) }
                HStack {
                    Button(downloading ? L("下载中…") : L("下载安装包")) { Task { await model.updateAction("updates.download") } }
                        .disabled(downloading || model.isBusy.contains("updates.download") || app?["available"]?.boolValue != true || !(app?["error"]?.stringValue ?? "").isEmpty)
                    Button(cancelling ? L("正在取消…") : L("取消下载")) { Task { await model.updateAction("updates.cancel") } }.disabled(!downloading || cancelling)
                    Button(L("打开安装包")) { Task { await model.openDownloadedUpdate() } }.disabled(model.environmentBusy || !ready || model.isBusy.contains("updates.installer"))
                }
                HStack {
                    Button(L("打开下载目录"), action: model.revealDownloadedUpdate).disabled(!ready)
                    Link(L("查看版本说明"), destination: URL(string: "https://github.com/konbakuyomu/smartsearch/releases")!)
                }
                Text(L("安装包校验 SHA256，尚未验证系统代码签名。打开 DMG 后先退出 App，再按正常方式安装并重新打开核对版本。"))
                    .font(.caption).foregroundStyle(.secondary)
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }

    private var cliCard: some View {
        GroupBox(L("独立 CLI")) {
            VStack(alignment: .leading, spacing: 10) {
                KeyValueLine(label: L("实际版本"), value: model.cliStatus?["external_version"]?.displayString ?? L("未安装或未知"))
                KeyValueLine(label: L("npm 稳定版"), value: cli?["latest_version"]?.displayString ?? L("尚未检查"))
                KeyValueLine(label: L("来源"), value: model.cliStatus?["manager_label"]?.displayString ?? L("未确认"))
                KeyValueLine(label: L("生效路径"), value: model.cliStatus?["resolved_path"]?.displayString ?? model.cliStatus?["external_path"]?.displayString ?? L("未发现"))
                Text(L("入口：") + (model.cliStatus?["external_path"]?.displayString ?? L("未发现"))).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                Text(model.cliStatus?["update_note"]?.displayString ?? "").font(.caption).foregroundStyle(.secondary)
                HStack {
                    Button(model.isUpdatingCLI ? L("更新中…") : L("更新 CLI")) { Task { await model.updateCLI() } }
                        .disabled(model.skillsBusy || model.environmentBusy || model.isUpdatingCLI || model.isBusy.contains("cli.update") || checking || cli?["available"]?.boolValue != true || model.cliStatus?["can_update"]?.boolValue != true || !(cli?["error"]?.stringValue ?? "").isEmpty)
                    Button(L("复制更新命令"), action: model.copyCLIUpdateCommand).disabled(cli?["command"] == nil)
                }
                if model.isUpdatingCLI { Text(L("请保持 App 打开，等待原管理器完成。")).foregroundStyle(.orange) }
                if model.updateResult?["cli_update"]?["status"]?.stringValue == "finished" { Text(L("已更新并验证实际版本。")).foregroundStyle(.green) }
                if let error = model.updateResult?["cli_update"]?["error"]?.stringValue, !error.isEmpty { Text(error).foregroundStyle(.red) }
                DisclosureGroup(L("更新日志与命令")) {
                    Text((cli?["command"]?.stringValue ?? "") + "\n" + (model.updateResult?["cli_update"]?["log"]?.stringValue ?? ""))
                        .font(.system(.caption, design: .monospaced)).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading)
                }
            }.frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private extension JSONValue {
    var readableText: String? {
        let preferredKeys = ["display_text", "answer", "content", "text", "summary", "message", "output", "error"]
        if let object = objectValue {
            for key in preferredKeys {
                if let text = object[key]?.stringValue, !text.isEmpty { return text }
            }
            for key in ["result", "data"] {
                if let text = object[key]?.readableText, !text.isEmpty { return text }
            }
        }
        return stringValue
    }

    var sourceLinks: [URL] {
        var links: Set<URL> = []
        collectSourceLinks(into: &links)
        return links.sorted { $0.absoluteString < $1.absoluteString }
    }

    private func collectSourceLinks(into links: inout Set<URL>) {
        switch self {
        case let .object(object):
            for key in ["url", "link", "source_url", "href"] {
                if let value = object[key]?.stringValue,
                   let url = URL(string: value),
                   let scheme = url.scheme?.lowercased(),
                   ["http", "https"].contains(scheme) {
                    links.insert(url)
                }
            }
            for value in object.values { value.collectSourceLinks(into: &links) }
        case let .array(values):
            for value in values { value.collectSourceLinks(into: &links) }
        default:
            break
        }
    }
}
