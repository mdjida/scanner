import Foundation
import Shared

/// Lets the Live Activity widget extension signal a manual scan back to the host app.
final class LiveActivityBridge {
    static let shared = LiveActivityBridge()
    private let messenger = AppGroupMessenger.shared
    
    private init() {}
    
    func requestManualScan() {
        messenger.requestScan()
    }
}
