// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

struct FullStackView: View {
    let client: VaultClient

    @State private var text = FullStackView.sample
    @State private var record: FullStackRecord?
    @State private var running = false
    @State private var errorText: String?
    @State private var inputFile: FileLoad.Loaded?

    static let sample = "The archive holds 4200 records and 1400 were revised "
        + "this quarter, so three in ten changed. Sequence: 1, 4, 9, 16, 25."

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(Screen.fullStack.subtitle)
                .foregroundStyle(.secondary)
            TextEditor(text: $text)
                .font(.body)
                .frame(height: 110)
                .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(.quaternary))
                .acceptsFileDrop(text: $text,
                                 onLoad: { inputFile = $0 },
                                 onError: { errorText = $0 })
            FileLoadBar(label: "Analyse a file…", text: $text,
                        onLoad: { inputFile = $0 })
            if let inputFile { FileLoadWarning(loaded: inputFile) }
            HStack {
                Button {
                    run()
                } label: {
                    Label("Run the stack", systemImage: "play.fill")
                }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(running || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                if running { ProgressView().controlSize(.small) }
                Spacer()
                if let r = record {
                    Text("\(r.stagesRun) stages · \(Int(r.elapsedMs)) ms")
                        .font(.callout.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
            }
            if let errorText { ErrorBanner(text: errorText) }
            if let r = record {
                HStack(spacing: 8) {
                    ForEach(r.tally.keys.sorted(), id: \.self) { k in
                        StatTile(title: k, value: "\(r.tally[k] ?? 0)")
                    }
                    if !r.numericSurface.isEmpty {
                        StatTile(title: "numeric surface",
                                 value: r.numericSurface.map(String.init).joined(separator: " "))
                    }
                }
                ResultsList(results: r.results)
            } else if !running {
                ContentUnavailableView(
                    "No record yet",
                    systemImage: "square.stack.3d.up",
                    description: Text("Run the stack to see every applicable module's answer. "
                        + "SKIPPED and ERROR are reported, never hidden."))
            }
            Spacer(minLength: 0)
        }
        .padding()
    }

    private func run() {
        running = true
        errorText = nil
        let input = text
        Task {
            defer { running = false }
            do { record = try await client.fullStack(text: input) }
            catch { errorText = error.localizedDescription; record = nil }
        }
    }
}

private struct ResultsList: View {
    let results: [StageResult]

    // Stages arrive shallow-to-deep; group consecutively so the reading
    // order stays the vault's order.
    // Position in the record is the identity: the stage table can legitimately
    // repeat a module.fn pair, and the reading order is the vault's order.
    private var groups: [(offset: Int, layer: String, stages: [(Int, StageResult)])] {
        var out: [(Int, String, [(Int, StageResult)])] = []
        for (i, r) in results.enumerated() {
            if let last = out.indices.last, out[last].1 == r.layer {
                out[last].2.append((i, r))
            } else {
                out.append((i, r.layer, [(i, r)]))
            }
        }
        return out
    }

    var body: some View {
        List {
            ForEach(groups, id: \.offset) { group in
                Section(group.layer.uppercased()) {
                    ForEach(group.stages, id: \.0) { StageRow(stage: $0.1) }
                }
            }
        }
        .listStyle(.inset)
    }
}

private struct StageRow: View {
    let stage: StageResult
    @State private var expanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $expanded) {
            if let result = stage.result {
                JSONDetail(value: result)
                    .frame(maxHeight: 260)
            } else {
                Text(stage.reason ?? stage.error ?? "no result payload")
                    .font(.callout)
                    .foregroundStyle(.secondary)
            }
        } label: {
            HStack(spacing: 8) {
                StatusIcon(status: stage.status)
                VStack(alignment: .leading, spacing: 1) {
                    Text("\(stage.module).\(stage.fn)")
                        .font(.system(.body, design: .monospaced))
                    Text(annotation)
                        .font(.caption)
                        .foregroundStyle(stage.status == .error ? .red : .secondary)
                        .lineLimit(2)
                }
                Spacer()
                if let ms = stage.ms {
                    Text("\(Int(ms)) ms")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.tertiary)
                }
            }
        }
    }

    private var annotation: String {
        if stage.status == .skipped, let reason = stage.reason {
            return "skipped: \(reason)"
        }
        if stage.status == .error, let error = stage.error {
            return error
        }
        return stage.asks
    }
}
