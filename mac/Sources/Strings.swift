import Foundation

/// The app speaks English or Simplified Chinese, chosen once from the Mac's first preferred language.
/// HEALTHAIO_LANG=en or zh overrides it (snapshots and tests).
enum Lang {
    static var chinese = Lang.fromEnvironment()

    static func fromEnvironment() -> Bool {
        if let forced = ProcessInfo.processInfo.environment["HEALTHAIO_LANG"], !forced.isEmpty {
            return forced.lowercased().hasPrefix("zh")
        }
        return Locale.preferredLanguages.first?.lowercased().hasPrefix("zh") ?? false
    }

    static var locale: Locale {
        chinese ? Locale(identifier: "zh_Hans_CN") : Locale(identifier: "en_" + (Locale.current.region?.identifier ?? "US"))
    }
}

func tr(_ en: String, _ zh: String) -> String { Lang.chinese ? zh : en }

/// Every sentence the app shows, in both languages.
enum S {
    // general
    static var ok: String { tr("OK", "好") }
    static var later: String { tr("Later", "以后再说") }
    static var cancel: String { tr("Cancel", "取消") }
    static var save: String { tr("Save", "保存") }
    static var choose: String { tr("Choose…", "选择…") }
    static var done: String { tr("Done", "完成") }
    static var settings: String { tr("Settings…", "设置…") }
    static var quit: String { tr("Quit", "退出") }
    static var quitApp: String { tr("Quit Health AIO", "退出 Health AIO") }
    static var showLogs: String { tr("Show logs", "查看日志") }

    // setup
    static var noConfig: String { tr("Choose your healthaio.toml to start.", "先选择你的 healthaio.toml。") }
    static func configMissing(_ path: String) -> String { tr("The config file is not there: \(path)", "找不到配置文件：\(path)") }
    static func noPython(_ path: String) -> String { tr("No Python at \(path). Choose one in Settings.", "\(path) 没有 Python，请在设置里选择。") }
    static func noExecutable(_ name: String) -> String { tr("Can't find \(name) (HEALTHAIO_CLI).", "找不到 \(name)（HEALTHAIO_CLI）。") }
    static var chooseConfig: String { tr("Choose healthaio.toml…", "选择 healthaio.toml…") }

    // dashboard
    static var dashboard: String { tr("Dashboard", "面板") }
    static var running: String { tr("Running", "正在运行") }
    static var runningElsewhere: String { tr("Running, started outside this app", "正在运行（不是这个应用启动的）") }
    static var starting: String { tr("Starting…", "正在启动…") }
    static var stopped: String { tr("Stopped", "已停止") }
    static func retrying(_ seconds: Int) -> String { tr("Stopped unexpectedly · trying again in \(seconds) s", "意外停止 · \(seconds) 秒后重试") }
    static var phonesCanConnect: String { tr("phones can connect", "手机可以连接") }
    static var thisMacOnly: String { tr("this Mac only", "只有这台 Mac") }
    static var openDashboard: String { tr("Open dashboard", "打开面板") }

    // screen time
    static var screenTime: String { tr("Screen Time collection", "屏幕使用时间采集") }
    static var collectNow: String { tr("Collect now", "立即采集") }
    static var collecting: String { tr("Collecting…", "正在采集…") }
    static var notCollectedYet: String { tr("Not collected yet", "还没有采集过") }
    static func lastRun(_ when: String) -> String { tr("Last run \(when)", "上次运行：\(when)") }
    static var allRead: String { tr("all read", "全部读到") }
    static var someFailed: String { tr("a source failed", "有来源失败") }
    static func nextRun(_ when: String, every hours: Int) -> String {
        tr("Next \(when) · every \(hours) h", "下次 \(when) · 每 \(hours) 小时")
    }
    static var fdaOn: String { tr("Full Disk Access is on", "完全磁盘访问权限已开启") }
    static var fdaOff: String { tr("Full Disk Access is off, so Screen Time can't be read.", "没有完全磁盘访问权限，读不到屏幕使用时间。") }
    static var fdaHow: String { tr("In the list, add “Health AIO” and switch it on.", "在列表里添加“Health AIO”并打开开关。") }
    static var fdaUnknown: String { tr("No Screen Time records on this Mac yet.", "这台 Mac 上还没有屏幕使用时间记录。") }
    static var openPrivacy: String { tr("Open Privacy settings", "打开隐私设置") }
    static func sourceName(_ raw: String) -> String {
        switch raw {
        case "macos-screentime": return tr("Screen Time", "屏幕使用时间")
        default: return raw
        }
    }

