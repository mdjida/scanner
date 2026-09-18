import ActivityKit
import Foundation

public struct OverlayActivityAttributes: ActivityAttributes {
    public typealias ContentState = OverlayActivityState
    
    public struct OverlayActivityState: Codable, Hashable {
        public let cardName: String?
        public let cardSet: String?
        public let marketPrice: String?
        public let variant: String?
        public let lowPrice: String?
        public let midPrice: String?
        public let highPrice: String?
        public let isDetecting: Bool
        public let scanMode: ScanMode
        public let remainingAutoMinutes: Int
        public let remainingManualScans: Int

        public init(
            cardName: String? = nil,
            cardSet: String? = nil,
            marketPrice: String? = nil,
            variant: String? = nil,
            lowPrice: String? = nil,
            midPrice: String? = nil,
            highPrice: String? = nil,
            isDetecting: Bool = false,
            scanMode: ScanMode = .manual,
            remainingAutoMinutes: Int = 25,
            remainingManualScans: Int = 100
        ) {
            self.cardName = cardName
            self.cardSet = cardSet
            self.marketPrice = marketPrice
            self.variant = variant
            self.lowPrice = lowPrice
            self.midPrice = midPrice
            self.highPrice = highPrice
            self.isDetecting = isDetecting
            self.scanMode = scanMode
            self.remainingAutoMinutes = remainingAutoMinutes
            self.remainingManualScans = remainingManualScans
        }
    }
    
    public enum ScanMode: String, Codable, Hashable, CaseIterable {
        case manual
        case auto
    }
    
    public init() {}
}
