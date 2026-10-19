import AppKit
import SwiftUI
import UniformTypeIdentifiers

/// The settings being edited. Nothing changes until Save.
final class SettingsDraft: ObservableObject {
    @Published var configPath: String
    @Published var pythonPath: String
    @Published var lan: Bool
    @Published var portText: String
    @Published var collectHours: Int
    @Published var openAtLogin: Bool
    @Published var autoUpdate: Bool
    @Published var sitting: Bool
    @Published var error: String?
    let repoPath: String?
    let defaultPython: String

    init(settings: AppSettings, openAtLogin: Bool, repoPath: String?, defaultPython: String = AppSettings.defaultPython) {
        configPath = settings.configPath ?? ""
        pythonPath = settings.pythonPath
        lan = settings.lan
        portText = String(settings.port)
        collectHours = settings.collectEveryHours
        self.openAtLogin = openAtLogin
        autoUpdate = settings.autoUpdateCheck
        sitting = settings.sittingReminders
        self.repoPath = repoPath
        self.defaultPython = defaultPython
    }

    var port: Int? {
        guard let value = Int(portText.trimmingCharacters(in: .whitespaces)), (1024...65535).contains(value) else { return nil }
        return value
    }
}

struct SettingsView: View {
    @ObservedObject var draft: SettingsDraft
    var onChooseConfig: () -> Void = {}
    var onChoosePython: () -> Void = {}
    var onShowLogs: () -> Void = {}
    var onCancel: () -> Void = {}
    var onSave: () -> Void = {}

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Grid(alignment: .leadingFirstTextBaseline, horizontalSpacing: 12, verticalSpacing: 14) {
                GridRow {
                    label(S.configFile)
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(alignment: .firstTextBaseline) {
                            Text(draft.configPath.isEmpty ? "—" : (draft.configPath as NSString).abbreviatingWithTildeInPath)
                                .font(.system(size: 12, design: .monospaced)).foregroundColor(Tok.ink)
                                .lineLimit(2).truncationMode(.middle).textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .leading)
                            Button(S.choose, action: onChooseConfig).aio()
                        }
                    }
                    .frame(width: Self.fieldWidth, alignment: .leading)
                }
                GridRow {
                    label(S.python)
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            TextField("", text: $draft.pythonPath).textFieldStyle(.roundedBorder)
                                .font(.system(size: 12, design: .monospaced))
                            Button(S.choose, action: onChoosePython).aio()
                        }
                        Text(S.pythonDefault(draft.defaultPython)).font(.system(size: 11)).foregroundColor(Tok.ink3)
                    }
                    .frame(width: Self.fieldWidth, alignment: .leading)
                }
                GridRow {
                    label(S.port)
                    TextField("", text: $draft.portText).textFieldStyle(.roundedBorder).frame(width: 80)
                        .font(.system(size: 12).monospacedDigit())
                }
                GridRow {
                    Color.clear.gridCellUnsizedAxes([.horizontal, .vertical])
                    VStack(alignment: .leading, spacing: 4) {
                        Toggle(S.lanToggle, isOn: $draft.lan)
                        Text(S.lanHelp).font(.system(size: 11)).foregroundColor(Tok.ink3).fixedSize(horizontal: false, vertical: true)
                            .padding(.leading, 20)
                    }
                    .frame(width: Self.fieldWidth, alignment: .leading)
                }
                GridRow {
                    label(S.collectEvery)
                    Stepper(value: $draft.collectHours, in: 1...24) {
                        Text(S.hours(draft.collectHours)).font(.system(size: 12.5).monospacedDigit())
                    }
                    .fixedSize()
                }
                GridRow {
                    Color.clear.gridCellUnsizedAxes([.horizontal, .vertical])
                    VStack(alignment: .leading, spacing: 8) {
                        Toggle(S.openAtLogin, isOn: $draft.openAtLogin)
                        Toggle(S.autoUpdate, isOn: $draft.autoUpdate)
                        Toggle(S.sittingToggle, isOn: $draft.sitting)
                    }
                }
            }
            .font(.system(size: 12.5))

            Divider()
            HStack(alignment: .firstTextBaseline) {
                Text(S.repository + ": " + (draft.repoPath.map { ($0 as NSString).abbreviatingWithTildeInPath } ?? S.notFound))
                    .font(.system(size: 11)).foregroundColor(Tok.ink3).lineLimit(1).truncationMode(.middle)
                Spacer()
                Button(S.showLogs, action: onShowLogs).aio(.quiet)
            }
            if let error = draft.error {
                Text(error).font(.system(size: 12, weight: .medium)).foregroundColor(Tone.off.ink)
            }
            HStack {
                Spacer()
                Button(S.cancel, action: onCancel).aio().keyboardShortcut(.cancelAction)
                Button(S.save, action: onSave).aio(.primary).keyboardShortcut(.defaultAction)
            }
        }
        .padding(20)
        .frame(width: 540, alignment: .leading)
    }

    private static let fieldWidth: CGFloat = 390

    private func label(_ text: String) -> some View {
        Text(text).font(.system(size: 12.5, weight: .medium)).foregroundColor(Tok.ink2).gridColumnAlignment(.trailing)
    }
}

final class SettingsWindowController: NSWindowController, NSWindowDelegate {
    let draft: SettingsDraft
    /// Gets the draft on Save; returns an error sentence to keep the window open.
    var onSave: (SettingsDraft) -> String? = { _ in nil }
    var onClose: () -> Void = {}

    init(draft: SettingsDraft) {
        self.draft = draft
        let window = NSWindow(contentRect: .zero, styleMask: [.titled, .closable], backing: .buffered, defer: true)
        window.title = S.settingsTitle
        window.isReleasedWhenClosed = false
        super.init(window: window)
        window.delegate = self
        var view = SettingsView(draft: draft)
        view.onChooseConfig = { [weak self] in self?.chooseConfig() }
        view.onChoosePython = { [weak self] in self?.choosePython() }
        view.onShowLogs = { NSWorkspace.shared.activateFileViewerSelecting([Paths.logs]) }
        view.onCancel = { [weak self] in self?.close() }
        view.onSave = { [weak self] in self?.save() }
        window.contentViewController = NSHostingController(rootView: view)
    }

    required init?(coder: NSCoder) { nil }

    func present() {
        window?.center()
        App.activate()
        showWindow(nil)
        window?.makeKeyAndOrderFront(nil)
    }

    private func chooseConfig() {
        if let path = Self.pickConfig(startingAt: draft.configPath) { draft.configPath = path }
    }

    private func choosePython() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.treatsFilePackagesAsDirectories = true
        panel.showsHiddenFiles = true
        panel.directoryURL = URL(fileURLWithPath: (draft.pythonPath as NSString).deletingLastPathComponent)
        App.activate()
        if panel.runModal() == .OK, let url = panel.url { draft.pythonPath = url.path }
    }

    /// The Open panel for healthaio.toml, used by the settings window and the popover.
    static func pickConfig(startingAt current: String?) -> String? {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.message = S.chooseConfig
        if let toml = UTType(filenameExtension: "toml") { panel.allowedContentTypes = [toml] }
        if let current, !current.isEmpty {
            panel.directoryURL = URL(fileURLWithPath: current).deletingLastPathComponent()
        }
        App.activate()
        guard panel.runModal() == .OK, let url = panel.url else { return nil }
        return url.path
    }

    private func save() {
        if let error = onSave(draft) {
            draft.error = error
        } else {
            close()
        }
    }

    func windowWillClose(_ notification: Notification) {
        onClose()
    }
}