    // iPhone
    static var iphone: String { "iPhone" }
    static var noPhone: String { tr("No phone paired yet.", "还没有配对手机。") }
    static func lastSeen(_ when: String) -> String { tr("last seen \(when)", "最近连接 \(when)") }
    static var notSeenYet: String { tr("not connected yet", "还没连接过") }
    static func signatureLeft(_ remaining: String) -> String { tr("Signature runs out \(remaining)", "签名\(remaining)到期") }
    static var signatureGone: String { tr("Signature ran out: renew to open the app again", "签名已过期：续签后才能再打开") }
    static var notInstalledHere: String { tr("Not installed from this Mac yet", "还没有从这台 Mac 安装过") }
    static var renew: String { tr("Renew iPhone app", "续签 iPhone 应用") }
    static var renewing: String { tr("Renewing… this takes a few minutes", "正在续签… 需要几分钟") }
    static var pair: String { tr("Pair iPhone…", "配对 iPhone…") }
    static func renewReason(_ reason: String?) -> String? {
        switch reason {
        case nil: return nil
        case "no_xcode": return tr("Renewing needs Xcode (the full app, not only the Command Line Tools).", "续签需要完整的 Xcode（不只是命令行工具）。")
        case "no_project": return tr("This copy of Health AIO has no iPhone project (ios/).", "这份 Health AIO 里没有 iPhone 工程（ios/）。")
        case "no_team": return tr("Put your Apple ID team in ios/Local.xcconfig first.", "先在 ios/Local.xcconfig 里填好你的 Apple ID 团队。")
        case "not_macos": return tr("Renewing works only on a Mac.", "只有 Mac 才能续签。")
        case let other?: return other
        }
    }

