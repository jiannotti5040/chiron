// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import UniformTypeIdentifiers
import ChironKit

/// Ground truth the operator chooses, so grounded checking is reachable
/// without hand-writing JSON.
///
/// Every layer beneath this already carried a fact table — the engine, the
/// packaged CLI, the MCP tool, `VaultClient.certifyRaw(text:factsJSON:)` —
/// and none of it was usable from the app, which made the capability
/// theoretical for anyone who is not writing JSON by hand.
///
/// The two shapes a person actually has are a JSON object and a CSV export.
/// Both are accepted; nothing else is guessed at.
enum FactsSource {

    static let supportedTypes: [UTType] = [.json, .commaSeparatedText, .plainText]

    /// Bounded like every other read in this app. A fact table larger than
    /// this is a dataset, and a dataset belongs behind the service boundary
    /// rather than pasted into a desktop process.
    static let maxBytes = 4 * 1024 * 1024

    enum LoadError: LocalizedError, Equatable {
        case tooLarge(limit: Int)
        case notUTF8
        case unreadableJSON(String)
        case emptyCSV
        case csvMissingColumns(header: String)
        case noUsableRows(rejected: Int)

        var errorDescription: String? {
            switch self {
            case .tooLarge(let limit):
                "That fact table is larger than \(limit / 1_048_576) MB. Load it through the service boundary instead."
            case .notUTF8:
                "That file is not valid UTF-8, so its subjects could not be read exactly."
            case .unreadableJSON(let detail):
                "That JSON could not be read: \(detail)"
            case .emptyCSV:
                "That CSV has a header and no rows."
            case .csvMissingColumns(let header):
                "A CSV needs a subject column and a value column. Found: \(header)"
            case .noUsableRows(let rejected):
                "None of the \(rejected) row(s) had both a subject and a numeric value. Nothing was assumed."
            }
        }
    }

    struct Loaded: Equatable {
        let name: String
        /// Serialized exactly as it will be handed to the engine.
        let json: String
        let factCount: Int
        /// Rows or entries that lacked a subject or a numeric value. Reported
        /// rather than defaulted: a fact invented from a blank cell is a fact
        /// the source does not contain.
        let skipped: Int
    }

    static func load(_ url: URL) throws -> Loaded {
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }

        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let raw = try handle.read(upToCount: maxBytes + 1) ?? Data()
        guard raw.count <= maxBytes else { throw LoadError.tooLarge(limit: maxBytes) }
        guard let text = String(data: raw, encoding: .utf8) else { throw LoadError.notUTF8 }

