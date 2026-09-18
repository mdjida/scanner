import Foundation

/// In-memory + on-disk nearest-neighbor catalog index for image embeddings.
/// Populated from TCGdex (free Pokémon API) and extensible to other card databases.
public final class CatalogIndex {
    public static let shared = CatalogIndex()

    private var cards: [String: CatalogCard] = [:]
    private let queue = DispatchQueue(label: "com.livecompoverlay.catalog", qos: .userInitiated)
    private let fileName = "catalog_embeddings.json"

    private init() {}

    public var cardCount: Int {
        queue.sync { cards.count }
    }

    public func load(cards: [CatalogCard]) {
        queue.sync {
            self.cards = Dictionary(uniqueKeysWithValues: cards.map { ($0.externalId, $0) })
        }
    }

    /// Find the nearest catalog card by cosine distance on feature-print embeddings.
    public func findNearestMatch(embedding: [Float], threshold: Float = 0.15, completion: @escaping (CatalogMatch?) -> Void) {
        queue.async { [weak self] in
            guard let self = self else { return }
            let candidates = self.cards.values.compactMap { card -> (CatalogCard, Float)? in
                guard let cardEmbedding = card.embedding, !cardEmbedding.isEmpty else { return nil }
                let dist = self.cosineDistance(embedding, cardEmbedding)
                return (card, dist)
            }
            guard let best = candidates.min(by: { $0.1 < $1.1 }), best.1 <= threshold else {
                DispatchQueue.main.async { completion(nil) }
                return
            }
            DispatchQueue.main.async { completion(CatalogMatch(card: best.0, distance: best.1)) }
        }
    }

    /// Persist the current catalog (with embeddings) to app-group storage.
    public func saveToDisk(completion: ((Bool) -> Void)? = nil) {
        queue.async { [weak self] in
            guard let self = self else { return }
            let list = Array(self.cards.values)
            do {
                let data = try JSONEncoder().encode(list)
                let url = self.storageURL()
                try data.write(to: url, options: .atomic)
                DispatchQueue.main.async { completion?(true) }
            } catch {
                DispatchQueue.main.async { completion?(false) }
            }
        }
    }

    /// Load catalog from disk into memory.
    public func loadFromDisk(completion: ((Bool) -> Void)? = nil) {
        queue.async { [weak self] in
            guard let self = self else { return }
            do {
                let data = try Data(contentsOf: self.storageURL())
                let list = try JSONDecoder().decode([CatalogCard].self, from: data)
                self.cards = Dictionary(uniqueKeysWithValues: list.map { ($0.externalId, $0) })
                DispatchQueue.main.async { completion?(true) }
            } catch {
                DispatchQueue.main.async { completion?(false) }
            }
        }
    }

    private func storageURL() -> URL {
        let base = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: QuotaStore.suiteName)
        ?? FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return base.appendingPathComponent(fileName)
    }

    private func cosineDistance(_ a: [Float], _ b: [Float]) -> Float {
        var dot: Float = 0
        var normA: Float = 0
        var normB: Float = 0
        let count = min(a.count, b.count)
        for i in 0..<count {
            dot += a[i] * b[i]
            normA += a[i] * a[i]
            normB += b[i] * b[i]
        }
        guard normA > 0, normB > 0 else { return Float.greatestFiniteMagnitude }
        let similarity = dot / (sqrt(normA) * sqrt(normB))
        return 1 - similarity
    }
}
