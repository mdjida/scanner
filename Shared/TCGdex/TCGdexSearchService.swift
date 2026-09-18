import Foundation

/// Searches TCGdex and resolves exact card matches for overlay display.
public final class TCGdexSearchService {
    public static let shared = TCGdexSearchService()
    private let api = TCGdexAPI.shared

    private init() {}

    /// Search by card name and optional set/number/variant filters.
    /// Returns candidates if multiple cards match, or a single exact match when possible.
    public func search(
        name: String,
        setId: String? = nil,
        localId: String? = nil,
        variant: String? = nil,
        language: String = "en"
    ) async throws -> TCGdexSearchResult {
        var queryItems: [URLQueryItem] = [URLQueryItem(name: "name", value: name)]
        if let setId = setId {
            queryItems.append(URLQueryItem(name: "set", value: setId))
        }
        if let localId = localId {
            queryItems.append(URLQueryItem(name: "localId", value: localId))
        }

        let candidates = try await api.searchCards(query: queryItems, language: language)
        guard !candidates.isEmpty else { return .noMatches }

        // If we have enough info to pin down one card, fetch full details.
        let exactMatches = candidates.filter {
            let nameMatch = $0.name.lowercased() == name.lowercased()
            let setMatch = setId == nil || $0.id.hasPrefix(setId!.lowercased())
            let numberMatch = localId == nil || $0.localId == localId
            return nameMatch && setMatch && numberMatch
        }

        if exactMatches.count == 1, let first = exactMatches.first {
            let fullCard = try await api.fetchCard(id: first.id, language: language)
            return .exact(fullCard)
        }

        return .multiple(candidates)
    }

    /// Fetches a card by its TCGdex ID and returns a normalized result with per-variant prices.
    public func fetchAndNormalizeCard(id: String, language: String = "en") async throws -> PokemonCardResult? {
        let card = try await api.fetchCard(id: id, language: language)
        return PokemonCardResult(card: card)
    }
}

public enum TCGdexSearchResult {
    case exact(TCGdexCard)
    case multiple([TCGdexCardLight])
    case noMatches
}
