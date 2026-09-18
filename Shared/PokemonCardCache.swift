import Foundation

/// Local cache for TCGdex-normalized Pokémon card results.
public final class PokemonCardCache {
    public static let shared = PokemonCardCache()

    private let defaults: UserDefaults?
    private let key = "pokemon_card_cache_v1"
    private let maxAge: TimeInterval = 24 * 60 * 60 // 24 hours

    private init() {
        defaults = UserDefaults(suiteName: QuotaStore.suiteName)
    }

    public func get(id: String) -> PokemonCardResult? {
        guard let data = defaults?.data(forKey: cacheKey(id: id)),
              let cached = try? JSONDecoder().decode(CachedEntry.self, from: data) else {
            return nil
        }
        guard Date().timeIntervalSince(cached.storedAt) < maxAge else {
            remove(id: id)
            return nil
        }
        return cached.result
    }

    public func set(_ result: PokemonCardResult) {
        let entry = CachedEntry(result: result, storedAt: Date())
        if let data = try? JSONEncoder().encode(entry) {
            defaults?.set(data, forKey: cacheKey(id: result.id))
        }
    }

    public func remove(id: String) {
        defaults?.removeObject(forKey: cacheKey(id: id))
    }

    public func clear() {
        guard let allKeys = defaults?.dictionaryRepresentation().keys else { return }
        for key in allKeys where key.hasPrefix("pokemon_cache_") {
            defaults?.removeObject(forKey: key)
        }
    }

    private func cacheKey(id: String) -> String {
        "pokemon_cache_\(id)"
    }

    private struct CachedEntry: Codable {
        let result: PokemonCardResult
        let storedAt: Date
    }
}
