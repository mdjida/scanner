#!/usr/bin/swift

// Build a precomputed catalog_embeddings.json from TCGdex.
// Run on macOS with Swift installed.
//
// Default usage (era-balanced mix):
//   swift build_tcgdex_embeddings.swift
//
// Import every available set:
//   swift build_tcgdex_embeddings.swift --sets=all

import Foundation
import CoreGraphics
import CoreImage
import Vision

let baseURL = "https://api.tcgdex.net/v2"
let language = "en"
let outputFile = "catalog_embeddings.json"

/// Default era-balanced set list. Covers every major Pokémon TCG era.
let defaultSetFilter: Set<String> = [
    "base1", "base2", "base3",       // Base / WotC
    "neo1",                            // Neo era
    "ecard1",                          // E-Card
    "ex1", "ex6",                      // EX era
    "dp1", "dp7",                      // Diamond & Pearl
    "pl1",                             // Platinum / LV.X
    "hgss1",                           // HeartGold SoulSilver
    "bw1", "bw11",                     // Black & White
    "xy1", "xy12",                     // XY / Evolutions
    "sm1", "sm115",                    // Sun & Moon / Hidden Fates
    "swsh3", "swsh12",                 // Sword & Shield
    "sv03", "sv03.5",                  // Scarlet & Violet
    "swshp",                           // SWSH promos
]

let arguments = CommandLine.arguments
let shouldUseAllSets = arguments.contains("--sets=all")
let session = URLSession(configuration: {
    let c = URLSessionConfiguration.default
    c.timeoutIntervalForRequest = 60
    c.timeoutIntervalForResource = 600
    c.httpAdditionalHeaders = ["User-Agent": "LiveCompOverlay-Embedder/0.1.0"]
    return c
}())

struct TCGdexSet: Codable {
    let id: String
    let name: String
    let releaseDate: String?
    let cards: [TCGdexCardLight]?
}

struct TCGdexCardLight: Codable {
    let id: String
    let localId: String
    let name: String
    let image: String?
}

struct TCGdexCard: Codable {
    let id: String
    let localId: String
    let name: String
    let image: String?
    let rarity: String?
    let set: TCGdexSet?
    let variantsDetailed: [TCGdexVariantDetail]?
}

struct TCGdexVariantDetail: Codable {
    let type: String?
    let size: String?
    let pricing: TCGdexPricingContainer?
}

struct TCGdexPricingContainer: Codable {
    let tcgplayer: TCGdexTCGplayerPrice?
    let cardmarket: TCGdexCardmarketPrice?
}

struct TCGdexTCGplayerPrice: Codable {
    let unit: String?
    let updated: String?
    let normal: TCGdexTCGplayerVariantPrice?
    let holofoil: TCGdexTCGplayerVariantPrice?
    let reverseHolofoil: TCGdexTCGplayerVariantPrice?
    let firstEdition: TCGdexTCGplayerVariantPrice?
    let firstEditionHolofoil: TCGdexTCGplayerVariantPrice?
    let unlimited: TCGdexTCGplayerVariantPrice?
}

struct TCGdexTCGplayerVariantPrice: Codable {
    let lowPrice: Double?
    let midPrice: Double?
    let highPrice: Double?
    let marketPrice: Double?
    let directLowPrice: Double?
}

struct TCGdexCardmarketPrice: Codable {
    let unit: String?
    let updated: String?
    let avg: Double?
    let low: Double?
    let trend: Double?
    let avg1: Double?
    let avg7: Double?
    let avg30: Double?
}

struct CatalogCard: Codable {
    let externalId: String
    let cardName: String
    let setName: String
    let setCode: String?
    let localId: String?
    let setYear: String?
    let variant: String?
    let imageUrl: String?
    let marketPrice: Double?
    let lowPrice: Double?
    let midPrice: Double?
    let highPrice: Double?
    let directLowPrice: Double?
    let cardmarketPrice: Double?
    let embedding: [Float]?
    let priceSource: String?
    let priceUpdatedAt: Date?
}

func fetchJSON<T: Decodable>(url: URL) async throws -> T {
    let (data, response) = try await session.data(from: url)
    guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
        throw URLError(.badServerResponse)
    }
    let decoder = JSONDecoder()
    decoder.keyDecodingStrategy = .convertFromSnakeCase
    return try decoder.decode(T.self, from: data)
}

func downloadImage(url: URL) async -> CGImage? {
    do {
        let (data, _) = try await session.data(from: url)
        #if canImport(AppKit)
        if let nsImage = NSImage(data: data) {
            var rect = CGRect(origin: .zero, size: nsImage.size)
            return nsImage.cgImage(forProposedRect: &rect, context: nil, hints: nil)
        }
        #elseif canImport(UIKit)
        if let uiImage = UIImage(data: data) {
            return uiImage.cgImage
        }
        #endif
    } catch {
        print("Image download failed: \(error)")
    }
    return nil
}

func encodeImage(_ cgImage: CGImage) async -> [Float]? {
    await withCheckedContinuation { continuation in
        let request = VNGenerateImageFeaturePrintRequest { request, error in
            guard error == nil,
                  let result = request.results?.first as? VNFeaturePrintObservation,
                  let data = result.data as? Data else {
                continuation.resume(returning: nil)
                return
            }
            var floats = [Float](repeating: 0, count: data.count / MemoryLayout<Float>.size)
            _ = floats.withUnsafeMutableBytes { data.copyBytes(to: $0) }
            continuation.resume(returning: floats)
        }
        let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])
        do {
            try handler.perform([request])
        } catch {
            continuation.resume(returning: nil)
        }
    }
}

