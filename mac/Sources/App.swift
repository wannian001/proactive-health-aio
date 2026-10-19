import AppKit

@main
enum App {
    static func main() {
        let args = CommandLine.arguments
        if let i = args.firstIndex(of: "--snapshot") {
            let dir = i + 1 < args.count ? args[i + 1] : "screenshots"
            exit(Snapshot.run(into: dir))
        }
        let app = NSApplication.shared
        let controller = AppController()
        app.delegate = controller
        app.setActivationPolicy(.accessory)
        app.run()
    }

    /// Brings the app forward (it has no Dock icon, so alerts and windows need this to show in front).
    static func activate() {
        if #available(macOS 14.0, *) {
            NSApp.activate()
        } else {
            NSApp.activate(ignoringOtherApps: true)
        }
    }
}

/// Owns everything: the server supervisor, the schedule, the menu bar icon and the windows, and runs what the
/// popover's buttons ask for.
final class AppController: NSObject, NSApplicationDelegate, AppActions {
    let model = AppModel()
    private let settings = AppSettings.shared
    private let supervisor = ServerSupervisor()
    private lazy var scheduler = Scheduler(quick: ProcessInfo.processInfo.environment["HEALTHAIO_MAC_QUICKSTART"] == "1")
    private lazy var updates = UpdateManager(model: model)
    private lazy var iphone = IPhoneManager(model: model)
    private let sitting = SittingWatch()
    private var status: StatusController?
    private var pairWindow: PairWindowController?
    private var settingsWindow: SettingsWindowController?
    private var signalSources: [DispatchSourceSignal] = []
    private var statusInFlight = false
    private var started = false

    func applicationDidFinishLaunching(_ notification: Notification) {
        if let other = otherInstance() {
            // two copies would fight over the port; the one already running stays
            if #available(macOS 14.0, *) { other.activate() } else { other.activate(options: []) }
            exit(0)
        }
        started = true
        AppLog.info("launched \(Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "?") (pid \(getpid()))")
        installMainMenu()
        installSignalHandlers()

        model.actions = self
        model.skippedVersion = settings.skippedVersion
        model.collectEveryHours = settings.collectEveryHours
        let status = StatusController(model: model)
        status.onOpen = { [weak self] in
            self?.refreshFullDiskAccess()
            self?.refreshStatus()
        }
        self.status = status

        supervisor.onChange = { [weak self] in self?.serverChanged() }
        updates.restartServer = { [weak self] in self?.restartServer() }
        updates.refreshStatus = { [weak self] in self?.refreshStatus() }
        iphone.refreshStatus = { [weak self] in self?.refreshStatus() }
        sitting.openDashboard = { [weak self] place in self?.openDashboard(at: place) }

        scheduler.onCollect = { [weak self] in self?.collect() }
        scheduler.onUpdateCheck = { [weak self] in self?.updates.check(userInitiated: false) }
        scheduler.onStatus = { [weak self] in self?.refreshStatus() }
        scheduler.onTick = { [weak self] in self?.tick() }

        LoginItem.refreshIfEnabled()
        checkSetup()
        refreshFullDiskAccess()
        restartServer()
        scheduler.start()
        model.nextCollect = scheduler.nextCollect
        DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in self?.refreshStatus() }

