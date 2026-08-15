// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironContract
import ChironService
import UniformTypeIdentifiers

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

    /// A quarter-close summary with one wrong figure in it. Two claims check
    /// out and the third does not: 3 percent of 1,240 is 37.2, not 38. That is
    /// the kind of rounding a reader skims past, which is the point of opening
    /// with it rather than with arithmetic nobody would get wrong.
    @State private var text = """
        Q3 close. We shipped 1,240 units at 25 dollars each is 31,000 in \
        product revenue. 31,000 plus 2,180 is 33,180 invoiced. \
        Returns ran at 3 percent of 1,240, or 38 units.
        """
    @State private var factsJSON = #"{"gross_margin": {"value": 74, "unit": "percent"}}"#
    @State private var useFacts = true
    /// A worked example, not filler. This ledger carries an exact pricing law
    /// and one row that breaks it, so the first thing anyone sees the engine
    /// do is find a rule nobody told it about and point at the bad row.
    @State private var tableJSON = """
        [{"units":3,"price":25,"ship":10,"total":85},
         {"units":4,"price":25,"ship":11,"total":111},
         {"units":5,"price":25,"ship":12,"total":137},
         {"units":6,"price":25,"ship":10,"total":160},
         {"units":7,"price":25,"ship":11,"total":186},
         {"units":8,"price":25,"ship":12,"total":212},
         {"units":9,"price":25,"ship":10,"total":235},
         {"units":10,"price":25,"ship":11,"total":261},
         {"units":11,"price":25,"ship":12,"total":287},
         {"units":12,"price":25,"ship":10,"total":360},
         {"units":13,"price":25,"ship":11,"total":336},
         {"units":14,"price":25,"ship":12,"total":362}]
        """
    @State private var targetColumn = "total"
    @State private var inputColumns = "units, price, ship"
    @State private var unknownColumn = "units"
    @State private var targetValue = "337"
    @State private var operation: LocalServiceOperation = .ingest
    @State private var record: LocalServiceRecord?
    @State private var failure: String?
    @State private var running = false
    @State private var importing = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    thesis
                    operationPicker
                    if operation.takesTable { tableFields } else { documentField }
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
            // Security-scoped, user-selected, and read through the same
            // bounded, strict-UTF-8 reader the certify screen uses. Nothing is
            // uploaded: the file becomes text in this field and goes only
            // where the operator then sends it.
            .fileImporter(isPresented: $importing,
                          allowedContentTypes: [.plainText, .text, .data,
                                                .commaSeparatedText, .json],
                          allowsMultipleSelection: false) { outcome in
                switch outcome {
                case .success(let urls):
                    guard let url = urls.first else { return }
                    let scoped = url.startAccessingSecurityScopedResource()
                    defer { if scoped { url.stopAccessingSecurityScopedResource() } }
                    do { text = try ServiceTextInput.read(from: url) }
                    catch { failure = String(describing: error) }
                case .failure(let error):
                    failure = String(describing: error)
                }
            }
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
            HStack {
                Text(operation == .ingest ? "Anything — text, CSV, or JSON records"
                                          : "Document")
                    .font(.subheadline.weight(.medium))
                Spacer()
                Button {
                    importing = true
                } label: {
                    Label("Import…", systemImage: "doc.badge.plus").font(.caption)
                }
                .buttonStyle(.plain)
            }
            TextEditor(text: $text)
                .font(.system(.callout, design: .monospaced))
                .frame(minHeight: 110)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
        }
    }

    private var tableFields: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Table — rows as JSON objects")
                .font(.subheadline.weight(.medium))
            TextEditor(text: $tableJSON)
                .font(.system(.caption2, design: .monospaced))
                .frame(minHeight: 140)
                .overlay(RoundedRectangle(cornerRadius: 8).stroke(.quaternary))
            HStack(spacing: 8) {
                labelled("target", $targetColumn)
                labelled("inputs", $inputColumns)
            }
            if operation == .solveFor {
                HStack(spacing: 8) {
                    labelled("solve for", $unknownColumn)
                    labelled("target value", $targetValue)
                }
            }
            Text("""
                The law is solved on the first few rows and then has to hold on \
                every row it never saw. Change one total and watch it move from \
                VERIFIED to PARTIAL with that row named.
                """)
                .font(.caption2)
                .foregroundStyle(.secondary)
        }
    }

    private func labelled(_ title: String, _ binding: Binding<String>) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title).font(.caption2).foregroundStyle(.secondary)
            TextField(title, text: binding)
                .textFieldStyle(.roundedBorder)
                .font(.system(.caption, design: .monospaced))
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
            if let status = record.record.objectValue?["status"]?.stringValue {
                statusBadge(status)
            }
            if let counts = record.dispositionCounts {
                dispositionRow(counts)
            }
            ForEach(record.headlines, id: \.self) { line in
                Text(line)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }
            if !record.nextSteps.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("What you can do with this")
                        .font(.caption.weight(.semibold))
                    ForEach(record.nextSteps, id: \.operation) { step in
                        nextStepRow(step)
                    }
                }
                .padding(.top, 2)
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

    /// A next step the engine said is meaningful for *this* invariant. One it
    /// refused to offer is shown too, greyed, with the reason — an operation
    /// that must not run is more informative than a hidden one.
    @ViewBuilder
    private func nextStepRow(_ step: LocalServiceRecord.NextStep) -> some View {
        if step.available, let op = LocalServiceOperation(rawValue: step.operation) {
            Button {
                operation = op
                record = nil
                failure = nil
            } label: {
                HStack(alignment: .top, spacing: 6) {
                    Image(systemName: "arrow.right.circle.fill").font(.caption)
                    VStack(alignment: .leading, spacing: 1) {
                        Text(op.title).font(.caption.weight(.medium))
                        Text(step.why).font(.caption2).foregroundStyle(.secondary)
                            .multilineTextAlignment(.leading)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .buttonStyle(.plain)
        } else {
            HStack(alignment: .top, spacing: 6) {
                Image(systemName: "nosign").font(.caption).foregroundStyle(.orange)
                VStack(alignment: .leading, spacing: 1) {
                    Text(step.operation).font(.caption.weight(.medium))
                        .foregroundStyle(.secondary)
                    Text(step.why).font(.caption2).foregroundStyle(.secondary)
                }
            }
        }
    }

    /// The engine's word, verbatim. PARTIAL gets its own colour because it is
    /// its own disposition — not a softened VERIFIED.
    private func statusBadge(_ status: String) -> some View {
        let tint: Color = switch status {
        case "VERIFIED": .green
        case "REFUTED": .red
        case "PARTIAL": .orange
        default: .secondary
        }
        return Text(status)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 10).padding(.vertical, 5)
            .background(tint.opacity(0.18), in: Capsule())
            .foregroundStyle(tint)
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
        let table = tableJSON
        let target = targetColumn.trimmingCharacters(in: .whitespaces)
        let inputs = inputColumns.split(separator: ",")
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
        let unknown = unknownColumn.trimmingCharacters(in: .whitespaces)
        let wanted = targetValue.trimmingCharacters(in: .whitespaces)
        Task {
            defer { running = false }
            do {
                var arguments = op.arguments(document: document, facts: facts)
                if op.takesTable {
                    guard let rows = JSONValue.decode(table),
                          rows.arrayValue != nil else {
                        failure = "The table must be a JSON array of row objects."
                        return
                    }
                    if op == .discoverMap {
                        // Until the workbench carries two tables, a single
                        // table is mapped against itself: every column maps to
                        // itself by the identity law. Honest, and it shows the
                        // shape of the answer without pretending to compare
                        // two things the screen never asked for.
                        arguments = ["source": rows, "destination": rows]
                    } else {
                        arguments = ["rows": rows, "target": .string(target)]
                        if !inputs.isEmpty {
                            arguments["inputs"] = .array(inputs.map { .string($0) })
                        }
                        if op == .solveFor {
                            arguments["unknown"] = .string(unknown)
                            arguments["target_value"] =
                                JSONValue.decode(wanted) ?? .string(wanted)
                            arguments["known"] = .object([:])
                        }
                    }
                }
                let client = try makeClient()
                record = try await client.invoke(op, arguments: arguments)
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

extension LocalServiceRecord {
    struct NextStep: Sendable {
        let operation: String
        let why: String
        /// False when the engine deliberately declined to offer it.
        let available: Bool
    }

    /// The operations the engine said are meaningful for this result.
    var nextSteps: [NextStep] {
        (record.objectValue?["next"]?.arrayValue ?? []).compactMap { entry in
            guard let object = entry.objectValue,
                  let operation = object["operation"]?.stringValue,
                  let why = object["why"]?.stringValue else { return nil }
            let available = !(object["arguments"]?.isNull ?? true)
            return NextStep(operation: operation, why: why, available: available)
        }
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
        // The status already has its own badge; repeating it as a sentence
        // only added noise, and "campaign status" was borrowed wording from
        // solve that made no sense for a relation.

        if let missing = object["counts"]?.objectValue?["actionable_now"]?.intValue,
           missing > 0 {
            lines.append("\(missing) refusal(s) can be resolved by supplying named evidence")
        }
        if let law = object["law"]?.stringValue {
            lines.insert("law: " + law, at: 0)
        }
        if let anomalies = object["anomalous_rows"]?.arrayValue, !anomalies.isEmpty {
            lines.append("rows inconsistent with that law: "
                         + anomalies.compactMap { $0.intValue.map(String.init) }
                             .joined(separator: ", "))
        }
        if let held = object["held_out_rows"]?.intValue {
            lines.append("confirmed on \(held) row(s) the solver never saw")
        }
        if let solutions = object["solutions"]?.arrayValue, !solutions.isEmpty {
            lines.append("solution: "
                         + solutions.compactMap { $0.stringValue }.joined(separator: ", "))
        }
        if let note = object["note"]?.stringValue { lines.append(note) }
        return lines
    }
}
