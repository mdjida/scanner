import Foundation

/// Free, no-key API client for TCGdex (https://api.tcgdex.net/v2).
/// Supports multiple languages; defaults to English.
public final class TCGdexAPI {
    public static let shared = TCGdexAPI()

    private let baseURL = "https://api.tcgdex.net/v2"
    private let session: URLSession

    public init(language: String = "en") {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 300
        config.httpAdditionalHeaders = ["User-Agent": "LiveCompOverlay/0.1.0"]
        config.urlCache = URLCache(memoryCapacity: 20 * 1024 * 1024,
                                    diskCapacity: 100 * 1024 * 1024)
        session = URLSession(configuration: config)
    }

    // MARK: - Sets

    public func fetchSets(language: String = "en") async throws -> [TCGdexSet] {
        let url = URL(string: "\(baseURL)/\(language)/sets")!
        return try await fetchJSON(url: url)
    }

    public func fetchSet(id: String, language: String = "en") async throws -> TCGdexSet {
        let url = URL(string: "\(baseURL)/\(language)/sets/\(id)")!
        return try await fetchJSON(url: url)
    }

    // MARK: - Cards

    public func fetchCards(language: String = "en", queryItems: [URLQueryItem]? = nil) async throws -> [TCGdexCard] {
        var components = URLComponents(string: "\(baseURL)/\(language)/cards")!
        components.queryItems = queryItems
        guard let url = components.url else { throw URLError(.badURL) }
        return try await fetchJSON(url: url)
    }

    public func fetchCard(id: String, language: String = "en") async throws -> TCGdexCard {
        let url = URL(string: "\(baseURL)/\(language)/cards/\(id)")!
        return try await fetchJSON(url: url)
    }

    public func searchCards(name: String, language: String = "en") async throws -> [TCGdexCardLight] {
        let query = URLQueryItem(name: "name", value: name)
        var components = URLComponents(string: "\(baseURL)/\(language)/cards")!
        components.queryItems = [query]
        guard let url = components.url else { throw URLError(.badURL) }
        return try await fetchJSON(url: url)
    }

    public func searchCards(query: [URLQueryItem], language: String = "en") async throws -> [TCGdexCardLight] {
        var components = URLComponents(string: "\(baseURL)/\(language)/cards")!
        components.queryItems = query
        guard let url = components.url else { throw URLError(.badURL) }
        return try await fetchJSON(url: url)
    }

    // MARK: - Private

    private func fetchJSON<T: Decodable>(url: URL) async throws -> T {
        let (data, response) = try await session.data(from: url)
        guard let httpResponse = response as? HTTPURLResponse,
              (200..<300).contains(httpResponse.statusCode) else {
            throw URLError(.badServerResponse)
        }
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(T.self, from: data)
    }
}
