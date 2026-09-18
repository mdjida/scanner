import SwiftUI
import Shared

struct BackendSettingsView: View {
    @State private var baseURL = BackendClient.shared.baseURL
    @State private var status = ""

    var body: some View {
        NavigationStack {
            VStack(spacing: 20) {
                Text("Backend Connection")
                    .font(.headline)
                Text("Point the app at your local backend (e.g. http://192.168.1.100:8000). Both devices must be on the same Wi-Fi network.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .multilineTextAlignment(.center)

                TextField("Backend URL", text: $baseURL)
                    .textFieldStyle(.roundedBorder)
                    .autocapitalization(.none)
                    .autocorrectionDisabled()

                Button(action: { testConnection() }) {
                    Label("Test Connection", systemImage: "network")
                        .padding()
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .tint(.indigo)

                if !status.isEmpty {
                    Text(status)
                        .font(.subheadline)
                        .foregroundStyle(status.contains("OK") ? .green : .red)
                }

                Spacer()
            }
            .padding()
            .navigationTitle("Backend")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Save") {
                        BackendClient.shared.baseURL = baseURL
                        status = "Saved"
                    }
                }
            }
        }
    }

    private func testConnection() {
        status = "Checking..."
        guard let url = URL(string: "\(baseURL)/health") else {
            status = "Invalid URL"
            return
        }
        var request = URLRequest(url: url)
        request.timeoutInterval = 5
        URLSession.shared.dataTask(with: request) { _, response, error in
            DispatchQueue.main.async {
                if let error = error {
                    status = "Failed: \(error.localizedDescription)"
                    return
                }
                if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                    status = "OK — backend is reachable"
                } else {
                    status = "Unexpected response"
                }
            }
        }.resume()
    }
}