    // updates
    static var updates: String { tr("Updates", "更新") }
    static func version(_ v: String) -> String { tr("Version \(v)", "版本 \(v)") }
    static func available(_ v: String) -> String { tr("\(v) available", "\(v) 可以更新") }
    static func skipped(_ v: String) -> String { tr("\(v) available (skipped)", "\(v) 可以更新（已跳过）") }
    static func upToDate(_ when: String?) -> String {
        guard let when else { return tr("Up to date", "已是最新") }
        return tr("Up to date · checked \(when)", "已是最新 · \(when)检查")
    }
    static var checkForUpdates: String { tr("Check for updates", "检查更新") }
    static var checking: String { tr("Checking…", "正在检查…") }
    static var updateButton: String { tr("Update…", "更新…") }
    static var updatingNow: String { tr("Updating…", "正在更新…") }
    static func updateTitle(_ v: String) -> String { tr("Health AIO \(v) is available", "Health AIO \(v) 可以更新了") }
    static func youHave(_ v: String) -> String { tr("You have \(v).", "你现在用的是 \(v)。") }
    static var update: String { tr("Update", "更新") }
    static var skipThisVersion: String { tr("Skip this version", "跳过这个版本") }
    static var openReleasePage: String { tr("Open release page", "打开发布页面") }
    static func cannotUpdateHere(_ reason: String) -> String { tr("It can't be updated from here: \(reason)", "这里没法直接更新：\(reason)") }
    static var upToDateTitle: String { tr("Health AIO is up to date", "Health AIO 已是最新版本") }
    static func upToDateText(_ v: String) -> String { tr("You have \(v), the latest version.", "你用的 \(v) 就是最新版本。") }
    static var checkFailedTitle: String { tr("Couldn't check for updates", "没能检查更新") }
    static var updatingTitle: String { tr("Updating Health AIO…", "正在更新 Health AIO…") }
    static var updatingText: String { tr("This can take a few minutes. The dashboard restarts when it is done.", "可能需要几分钟。完成后面板会重新启动。") }
    static func updatedTitle(_ v: String) -> String { tr("Health AIO is updated to \(v)", "Health AIO 已更新到 \(v)") }
    static var updateFailedTitle: String { tr("The update didn't finish", "更新没有完成") }
    static var dashboardRestarted: String { tr("The dashboard has restarted.", "面板已重新启动。") }
    static var macAppChanged: String {
        tr("The Mac app itself changed too. To use the new one: quit Health AIO, run mac/build.sh in the repository, open mac/build/Health AIO.app, then switch Full Disk Access on again for “Health AIO” (each build has a new signature, so macOS asks again).",
           "Mac 应用本身也有改动。要用新版：退出 Health AIO，在仓库里运行 mac/build.sh，打开 mac/build/Health AIO.app，再给“Health AIO”重新打开完全磁盘访问权限（每次构建的签名都不同，macOS 会重新询问）。")
    }
    static var iosAppChanged: String {
        tr("The iPhone app has a new version too: Renew iPhone app installs it.", "iPhone 应用也有新版本：点“续签 iPhone 应用”就会装上。")
    }
    static var showBuildScript: String { tr("Show build.sh", "显示 build.sh") }
    static var waitForRenew: String { tr("Wait until the iPhone app is renewed, then update.", "等 iPhone 应用续签完再更新。") }
    static var waitForUpdate: String { tr("Wait until the update has finished, then renew.", "等更新完成后再续签。") }

    // iPhone alerts
    static func signatureAlertTitle(_ remaining: String) -> String { tr("The iPhone app's signature runs out \(remaining)", "iPhone 应用的签名\(remaining)到期") }
    static var signatureExpiredTitle: String { tr("The iPhone app's signature has run out", "iPhone 应用的签名已经过期") }
    static var signatureAlertText: String {
        tr("Renew it so the app keeps opening. The iPhone needs to be on a cable or the same Wi-Fi, and this Mac logged in at the desktop.",
           "续签之后应用才能继续打开。iPhone 需要连着数据线或在同一个 Wi-Fi 下，这台 Mac 需要登录在桌面。")
    }
    static var renewNow: String { tr("Renew now", "立即续签") }
    static var renewedTitle: String { tr("The iPhone app is renewed", "iPhone 应用已续签") }
    static func renewedText(_ day: String) -> String { tr("Its signature now runs out on \(day).", "新签名在 \(day) 到期。") }
    static var renewFailedTitle: String { tr("Renewing didn't work", "续签没有成功") }
    static var cannotRenewTitle: String { tr("This Mac can't renew the iPhone app yet", "这台 Mac 暂时不能续签 iPhone 应用") }

