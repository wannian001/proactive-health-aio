import AppKit
import CoreGraphics
import UserNotifications

/// Long stretches at the computer, seen from the keyboard and mouse. Screen Time reaches the dashboard only every few
/// hours, so "right now" comes from here: BREAK seconds without either is a break. The tracker tells the server when a
/// stretch starts, every HEARTBEAT seconds while it goes on (the server trusts its word for 3 minutes), and when a break
/// starts (`healthaio sitting --since …` / `--off --since …`, modules/sitting.py). The server answers with the
/// reminder; once per reminder (a stretch's start and its round) it becomes a notification with one short move.
/// A break after a long stretch is written down as a rest by the server itself.
struct SittingTracker {
    static let breakSeconds: TimeInterval = 300
    static let heartbeat: TimeInterval = 120

    enum Event: Equatable {
        case started(Date)   // a stretch began at this time (the first input after a break)
        case going(Date)     // still at it, since this time
        case stopped(Date)   // a break began at this time (the last input)
    }

    private(set) var since: Date?
    private var lastSent: Date?

    /// `idle`: seconds since the last keyboard or mouse event, at `now`. What to tell the server, if anything.
    mutating func step(now: Date, idle: TimeInterval) -> Event? {
        if idle >= Self.breakSeconds {
            guard since != nil else { return nil }
            since = nil
            lastSent = now
            return .stopped(now.addingTimeInterval(-idle))
        }
        guard let start = since else {
            let start = now.addingTimeInterval(-idle)
            since = start
            lastSent = now
            return .started(start)
        }
        if let last = lastSent, now.timeIntervalSince(last) >= Self.heartbeat {
            lastSent = now
            return .going(start)
        }
        return nil
    }
}

final class SittingWatch: NSObject, UNUserNotificationCenterDelegate {
    var openDashboard: ((String) -> Void)?
    private var tracker = SittingTracker()
    private var inFlight = false
    private var shown: String?
    private var asked = false

    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        f.timeZone = .current
        return f
    }()

    /// Called every scheduler tick (10 seconds).
    func tick() {
        guard AppSettings.shared.configPath != nil, !inFlight else { return }
        let idle = CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: CGEventType(rawValue: UInt32.max)!)
        guard let event = tracker.step(now: Date(), idle: idle) else { return }
        let args: [String]
        switch event {
        case .started(let at), .going(let at): args = ["sitting", "--since", Self.iso.string(from: at)]
        case .stopped(let at): args = ["sitting", "--off", "--since", Self.iso.string(from: at)]
        }
        inFlight = true
        CLI.shared.run(args, timeout: Timeouts.short) { [weak self] result in
            guard let self else { return }
            self.inFlight = false
            if let nudge = result.json { self.remind(nudge) }
        }
    }

    private func remind(_ n: JSONObject) {
        guard AppSettings.shared.sittingReminders, n["kind"] as? String == "sitting",
              let since = n["since"] as? String, let round = n["round"] as? Int, let minutes = n["minutes"] as? Int else { return }
        let key = "\(since)#\(round)"
        guard key != shown else { return }
        shown = key
        let ids = n["routines"] as? [String] ?? []
        let info = n["info"] as? [String: JSONObject] ?? [:]
        func words(_ id: String) -> JSONObject? { info[id]?[Lang.chinese ? "zh" : "en"] as? JSONObject }
        let content = UNMutableNotificationContent()
        content.title = S.sittingTitle(minutes)
        if let first = ids.first, let w = words(first), let name = w["name"] as? String {
            let dose = w["dose"] as? String ?? ""
            let walk = ids.dropFirst().compactMap { words($0)?["name"] as? String }.first
            content.body = S.sittingBody(name, dose, walk)
        }
        content.userInfo = ["open": "#exercise/sitting"]
        let center = UNUserNotificationCenter.current()
        center.delegate = self
        let post = {
            center.add(UNNotificationRequest(identifier: "sitting-\(key)", content: content, trigger: nil)) { error in
                if let error { AppLog.info("sitting reminder not shown: \(error.localizedDescription)") }
            }
        }
        if asked { post(); return }
        center.requestAuthorization(options: [.alert, .sound]) { [weak self] granted, _ in
            DispatchQueue.main.async {
                self?.asked = true
                if granted { post() } else { AppLog.info("sitting reminders: notifications not allowed") }
            }
        }
    }

    // a click on the reminder opens the sitting card
    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        let place = response.notification.request.content.userInfo["open"] as? String ?? ""
        DispatchQueue.main.async { self.openDashboard?(place) }
        completionHandler()
    }

    // shown even while the app is the frontmost one (its popover is open)
    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([.banner, .sound])
    }
}
