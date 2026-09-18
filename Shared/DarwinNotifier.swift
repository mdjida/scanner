import Foundation

/// Cross-process notification helper using CFNotificationCenter.
/// Used by the broadcast extension to wake the host app when a new card is detected.
public final class DarwinNotifier {
    public static let shared = DarwinNotifier()

    private let center = CFNotificationCenterGetDarwinNotifyCenter()
    private var observers: [String: ObserverBox] = [:]

    private init() {}

    public func post(name: String) {
        let notificationName = CFNotificationName(name as CFString)
        CFNotificationCenterPostNotification(center, notificationName, nil, nil, true)
    }

    public func observe(name: String, queue: DispatchQueue = .main, callback: @escaping () -> Void) -> Any {
        let box = ObserverBox(callback: callback, queue: queue)
        let raw = Unmanaged.passUnretained(box).toOpaque()
        observers[name] = box

        CFNotificationCenterAddObserver(
            center,
            raw,
            DarwinNotifier.callback,
            CFNotificationName(name as CFString).rawValue,
            nil,
            .deliverImmediately
        )
        return raw
    }

    public func removeObserver(_ observer: Any, name: String) {
        guard let raw = observer as? UnsafeMutableRawPointer else { return }
        let notificationName = CFNotificationName(name as CFString)
        CFNotificationCenterRemoveObserver(center, raw, notificationName, nil)
        observers.removeValue(forKey: name)
    }

    private static let callback: CFNotificationCallback = { _, observer, _, _, _ in
        guard let raw = observer else { return }
        let box = Unmanaged<ObserverBox>.fromOpaque(raw).takeUnretainedValue()
        box.queue.async { box.callback() }
    }
}

private final class ObserverBox {
    let callback: () -> Void
    let queue: DispatchQueue

    init(callback: @escaping () -> Void, queue: DispatchQueue) {
        self.callback = callback
        self.queue = queue
    }
}
