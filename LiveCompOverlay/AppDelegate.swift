import UIKit

final class AppDelegate: NSObject, UIApplicationDelegate {
    func application(
        _ app: UIApplication,
        open url: URL,
        options: [UIApplication.OpenURLOptionsKey: Any] = [:]
    ) -> Bool {
        guard url.scheme == "livecompoverlay" else { return false }
        if url.host == "scan" {
            // Notify the active OverlayManager to request a manual scan.
            NotificationCenter.default.post(name: .requestManualScan, object: nil)
            return true
        }
        return false
    }
}

extension Notification.Name {
    static let requestManualScan = Notification.Name("requestManualScan")
}
