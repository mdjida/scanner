import Foundation

// MARK: - Sets

public struct TCGdexSet: Codable, Identifiable {
    public let id: String
    public let name: String
    public let logo: String?
    public let symbol: String?
    public let cardCount: TCGdexCardCount?
    public let releaseDate: String?
    public let cards: [TCGdexCardLight]?
}

public struct TCGdexCardCount: Codable {
    public let total: Int?
    public let official: Int?
}

// MARK: - Card (light + full)

public struct TCGdexCardLight: Codable, Identifiable {
    public let id: String
    public let localId: String
    public let name: String
    public let image: String?
}

public struct TCGdexCard: Codable, Identifiable {
    public let id: String
    public let localId: String
    public let name: String
    public let image: String?
    public let category: String?
    public let illustrator: String?
    public let rarity: String?
    public let set: TCGdexSet?
    public let variants: TCGdexVariants?
    public let variantsDetailed: [TCGdexVariantDetail]?
    public let hp: Int?
    public let types: [String]?
    public let stage: String?
    public let suffix: String?
    public let updated: String?
}

public struct TCGdexVariants: Codable {
    public let firstEdition: Bool?
    public let holo: Bool?
    public let normal: Bool?
    public let reverse: Bool?
    public let wPromo: Bool?
}

public struct TCGdexVariantDetail: Codable {
    public let type: String?
    public let size: String?
    public let variantId: String?
    public let thirdParty: TCGdexThirdPartyIDs?
    public let pricing: TCGdexPricingContainer?
}

public struct TCGdexThirdPartyIDs: Codable {
    public let tcgplayer: Int?
    public let cardmarket: Int?
}

// MARK: - Pricing

public struct TCGdexPricingContainer: Codable {
    public let tcgplayer: TCGdexTCGplayerPrice?
    public let cardmarket: TCGdexCardmarketPrice?
}

public struct TCGdexTCGplayerPrice: Codable {
    public let unit: String?
    public let updated: String?
    public let normal: TCGdexTCGplayerVariantPrice?
    public let holofoil: TCGdexTCGplayerVariantPrice?
    public let reverseHolofoil: TCGdexTCGplayerVariantPrice?
    public let firstEdition: TCGdexTCGplayerVariantPrice?
    public let firstEditionHolofoil: TCGdexTCGplayerVariantPrice?
    public let unlimited: TCGdexTCGplayerVariantPrice?
}

public struct TCGdexTCGplayerVariantPrice: Codable {
    public let productId: Int?
    public let lowPrice: Double?
    public let midPrice: Double?
    public let highPrice: Double?
    public let marketPrice: Double?
    public let directLowPrice: Double?
}

public struct TCGdexCardmarketPrice: Codable {
    public let unit: String?
    public let updated: String?
    public let idProduct: Int?
    public let avg: Double?
    public let low: Double?
    public let trend: Double?
    public let avg1: Double?
    public let avg7: Double?
    public let avg30: Double?
}
