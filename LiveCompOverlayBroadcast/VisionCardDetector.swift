import CoreImage
import CoreVideo
import Foundation
import Vision

/// Detects rectangular cards in a pixel buffer and returns normalized cropped images.
final class VisionCardDetector {
    static let shared = VisionCardDetector()
    private let context = CIContext(options: [.useSoftwareRenderer: false])

    private init() {}

    /// Finds the most card-like rectangle in the buffer and returns a normalized crop.
    func detectCards(in pixelBuffer: CVPixelBuffer, completion: @escaping (CardCrop?) -> Void) {
        let request = VNDetectRectanglesRequest { [weak self] request, error in
            guard let self = self,
                  error == nil,
                  let results = request.results as? [VNRectangleObservation],
                  let best = results.first else {
                completion(nil)
                return
            }

            // Prefer rectangles close to a trading-card aspect ratio (~2.5:3.5, or ~0.714).
            let cardRatio: Float = 2.5 / 3.5
            let chosen = results.min {
                abs($0.boundingBox.aspectRatio - cardRatio) < abs($1.boundingBox.aspectRatio - cardRatio)
            } ?? best

            guard let cropped = self.crop(pixelBuffer: pixelBuffer, observation: chosen) else {
                completion(nil)
                return
            }
            completion(CardCrop(image: cropped, confidence: Double(chosen.confidence)))
        }

        request.minimumConfidence = 0.6
        request.minimumAspectRatio = 0.5
        request.maximumAspectRatio = 1.0
        request.quadratureTolerance = 30
        request.minimumSize = 0.05
        request.maximumObservations = 5

        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up, options: [:])
        DispatchQueue.global(qos: .userInitiated).async {
            do {
                try handler.perform([request])
            } catch {
                completion(nil)
            }
        }
    }

    /// Perspective-correct crop of the detected rectangle.
    private func crop(pixelBuffer: CVPixelBuffer, observation: VNRectangleObservation) -> CGImage? {
        let ciImage = CIImage(cvPixelBuffer: pixelBuffer)
        let imageWidth = CGFloat(CVPixelBufferGetWidth(pixelBuffer))
        let imageHeight = CGFloat(CVPixelBufferGetHeight(pixelBuffer))

        let topLeft = CGPoint(x: observation.topLeft.x * imageWidth,
                              y: (1 - observation.topLeft.y) * imageHeight)
        let topRight = CGPoint(x: observation.topRight.x * imageWidth,
                               y: (1 - observation.topRight.y) * imageHeight)
        let bottomLeft = CGPoint(x: observation.bottomLeft.x * imageWidth,
                                 y: (1 - observation.bottomLeft.y) * imageHeight)
        let bottomRight = CGPoint(x: observation.bottomRight.x * imageWidth,
                                  y: (1 - observation.bottomRight.y) * imageHeight)

        let perspectiveCorrection = CIFilter(name: "CIPerspectiveCorrection")!
        perspectiveCorrection.setValue(ciImage, forKey: kCIInputImageKey)
        perspectiveCorrection.setValue(CIVector(cgPoint: topLeft), forKey: "inputTopLeft")
        perspectiveCorrection.setValue(CIVector(cgPoint: topRight), forKey: "inputTopRight")
        perspectiveCorrection.setValue(CIVector(cgPoint: bottomRight), forKey: "inputBottomRight")
        perspectiveCorrection.setValue(CIVector(cgPoint: bottomLeft), forKey: "inputBottomLeft")

        guard let output = perspectiveCorrection.outputImage else { return nil }
        return context.createCGImage(output, from: output.extent)
    }
}

struct CardCrop {
    let image: CGImage
    let confidence: Double
}

private extension CGRect {
    var aspectRatio: Float {
        guard height != 0 else { return 1 }
        return Float(width / height)
    }
}