    // pairing
    static var pairTitle: String { tr("Pair iPhone", "配对 iPhone") }
    static var pairHeading: String { tr("Pair your iPhone", "配对你的 iPhone") }
    static var code: String { tr("Code", "配对码") }
    static func codeWorks(_ left: String) -> String { tr("Works for \(left) more", "还能用 \(left)") }
    static var codeExpired: String { tr("This code has run out.", "这个配对码已经失效。") }
    static var newCode: String { tr("New code", "换一个") }
    static var addresses: String { tr("Addresses", "地址") }
    static var pairHint: String {
        tr("On the iPhone, scan this with the camera, or open Health AIO and type the code. The phone must be on the same Wi-Fi as this Mac, or on Tailscale.",
           "在 iPhone 上用相机扫这个码，或者打开 Health AIO 输入配对码。手机需要和这台 Mac 在同一个 Wi-Fi 下，或者都在 Tailscale 上。")
    }
    static var pairNeedsLAN: String {
        tr("Phones can't reach the dashboard yet: it only answers this Mac.", "手机还连不上面板：它现在只回应这台 Mac。")
    }
    static var pairServerDown: String { tr("The dashboard is not running, so the phone has nothing to reach.", "面板没有在运行，手机连不上。") }
    static var letPhoneConnect: String { tr("Let my phone connect", "允许手机连接") }
    static func paired(_ name: String) -> String { tr("Paired with \(name).", "已和 \(name) 配对。") }
    static var gettingCode: String { tr("Getting a code…", "正在获取配对码…") }

    // settings
    static var settingsTitle: String { tr("Health AIO Settings", "Health AIO 设置") }
    static var configFile: String { tr("Config file", "配置文件") }
    static var python: String { "Python" }
    static func pythonDefault(_ path: String) -> String { tr("Default: \(path)", "默认：\(path)") }
    static var port: String { tr("Port", "端口") }
    static var lanToggle: String { tr("Let my phone connect (local network)", "允许手机连接（本地网络）") }
    static var lanHelp: String {
        tr("After pairing, devices on your Wi-Fi or Tailscale can reach the dashboard; everything else is refused.",
           "配对后，同一 Wi-Fi 或 Tailscale 里的设备可以访问面板；其他来源一律拒绝。")
    }
    static var collectEvery: String { tr("Collect every", "采集间隔") }
    static func hours(_ n: Int) -> String { tr(n == 1 ? "1 hour" : "\(n) hours", "\(n) 小时") }
    static var openAtLogin: String { tr("Open at login", "登录时打开") }
    static var autoUpdate: String { tr("Check for updates automatically", "自动检查更新") }
    static var sittingToggle: String { tr("Remind me after 50 minutes at the computer", "在电脑前连续坐满 50 分钟时提醒我") }
    static func sittingTitle(_ minutes: Int) -> String {
        let h = minutes / 60, m = minutes % 60
        let d = h > 0 ? tr("\(h) h \(m) min", "\(h) 小时 \(m) 分") : tr("\(m) min", "\(m) 分钟")
        return tr("At the computer for \(d)", "已经连续坐了 \(d)")
    }
    static func sittingBody(_ move: String, _ dose: String, _ walk: String?) -> String {
        let first = dose.isEmpty ? move : tr("\(move) (\(dose))", "\(move)（\(dose)）")
        guard let walk else { return tr("Get up for two minutes: \(first)", "起来动两分钟：\(first)") }
        return tr("Get up for two minutes: \(first), or \(walk.lowercased())", "起来动两分钟：\(first)，或者\(walk)")
    }
    static var repository: String { tr("Repository", "仓库") }
    static var notFound: String { tr("not found", "未找到") }
    static var badPort: String { tr("The port must be a number from 1024 to 65535.", "端口必须是 1024 到 65535 之间的数字。") }
    static var badPython: String { tr("That Python path is not a program.", "这个 Python 路径不是可执行程序。") }
    static var loginItemFailed: String { tr("Couldn't change Open at login", "没能修改“登录时打开”") }

    // running healthaio
    static var timedOut: String { tr("healthaio took too long and was stopped.", "healthaio 运行太久，已被停止。") }
    static func noAnswer(_ code: Int32) -> String { tr("healthaio gave no answer (exit \(code)).", "healthaio 没有给出结果（退出码 \(code)）。") }
    static func cannotStart(_ error: String) -> String { tr("Couldn't start healthaio: \(error)", "没能启动 healthaio：\(error)") }
    static var statusFailed: String { tr("Couldn't read the status:", "读不到状态：") }

