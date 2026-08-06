// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

struct ModulesView: View {
    let client: VaultClient

    @State private var catalog: ModuleCatalog?
    @State private var loading = false
    @State private var errorText: String?
    @State private var search = ""
    @State private var selected: String?

    private var filtered: [ModuleInfo] {
        guard let catalog else { return [] }
        let q = search.trimmingCharacters(in: .whitespaces).lowercased()
        guard !q.isEmpty else { return catalog.modules }
        return catalog.modules.filter {
            $0.name.lowercased().contains(q)
                || ($0.doc ?? "").lowercased().contains(q)
                || $0.functions.contains { f in f.name.lowercased().contains(q) }
        }
    }

    var body: some View {
        HSplitView {
            VStack(alignment: .leading, spacing: 8) {
                if let catalog {
                    Text("\(catalog.importedCount) of \(catalog.modules.count) modules import clean · "
                         + "\(catalog.entrypointCount) entrypoints")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                TextField("Filter modules and functions", text: $search)
                    .textFieldStyle(.roundedBorder)
                if loading { ProgressView("Reading the vault…").controlSize(.small) }
                if let errorText { ErrorBanner(text: errorText) }
                List(filtered, selection: $selected) { m in
                    HStack(spacing: 6) {
                        Image(systemName: m.status == "OK"
                              ? "cube.fill" : "exclamationmark.triangle.fill")
                            .foregroundStyle(m.status == "OK" ? Color.secondary : Color.red)
                        VStack(alignment: .leading, spacing: 1) {
                            Text(m.name).font(.system(.body, design: .monospaced))
                            Text(m.status == "OK"
                                 ? "\(m.functions.count) entrypoints"
                                 : (m.error ?? "import failed"))
                                .font(.caption)
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                        }
                    }
                    .tag(m.name)
                }
                .listStyle(.inset)
            }
            .padding()
            .frame(minWidth: 260, idealWidth: 300)

            Group {
                if let m = catalog?.modules.first(where: { $0.name == selected }) {
                    ModuleDetail(client: client, module: m)
                } else {
                    ContentUnavailableView(
                        "Pick a module",
                        systemImage: "cube",
                        description: Text("Every module in Chiron/ is here, discovered by "
                            + "introspection. Add one to the folder and it appears — "
                            + "there is no list to edit."))
                }
            }
            .frame(minWidth: 420)
        }
        .task { await load() }
    }

    private func load() async {
        guard catalog == nil, !loading else { return }
        loading = true
        defer { loading = false }
        do { catalog = try await client.catalog() }
        catch { errorText = error.localizedDescription }
    }
}

private struct ModuleDetail: View {
    let client: VaultClient
    let module: ModuleInfo

    @State private var input = "The archive holds 4200 records, 1400 revised this quarter. "
        + "Sequence: 1, 4, 9, 16, 25."
    @State private var running: String?
    @State private var results: [String: ModuleCallResult] = [:]
    @State private var errors: [String: String] = [:]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(module.name).font(.title2.monospaced().weight(.semibold))
                if let doc = module.doc, !doc.isEmpty {
                    Text(doc).font(.callout).foregroundStyle(.secondary)
                }
                if module.status != "OK" {
                    ErrorBanner(text: module.error ?? "module failed to import")
                }
            }
            TextEditor(text: $input)
                .font(.callout)
                .frame(height: 64)
                .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(.quaternary))
            Text("Text entrypoints get this string. Surface entrypoints get the integers "
                 + "in it: \(VaultClient.numericSurface(of: input).map(String.init).joined(separator: " "))")
                .font(.caption)
                .foregroundStyle(.secondary)

            List(module.functions) { fn in
                FunctionRow(
                    fn: fn,
                    running: running == fn.name,
                    result: results[fn.name],
                    error: errors[fn.name],
                    onRun: { run(fn) })
            }
            .listStyle(.inset)
        }
        .padding()
    }

    private func run(_ fn: FunctionInfo) {
        running = fn.name
        errors[fn.name] = nil
        let text = input
        Task {
            defer { running = nil }
            do {
                results[fn.name] = try await client.call(
                    module: module.name, function: fn.name,
                    text: text, kind: fn.firstArgKind)
            } catch {
                errors[fn.name] = error.localizedDescription
                results[fn.name] = nil
            }
        }
    }
}

private struct FunctionRow: View {
    let fn: FunctionInfo
    let running: Bool
    let result: ModuleCallResult?
    let error: String?
    let onRun: () -> Void

    @State private var expanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack(spacing: 8) {
                VStack(alignment: .leading, spacing: 1) {
                    Text("\(fn.name)(\(fn.params.joined(separator: ", ")))")
                        .font(.system(.callout, design: .monospaced))
                        .lineLimit(1)
                    if let doc = fn.doc, !doc.isEmpty {
                        Text(doc).font(.caption).foregroundStyle(.secondary).lineLimit(2)
                    }
                }
                Spacer()
                if running {
                    ProgressView().controlSize(.small)
                } else if fn.isRunnable {
                    Button("Run", action: onRun)
                } else {
                    // Say why rather than silently hiding it — the vault's
                    // surface is bigger than what one input box can drive.
                    Text(fn.requiredArity > 1 ? "needs \(fn.requiredArity) args" : "not text/surface")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
            }
            if let error { ErrorBanner(text: error) }
            if let result {
                DisclosureGroup(isExpanded: $expanded) {
                    if let value = result.result {
                        JSONDetail(value: value).frame(maxHeight: 300)
                    } else {
                        Text(result.error ?? "no payload")
                            .font(.caption.monospaced())
                            .foregroundStyle(.red)
                            .textSelection(.enabled)
                    }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: result.status == "OK"
                              ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                            .foregroundStyle(result.status == "OK" ? .green : .red)
                        Text(result.status == "OK"
                             ? "returned in \(Int(result.ms ?? 0)) ms"
                             : (result.error ?? "error"))
                            .font(.caption)
                            .lineLimit(1)
                    }
                }
            }
        }
        .padding(.vertical, 3)
    }
}
