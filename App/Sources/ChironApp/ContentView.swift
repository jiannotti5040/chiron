// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

enum Screen: String, CaseIterable, Identifiable {
    case workspace = "Workspace"
    case attest = "Attest"
    case gates = "Gates"
    case modules = "Modules"

    var id: String { rawValue }

    var symbol: String {
        switch self {
        case .workspace: "rectangle.3.group"
        case .attest: "text.magnifyingglass"
        case .gates: "shield.checkerboard"
        case .modules: "square.grid.3x3"
        }
    }

    var subtitle: String {
        switch self {
        case .workspace: "One source, one full-stack record, one exact certificate"
        case .attest: "Which input produced each word"
        case .gates: "Run the vault's own selftests"
        case .modules: "Every module in the vault — read only"
        }
    }
}

struct ContentView: View {
    @Environment(AppModel.self) private var model
    @State private var screen: Screen = .workspace

    var body: some View {
        if let client = model.client {
            NavigationSplitView {
                List(Screen.allCases, selection: $screen) { s in
                    Label(s.rawValue, systemImage: s.symbol).tag(s)
                }
                .navigationSplitViewColumnWidth(min: 180, ideal: 200)
                .safeAreaInset(edge: .bottom) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Vault")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                        Text(client.vaultRoot.path)
                            .font(.caption2.monospaced())
                            .lineLimit(2)
                            .truncationMode(.head)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(8)
                }
            } detail: {
                switch screen {
                case .workspace: WorkspaceView(client: client)
                case .attest: AttestView(client: client)
                case .gates: GatesView(client: client)
                case .modules: ModulesView(client: client)
                }
            }
        } else {
            VaultSetupView()
        }
    }
}

struct VaultSetupView: View {
    @Environment(AppModel.self) private var model
    @State private var importing = false
    @State private var rejected = false

    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "shippingbox")
                .font(.system(size: 44))
                .foregroundStyle(.secondary)
            Text("Point Chiron at the vault")
                .font(.title2.weight(.semibold))
            Text("This app is a front end for the Portfolio Vault's own engines. "
                 + "Pick the repository root (the folder containing Chiron/ and Primus/), "
                 + "or set CHIRON_VAULT before launching.")
                .frame(maxWidth: 440)
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
            Button("Choose Vault Folder…") { importing = true }
                .keyboardShortcut(.defaultAction)
            if rejected {
                Text("That folder has no Chiron/full_stack.py — not a vault root.")
                    .font(.callout)
                    .foregroundStyle(.red)
            }
            if PythonRunner.locate() == nil {
                Text("No python3 found on this Mac. Install Python 3 (e.g. via Homebrew) "
                     + "or set CHIRON_PYTHON.")
                    .font(.callout)
                    .foregroundStyle(.red)
            }
        }
        .padding(40)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .fileImporter(isPresented: $importing,
                      allowedContentTypes: [.folder]) { result in
            if case .success(let url) = result {
                rejected = !model.setVault(url)
            }
        }
    }
}
