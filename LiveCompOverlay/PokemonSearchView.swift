import SwiftUI
import Shared

struct PokemonSearchView: View {
    @State private var name = ""
    @State private var setId = ""
    @State private var localId = ""
    @State private var isSearching = false
    @State private var result: TCGdexSearchResult?
    @State private var errorMessage: String?

    var body: some View {
        NavigationStack {
            VStack(spacing: 16) {
                searchForm
                searchButton
                resultView
                Spacer()
            }
            .padding()
            .navigationTitle("Pokémon Search")
        }
    }

    private var searchForm: some View {
        VStack(spacing: 12) {
            TextField("Card name (e.g. Charizard)", text: $name)
                .textFieldStyle(.roundedBorder)
            TextField("Set code (optional, e.g. sv03.5)", text: $setId)
                .textFieldStyle(.roundedBorder)
            TextField("Card number (optional, e.g. 199)", text: $localId)
                .textFieldStyle(.roundedBorder)
            Text("Example: \"Charizard\" + set sv03.5 + number 199")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var searchButton: some View {
        Button(action: { Task { await search() } }) {
            Label(isSearching ? "Searching..." : "Search TCGdex", systemImage: "magnifyingglass")
                .font(.headline)
                .padding()
                .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .tint(.indigo)
        .disabled(isSearching || name.isEmpty)
    }

    @ViewBuilder
    private var resultView: some View {
        if let errorMessage = errorMessage {
            Text(errorMessage)
                .foregroundStyle(.red)
                .font(.subheadline)
        }

        switch result {
        case .exact(let card):
            if let normalized = PokemonCardResult(card: card) {
                VStack(alignment: .leading, spacing: 12) {
                    Text(normalized.name)
                        .font(.title2)
                        .fontWeight(.bold)
                    Text("\(normalized.setName) · \(normalized.localId)")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                    if let imageUrl = normalized.imageUrl, let url = URL(string: imageUrl) {
                        AsyncImage(url: url) { phase in
                            switch phase {
                            case .success(let image):
                                image.resizable().scaledToFit()
                            case .failure(_), .empty:
                                Rectangle().fill(Color.gray.opacity(0.2))
                            @unknown default:
                                EmptyView()
                            }
                        }
                        .frame(maxHeight: 250)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                    if let firstVariant = normalized.variants.first {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Variant: \(firstVariant.name)")
                                .font(.headline)
                            ForEach(Array(firstVariant.prices.prefix(5))) { price in
                                HStack {
                                    Text("\(price.priceType) · \(price.priceSource)")
                                        .font(.caption)
                                    Spacer()
                                    if let value = price.price {
                                        Text(String(format: "\(price.currency == "EUR" ? "€" : "$")%.2f", value))
                                            .font(.subheadline)
                                    }
                                }
                            }
                        }
                        .padding()
                        .background(Color(.secondarySystemBackground))
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    }
                }
            }
        case .multiple(let matches):
            VStack(alignment: .leading, spacing: 8) {
                Text("Multiple matches found")
                    .font(.headline)
                Text("Tap a card to view details")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                List(matches) { match in
                    VStack(alignment: .leading) {
                        Text(match.name)
                            .font(.headline)
                        Text("\(match.id) · #\(match.localId)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .listStyle(.plain)
            }
        case .noMatches:
            Text("No matches found on TCGdex.")
                .foregroundStyle(.secondary)
        case .none:
            EmptyView()
        }
    }

    private func search() async {
        isSearching = true
        errorMessage = nil
        result = nil
        do {
            result = try await TCGdexSearchService.shared.search(
                name: name,
                setId: setId.isEmpty ? nil : setId,
                localId: localId.isEmpty ? nil : localId
            )
        } catch {
            errorMessage = error.localizedDescription
        }
        isSearching = false
    }
}
