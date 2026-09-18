import CoreMedia
import CoreVideo

/// Extracts a CVPixelBuffer from a CMSampleBuffer for image analysis.
enum PixelBufferExtractor {
    static func extract(from sampleBuffer: CMSampleBuffer) -> CVPixelBuffer? {
        guard CMSampleBufferGetNumSamples(sampleBuffer) == 1,
              CMSampleBufferIsValid(sampleBuffer),
              let pixelBuffer = CMSampleBufferGetImageBuffer(sampleBuffer) else {
            return nil
        }
        return pixelBuffer
    }
}
