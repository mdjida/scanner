import Foundation

/// A lightweight, Codable result sent from the broadcast extension to the host app
/// whenever a card is detected on screen.
public struct OverlayResultPayload: Codable {
    public let externalId: String
    public let cardName: String
    public let setName: String
    public let setCode: String?
    public let localId: String?
    public let marketPrice: String?
    public let variant: String?
    public let lowPrice: String?
    public let midPrice: String?
    public let highPrice: String?
    public let directLowPrice: String?
    public let cardmarketPrice: String?
    public let priceSource: String?
    public let score: Double?
    public let timestamp: TimeInterval
    
    public init(
        externalId: String,
        cardName: String,
        setName: String,
        setCode: String? = nil,
        localId: String? = nil,
        marketPrice: String? = nil,
        variant: String? = nil,
        lowPrice: String? = nil,
        midPrice: String? = nil,
        highPrice: String? = nil,
        directLowPrice: String? = nil,
        cardmarketPrice: String? = nil,
        priceSource: String? = nil,
        score: Double? = nil,
        timestamp: TimeInterval = Date().timeIntervalSince1970
    ) {
        self.externalId = externalId
        self.cardName = cardName
        self.setName = setName
        self.setCode = setCode
        self.localId = localId
        self.marketPrice = marketPrice
        self.variant = variant
        self.lowPrice = lowPrice
        self.midPrice = midPrice
        self.highPrice = highPrice
        self.directLowPrice = directLowPrice
        self.cardmarketPrice = cardmarketPrice
        self.priceSource = priceSource
        self.score = score
        self.timestamp = timestamp
    }
}

extension OverlayResultPayload {
    /// Key used in app-group UserDefaults to store the latest result.
    public static let defaultsKey = "overlay_latest_result"
    
    /// Darwin notification name broadcast when a new result arrives.
    public static let notificationName = "com.livecompoverlay.newresult"
    
    public func encoded() -> Data? {
        try? JSONEncoder().encode(self)
    }
    
    public init?(data: Data) {
        guard let decoded = try? JSONDecoder().decode(Self.self, from: data) else { return nil }
        self = decoded
    }
}
