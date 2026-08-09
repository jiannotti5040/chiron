// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

/// The module catalog — a reader, and only a reader.
///
/// The screen this replaces could call any function it discovered, through a
/// Python dispatch shim embedded in the Swift source. That is why it is not
/// being restored in its original form: arbitrary module dispatch is
/// deliberately unavailable across this system, and the MCP server exposes a
/// reviewed static allowlist precisely so no surface can reach past it.
///
/// So there is no Run button here, and there is no code path that could
/// acquire one. What the vault can be asked to do lives in `WorkspaceView`,
/// `AttestView`, and `GatesView`, all of which go through `VaultClient`.
struct ModulesView: View {
    let client: VaultClient

    @State private var manifest: ModuleManifest?
    @State private var loadError: String?
    @State private var query = ""
    @State private var selection: ModuleManifest.Script.ID?

    private var results: [ModuleManifest.Script] {
        manifest?.matching(query) ?? []
    }

    var body: some View {
        Group {
            if let loadError {
                ContentUnavailableView {
                    Label("No manifest", systemImage: "questionmark.folder")
                } description: {
                    Text(loadError)
                    Text("Regenerate it with `python3 Chiron/build_manifest.py`.")
                        .font(.caption.monospaced())
                }
            } else if let manifest {
                content(manifest)
            } else {
                ProgressView().task { load() }
            }
        }
        .navigationTitle("Modules")
    }

    private func content(_ manifest: ModuleManifest) -> some View {
        VStack(alignment: .leading, spacing: 0) {
            summaryBar(manifest.summary)
            Divider()
            List(results, selection: $selection) { script in
                row(script)
            }
            .searchable(text: $query, prompt: "Filter modules")
        }
        .safeAreaInset(edge: .bottom) { provenanceFooter(manifest) }
    }

    /// The counts come from the manifest, not from re-counting the rows. The
    /// deleted catalog computed its summary separately from the list it drew,
    /// which is how a header and its detail drift apart without anyone seeing.
    private func summaryBar(_ summary: ModuleManifest.Summary) -> some View {
        HStack(spacing: 18) {
            stat("\(summary.runnableScripts)", "runnable")
            stat("\(summary.withSelftest)", "carry a self-test")
            stat("\(summary.stdlibOnly)", "stdlib only")
            stat("\(summary.internalEdges)", "internal edges")
            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 9)
    }

    private func stat(_ value: String, _ label: String) -> some View {
        VStack(alignment: .leading, spacing: 1) {
            Text(value).font(.title3.monospacedDigit().weight(.semibold))
            Text(label).font(.caption2).foregroundStyle(.secondary)
        }
    }

    private func row(_ script: ModuleManifest.Script) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            HStack(spacing: 8) {
                Text(script.script).font(.callout.monospaced().weight(.medium))
                if script.hasSelftest {
                    Label("self-test", systemImage: "checkmark.seal")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .labelStyle(.titleAndIcon)
                }
                if !script.stdlibOnly {
                    // Surfaced rather than hidden: a third-party import is a
                    // dependency-surface fact, not a detail.
                    Label("third-party import", systemImage: "shippingbox")
                        .font(.caption2)
                        .foregroundStyle(.orange)
                }
                Spacer()
                Text("\(script.lines) lines")
                    .font(.caption2.monospacedDigit())
                    .foregroundStyle(.tertiary)
            }
            if let title = script.title {
                Text(title).font(.caption.weight(.medium)).foregroundStyle(.secondary)
            }
            if let purpose = script.purpose {
                Text(purpose).font(.caption).foregroundStyle(.secondary).lineLimit(2)
            }
            if selection == script.id, let lens = script.lens {
                lensDetail(lens, imports: script.imports)
            }
        }
        .padding(.vertical, 2)
    }

    private func lensDetail(_ lens: ModuleManifest.Script.Lens,
                            imports: [String]) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            if let math = lens.math { labelled("math", math) }
            if let prog = lens.prog { labelled("code", prog) }
            if let concept = lens.concept { labelled("idea", concept) }
            if !imports.isEmpty {
                labelled("imports", imports.joined(separator: ", "))
            }
        }
        .padding(.top, 4)
        .padding(.leading, 10)
    }

    private func labelled(_ key: String, _ value: String) -> some View {
        HStack(alignment: .top, spacing: 6) {
            Text(key)
                .font(.caption2.monospaced())
                .foregroundStyle(.tertiary)
                .frame(width: 46, alignment: .leading)
            Text(value).font(.caption2).foregroundStyle(.secondary)
        }
    }

    /// Says where this came from and when. A catalog that cannot be dated is
    /// a catalog that can quietly go stale.
    private func provenanceFooter(_ manifest: ModuleManifest) -> some View {
        HStack(spacing: 6) {
            Image(systemName: "doc.text.magnifyingglass").font(.caption2)
            Text("Read from Chiron/manifest.json"
                 + (manifest.generatedUTC.map { ", generated \($0)" } ?? "")
                 + " · this screen reads; it cannot run a module.")
                .font(.caption2)
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 7)
        .background(.thinMaterial)
    }

    private func load() {
        do {
            manifest = try ModuleManifest.load(vaultRoot: client.vaultRoot)
        } catch {
            loadError = String(describing: error)
        }
    }
}
