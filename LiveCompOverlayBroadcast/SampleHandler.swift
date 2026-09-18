import ReplayKit
import Shared

/// Broadcast upload extension entry point.
/// Receives screen frames while the user has granted screen recording.
class SampleHandler: RPBroadcastSampleHandler {
    private let messenger = AppGroupMessenger.shared
    private let detector = StreamCardDetector()
    private var frameCount = 0
    private var lastScanTime: TimeInterval = 0
    private var lastDetectionTime: TimeInterval = 0
    
    override func broadcastStarted(withSetupInfo setupInfo: [String: NSObject]?) {
        // Called when user starts screen recording from Control Center.
    }
    
    override func broadcastPaused() {
        // User paused the broadcast.
    }
    
    override func broadcastResumed() {
        // User resumed the broadcast.
    }
    
    override func broadcastFinished() {
        // Called when user stops screen recording.
    }
    
    override func processSampleBuffer(_ sampleBuffer: CMSampleBuffer, with sampleBufferType: RPSampleBufferType) {
        switch sampleBufferType {
        case .video:
            frameCount += 1
            handleVideoFrame(sampleBuffer)
        case .audioApp, .audioMic:
            // We ignore audio; only analyzing video frames.
            break
        @unknown default:
            break
        }
    }
    
    private func handleVideoFrame(_ sampleBuffer: CMSampleBuffer) {
        let now = Date().timeIntervalSince1970
        
        if messenger.autoScanEnabled {
            // Auto-scan at roughly 1 frame per second to save quota/battery.
            // The host app is responsible for quota enforcement; the extension
            // just reads the flag and scans while enabled.
            if now - lastScanTime < 1.0 { return }
            lastScanTime = now
            detector.analyzeFrame(sampleBuffer, isAuto: true)
        } else {
            // Manual mode: check if host app requested a scan.
            let lastRequest = messenger.lastScanRequest
            if lastRequest > lastDetectionTime {
                lastDetectionTime = lastRequest
                detector.analyzeFrame(sampleBuffer, isAuto: false)
            }
        }
    }
}
