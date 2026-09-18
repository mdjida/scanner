import Foundation

/// Tracks free-tier scan quotas on-device.
/// Free: 25 minutes auto-scan + 100 manual scans per calendar month.
public final class QuotaStore {
    public static let shared = QuotaStore()
    public static let suiteName = "group.com.livecompoverlay.shared"
    
    private let defaults: UserDefaults?
    
    private init() {
        defaults = UserDefaults(suiteName: QuotaStore.suiteName)
    }
    
    public var remainingAutoMinutesThisMonth: Int {
        reconcile()
        let used = defaults?.integer(forKey: Keys.autoMinutesUsed) ?? 0
        return max(0, 25 - used)
    }
    
    public var remainingManualScansThisMonth: Int {
        reconcile()
        let used = defaults?.integer(forKey: Keys.manualScansUsed) ?? 0
        return max(0, 100 - used)
    }
    
    public func consumeAutoMinute() {
        reconcile()
        let current = defaults?.integer(forKey: Keys.autoMinutesUsed) ?? 0
        defaults?.set(current + 1, forKey: Keys.autoMinutesUsed)
        defaults?.synchronize()
    }
    
    public func consumeManualScan() {
        reconcile()
        let current = defaults?.integer(forKey: Keys.manualScansUsed) ?? 0
        defaults?.set(current + 1, forKey: Keys.manualScansUsed)
        defaults?.synchronize()
    }
    
    public func resetMonthlyQuota() {
        defaults?.set(0, forKey: Keys.autoMinutesUsed)
        defaults?.set(0, forKey: Keys.manualScansUsed)
        defaults?.set(currentMonthKey, forKey: Keys.trackedMonth)
        defaults?.synchronize()
    }
    
    private func reconcile() {
        let tracked = defaults?.string(forKey: Keys.trackedMonth) ?? ""
        if tracked != currentMonthKey {
            resetMonthlyQuota()
        }
    }
    
    private var currentMonthKey: String {
        let comps = Calendar.current.dateComponents([.year, .month], from: Date())
        return "\(comps.year ?? 0)-\(comps.month ?? 0)"
    }
    
    private enum Keys {
        static let autoMinutesUsed = "quota_auto_minutes_used"
        static let manualScansUsed = "quota_manual_scans_used"
        static let trackedMonth = "quota_tracked_month"
    }
}
