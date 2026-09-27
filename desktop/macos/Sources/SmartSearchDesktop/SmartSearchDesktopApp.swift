import AppKit
import SwiftUI

@main
struct SmartSearchDesktopApp: App {
    @NSApplicationDelegateAdaptor(ApplicationDelegate.self) private var applicationDelegate
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup(id: "main") {
            ContentView(model: model)
                .frame(minWidth: 920, minHeight: 620)
                .background(WindowConfigurator { window in
                    applicationDelegate.configure(window: window, model: model)
                })
        }
        .commands {
            CommandMenu(L("导航")) {
                Button(L("概览")) { model.selectedDestination = .overview }.keyboardShortcut("1", modifiers: .command)
                Button(L("服务商")) { model.selectedDestination = .providers }.keyboardShortcut("2", modifiers: .command)
                Button(L("搜索与研究")) { model.selectedDestination = .search }.keyboardShortcut("3", modifiers: .command)
                Button(L("活动")) { model.selectedDestination = .activity }.keyboardShortcut("4", modifiers: .command)
                Button(L("更新 Skills")) { model.selectedDestination = .integration }.keyboardShortcut("5", modifiers: .command)
                Button(L("设置与关于")) { model.selectedDestination = .settings }.keyboardShortcut("6", modifiers: .command)
            }
            CommandGroup(after: .appInfo) {
                Button(L("刷新状态")) { Task { await model.refreshState() } }.keyboardShortcut("r", modifiers: .command)
            }
        }

        MenuBarExtra {
            Button(L("显示 Smart Search")) { applicationDelegate.showMainWindow() }
            if model.hasOwnedActiveRuns {
                Text(L("有 App 任务正在后台运行"))
            }
            Divider()
            Button(L("退出")) { NSApp.terminate(nil) }
        } label: {
            Image(nsImage: NSApp.applicationIconImage)
                .resizable().scaledToFit().frame(width: 18, height: 18)
                .accessibilityLabel("Smart Search")
        }
        .menuBarExtraStyle(.menu)
    }
}

@MainActor
final class ApplicationDelegate: NSObject, NSApplicationDelegate {
    private let mainWindowDelegate = MainWindowDelegate()
    private weak var model: AppModel?

    func configure(window: NSWindow, model: AppModel) {
        self.model = model
        mainWindowDelegate.model = model
        window.delegate = mainWindowDelegate
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if !flag { showMainWindow() }
        return true
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        if let model, model.isUpdatingCLI || model.environmentBusy || model.skillsBusy {
            model.noticeMessage = L("环境或 Skills 操作正在进行，请等待完成后退出。")
            showMainWindow()
            return .terminateCancel
        }
        guard let model, model.hasOwnedActiveRuns else { return .terminateNow }
        model.presentQuitChoice { choice in
            switch choice {
            case .background, .return:
                sender.reply(toApplicationShouldTerminate: false)
            case .stopAndQuit:
                Task {
                    await model.shutdownForQuit()
                    sender.reply(toApplicationShouldTerminate: true)
                }
            }
        }
        return .terminateLater
    }

    func showMainWindow() {
        NSApp.activate(ignoringOtherApps: true)
        let window = NSApp.windows.first { $0.isVisible || $0.canBecomeKey }
        window?.makeKeyAndOrderFront(nil)
    }
}

@MainActor
private final class MainWindowDelegate: NSObject, NSWindowDelegate {
    weak var model: AppModel?

    func windowShouldClose(_ sender: NSWindow) -> Bool {
        if let model, model.isUpdatingCLI || model.environmentBusy || model.skillsBusy {
            model.noticeMessage = L("环境操作或 CLI 更新正在进行，请等待完成；可以最小化窗口。")
            return false
        }
        guard let model, model.hasOwnedActiveRuns else { return true }
        model.presentWindowCloseChoice(for: sender)
        return false
    }
}

private struct WindowConfigurator: NSViewRepresentable {
    let configure: (NSWindow) -> Void

    func makeNSView(context: Context) -> NSView {
        let view = NSView()
        DispatchQueue.main.async {
            if let window = view.window { configure(window) }
        }
        return view
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        if let window = nsView.window { configure(window) }
    }
}
