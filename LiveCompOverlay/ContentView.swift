import SwiftUI
import ActivityKit
import Shared

struct ContentView: View {
    @StateObject private var overlayManager = OverlayManager()
    
    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                header
                modePicker
                startButton
                quotaDisplay
                statusDisplay
                Spacer()
            }
            .padding()
            .navigationTitle("Live Comp Overlay")
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Menu {
                    NavigationLink(destination: CatalogSettingsView()) {
                        Label("Catalog", systemImage: "gearshape")
                    }
                    NavigationLink(destination: PokemonSearchView()) {
                        Label("Pokémon Search", systemImage: "magnifyingglass")
                    }
                    NavigationLink(destination: BackendSettingsView()) {
                        Label("Backend", systemImage: "network")
                    }
                } label: {
                    Image(systemName: "ellipsis.circle")
                }
            }
        }
        .sheet(isPresented: $overlayManager.showPaywall) {
            paywallView
        }
    }

    private var paywallView: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Image(systemName: "crown.fill")
                    .font(.system(size: 64))
                    .foregroundStyle(.yellow)
                Text("Upgrade to Premium")
                    .font(.title)
                    .fontWeight(.bold)
                Text("Unlock unlimited auto-scan and manual scans every month.")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)
                Spacer()
            }
            .padding()
            .navigationTitle("Premium")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Close") {
                        overlayManager.showPaywall = false
                    }
                }
            }
        }
    }

    private var header: some View {
        VStack(spacing: 8) {
            Image(systemName: "scope")
                .font(.system(size: 64))
                .foregroundStyle(.indigo)
            Text("Detect cards on any stream")
                .font(.headline)
            Text("Open Whatnot, Twitch, or YouTube after starting the overlay.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
    }
    
    private var modePicker: some View {
        VStack(spacing: 8) {
            Picker("Scan Mode", selection: $overlayManager.scanMode) {
                Text("Manual").tag(OverlayActivityAttributes.ScanMode.manual)
                Text("Auto").tag(OverlayActivityAttributes.ScanMode.auto)
            }
            .pickerStyle(.segmented)

            Text("Auto is free for testing. Paid tier unlocks unlimited auto-scan.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
    
    private var startButton: some View {
        VStack(spacing: 12) {
            Button(action: { overlayManager.toggleOverlay() }) {
                Label(
                    overlayManager.isActive ? "Stop Overlay" : "Start Overlay",
                    systemImage: overlayManager.isActive ? "stop.circle.fill" : "play.circle.fill"
                )
                .font(.title2)
                .padding()
                .frame(maxWidth: .infinity)
            }
            .buttonStyle(.borderedProminent)
            .tint(overlayManager.isActive ? .red : .indigo)
            
            if overlayManager.isActive {
                Button(action: { overlayManager.requestManualScan() }) {
                    Label("Scan Now", systemImage: "camera.viewfinder")
                        .font(.headline)
                        .padding()
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.bordered)
                .tint(.indigo)
                .disabled(overlayManager.remainingManualScans <= 0 && !PaywallStore.shared.isSubscribed)
            }
        }
    }
    
    private var quotaDisplay: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Free usage this month")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            HStack {
                quotaBadge(
                    title: "Auto",
                    value: "\(overlayManager.remainingAutoMinutes)m / 25m"
                )
                quotaBadge(
                    title: "Manual",
                    value: "\(overlayManager.remainingManualScans) / 100"
                )
            }
        }
    }
    
    private func quotaBadge(title: String, value: String) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title)
                .font(.caption2)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.headline)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    
    private var statusDisplay: some View {
        VStack(spacing: 12) {
                if overlayManager.isActive {
                    Text("Overlay active")
                        .font(.headline)
                        .foregroundStyle(Color.green)
                    Text("Switch to your stream app to scan cards.")
                        .font(.caption)
                        .foregroundStyle(Color.secondary)
                }
                if overlayManager.backendUnreachable {
                backendStatusBadge(message: "Backend unreachable. Check Backend settings.", color: .orange, icon: "exclamationmark.triangle")
            }
            if overlayManager.isDetecting {
                backendStatusBadge(message: "Scanning...", color: .indigo, icon: "scope")
            }
            if let lastCard = overlayManager.lastCard {
                VStack(alignment: .leading, spacing: 4) {
                    HStack {
                        Text(lastCard.name)
                            .font(.headline)
                        Spacer()
                        if let score = lastCard.score {
                            Text(String(format: "%.0f%%", score * 100))
                                .font(.caption)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(scoreColor(score))
                                .clipShape(Capsule())
                        }
                    }
                    Text("\(lastCard.setCode ?? "") \(lastCard.localId ?? "") · \(lastCard.setName)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(lastCard.marketPrice)
                        .font(.title3)
                        .fontWeight(.semibold)
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color(.tertiarySystemBackground))
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
            if overlayManager.candidates.count > 1 {
                Text("Other possible matches")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                ForEach(Array(overlayManager.candidates.dropFirst().prefix(3))) { card in
                    HStack {
                        VStack(alignment: .leading, spacing: 2) {
                            Text(card.name)
                                .font(.subheadline)
                            Text("\(card.setCode ?? "") \(card.localId ?? "") · \(card.setName)")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if let score = card.score {
                            Text(String(format: "%.0f%%", score * 100))
                                .font(.caption)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(scoreColor(score).opacity(0.2))
                                .clipShape(Capsule())
                        }
                    }
                    .padding(.horizontal)
                }
            }
        }
    }
    
    private func backendStatusBadge(message: String, color: Color, icon: String) -> some View {
        HStack(spacing: 6) {
            Image(systemName: icon)
            Text(message)
        }
        .font(.caption)
        .foregroundStyle(color)
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(color.opacity(0.12))
        .clipShape(Capsule())
    }
    
    private func scoreColor(_ score: Double) -> Color {
        if score >= 0.95 { return .green }
        if score >= 0.90 { return .yellow }
        return .orange
    }
}