        if settings.configPath == nil && ProcessInfo.processInfo.environment["HEALTHAIO_CLI"] == nil {
            openSettings()
        }
        if let dir = ProcessInfo.processInfo.environment["HEALTHAIO_MAC_SELFTEST"], !dir.isEmpty {
            Snapshot.selfTest(status: status, into: dir)
        }
    }

    func applicationShouldTerminate(_ sender: NSApplication) -> NSApplication.TerminateReply {
        guard model.updating || model.renewing else { return .terminateNow }
        let alert = Alerts.make(title: S.quitWhileBusyTitle, text: S.quitWhileBusyText, buttons: [S.wait, S.quitAnyway], style: .warning)
        return Alerts.run(alert) == .alertSecondButtonReturn ? .terminateNow : .terminateCancel
    }

    func applicationWillTerminate(_ notification: Notification) {
        shutdown()
    }

    /// Stops the server and every command still running, so quitting leaves no process behind.
    func shutdown() {
        guard started else { return }
        started = false
        scheduler.stop()
        supervisor.stop()
        CLI.shared.terminateAll()
        AppLog.info("quit")
        AppLog.file.flush()
    }

    // MARK: state

    private func otherInstance() -> NSRunningApplication? {
        guard let id = Bundle.main.bundleIdentifier else { return nil }
        return NSRunningApplication.runningApplications(withBundleIdentifier: id).first { $0.processIdentifier != getpid() }
    }

    private func checkSetup() {
        switch CLI.shared.command(["status"]) {
        case .failure(let problem): model.setupProblem = problem.message
        case .success: model.setupProblem = nil
        }
    }

    private func serverChanged() {
        model.server = supervisor.state
        model.serverLAN = supervisor.lan
        model.port = supervisor.port
    }

    private func restartServer() {
        supervisor.start(lan: settings.lan, port: settings.port)
        serverChanged()
    }

    private func tick() {
        model.now = Date()
        model.nextCollect = scheduler.nextCollect
        updates.offerPendingIfIdle()
        iphone.checkSignature()
        sitting.tick()
    }

    func refreshFullDiskAccess() {
        let probed = FullDiskAccess.probe()
        if probed != .unknown || model.fda == .unknown { model.fda = probed }
    }

    func refreshStatus() {
        guard !statusInFlight else { return }
        statusInFlight = true
        scheduler.statusRead()
        CLI.shared.run(["status", "--json"], timeout: Timeouts.short) { [weak self] result in
            guard let self else { return }
            self.statusInFlight = false
            self.statusArrived(result)
        }
    }

    private func statusArrived(_ result: CLIResult) {
        guard let json = result.json else {
            if result.problem == nil { model.statusError = result.failureText }
            return
        }
        model.statusError = nil
        let info = StatusInfo(json)
        if let version = info.version { model.version = version }
        model.devices = info.devices
        model.iphone = info.iphone
        if let collect = info.collect, !model.collecting {
            // keep the newer of what we ran ourselves and what the status file says
            if (collect.at ?? .distantPast) >= (model.collect?.at ?? .distantPast) { model.collect = collect }
        }
        if let update = info.update, !model.checkingUpdate {
            if (update.checkedAt ?? .distantPast) >= (model.update?.checkedAt ?? .distantPast) { model.update = update }
        }
        if FullDiskAccess.probe() == .unknown, let fda = info.fullDiskAccess {
            model.fda = fda ? .granted : .denied
        }
        iphone.checkSignature()
    }

    func collect() {
        guard !model.collecting, !model.updating, model.setupProblem == nil else { return }
        model.collecting = true
        model.collectError = nil
        scheduler.collectStarted()
        model.nextCollect = scheduler.nextCollect
        CLI.shared.run(["collect", "--json"], timeout: Timeouts.collect) { [weak self] result in
            guard let self else { return }
            self.model.collecting = false
            if let collect = CollectResult(result.json) {
                self.model.collect = collect
            } else {
                self.model.collectError = result.failureText
            }
            self.refreshFullDiskAccess()
            self.refreshStatus()
        }
    }

    // MARK: AppActions

    func openDashboard() { openDashboard(at: "") }

    /// The dashboard, at a place on a page (`#exercise/sitting`) or at its first page.
    func openDashboard(at place: String) {
        if let url = URL(string: "http://localhost:\(supervisor.port)/\(place)") { NSWorkspace.shared.open(url) }
        status?.close()
    }

    func collectNow() { collect() }

    func openPrivacySettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles") {
            NSWorkspace.shared.open(url)
        }
        status?.close()
    }

    func renewIPhone() { iphone.renew() }

    func pairIPhone() {
        status?.close()
        if let window = pairWindow {
            window.present()
            return
        }
        let window = PairWindowController()
        window.onLetConnect = { [weak self] in
            guard let self else { return }
            self.settings.lan = true
            self.restartServer()
        }
        window.onClose = { [weak self] in
            self?.pairWindow = nil
            self?.refreshStatus()
        }
        pairWindow = window
        window.present()
    }

    func checkForUpdates() { updates.check(userInitiated: true) }

    func installUpdate() {
        status?.close()
        updates.offerCurrent()
    }

    func openSettings() {
        status?.close()
        if let window = settingsWindow {
            window.present()
            return
        }
        let draft = SettingsDraft(settings: settings, openAtLogin: LoginItem.isEnabled, repoPath: AppSettings.repoPath)
        let window = SettingsWindowController(draft: draft)
        window.onSave = { [weak self] draft in self?.apply(draft) }
        window.onClose = { [weak self] in self?.settingsWindow = nil }
        settingsWindow = window
        window.present()
    }

    func chooseConfig() {
        status?.close()
        guard let path = SettingsWindowController.pickConfig(startingAt: settings.configPath) else { return }
        settings.configPath = path
        AppLog.info("config chosen")
        settingsChanged(restart: true)
    }

    func quit() {
        status?.close()
        NSApp.terminate(nil)
    }

    /// Saves the settings window. Returns an error sentence instead when something is not usable.
    private func apply(_ draft: SettingsDraft) -> String? {
        guard let port = draft.port else { return S.badPort }
        let python = draft.pythonPath.trimmingCharacters(in: .whitespaces)
        guard FileManager.default.isExecutableFile(atPath: python) else { return S.badPython }
        let config = draft.configPath.isEmpty ? nil : draft.configPath

        let restart = config != settings.configPath || python != settings.pythonPath || draft.lan != settings.lan || port != settings.port
        let intervalChanged = draft.collectHours != settings.collectEveryHours
        settings.configPath = config
        settings.pythonPath = python
        settings.lan = draft.lan
        settings.port = port
        settings.collectEveryHours = draft.collectHours
        settings.autoUpdateCheck = draft.autoUpdate
        settings.sittingReminders = draft.sitting
        if draft.openAtLogin != LoginItem.isEnabled {
            do {
                try LoginItem.setEnabled(draft.openAtLogin)
            } catch {
                return S.loginItemFailed + ": " + error.localizedDescription
            }
        }
        if intervalChanged {
            scheduler.intervalChanged()
            model.collectEveryHours = settings.collectEveryHours
            model.nextCollect = scheduler.nextCollect
        }
        AppLog.info("settings saved")
        settingsChanged(restart: restart)
        return nil
    }

    private func settingsChanged(restart: Bool) {
        checkSetup()
        if restart { restartServer() }
        refreshStatus()
    }

    // MARK: plumbing

    /// SIGTERM or SIGINT (a logout, `kill`, Ctrl-C in a terminal) still stops the server before the app goes.
    private func installSignalHandlers() {
        let queue = DispatchQueue(label: "healthaio.signals")
        for sig in [SIGTERM, SIGINT, SIGHUP] {
            signal(sig, SIG_IGN)
            let source = DispatchSource.makeSignalSource(signal: sig, queue: queue)
            source.setEventHandler { [weak self] in
                // while an alert is open the main run loop turns in its modal mode, where the main queue waits;
                // asking for that mode too means a `kill` still quits with an update alert on screen
                RunLoop.main.perform(inModes: [.common, .modalPanel]) {
                    self?.shutdown()
                    exit(0)
                }
                CFRunLoopWakeUp(CFRunLoopGetMain())
            }
            source.resume()
            signalSources.append(source)
        }
    }

    /// The app has no visible menu bar, but text fields still need Copy and Paste and windows need ⌘W.
    private func installMainMenu() {
        let main = NSMenu()
        let appItem = NSMenuItem()
        let appMenu = NSMenu()
        appMenu.addItem(withTitle: S.quitApp, action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
        appItem.submenu = appMenu
        main.addItem(appItem)

        let editItem = NSMenuItem()
        let edit = NSMenu(title: "Edit")
        edit.addItem(withTitle: "Undo", action: Selector(("undo:")), keyEquivalent: "z")
        edit.addItem(withTitle: "Redo", action: Selector(("redo:")), keyEquivalent: "Z")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Cut", action: #selector(NSText.cut(_:)), keyEquivalent: "x")
        edit.addItem(withTitle: "Copy", action: #selector(NSText.copy(_:)), keyEquivalent: "c")
        edit.addItem(withTitle: "Paste", action: #selector(NSText.paste(_:)), keyEquivalent: "v")
        edit.addItem(withTitle: "Select All", action: #selector(NSText.selectAll(_:)), keyEquivalent: "a")
        edit.addItem(.separator())
        edit.addItem(withTitle: "Close", action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
        editItem.submenu = edit
        main.addItem(editItem)
        NSApp.mainMenu = main
    }
}
