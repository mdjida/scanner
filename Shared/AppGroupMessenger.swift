import Foundation

/// Lightweight app-group message bus for the broadcast extension to notify the host app.
public final class AppGroupMessenger {
    public static let shared = AppGroupMessenger()
    public static let suiteName = "group.com.livecompoverlay.shared"
    public static let scanRequestKey = "scan_request_timestamp"
    public static let autoScanEnabledKey = "auto_scan_enabled"
    
    private let defaults: UserDefaults?
    
    private init() {
        defaults = UserDefaults(suiteName: AppGroupMessenger.suiteName)
    }
    
    public func requestScan() {
        defaults?.set(Date().timeIntervalSince1970, forKey: AppGroupMessenger.scanRequestKey)
        defaults?.synchronize()
    }
    
    public var lastScanRequest: TimeInterval {
        defaults?.double(forKey: AppGroupMessenger.scanRequestKey) ?? 0
    }
    
    public var autoScanEnabled: Bool {
        get { defaults?.bool(forKey: AppGroupMessenger.autoScanEnabledKey) ?? false }
        set {
            defaults?.set(newValue, forKey: AppGroupMessenger.autoScanEnabledKey)
            defaults?.synchronize()
        }
    }
    
    /// Stores a detection result from the broadcast extension and posts a Darwin notification
    /// so the host app can pick it up immediately.
    public func publishResult(_ result: OverlayResultPayload) {
        if let data = result.encoded() {
            defaults?.set(data, forKey: OverlayResultPayload.defaultsKey)
            defaults?.synchronize()
        }
        DarwinNotifier.shared.post(name: OverlayResultPayload.notificationName)
    }
    
    /// Stores the full ranked candidate list from the backend identify call.
    public func publishCandidates(_ candidates: IdentifyCandidates) {
        if let data = candidates.encoded() {
            defaults?.set(data, forKey: IdentifyCandidates.defaultsKey)
            defaults?.synchronize()
        }
    }
    
    public var latestResult: OverlayResultPayload? {
        guard let data = defaults?.data(forKey: OverlayResultPayload.defaultsKey) else { return nil }
        return OverlayResultPayload(data: data)
    }
    
    public var latestCandidates: IdentifyCandidates? {
        guard let data = defaults?.data(forKey: IdentifyCandidates.defaultsKey) else { return nil }
        return IdentifyCandidates(data: data)
    }
}
