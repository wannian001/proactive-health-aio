import Foundation

/// The app's own preferences (UserDefaults of io.github.wannian001.healthaio.mac). Launch arguments such as
/// `-configPath /path/healthaio.toml` override them without writing anything, which the tests use.
final class AppSettings: @unchecked Sendable {
    static let shared = AppSettings()

    private let defaults = UserDefaults.standard

    private enum Key {
        static let config = "configPath"
        static let python = "pythonPath"
        static let lan = "lan"
        static let port = "port"
        static let collectHours = "collectEveryHours"
        static let autoUpdate = "autoUpdateCheck"
        static let sitting = "sittingReminders"
        static let skipped = "skippedVersion"
        static let signatureAlertDay = "signatureAlertDay"
    }

    static let defaultPort = 8790
    static let defaultCollectHours = 2

    var configPath: String? {
        get { nonEmpty(defaults.string(forKey: Key.config)) }
        set { store(nonEmpty(newValue), Key.config) }
    }

    var pythonPath: String {
        get { nonEmpty(defaults.string(forKey: Key.python)) ?? Self.defaultPython }
        set { store(newValue == Self.defaultPython ? nil : nonEmpty(newValue), Key.python) }
    }

    /// `serve --lan`: answer phones on the local network and Tailscale, not only this Mac.
    var lan: Bool {
        get { defaults.bool(forKey: Key.lan) }
        set { defaults.set(newValue, forKey: Key.lan) }
    }

    var port: Int {
        get {
            let value = defaults.integer(forKey: Key.port)
            return (1024...65535).contains(value) ? value : Self.defaultPort
        }
        set { store(newValue == Self.defaultPort ? nil : newValue, Key.port) }
    }

    var collectEveryHours: Int {
        get {
            let value = defaults.integer(forKey: Key.collectHours)
            return value == 0 ? Self.defaultCollectHours : min(24, max(1, value))
        }
        set { store(newValue == Self.defaultCollectHours ? nil : newValue, Key.collectHours) }
    }

    /// A notification after 50 minutes at the computer (SittingWatch); on unless switched off.
    var sittingReminders: Bool {
        get { defaults.object(forKey: Key.sitting) == nil ? true : defaults.bool(forKey: Key.sitting) }
        set { defaults.set(newValue, forKey: Key.sitting) }
    }

    var autoUpdateCheck: Bool {
        get { defaults.object(forKey: Key.autoUpdate) == nil ? true : defaults.bool(forKey: Key.autoUpdate) }
        set { store(newValue ? nil : false, Key.autoUpdate) }
    }

    var skippedVersion: String? {
        get { nonEmpty(defaults.string(forKey: Key.skipped)) }
        set { store(nonEmpty(newValue), Key.skipped) }
    }

    /// The day (yyyy-MM-dd) the signature reminder was last shown, so it comes at most once a day.
    var signatureAlertDay: String? {
        get { defaults.string(forKey: Key.signatureAlertDay) }
        set { store(newValue, Key.signatureAlertDay) }
    }

    /// The Python recorded by mac/build.sh, else the one macOS ships.
    static var defaultPython: String {
        if let recorded = Bundle.main.object(forInfoDictionaryKey: "HealthAIOPython") as? String,
           FileManager.default.isExecutableFile(atPath: recorded) {
            return recorded
        }
        return "/usr/bin/python3"
    }

    /// The repository the app was built from (it becomes PYTHONPATH). Recorded by mac/build.sh; if the folder has
    /// moved since, the app looks for it above its own bundle (mac/build/Health AIO.app sits inside it).
    static var repoPath: String? {
        let fm = FileManager.default
        func isRepo(_ url: URL) -> Bool {
            fm.fileExists(atPath: url.appendingPathComponent("healthaio/__main__.py").path)
        }
        if let recorded = Bundle.main.object(forInfoDictionaryKey: "HealthAIORepo") as? String,
           isRepo(URL(fileURLWithPath: recorded)) {
            return recorded
        }
        var url = Bundle.main.bundleURL
        for _ in 0..<4 {
            url = url.deletingLastPathComponent()
            if isRepo(url) { return url.path }
        }
        return nil
    }

    private func store(_ value: Any?, _ key: String) {
        if let value { defaults.set(value, forKey: key) } else { defaults.removeObject(forKey: key) }
    }

    private func nonEmpty(_ s: String?) -> String? {
        guard let s, !s.trimmingCharacters(in: .whitespaces).isEmpty else { return nil }
        return s
    }
}
