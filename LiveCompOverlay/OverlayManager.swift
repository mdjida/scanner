import SwiftUI
import ActivityKit
import Shared

@MainActor
final class OverlayManager: ObservableObject {
    @Published var isActive = false
    @Published var scanMode: OverlayActivityAttributes.ScanMode = .manual
    @Published var remainingAutoMinutes: Int = 0
    @Published var remainingManualScans: Int = 0
    @Published var lastCard: DetectedCard? = nil
    
    private var activity: Activity<OverlayActivityAttributes>?
    private var timer: Timer?
    private var darwinObserver: Any?
    private let quotaStore = QuotaStore.shared
    private let messenger = AppGroupMessenger.shared
    private let paywall = PaywallStore.shared
    
    @Published var showPaywall = false
    @Published var candidates: [DetectedCard] = []
    @Published var backendUnreachable = false
    @Published var isDetecting = false
    
    init() {
        refreshQuota()
        listenForDetectionResults()
        listenForManualScanRequests()
    }
    
    func toggleOverlay() {
        if isActive {
            stopOverlay()
        } else {
            startOverlay()
        }
    }
    
    /// Triggered by user tapping the Live Activity / manual scan button.
    func requestManualScan() {
        guard isActive else { return }
        guard remainingManualScans > 0 || paywall.isSubscribed else {
            showPaywall = true
            return
        }
        isDetecting = true
        updateLiveActivity(isDetecting: true)
        quotaStore.consumeManualScan()
        refreshQuota()
        messenger.requestScan()
    }
    
    private func startOverlay() {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else {
            // TODO: surface error
            return
        }
        
        refreshQuota()
        
        if scanMode == .auto, remainingAutoMinutes <= 0, !paywall.isSubscribed {
            showPaywall = true
            return
        }
        if scanMode == .manual, remainingManualScans <= 0, !paywall.isSubscribed {
            showPaywall = true
            return
        }
        
        messenger.autoScanEnabled = (scanMode == .auto)
        isActive = true
        startLiveActivity()
        beginMonitoring()
    }
    
    private func stopOverlay() {
        isActive = false
        timer?.invalidate()
        timer = nil
        messenger.autoScanEnabled = false
        Task {
            await activity?.end(nil, dismissalPolicy: .immediate)
        }
    }
    
    private func startLiveActivity() {
        let attributes = OverlayActivityAttributes()
        let state = OverlayActivityAttributes.ContentState(
            cardName: nil,
            cardSet: nil,
            marketPrice: nil,
            isDetecting: true,
            scanMode: scanMode,
            remainingAutoMinutes: remainingAutoMinutes,
            remainingManualScans: remainingManualScans
        )
        
        do {
            activity = try Activity.request(
                attributes: attributes,
                contentState: state,
                pushType: nil
            )
        } catch {
            print("Failed to start Live Activity: \(error)")
        }
    }
    
    private func beginMonitoring() {
        timer?.invalidate()
        timer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            Task { @MainActor [weak self] in
                self?.refreshQuota()
                if self?.scanMode == .auto {
                    self?.quotaStore.consumeAutoMinute()
                }
            }
        }
    }
    
    private func refreshQuota() {
        remainingAutoMinutes = quotaStore.remainingAutoMinutesThisMonth
        remainingManualScans = quotaStore.remainingManualScansThisMonth
    }
    
    private func listenForDetectionResults() {
        darwinObserver = DarwinNotifier.shared.observe(
            name: OverlayResultPayload.notificationName,
            queue: .main
        ) { [weak self] in
            Task { @MainActor [weak self] in
                self?.handleLatestResult()
            }
        }
    }
    
    private func listenForManualScanRequests() {
        NotificationCenter.default.addObserver(
            forName: .requestManualScan,
            object: nil,
            queue: .main
        ) { [weak self] _ in
            self?.requestManualScan()
        }
    }
    
    private func handleLatestResult() {
        guard let result = messenger.latestResult else {
            backendUnreachable = true
            isDetecting = false
            return
        }
        backendUnreachable = false
        isDetecting = false
        
        let card = makeDetectedCard(from: result)
        lastCard = card
        
        if let all = messenger.latestCandidates {
            candidates = all.candidates.map { makeDetectedCard(from: $0) }
        } else {
            candidates = [card]
        }
        
        updateLiveActivity(with: card)
    }
    
    private func makeDetectedCard(from result: OverlayResultPayload) -> DetectedCard {
        DetectedCard(
            id: result.externalId,
            name: result.cardName,
            setName: result.setName,
            setCode: result.setCode,
            localId: result.localId,
            marketPrice: result.marketPrice ?? "N/A",
            variant: result.variant,
            lowPrice: result.lowPrice,
            midPrice: result.midPrice,
            highPrice: result.highPrice,
            directLowPrice: result.directLowPrice,
            cardmarketPrice: result.cardmarketPrice,
            priceSource: result.priceSource,
            score: result.score
        )
    }
    
    private func updateLiveActivity(with card: DetectedCard) {
        let state = OverlayActivityAttributes.ContentState(
            cardName: card.name,
            cardSet: "\(card.setCode ?? "") \(card.localId ?? "") · \(card.setName)",
            marketPrice: card.marketPrice,
            variant: card.variant,
            lowPrice: card.lowPrice,
            midPrice: card.midPrice,
            highPrice: card.highPrice,
            isDetecting: false,
            scanMode: scanMode,
            remainingAutoMinutes: remainingAutoMinutes,
            remainingManualScans: remainingManualScans
        )
        Task {
            await activity?.update(using: state)
        }
    }
    
    private func updateLiveActivity(isDetecting: Bool) {
        let state = OverlayActivityAttributes.ContentState(
            cardName: lastCard?.name,
            cardSet: lastCard.map { "\($0.setCode ?? "") \($0.localId ?? "") · \($0.setName)" },
            marketPrice: lastCard?.marketPrice,
            variant: lastCard?.variant,
            lowPrice: lastCard?.lowPrice,
            midPrice: lastCard?.midPrice,
            highPrice: lastCard?.highPrice,
            isDetecting: isDetecting,
            scanMode: scanMode,
            remainingAutoMinutes: remainingAutoMinutes,
            remainingManualScans: remainingManualScans
        )
        Task {
            await activity?.update(using: state)
        }
    }
}

struct DetectedCard: Identifiable {
    let id: String
    let name: String
    let setName: String
    let setCode: String?
    let localId: String?
    let marketPrice: String
    let variant: String?
    let lowPrice: String?
    let midPrice: String?
    let highPrice: String?
    let directLowPrice: String?
    let cardmarketPrice: String?
    let priceSource: String?
    let score: Double?
}