    // quitting
    static var quitWhileBusyTitle: String { tr("A job is still running", "还有任务在运行") }
    static var quitWhileBusyText: String { tr("Quitting now stops it halfway.", "现在退出会让它中途停下。") }
    static var quitAnyway: String { tr("Quit anyway", "仍然退出") }
    static var wait: String { tr("Wait", "等一等") }
}

/// Times as people say them: "today 21:00", "20 min ago", "in 2 days".
enum TimeText {
    /// Snapshots pin this so the pictures do not depend on where they are made.
    static var timeZone = TimeZone.current

    private static var calendar: Calendar {
        var c = Calendar(identifier: .gregorian)
        c.timeZone = timeZone
        c.locale = Lang.locale
        return c
    }

    private static func format(_ date: Date, template: String) -> String {
        let f = DateFormatter()
        f.locale = Lang.locale
        f.timeZone = timeZone
        f.setLocalizedDateFormatFromTemplate(template)
        return f.string(from: date)
    }

    static func clock(_ date: Date) -> String {
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US_POSIX")
        f.timeZone = timeZone
        f.dateFormat = "HH:mm"
        return f.string(from: date)
    }

    static func day(_ date: Date) -> String { format(date, template: Lang.chinese ? "MMMdEEE" : "EEEdMMM") }

    /// "today 21:00", "yesterday 21:00", "tomorrow 09:00", else "Sun 11 Oct 21:00".
    static func moment(_ date: Date, now: Date) -> String {
        let cal = calendar
        let time = clock(date)
        if cal.isDate(date, inSameDayAs: now) { return tr("today \(time)", "今天 \(time)") }
        if let y = cal.date(byAdding: .day, value: -1, to: now), cal.isDate(date, inSameDayAs: y) {
            return tr("yesterday \(time)", "昨天 \(time)")
        }
        if let t = cal.date(byAdding: .day, value: 1, to: now), cal.isDate(date, inSameDayAs: t) {
            return tr("tomorrow \(time)", "明天 \(time)")
        }
        return "\(day(date)) \(time)"
    }

    static func ago(_ date: Date, now: Date) -> String {
        let s = max(0, now.timeIntervalSince(date))
        if s < 90 { return tr("just now", "刚刚") }
        if s < 3600 { let m = Int(s / 60); return tr("\(m) min ago", "\(m) 分钟前") }
        if s < 86400 { let h = Int(s / 3600); return tr("\(h) h ago", "\(h) 小时前") }
        let d = Int(s / 86400)
        return tr(d == 1 ? "1 day ago" : "\(d) days ago", "\(d) 天前")
    }

    /// For "Signature runs out …": "in 2 days" / "还有 2 天".
    static func remaining(_ date: Date, now: Date) -> String {
        let s = date.timeIntervalSince(now)
        if s < 3600 { return tr("within the hour", "一小时内") }
        if s < 86400 { let h = Int(s / 3600); return tr(h == 1 ? "in 1 hour" : "in \(h) hours", "还有 \(h) 小时") }
        let d = Int(s / 86400)
        return tr(d == 1 ? "in 1 day" : "in \(d) days", "还有 \(d) 天")
    }

    /// For "Next …": "in 1 h 20 min" / "1 小时 20 分钟后".
    static func until(_ date: Date, now: Date) -> String {
        let s = max(0, date.timeIntervalSince(now))
        if s < 60 { return tr("in a moment", "马上") }
        let h = Int(s / 3600), m = Int(s.truncatingRemainder(dividingBy: 3600) / 60)
        if h == 0 { return tr("in \(m) min", "\(m) 分钟后") }
        if m == 0 { return tr("in \(h) h", "\(h) 小时后") }
        return tr("in \(h) h \(m) min", "\(h) 小时 \(m) 分钟后")
    }

    static func countdown(_ seconds: Int) -> String {
        let s = max(0, seconds)
        return String(format: "%d:%02d", s / 60, s % 60)
    }
}
