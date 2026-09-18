import Foundation

/// Cross-process notification helper using CFNotificationCenter.
/// Used by the broadcast extension to wake the host app when a new card is detected.
public final class DarwinNotifier {
    public static let shared = DarwinNotifier()
    
    private let center = CFNotificationCenterGetDarwinNotifyCenter()
    
    private init() {}
    
    public func post(name: String) {
        let notificationName = CFNotificationName(name as CFString)
        CFNotificationCenterPostNotification(center, notificationName, nil, nil, true)
    }
    
    public func observe(name: String, queue: DispatchQueue = .main, callback: @escaping () -> Void) -> Any {
        let observer = UnsafeRawPointer(Unmanaged.passUnretained(self as AnyObject).toOpaque())
        let notificationName = CFNotificationName(name as CFString)
        
        CFNotificationCenterAddObserver(
            center,
            observer,
            { _, _, _, _, _ in callback() },
            notificationName.rawValue,
            nil,
            .deliverImmediately
        )
        return observer
    }
    
    public func removeObserver(_ observer: Any, name: String) {
        guard let pointer = observer as? UnsafeRawPointer else { return }
        let notificationName = CFNotificationName(name as CFString)
        CFNotificationCenterRemoveObserver(center, pointer, notificationName, nil)
    }
}
