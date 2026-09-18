import WidgetKit
import SwiftUI
import ActivityKit
import Shared

struct OverlayLiveActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: OverlayActivityAttributes.self) { context in
            LockScreenView(context: context)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.leading) {
                    leadingExpanded(context: context)
                }
                DynamicIslandExpandedRegion(.trailing) {
                    trailingExpanded(context: context)
                }
                DynamicIslandExpandedRegion(.center) {
                    centerExpanded(context: context)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    bottomExpanded(context: context)
                }
            } compactLeading: {
                compactLeading(context: context)
            } compactTrailing: {
                compactTrailing(context: context)
            } minimal: {
                minimal(context: context)
            }
            .widgetURL(URL(string: "livecompoverlay://scan")!)
        }
    }
}

private struct LockScreenView: View {
    let context: ActivityViewContext<OverlayActivityAttributes>
    
    var body: some View {
        Button(action: {
            // Tapping the Live Activity requests a manual scan.
            LiveActivityBridge.shared.requestManualScan()
        }) {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Image(systemName: "scope")
                        .foregroundStyle(.indigo)
                    Text(context.state.isDetecting ? "Scanning stream..." : "Card detected")
                        .font(.headline)
                    Spacer()
                    Text(context.state.scanMode == .auto ? "Auto" : "Manual")
                        .font(.caption)
                        .padding(.horizontal, 8)
                        .padding(.vertical, 2)
                        .background(Color.indigo.opacity(0.2))
                        .clipShape(Capsule())
                }
                
                if let name = context.state.cardName,
                   let set = context.state.cardSet,
                   let price = context.state.marketPrice {
                    VStack(alignment: .leading, spacing: 4) {
                        Text(name)
                            .font(.title3)
                            .fontWeight(.semibold)
                        Text("\(set)" + (context.state.variant.map { " · \($0)" } ?? ""))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        HStack(spacing: 12) {
                            pricePill(title: "Market", value: price)
                            if let low = context.state.lowPrice {
                                pricePill(title: "Low", value: low)
                            }
                            if let mid = context.state.midPrice {
                                pricePill(title: "Mid", value: mid)
                            }
                            if let high = context.state.highPrice {
                                pricePill(title: "High", value: high)
                            }
                        }
                    }
                }
                
                HStack {
                    Text("Auto: \(context.state.remainingAutoMinutes)m")
                    Spacer()
                    Text("Manual: \(context.state.remainingManualScans)")
                }
                .font(.caption2)
                .foregroundStyle(.secondary)
            }
            .padding()
        }
        .buttonStyle(.plain)
    }
    
    private func pricePill(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.subheadline)
                .fontWeight(.medium)
        }
    }
}

// MARK: - Dynamic Island Views

private func leadingExpanded(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    Image(systemName: "scope")
        .font(.title2)
        .foregroundStyle(.indigo)
}

private func trailingExpanded(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    Text(context.state.scanMode == .auto ? "Auto" : "Manual")
        .font(.caption)
        .padding(.horizontal, 8)
        .padding(.vertical, 2)
        .background(Color.indigo.opacity(0.2))
        .clipShape(Capsule())
}

private func centerExpanded(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    VStack(spacing: 4) {
        Text(context.state.cardName ?? "Scanning stream...")
            .font(.headline)
        if let set = context.state.cardSet {
            Text(set)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}

private func bottomExpanded(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    HStack(spacing: 16) {
        if let price = context.state.marketPrice {
            priceBadge(title: "Market", value: price)
        }
        if let low = context.state.lowPrice {
            priceBadge(title: "Low", value: low)
        }
        if let mid = context.state.midPrice {
            priceBadge(title: "Mid", value: mid)
        }
        if let high = context.state.highPrice {
            priceBadge(title: "High", value: high)
        }
    }
}

private func compactLeading(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    Image(systemName: "scope")
        .foregroundStyle(.indigo)
}

private func compactTrailing(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    Text(context.state.marketPrice ?? "Tap to scan")
        .font(.caption)
        .fontWeight(.semibold)
}

private func minimal(context: ActivityViewContext<OverlayActivityAttributes>) -> some View {
    Image(systemName: context.state.cardName == nil ? "scope" : "creditcard.fill")
        .foregroundStyle(.indigo)
}

private func priceBadge(title: String, value: String) -> some View {
    VStack(spacing: 2) {
        Text(title)
            .font(.caption2)
            .foregroundStyle(.secondary)
        Text(value)
            .font(.subheadline)
            .fontWeight(.semibold)
    }
}

@main
struct LiveCompOverlayWidgetBundle: WidgetBundle {
    var body: some Widget {
        OverlayLiveActivityWidget()
    }
}

// Convenience alias matching NSExtensionPrincipalClass in Info.plist.
typealias LiveActivityBundle = LiveCompOverlayWidgetBundle
