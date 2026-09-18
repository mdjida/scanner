import SwiftUI
import Shared

@main
struct LiveCompOverlayApp: App {
    @UIApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    init() {
        CatalogBundleLoader.shared.loadBundledCatalogIfNeeded()
        CatalogIndex.shared.loadFromDisk()
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
