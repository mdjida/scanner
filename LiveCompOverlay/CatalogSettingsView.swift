import SwiftUI
import Shared

struct CatalogSettingsView: View {
    @State private var status = "Ready"
    @State private var isSyncing = false
    @State private var cardCount = 0

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                statusCard
                syncButton
                Spacer()
            }
            .padding()
            .navigationTitle("Catalog")
            .task {
                await loadSavedCatalog()
            }
        }
    }

    private var statusCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Catalog status")
                .font(.headline)
            Text(status)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("Cached cards: \(cardCount)")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var syncButton: some View {
        Button(action: { Task { await sync() } }) {
            Label(isSyncing ? "Syncing..." : "Sync Pokémon Catalog", systemImage: "arrow.clockwise")
                .font(.title3)
                .padding()
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .tint(.indigo)
        .disabled(isSyncing)
    }

    private func loadSavedCatalog() async {
        await CatalogIndex.shared.loadFromDisk()
        cardCount = CatalogIndex.shared.cardCount
        status = "Loaded saved catalog"
    }

    private func searchExample() async {
        status = "Searching..."
        do {
            let result = try await TCGdexSearchService.shared.search(name: "Charizard", setId: "sv03.5", localId: "199")
            switch result {
            case .exact(let card):
                status = "Found: \(card.name) from \(card.set?.name ?? "Unknown set")"
            case .multiple(let matches):
                status = "Multiple matches: \(matches.count)"
            case .noMatches:
                status = "No matches"
            }
        } catch {
            status = "Search failed: \(error.localizedDescription)"
        }
    }

    private func sync() async {
        isSyncing = true
        status = "Downloading from TCGdex..."
        do {
            // Limit to first 3 sets during early testing to keep sync fast.
            try await TCGdexCatalogImporter.shared.importCatalog(limitSets: 3)
            cardCount = CatalogIndex.shared.cardCount
            status = "Sync complete"
        } catch {
            status = "Sync failed: \(error.localizedDescription)"
        }
        isSyncing = false
    }
}
