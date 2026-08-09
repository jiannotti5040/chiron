// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironContract
import ChironService

/// The workbench: one document, every operation the vault can perform on it.
///
/// What this replaces was a single certify field. That screen was honest but
/// it taught the wrong thing — it implied the system checks arithmetic. The
/// system's actual claim is larger and harder: it will tell you what it can
/// prove, what it cannot, *why* the refusals happened, and what to go get to
/// resolve them. None of that was reachable from a device until the service
/// exposed the whole dispatch.
///
/// The design rule here is the same one the engines keep: **never paraphrase a
/// verdict.** The record is rendered as the engine returned it. A summary line
/// above it is allowed to count, never to soften — no screen in this app can
/// turn a REFUSED into "inconclusive" or a REFUTED into "needs review".
struct WorkbenchView: View {
    /// Built per run from the stored endpoint, exactly as the certify screen
    /// does, so both surfaces honour the same configuration and the same
    /// Keychain-bound token.
    let makeClient: () throws -> LocalServiceClient

    @State private var text = """
        Revenue grew to 4.2 million in Q3. \
        The sum of 2 and 2 is 4. The product of 3 and 4 is 11.
        """
    @State private var factsJSON = #"{"gross_margin": {"value": 74, "unit": "percent"}}"#
    @State private var useFacts = true
    @State private var operation: LocalServiceOperation = .certify
    @State private var record: LocalServiceRecord?
    @State private var failure: String?
    @State private var running = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    thesis
                    operationPicker
                    documentField
                    if operation.usesFacts { factsField }
                    runRow
                    if let failure {
                        Label(failure, systemImage: "exclamationmark.triangle")
                            .font(.caption)
                            .foregroundStyle(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(10)
                            .background(.red.opacity(0.10),
                                        in: RoundedRectangle(cornerRadius: 8))
                    }
                    if let record { resultSection(record) }
                }
                .padding()
            }
            .navigationTitle("Chiron")
        }
    }

    // MARK: - The idea, stated once and plainly

    private var thesis: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("It will not guess, and it will tell you what it needs.")
                .font(.headline)
            Text("""
                Every result below is one of VERIFIED, REFUTED, or REFUSED. \
                A refusal is an answer, not a gap — and where one can be \
                resolved, the vault names the exact evidence that would \
                resolve it.
                """)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 10))
    }

    private var operationPicker: some View {
        VStack(alignment: .leading, spacing: 6) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 8) {
                    ForEach(LocalServiceOperation.workbench, id: \.self) { op in
                        Button {
                            operation = op
                            record = nil
                            failure = nil
                        } label: {
                            Text(op.title)
                                .font(.subheadline.weight(operation == op ? .semibold : .regular))
                                .padding(.horizontal, 12).padding(.vertical, 7)
                                .background(operation == op ? Color.accentColor.opacity(0.18)
                                                            : Color.secondary.opacity(0.12),
                                            in: Capsule())
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
            // The engine's own description, so the app cannot oversell an
            // operation the vault describes more carefully.
            Text(operation.summary)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var documentField: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("Document").font(.subheadline.weight(.medium))
            TextEditor(text: $text)
                .font(.system(.callout, design: .monospaced))
                .frame(minHeight: 110)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
        }
    }

    private var factsField: some View {
        VStack(alignment: .leading, spacing: 4) {
            Toggle(isOn: $useFacts) {
                Text("Supply ground truth").font(.subheadline.weight(.medium))
            }
            if useFacts {
                TextEditor(text: $factsJSON)
                    .font(.system(.caption, design: .monospaced))
                    .frame(minHeight: 62)
                    .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
                Text("""
                    Without these, a claim whose truth lives outside the \
                    sentence REFUSES — there is nothing to check it against. \
                    Turn this off to see that happen.
                    """)
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private var runRow: some View {
        HStack(spacing: 10) {
            Button {
                run()
            } label: {
                Label(running ? "Running…" : operation.title,
                      systemImage: "play.fill")
            }
            .buttonStyle(.borderedProminent)
            .disabled(running || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            if running { ProgressView().controlSize(.small) }
            Spacer()
        }
    }

    // MARK: - Results

    @ViewBuilder
    private func resultSection(_ record: LocalServiceRecord) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            if let counts = record.dispositionCounts {
                dispositionRow(counts)
            }
            ForEach(record.headlines, id: \.self) { line in
                Text(line)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            DisclosureGroup("The record, as the engine returned it") {
                Text(record.prettyJSON)
                    .font(.system(.caption2, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            .font(.caption)
            Text("schema \(record.schema ?? "—") · request \(record.envelope.requestID.prefix(12))…")
                .font(.caption2.monospaced())
                .foregroundStyle(.tertiary)
        }
        .padding(12)
        .background(.quaternary.opacity(0.25), in: RoundedRectangle(cornerRadius: 10))
    }

    /// Counts only. The badge colours are the engine's three words, and there
    /// is no fourth bucket into which an awkward result could be filed.
    private func dispositionRow(_ counts: (verified: Int, refuted: Int, refused: Int)) -> some View {
        HStack(spacing: 8) {
            badge("VERIFIED", counts.verified, .green)
            badge("REFUTED", counts.refuted, .red)
            badge("REFUSED", counts.refused, .orange)
            Spacer()
        }
    }

    private func badge(_ label: String, _ count: Int, _ tint: Color) -> some View {
        HStack(spacing: 4) {
            Text("\(count)").font(.caption.monospacedDigit().weight(.semibold))
            Text(label).font(.caption2)
        }
        .padding(.horizontal, 9).padding(.vertical, 5)
        .background(tint.opacity(count > 0 ? 0.18 : 0.06), in: Capsule())
        .foregroundStyle(count > 0 ? tint : .secondary)
    }

    private func run() {
        running = true
        failure = nil
        record = nil
        let op = operation
        let document = text
        let facts = useFacts ? factsJSON : nil
        Task {
            defer { running = false }
            do {
                let client = try makeClient()
                record = try await client.invoke(op, arguments: op.arguments(
                    document: document, facts: facts))
            } catch {
                failure = String(describing: error)
            }
        }
    }
}

private extension LocalServiceOperation {
    var usesFacts: Bool { self == .certify || self == .falsifiers || self == .proposeExperiment }

    /// Build the argument object each operation expects.
    ///
    /// Surface-shaped operations get the document as a surface; text-shaped
    /// ones get it as text. Nothing here reinterprets a result — only routes
    /// the same document to the argument name the engine declared.
    func arguments(document: String, facts: String?) -> [String: JSONValue] {
        var args: [String: JSONValue] = [:]
        switch self {
        case .collapse, .trace, .solve, .explore:
            args["surface"] = .string(document)
        case .attest:
            args["output"] = .string(document)
        case .compare:
            args["a"] = .string(document)
            args["b"] = .string(document)
        default:
            args["text"] = .string(document)
        }
        if usesFacts, let facts, let parsed = JSONValue.decode(facts) {
            args["facts"] = parsed
        }
        return args
    }
}

private extension LocalServiceRecord {
    /// Counts pulled from whichever shape the engine used, or nil when the
    /// record has no dispositions to count. Never synthesised.
    var dispositionCounts: (verified: Int, refuted: Int, refused: Int)? {
        guard let object = record.objectValue else { return nil }
        if let counts = object["counts"]?.objectValue,
           let v = counts["verified"]?.intValue,
           let rf = counts["refuted"]?.intValue,
           let rs = counts["refused"]?.intValue {
            return (v, rf, rs)
        }
        if let spans = object["spans"]?.arrayValue {
            var v = 0, rf = 0, rs = 0
            for span in spans {
                switch span.objectValue?["verdict"]?.stringValue {
                case "VERIFIED": v += 1
                case "REFUTED": rf += 1
                case "REFUSED": rs += 1
                default: break
                }
            }
            return (v, rf, rs)
        }
        return nil
    }

    /// One or two lines that state what the engine said, quoting its own
    /// fields. Adds no interpretation of its own.
    var headlines: [String] {
        guard let object = record.objectValue else { return [] }
        var lines: [String] = []
        if let verdict = object["verdict"]?.stringValue { lines.append(verdict) }
        if let coverage = object["coverage"]?.doubleValue {
            lines.append(String(format: "coverage %.1f%% of the input was checkable",
                                coverage * 100))
        }
        if let status = object["status"]?.stringValue {
            lines.append("campaign status: \(status)")
        }
        if let missing = object["counts"]?.objectValue?["actionable_now"]?.intValue,
           missing > 0 {
            lines.append("\(missing) refusal(s) can be resolved by supplying named evidence")
        }
        if let note = object["note"]?.stringValue { lines.append(note) }
        return lines
    }
}
