import Foundation

/// A catalog card record used for both lookup and display.
public struct CatalogCard: Codable {
    public let externalId: String
    public let cardName: String
    public let setName: String
    public let setCode: String?
    public let localId: String?
    public let setYear: String?
    public let variant: String?
    public let imageUrl: String?
    public let marketPrice: Double?
    public let lowPrice: Double?
    public let midPrice: Double?
    public let highPrice: Double?
    public let directLowPrice: Double?
    public let cardmarketPrice: Double?
    public let embedding: [Float]?
    public let priceSource: String?
    public let priceUpdatedAt: Date?

    public init(
        externalId: String,
        cardName: String,
        setName: String,
        setCode: String? = nil,
        localId: String? = nil,
        setYear: String? = nil,
        variant: String? = nil,
        imageUrl: String? = nil,
        marketPrice: Double? = nil,
        lowPrice: Double? = nil,
        midPrice: Double? = nil,
        highPrice: Double? = nil,
        directLowPrice: Double? = nil,
        cardmarketPrice: Double? = nil,
        embedding: [Float]? = nil,
        priceSource: String? = nil,
        priceUpdatedAt: Date? = nil
    ) {
        self.externalId = externalId
        self.cardName = cardName
        self.setName = setName
        self.setCode = setCode
        self.localId = localId
        self.setYear = setYear
        self.variant = variant
        self.imageUrl = imageUrl
        self.marketPrice = marketPrice
        self.lowPrice = lowPrice
        self.midPrice = midPrice
        self.highPrice = highPrice
        self.directLowPrice = directLowPrice
        self.cardmarketPrice = cardmarketPrice
        self.embedding = embedding
        self.priceSource = priceSource
        self.priceUpdatedAt = priceUpdatedAt
    }
}

public struct CatalogMatch {
    public let externalId: String
    public let cardName: String
    public let setName: String
    public let setCode: String?
    public let localId: String?
    public let setYear: String?
    public let variant: String?
    public let marketPrice: Double?
    public let lowPrice: Double?
    public let midPrice: Double?
    public let highPrice: Double?
    public let directLowPrice: Double?
    public let cardmarketPrice: Double?
    public let distance: Float
    public let priceSource: String?
    public let priceUpdatedAt: Date?

    public init(card: CatalogCard, distance: Float) {
        self.externalId = card.externalId
        self.cardName = card.cardName
        self.setName = card.setName
        self.setCode = card.setCode
        self.localId = card.localId
        self.setYear = card.setYear
        self.variant = card.variant
        self.marketPrice = card.marketPrice
        self.lowPrice = card.lowPrice
        self.midPrice = card.midPrice
        self.highPrice = card.highPrice
        self.directLowPrice = card.directLowPrice
        self.cardmarketPrice = card.cardmarketPrice
        self.distance = distance
        self.priceSource = card.priceSource
        self.priceUpdatedAt = card.priceUpdatedAt
    }
}
