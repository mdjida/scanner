import CoreImage
import Foundation
import Vision

/// Computes a 1,024-element image embedding using Apple's Image Feature Print.
/// This runs on-device and is used to match a detected card against the catalog.
public final class ImageFeaturePrintEncoder {
    public static let shared = ImageFeaturePrintEncoder()
    private let context = CIContext(options: [.useSoftwareRenderer: false])

    private init() {}

    /// Encodes a CGImage into a feature print vector.
    public func encode(_ cgImage: CGImage, completion: @escaping ([Float]?) -> Void) {
        let request = VNGenerateImageFeaturePrintRequest { request, error in
            guard error == nil,
                  let result = request.results?.first as? VNFeaturePrintObservation,
                  let data = result.data as? Data else {
                completion(nil)
                return
            }
            var floats = [Float](repeating: 0, count: data.count / MemoryLayout<Float>.size)
            _ = floats.withUnsafeMutableBytes { data.copyBytes(to: $0) }
            completion(floats)
        }

        let handler = VNImageRequestHandler(cgImage: cgImage, orientation: .up, options: [:])
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try handler.perform([request])
            } catch {
                completion(nil)
            }
        }
    }
}