        let name = url.lastPathComponent
        if url.pathExtension.lowercased() == "csv" || looksLikeCSV(text) {
            return try loadCSV(text, name: name)
        }
        return try loadJSON(text, name: name)
    }

    private static func looksLikeCSV(_ text: String) -> Bool {
        let first = text.split(separator: "\n", maxSplits: 1).first.map(String.init) ?? ""
        return first.contains(",") && !first.trimmingCharacters(in: .whitespaces).hasPrefix("{")
    }

    private static func loadJSON(_ text: String, name: String) throws -> Loaded {
        let data = Data(text.utf8)
        let parsed: Any
        do { parsed = try JSONSerialization.jsonObject(with: data) }
        catch { throw LoadError.unreadableJSON(String(describing: error)) }

        // Counted, not validated: the engine decides what it will accept, and
        // duplicating that judgement here would be a second implementation of
        // a rule that already exists.
        let count: Int
        if let object = parsed as? [String: Any] { count = object.count }
        else if let array = parsed as? [Any] { count = array.count }
        else { throw LoadError.unreadableJSON("expected an object or an array") }

        return Loaded(name: name, json: text, factCount: count, skipped: 0)
    }

    /// A minimal CSV reader: header plus rows, quoted fields honoured.
    ///
    /// The subject column is the first of `subject`/`name`/`key`/`unit`, the
    /// value column the first of `value`/`amount`/`qty`/`count`, and a `unit`
    /// column is carried through when present. A file without both is refused
    /// by name rather than guessed at positionally.
    private static func loadCSV(_ text: String, name: String) throws -> Loaded {
        var rows = text.split(whereSeparator: \.isNewline).map(String.init)
        guard let headerLine = rows.first else { throw LoadError.emptyCSV }
        rows.removeFirst()
        guard !rows.isEmpty else { throw LoadError.emptyCSV }

        let header = splitRow(headerLine).map {
            $0.trimmingCharacters(in: .whitespaces).lowercased()
        }
        let subjectNames = ["subject", "name", "key", "label", "unit_name"]
        let valueNames = ["value", "amount", "qty", "quantity", "count", "personnel"]
        guard let subjectIndex = header.firstIndex(where: { subjectNames.contains($0) }),
              let valueIndex = header.firstIndex(where: { valueNames.contains($0) })
        else { throw LoadError.csvMissingColumns(header: header.joined(separator: ", ")) }
        let unitIndex = header.firstIndex(of: "unit")

        var facts: [[String: Any]] = []
        var skipped = 0
        for row in rows {
            let cells = splitRow(row)
            guard cells.count > max(subjectIndex, valueIndex) else { skipped += 1; continue }
            let subject = cells[subjectIndex].trimmingCharacters(in: .whitespaces)
            let rawValue = cells[valueIndex].trimmingCharacters(in: .whitespaces)
                .replacingOccurrences(of: ",", with: "")
            guard !subject.isEmpty, Double(rawValue) != nil else { skipped += 1; continue }

            var fact: [String: Any] = ["subject": subject, "value": rawValue]
            if let unitIndex, cells.count > unitIndex {
                let unit = cells[unitIndex].trimmingCharacters(in: .whitespaces)
                if !unit.isEmpty { fact["unit"] = unit }
            }
            facts.append(fact)
        }
        guard !facts.isEmpty else { throw LoadError.noUsableRows(rejected: skipped) }

        let data = try JSONSerialization.data(withJSONObject: facts)
        return Loaded(name: name,
                      json: String(decoding: data, as: UTF8.self),
                      factCount: facts.count, skipped: skipped)
    }

    /// Handles quoted fields containing commas. Not a full RFC 4180 parser,
    /// and it does not pretend to be: embedded newlines inside quotes are not
    /// supported, and such a row is simply skipped and counted.
    private static func splitRow(_ row: String) -> [String] {
        var out: [String] = []
        var current = ""
        var inQuotes = false
        for character in row {
            if character == "\"" { inQuotes.toggle(); continue }
            if character == "," && !inQuotes { out.append(current); current = ""; continue }
            current.append(character)
        }
        out.append(current)
        return out
    }
}

/// The control that puts a fact table in front of the operator.
struct FactsPicker: View {
    @Binding var facts: FactsSource.Loaded?
    @State private var importing = false
    @State private var errorText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Button {
                    importing = true
                } label: {
                    Label(facts == nil ? "Ground truth…" : "Change facts",
                          systemImage: "tablecells")
                }
                if let facts {
                    Text("\(facts.factCount) fact(s) from \(facts.name)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    if facts.skipped > 0 {
                        // Surfaced, never silent: a skipped row is a fact the
                        // source did not usably contain.
                        Text("\(facts.skipped) row(s) skipped")
                            .font(.caption2)
                            .foregroundStyle(.orange)
                    }
                    Button("Clear", role: .destructive) { self.facts = nil }
                        .buttonStyle(.link)
                        .font(.caption)
                }
                Spacer()
            }
            Text(facts == nil
                 ? "Without ground truth, a claim whose subject lives outside the sentence is REFUSED — on operational prose that is most of them."
                 : "Claims are checked against these facts exactly. A subject they do not name still refuses.")
                .font(.caption2)
                .foregroundStyle(.tertiary)
            if let errorText {
                Text(errorText).font(.caption2).foregroundStyle(.orange)
            }
        }
        .fileImporter(isPresented: $importing,
                      allowedContentTypes: FactsSource.supportedTypes) { result in
            switch result {
            case .success(let url):
                do {
                    facts = try FactsSource.load(url)
                    errorText = nil
                } catch {
                    facts = nil
                    errorText = error.localizedDescription
                }
            case .failure(let error):
                errorText = error.localizedDescription
            }
        }
    }
}
