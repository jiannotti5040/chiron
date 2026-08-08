// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

struct CertifyView: View {
    let client: VaultClient

    @State private var text = "The sum of 2 and 2 is 4. The product of 3 and 4 is 11."
    @State private var cert: Certificate?
    @State private var running = false
    @State private var errorText: String?
    @State private var inputFile: FileLoad.Loaded?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(Screen.certify.subtitle)
                .foregroundStyle(.secondary)
            TextEditor(text: $text)
                .font(.body)
                .frame(height: 110)
                .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(.quaternary))
                .acceptsFileDrop(text: $text,
                                 onLoad: { inputFile = $0 },
                                 onError: { errorText = $0 })
            FileLoadBar(label: "Certify a file…", text: $text,
                        onLoad: { inputFile = $0 })
            if let inputFile { FileLoadWarning(loaded: inputFile) }
            HStack {
                Button {
                    run()
                } label: {
                    Label("Certify", systemImage: "checkmark.seal")
                }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(running || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                if running { ProgressView().controlSize(.small) }
                Spacer()
                if let e = cert?.engine {
                    Text("\(e.name) \(e.version)")
                        .font(.callout.monospaced())
                        .foregroundStyle(.secondary)
                }
            }
            if let errorText { ErrorBanner(text: errorText) }
            if let cert {
                HStack(spacing: 8) {
                    if let c = cert.counts {
                        StatTile(title: "checkable", value: "\(c.checkable)")
                        StatTile(title: "VERIFIED", value: "\(c.verified)")
                        StatTile(title: "REFUTED", value: "\(c.refuted)")
                        StatTile(title: "REFUSED", value: "\(c.refused)")
                    }
                    StatTile(title: "coverage", value: percent(cert.coverage))
                }
                List(Array(cert.claims.enumerated()), id: \.offset) {
                    ClaimRow(claim: $0.element)
                }
                .listStyle(.inset)
                if let verdict = cert.verdict {
                    Text(verdict)
                        .font(.callout)
                        .foregroundStyle(.secondary)
                        .textSelection(.enabled)
                }
            } else if !running {
                ContentUnavailableView(
                    "No certificate yet",
                    systemImage: "checkmark.seal",
                    description: Text("Primus certifies the exactly checkable claims and "
                        + "refuses to bless the rest. Free text is never scored."))
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
            do { cert = try await client.certify(text: input) }
            catch { errorText = error.localizedDescription; cert = nil }
        }
    }
}

private struct ClaimRow: View {
    let claim: Certificate.Claim

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                VerdictBadge(verdict: claim.status)
                Text(claim.kind)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Spacer()
            }
            Text(claim.text)
                .font(.system(.body, design: .monospaced))
                .textSelection(.enabled)
            HStack(spacing: 12) {
                if let op = claim.operation {
                    Text("operation: \(op)").font(.caption).foregroundStyle(.secondary)
                }
                if let expected = claim.expected {
                    Text("expected: \(expected.rendered())").font(.caption).foregroundStyle(.secondary)
                }
                if let reason = claim.reason ?? claim.detail {
                    Text(reason).font(.caption).foregroundStyle(.secondary)
                }
            }
        }
        .padding(.vertical, 3)
    }
}
