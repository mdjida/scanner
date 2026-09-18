import Foundation

/// Loads a precomputed catalog_embeddings.json bundled with the app into shared app-group storage.
/// This avoids heavy on-device embedding computation for large card databases.
public final class CatalogBundleLoader {
    public static let shared = CatalogBundleLoader()

    private let catalogFileName = "catalog_embeddings.json"
    private let bundledVersionKey = "bundled_catalog_version"

    private init() {}

    /// Returns the app-group URL where the catalog is stored.
    public var localCatalogURL: URL {
        let base = FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: QuotaStore.suiteName)
        ?? FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first!
        return base.appendingPathComponent(catalogFileName)
    }

    /// Checks whether a catalog file already exists in app-group storage.
    public var hasLocalCatalog: Bool {
        FileManager.default.fileExists(atPath: localCatalogURL.path)
    }

    /// Copies the bundled catalog into app-group storage if it is newer or missing.
    /// Call once at app launch.
    public func loadBundledCatalogIfNeeded(bundle: Bundle = .main) {
        guard let bundledURL = bundle.url(forResource: catalogFileName, withExtension: nil) else {
            print("No bundled catalog found.")
            return
        }

        let fm = FileManager.default
        let localURL = localCatalogURL

        // If no local file, always copy.
        if !fm.fileExists(atPath: localURL.path) {
            copyCatalog(from: bundledURL, to: localURL)
            return
        }

        // Compare modification dates to decide whether to update.
        if let bundledAttrs = try? fm.attributesOfItem(atPath: bundledURL.path),
           let bundledDate = bundledAttrs[.modificationDate] as? Date,
           let localAttrs = try? fm.attributesOfItem(atPath: localURL.path),
           let localDate = localAttrs[.modificationDate] as? Date,
           bundledDate <= localDate {
            print("Local catalog is up to date.")
            return
        }

        copyCatalog(from: bundledURL, to: localURL)
    }

    /// Copies a catalog file to app-group storage and reloads the index.
    public func copyCatalog(from sourceURL: URL, to destinationURL: URL) {
        do {
            let fm = FileManager.default
            if fm.fileExists(atPath: destinationURL.path) {
                try fm.removeItem(at: destinationURL)
            }
            try fm.copyItem(at: sourceURL, to: destinationURL)
            print("Copied bundled catalog to \(destinationURL.path)")
            CatalogIndex.shared.loadFromDisk()
        } catch {
            print("Failed to copy bundled catalog: \(error)")
        }
    }
}
