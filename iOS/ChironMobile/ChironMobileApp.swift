// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironService

@main
struct ChironMobileApp: App {
    var body: some Scene {
        WindowGroup {
            RootTabs()
        }
    }
}


/// Two surfaces over one service.
///
/// `Certify` is the narrow, single-purpose path someone can be handed with no
/// explanation. `Workbench` is the whole system: every operation the vault
/// exposes, over the same document, including the ones that explain a refusal
/// and say what to go get. Keeping both is deliberate — the narrow screen is
/// the demo, the workbench is the product.
struct RootTabs: View {
    var body: some View {
        TabView {
            ContentView()
                .tabItem { Label("Certify", systemImage: "checkmark.seal") }
            WorkbenchTab()
                .tabItem { Label("Workbench", systemImage: "square.grid.2x2") }
        }
    }
}


/// Reads the same stored endpoint the certify screen uses. Kept as its own
/// view so `@AppStorage` observes changes — a client captured once would keep
/// talking to a stale endpoint after the operator changed it.
private struct WorkbenchTab: View {
    @AppStorage("chiron.service.endpoint") private var endpointText = ""

    var body: some View {
        WorkbenchView(makeClient: {
            let endpoint = try ServiceEndpoint(text: endpointText).url
            return try LocalServiceClient(
                baseURL: endpoint,
                authorizer: LocalServiceAuthorizer(nextBearerToken: {
                    KeychainTokenStore.read(for: endpoint)
                }))
        })
    }
}