func pricePoints(from tcg: TCGdexTCGplayerVariantPrice, variant: String) -> [(String, Double?)] {
    [
        ("market", tcg.marketPrice),
        ("low", tcg.lowPrice),
        ("mid", tcg.midPrice),
        ("high", tcg.highPrice),
        ("directLow", tcg.directLowPrice)
    ]
}

func catalogCards(from fullCard: TCGdexCard, set: TCGdexSet) -> [CatalogCard] {
    guard let imageUrl = fullCard.image else { return [] }
    let variants = fullCard.variantsDetailed ?? []
    var output: [CatalogCard] = []

    for detail in variants {
        let variantName = detail.type?.capitalized ?? "Normal"
        let externalId = "\(fullCard.id)_\(variantName)"

        var market: Double?
        var low: Double?
        var mid: Double?
        var high: Double?
        var directLow: Double?
        var cardmarket: Double?
        var source: String?
        var updatedAt: Date?

        if let tcg = detail.pricing?.tcgplayer {
            market = tcg.marketPrice
            low = tcg.lowPrice
            mid = tcg.midPrice
            high = tcg.highPrice
            directLow = tcg.directLowPrice
            source = "TCGdex/TCGplayer"
            updatedAt = tcg.updated?.isoDate()
        }
        if let cm = detail.pricing?.cardmarket {
            if market == nil {
                cardmarket = cm.trend
                source = source ?? "TCGdex/Cardmarket"
                updatedAt = updatedAt ?? cm.updated?.isoDate()
            }
        }

        let card = CatalogCard(
            externalId: externalId,
            cardName: fullCard.name,
            setName: set.name,
            setCode: set.id,
            localId: fullCard.localId,
            setYear: set.releaseDate?.prefix(4).map(String.init).joined(),
            variant: variantName,
            imageUrl: imageUrl,
            marketPrice: market,
            lowPrice: low,
            midPrice: mid,
            highPrice: high,
            directLowPrice: directLow,
            cardmarketPrice: cardmarket,
            embedding: nil,
            priceSource: source,
            priceUpdatedAt: updatedAt
        )
        output.append(card)
    }

    if output.isEmpty {
        output.append(CatalogCard(
            externalId: "\(fullCard.id)_Normal",
            cardName: fullCard.name,
            setName: set.name,
            setCode: set.id,
            localId: fullCard.localId,
            setYear: set.releaseDate?.prefix(4).map(String.init).joined(),
            variant: "Normal",
            imageUrl: imageUrl,
            marketPrice: nil,
            lowPrice: nil,
            midPrice: nil,
            highPrice: nil,
            directLowPrice: nil,
            cardmarketPrice: nil,
            embedding: nil,
            priceSource: nil,
            priceUpdatedAt: nil
        ))
    }

    return output
}

func main() async throws {
    print("Fetching sets...")
    let setsURL = URL(string: "\(baseURL)/\(language)/sets")!
    let sets: [TCGdexSet] = try await fetchJSON(url: setsURL)

    let activeFilter = shouldUseAllSets ? nil : defaultSetFilter
    let filteredSets = activeFilter == nil ? sets : sets.filter { activeFilter!.contains($0.id) }

    if let filter = activeFilter {
        print("Using era-mix filter: \(filter.count) set(s).")
    } else {
        print("Importing all \(sets.count) sets.")
    }

    var allCards: [CatalogCard] = []

    for (index, set) in filteredSets.enumerated() {
        guard let lightCards = set.cards, !lightCards.isEmpty else { continue }
        print("[\(index + 1)/\(filteredSets.count)] Processing \(set.name) (\(lightCards.count) cards)...")

        for light in lightCards {
            guard let imageUrlString = light.image, let imageURL = URL(string: imageUrlString) else { continue }

            let cardURL = URL(string: "\(baseURL)/\(language)/cards/\(light.id)")!
            do {
                let fullCard: TCGdexCard = try await fetchJSON(url: cardURL)
                var cards = catalogCards(from: fullCard, set: set)

                // Compute embedding once per card image.
                if let cgImage = await downloadImage(url: imageURL) {
                    if let embedding = await encodeImage(cgImage) {
                        cards = cards.map {
                            var c = $0
                            c = CatalogCard(
                                externalId: c.externalId,
                                cardName: c.cardName,
                                setName: c.setName,
                                setCode: c.setCode,
                                localId: c.localId,
                                setYear: c.setYear,
                                variant: c.variant,
                                imageUrl: c.imageUrl,
                                marketPrice: c.marketPrice,
                                lowPrice: c.lowPrice,
                                midPrice: c.midPrice,
                                highPrice: c.highPrice,
                                directLowPrice: c.directLowPrice,
                                cardmarketPrice: c.cardmarketPrice,
                                embedding: embedding,
                                priceSource: c.priceSource,
                                priceUpdatedAt: c.priceUpdatedAt
                            )
                            return c
                        }
                    }
                }

                allCards.append(contentsOf: cards)
            } catch {
                print("Failed to fetch card \(light.id): \(error)")
            }
        }
    }

    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
    encoder.dateEncodingStrategy = .iso8601
    let data = try encoder.encode(allCards)
    let url = URL(fileURLWithPath: outputFile)
    try data.write(to: url)
    print("Wrote \(allCards.count) catalog entries to \(url.path)")
}

extension String {
    func isoDate() -> Date? {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f.date(from: self)
    }
}

await main()
