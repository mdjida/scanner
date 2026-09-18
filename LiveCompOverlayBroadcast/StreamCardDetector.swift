import Foundation
import CoreMedia
import Shared

/// Detects cards in screen-capture frames, crops them, and sends them to the backend for identification.
public final class StreamCardDetector {
    private let messenger = AppGroupMessenger.shared
    private var isProcessing = false

    public func analyzeFrame(_ sampleBuffer: CMSampleBuffer, isAuto: Bool) {
        guard !isProcessing,
              let pixelBuffer = PixelBufferExtractor.extract(from: sampleBuffer) else {
            return
        }
        isProcessing = true

        VisionCardDetector.shared.detectCards(in: pixelBuffer) { [weak self] crop in
            guard let self = self, let crop = crop else {
                self?.isProcessing = false
                return
            }

            BackendClient.shared.identifyCard(crop.image) { [weak self] candidates in
                defer { self?.isProcessing = false }
                guard let candidates = candidates else { return }
                self?.messenger.publishResult(candidates.bestMatch)
                self?.messenger.publishCandidates(candidates)
            }
        }
    }
}
