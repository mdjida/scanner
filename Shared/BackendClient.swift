import Foundation
import UIKit

/// Client for the local (later cloud) backend that identifies cards from image crops.
public final class BackendClient {
    public static let shared = BackendClient()
    
    private let session: URLSession
    private let defaults = UserDefaults(suiteName: QuotaStore.suiteName)
    private let baseURLKey = "backend_base_url"
    private let maxRetries = 2
    
    public var baseURL: String {
        get { defaults?.string(forKey: baseURLKey) ?? "http://192.168.1.100:8000" }
        set {
            defaults?.set(newValue, forKey: baseURLKey)
            defaults?.synchronize()
        }
    }
    
    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 120
        session = URLSession(configuration: config)
    }
    
    /// Sends a cropped card image to the backend /identify endpoint and returns ranked candidates.
    public func identifyCard(_ cgImage: CGImage, completion: @escaping (IdentifyCandidates?) -> Void) {
        guard let imageData = cgImage.jpegData(compressionQuality: 0.85) else {
            completion(nil)
            return
        }
        
        guard let url = URL(string: "\(baseURL)/identify") else {
            completion(nil)
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        request.httpBody = buildMultipartBody(imageData: imageData, boundary: boundary, fieldName: "file", fileName: "card.jpg")
        
        performRequest(request: request, retryCount: 0, completion: completion)
    }
    
    private func performRequest(request: URLRequest, retryCount: Int, completion: @escaping (IdentifyCandidates?) -> Void) {
        let task = session.dataTask(with: request) { [weak self] data, response, error in
            guard let self = self else { return }
            
            if let error = error, retryCount < self.maxRetries {
                DispatchQueue.global().asyncAfter(deadline: .now() + 1.0) {
                    self.performRequest(request: request, retryCount: retryCount + 1, completion: completion)
                }
                return
            }
            
            guard let data = data, error == nil,
                  let httpResponse = response as? HTTPURLResponse,
                  (200..<300).contains(httpResponse.statusCode) else {
                DispatchQueue.main.async { completion(nil) }
                return
            }
            
            do {
                let decoded = try JSONDecoder().decode(IdentifyResponse.self, from: data)
                let candidates = IdentifyCandidates(
                    bestMatch: self.makePayload(from: decoded.bestMatch),
                    candidates: decoded.candidates.map { self.makePayload(from: $0) }
                )
                DispatchQueue.main.async { completion(candidates) }
            } catch {
                DispatchQueue.main.async { completion(nil) }
            }
        }
        task.resume()
    }
    
    private func makePayload(from candidate: IdentifyCandidate) -> OverlayResultPayload {
        OverlayResultPayload(
            externalId: candidate.card.externalId,
            cardName: candidate.card.name,
            setName: candidate.card.setName ?? "",
            setCode: candidate.card.setCode,
            localId: candidate.card.localId,
            marketPrice: candidate.card.marketPrice.map { String(format: "$%.2f", $0) },
            variant: candidate.card.variant,
            lowPrice: candidate.card.lowPrice.map { String(format: "$%.2f", $0) },
            midPrice: candidate.card.midPrice.map { String(format: "$%.2f", $0) },
            highPrice: candidate.card.highPrice.map { String(format: "$%.2f", $0) },
            directLowPrice: candidate.card.directLowPrice.map { String(format: "$%.2f", $0) },
            cardmarketPrice: candidate.card.cardmarketPrice.map { String(format: "€%.2f", $0) },
            priceSource: candidate.card.priceSource,
            score: candidate.score
        )
    }
    
    private func buildMultipartBody(imageData: Data, boundary: String, fieldName: String, fileName: String) -> Data {
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"\(fieldName)\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)
        return body
    }
}

public struct IdentifyCandidates: Codable {
    public static let defaultsKey = "identify_latest_candidates"
    
    public let bestMatch: OverlayResultPayload
    public let candidates: [OverlayResultPayload]
    
    public init(bestMatch: OverlayResultPayload, candidates: [OverlayResultPayload]) {
        self.bestMatch = bestMatch
        self.candidates = candidates
    }
    
    public func encoded() -> Data? {
        try? JSONEncoder().encode(self)
    }
    
    public init?(data: Data) {
        guard let decoded = try? JSONDecoder().decode(Self.self, from: data) else { return nil }
        self = decoded
    }
}

private struct IdentifyResponse: Codable {
    let bestMatch: IdentifyCandidate
    let candidates: [IdentifyCandidate]
}

private struct IdentifyCandidate: Codable {
    let score: Double
    let card: IdentifyCard
}

private struct IdentifyCard: Codable {
    let externalId: String
    let name: String
    let localId: String?
    let setCode: String?
    let setName: String?
    let variant: String?
    let marketPrice: Double?
    let lowPrice: Double?
    let midPrice: Double?
    let highPrice: Double?
    let directLowPrice: Double?
    let cardmarketPrice: Double?
    let priceSource: String?
}

private extension CGImage {
    func jpegData(compressionQuality: CGFloat) -> Data? {
        let uiImage = UIImage(cgImage: self)
        return uiImage.jpegData(compressionQuality: compressionQuality)
    }
}
