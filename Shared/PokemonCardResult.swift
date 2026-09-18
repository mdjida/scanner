import Foundation

/// A normalized, provider-agnostic Pokémon card result for display and caching.
public struct PokemonCardResult: Codable, Identifiable {
    public let id: String
    public let tcgDexId: String
    public let name: String
    public let setName: String
    public let setCode: String?
    public let localId: String
    public let rarity: String?
    public let imageUrl: String?
    public let language: String
    public let variants: [PokemonCardVariant]
    public let cachedAt: Date
    public let priceUpdatedAt: Date?

    public init?(card: TCGdexCard) {
        guard let set = card.set else { return nil }
        self.tcgDexId = card.id
        self.id = card.id
        self.name = card.name
        self.setName = set.name
        self.setCode = set.id
        self.localId = card.localId
        self.rarity = card.rarity
        self.imageUrl = card.image
        self.language = "en"
        self.cachedAt = Date()
        self.priceUpdatedAt = card.variantsDetailed?.first?.pricing?.tcgplayer?.updated?.isoDate()
                              ?? card.variantsDetailed?.first?.pricing?.cardmarket?.updated?.isoDate()
        self.variants = PokemonCardVariant.variants(from: card)
    }
}

public struct PokemonCardVariant: Codable, Identifiable {
    public let id: String
    public let name: String
    public let type: String?
    public let size: String?
    public let prices: [PokemonPrice]

    public static func variants(from card: TCGdexCard) -> [PokemonCardVariant] {
        let details = card.variantsDetailed ?? []
        var output: [PokemonCardVariant] = []

        for detail in details {
            let variantName = detail.type?.capitalized ?? "Normal"
            var prices: [PokemonPrice] = []

            if let tcg = detail.pricing?.tcgplayer {
                prices.append(contentsOf: tcg.pricePoints(variant: variantName, source: "TCGdex/TCGplayer", currency: tcg.unit ?? "USD"))
            }
            if let cm = detail.pricing?.cardmarket {
                prices.append(contentsOf: cm.pricePoints(variant: variantName, source: "TCGdex/Cardmarket", currency: cm.unit ?? "EUR"))
            }

            let vid = "\(card.id)_\(variantName)"
            output.append(PokemonCardVariant(id: vid, name: variantName, type: detail.type, size: detail.size, prices: prices))
        }

        if output.isEmpty {
            // No detailed variants: create a single placeholder variant without prices.
            output.append(PokemonCardVariant(id: card.id, name: "Normal", type: "normal", size: nil, prices: []))
        }

        return output
    }
}

public struct PokemonPrice: Codable, Identifiable {
    public let id: String
    public let priceSource: String
    public let priceType: String
    public let condition: String?
    public let variant: String
    public let currency: String
    public let price: Double?
    public let updatedAt: Date?

    public init(priceSource: String, priceType: String, condition: String?, variant: String, currency: String, price: Double?, updatedAt: Date?) {
        self.id = "\(priceSource)_\(priceType)_\(variant)_\(currency)_\(UUID().uuidString)"
        self.priceSource = priceSource
        self.priceType = priceType
        self.condition = condition
        self.variant = variant
        self.currency = currency
        self.price = price
        self.updatedAt = updatedAt
    }
}

// MARK: - TCGdex price mappers

private extension TCGdexTCGplayerVariantPrice {
    func pricePoints(variant: String, source: String, currency: String) -> [PokemonPrice] {
        var out: [PokemonPrice] = []
        let now = Date()
        if let low = lowPrice {
            out.append(PokemonPrice(priceSource: source, priceType: "low", condition: "Near Mint", variant: variant, currency: currency, price: low, updatedAt: now))
        }
        if let mid = midPrice {
            out.append(PokemonPrice(priceSource: source, priceType: "mid", condition: "Near Mint", variant: variant, currency: currency, price: mid, updatedAt: now))
        }
        if let high = highPrice {
            out.append(PokemonPrice(priceSource: source, priceType: "high", condition: "Near Mint", variant: variant, currency: currency, price: high, updatedAt: now))
        }
        if let market = marketPrice {
            out.append(PokemonPrice(priceSource: source, priceType: "market", condition: "Near Mint", variant: variant, currency: currency, price: market, updatedAt: now))
        }
        if let direct = directLowPrice {
            out.append(PokemonPrice(priceSource: source, priceType: "directLow", condition: "Near Mint", variant: variant, currency: currency, price: direct, updatedAt: now))
        }
        return out
    }
}

private extension TCGdexTCGplayerPrice {
    func pricePoints(variant: String, source: String, currency: String) -> [PokemonPrice] {
        var out: [PokemonPrice] = []
        let date = updated?.isoDate()
        let pairs: [(key: String, value: TCGdexTCGplayerVariantPrice?)] = [
            ("Normal", normal),
            ("Holofoil", holofoil),
            ("ReverseHolofoil", reverseHolofoil),
            ("FirstEdition", firstEdition),
            ("FirstEditionHolofoil", firstEditionHolofoil),
            ("Unlimited", unlimited)
        ]
        for (key, value) in pairs {
            guard let value = value else { continue }
            let pts = value.pricePoints(variant: key, source: source, currency: currency)
            out.append(contentsOf: pts.map {
                PokemonPrice(
                    priceSource: $0.priceSource,
                    priceType: $0.priceType,
                    condition: $0.condition,
                    variant: $0.variant,
                    currency: $0.currency,
                    price: $0.price,
                    updatedAt: date ?? $0.updatedAt
                )
            })
        }
        return out
    }
}

private extension TCGdexCardmarketPrice {
    func pricePoints(variant: String, source: String, currency: String) -> [PokemonPrice] {
        var out: [PokemonPrice] = []
        let date = updated?.isoDate()
        let pairs: [(String, Double?)] = [
            ("avg", avg), ("low", low), ("trend", trend),
            ("avg1", avg1), ("avg7", avg7), ("avg30", avg30)
        ]
        for (type, value) in pairs {
            guard let value = value else { continue }
            out.append(PokemonPrice(priceSource: source, priceType: type, condition: "Near Mint", variant: variant, currency: currency, price: value, updatedAt: date))
        }
        return out
    }
}

private extension String {
    func isoDate() -> Date? {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return formatter.date(from: self)
    }
}
