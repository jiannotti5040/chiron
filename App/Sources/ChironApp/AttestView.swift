// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

private struct Candidate: Identifiable {
    let id = UUID()
    var name: String
    var text: String
}

struct AttestView: View {
    let client: VaultClient

    @State private var output = "The depot holds 4200 gallons. Burn rate is 1400 "
        + "gallons per day. Resupply is not required at this time."
    @State private var candidates: [Candidate] = [
        Candidate(name: "logistics_report",
                  text: "Depot BRAVO inventory: 4200 gallons diesel. Daily consumption 1400 gallons."),
    ]
    @State private var record: AttestationRecord?
    @State private var running = false
    @State private var errorText: String?

    var body: some View {
        HSplitView {
            VStack(alignment: .leading, spacing: 10) {
                Text("The output to attest")
                    .font(.headline)
                TextEditor(text: $output)
                    .font(.body)
                    .frame(minHeight: 90)
                    .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(.quaternary))

                HStack {
                    Text("Candidate inputs")
                        .font(.headline)
                    Spacer()
                    Button {
                        candidates.append(Candidate(name: "input_\(candidates.count + 1)", text: ""))
                    } label: {
                        Image(systemName: "plus")
                    }
                }
                List {
                    ForEach($candidates) { $c in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                TextField("name", text: $c.name)
                                    .font(.system(.callout, design: .monospaced))
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 180)
                                Spacer()
                                Button(role: .destructive) {
                                    candidates.removeAll { $0.id == c.id }
                                } label: {
                                    Image(systemName: "trash")
                                }
                                .buttonStyle(.borderless)
                            }
                            TextEditor(text: $c.text)
                                .font(.callout)
                                .frame(height: 60)
                                .overlay(RoundedRectangle(cornerRadius: 4).strokeBorder(.quaternary))
                        }
                        .padding(.vertical, 3)
                    }
                }
                .listStyle(.inset)

                HStack {
                    Button {
                        run()
                    } label: {
                        Label("Attest", systemImage: "text.magnifyingglass")
                    }
                    .keyboardShortcut(.return, modifiers: .command)
                    .disabled(running || output.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    if running { ProgressView().controlSize(.small) }
                }
                // The module's own contract, stated where the user acts on it.
                Text("Attribution is relative to the candidate inputs you supply. "
                     + "With none, the honest answer is REFUSED. This tool never "
                     + "reports a probability that text is machine-written — that "
                     + "measurement does not exist.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding()
            .frame(minWidth: 380)

            VStack(alignment: .leading, spacing: 10) {
                if let errorText { ErrorBanner(text: errorText) }
                if let r = record {
                    HStack(spacing: 8) {
                        StatTile(title: "traceable words", value: percent(r.traceableWordFraction))
                        StatTile(title: "machine-warranted", value: percent(r.machineWarranted))
                        StatTile(title: "human-owned", value: percent(r.humanOwned))
                        if let counts = r.counts {
                            ForEach(counts.keys.sorted(), id: \.self) { k in
                                StatTile(title: k, value: "\(counts[k] ?? 0)")
                            }
                        }
                    }
                    List(Array(r.spans.enumerated()), id: \.offset) {
                        SpanRow(span: $0.element)
                    }
                    .listStyle(.inset)
                } else {
                    ContentUnavailableView(
                        "No attestation yet",
                        systemImage: "text.magnifyingglass",
                        description: Text("Each span of the output is attributed to what "
                            + "actually caused it — or handed back REFUSED, intact."))
                }
            }
            .padding()
            .frame(minWidth: 380)
        }
    }

    private func run() {
        running = true
        errorText = nil
        let out = output
        // Two candidates can carry the same name — the fields are free text.
        // Last one wins rather than trapping, which uniqueKeysWithValues would.
        let inputs = candidates
            .filter { !$0.text.isEmpty && !$0.name.isEmpty }
            .reduce(into: [String: String]()) { $0[$1.name] = $1.text }
        Task {
            defer { running = false }
            do { record = try await client.attest(output: out, inputs: inputs) }
            catch { errorText = error.localizedDescription; record = nil }
        }
    }
}

private struct SpanRow: View {
    let span: AttestSpan

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                VerdictBadge(verdict: span.verdict)
                if let owner = span.owner {
                    Text(owner)
                        .font(.caption)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(.quaternary.opacity(0.5), in: Capsule())
                }
                Spacer()
                if let frac = span.traceableFraction {
                    Text("traceable \(percent(frac))")
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.tertiary)
                }
            }
            Text(span.text)
                .textSelection(.enabled)
            if let origin = span.origin {
                Text("closest input: \(origin)"
                     + (span.originDelta.map { String(format: " · Δ %.3f", $0) } ?? ""))
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
            }
            if let reason = span.reason {
                Text(reason)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if let novel = span.novelContentWords, !novel.isEmpty {
                Text("novel: \(novel.joined(separator: ", "))")
                    .font(.caption)
                    .foregroundStyle(.orange)
                    .lineLimit(2)
            }
        }
        .padding(.vertical, 4)
    }
}
