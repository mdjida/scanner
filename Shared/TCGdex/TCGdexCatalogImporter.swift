import Foundation

/// Imports TCGdex cards into the shared CatalogIndex for image-embedding lookup.
/// This is the free backbone of the Pokémon card database.
public final class TCGdexCatalogImporter {
    public static let shared = TCGdexCatalogImporter()
    private let api = TCGdexAPI.shared
    private let index = CatalogIndex.shared

    private init() {}

    /// Downloads all English Pokémon sets and their cards, then builds the nearest-neighbor index.
    /// Use limitSets to control how many sets are imported during testing.
    public func importCatalog(limitSets: Int? = nil) async throws {
        let sets = try await api.fetchSets(language: "en")
        let targetSets = limitSets.map { Array(sets.prefix($0)) } ?? sets

        var cards: [CatalogCard] = []
        for set in targetSets {
            let fullSet = try await api.fetchSet(id: set.id, language: "en")
            guard let setCards = fullSet.cards else { continue }

            for lightCard in setCards {
                guard let imageUrl = lightCard.image else { continue }

                let fullCard = try await api.fetchCard(id: lightCard.id, language: "en")
                let result = PokemonCardResult(card: fullCard)
                let variants = result?.variants ?? [PokemonCardVariant(id: fullCard.id, name: "Normal", type: "normal", size: nil, prices: [])]

                // Build one catalog row per variant so prices stay separate.
                for variant in variants {
                    let market = variant.prices.first { $0.priceType == "market" && $0.priceSource.contains("TCGplayer") }
                    let low = variant.prices.first { $0.priceType == "low" && $0.priceSource.contains("TCGplayer") }
                    let mid = variant.prices.first { $0.priceType == "mid" && $0.priceSource.contains("TCGplayer") }
                    let high = variant.prices.first { $0.priceType == "high" && $0.priceSource.contains("TCGplayer") }
                    let direct = variant.prices.first { $0.priceType == "directLow" && $0.priceSource.contains("TCGplayer") }
                    let cm = variant.prices.first { $0.priceSource.contains("Cardmarket") && $0.priceType == "trend" }

                    let externalId = "\(fullCard.id)_\(variant.name)"
                    let catalogCard = CatalogCard(
                        externalId: externalId,
                        cardName: fullCard.name,
                        setName: set.name,
                        setCode: set.id,
                        localId: fullCard.localId,
                        setYear: releaseYear(from: set),
                        variant: variant.name,
                        imageUrl: imageUrl,
                        marketPrice: market?.price,
                        lowPrice: low?.price,
                        midPrice: mid?.price,
                        highPrice: high?.price,
                        directLowPrice: direct?.price,
                        cardmarketPrice: cm?.price,
                        embedding: nil,
                        priceSource: market?.priceSource ?? cm?.priceSource,
                        priceUpdatedAt: market?.updatedAt ?? cm?.updatedAt
                    )
                    cards.append(catalogCard)
                }
            }
        }

        index.load(cards: cards)
        await withCheckedContinuation { continuation in
            index.saveToDisk { _ in continuation.resume() }
        }
    }

    private func releaseYear(from set: TCGdexSet) -> String? {
        return set.releaseDate?.prefix(4).map(String.init).joined()
    }
}
