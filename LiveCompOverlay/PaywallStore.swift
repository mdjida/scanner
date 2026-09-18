import Foundation

/// Tracks subscription status.
/// Currently stubs all users as free-tier; replace with StoreKit / RevenueCat later.
final class PaywallStore {
    static let shared = PaywallStore()
    
    var isSubscribed: Bool {
        // TODO: integrate StoreKit / RevenueCat.
        false
    }
    
    private init() {}
}
