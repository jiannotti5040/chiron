// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import UniformTypeIdentifiers
import ChironKit

/// The macOS work surface is deliberately narrow: one text source enters the
/// two canonical engines, and their untouched records stay together with the
/// provenance observation for a complete selected file.
struct WorkspaceView: View {
    let client: VaultClient

    @State private var text = WorkspaceView.sample
    @State private var selectedFile: FileLoad.Loaded?
    @State private var record: WorkspaceRecord?
    @State private var running = false
    @State private var errorText: String?
    @State private var exportDocument = RawJSONDocument(data: Data())
    @State private var exportName = "chiron-record.json"
    @State private var exporting = false

    static let sample = "The archive holds 4200 records and 1400 were revised "
        + "this quarter, so three in ten changed. Sequence: 1, 4, 9, 16, 25."

    /// Editing after selecting a file makes the file record inapplicable. The
    /// file controls set `$text` directly before their load callback, so they
    /// retain the selection; only an ordinary text edit clears it.
    private var editableText: Binding<String> {
        Binding(
            get: { text },
            set: { value in
                guard value != text else { return }
                text = value
                selectedFile = nil
                record = nil
            }
        )
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            inputPanel
            if let errorText { ErrorBanner(text: errorText) }
            if let record {
                resultHeader(record)
                if let source = record.source {
                    SourceRecordPanel(record: source, fileName: record.sourceFileName)
                } else if let selectedFile, selectedFile.truncated {
                    Text("No source record was requested: this file was only analysed as a "
                         + "bounded prefix. Choose a complete file at or below "
                         + "\(FileLoad.byteLabel(FileLoad.maxBytes)) for canonical file provenance.")
                        .font(.caption)
                        .foregroundStyle(.orange)
                }
                HSplitView {
                    AnalysisPane(record: record.analysis)
                        .frame(minWidth: 420)
                    CertificatePane(certificate: record.certificate)
                        .frame(minWidth: 420)
                }
            } else if !running {
                ContentUnavailableView(
                    "No workspace record yet",
                    systemImage: "rectangle.3.group",
                    description: Text("Paste text or choose a UTF-8 file, then run the canonical "
                        + "full stack and exact certificate together."))
            }
            Spacer(minLength: 0)
        }
        .padding()
        .fileExporter(
            isPresented: $exporting,
            document: exportDocument,
            contentType: .json,
            defaultFilename: exportName
        ) { result in
            if case .failure(let error) = result {
                errorText = "Could not export the canonical record: \(error.localizedDescription)"
            }
        }
    }

    private var inputPanel: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(Screen.workspace.subtitle)
                .foregroundStyle(.secondary)
            TextEditor(text: editableText)
                .font(.body)
                .frame(height: 130)
                .overlay(RoundedRectangle(cornerRadius: 6).strokeBorder(.quaternary))
                .acceptsFileDrop(
                    text: $text,
                    onLoad: selectFile,
                    onError: { errorText = $0 }
                )
            FileLoadBar(label: "Choose a UTF-8 text file…", text: $text, onLoad: selectFile)
            if let selectedFile {
                HStack(spacing: 8) {
                    Text(selectedFile.name)
                        .font(.caption.monospaced())
                        .lineLimit(1)
                        .truncationMode(.middle)
                    Text(FileLoad.byteLabel(selectedFile.bytes)
                         + (selectedFile.sizeKnown ? "" : "+"))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                    if !selectedFile.truncated {
                        Label("complete file", systemImage: "checkmark.circle")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            if let selectedFile { FileLoadWarning(loaded: selectedFile) }
            HStack {
                Button {
                    run()
                } label: {
                    Label("Run workspace", systemImage: "play.fill")
                }
                .keyboardShortcut(.return, modifiers: .command)
                .disabled(running || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                if running { ProgressView().controlSize(.small) }
                Spacer()
                Text("Full stack and certificate use the same input bytes.")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
    }

    @ViewBuilder
    private func resultHeader(_ record: WorkspaceRecord) -> some View {
        HStack(spacing: 8) {
            Text("Canonical records")
                .font(.headline)
            Text("\(record.analysis.stagesRun) stages · \(Int(record.analysis.elapsedMs)) ms")
                .font(.caption.monospacedDigit())
                .foregroundStyle(.secondary)
            Spacer()
            Menu {
                Button("Full-stack record…") {
                    prepareExport(record.analysisRaw, named: "chiron-full-stack.json")
                }
                Button("Certificate…") {
                    prepareExport(record.certificateRaw, named: "primus-certificate.json")
                }
                if let sourceRaw = record.sourceRaw {
                    Button("Source record…") {
                        prepareExport(sourceRaw, named: "chiron-source-record.json")
                    }
                }
            } label: {
                Label("Export raw records", systemImage: "square.and.arrow.up")
            }
        }
    }

    private func selectFile(_ loaded: FileLoad.Loaded) {
        selectedFile = loaded
        record = nil
        errorText = nil
    }

    private func prepareExport(_ data: Data, named: String) {
        exportDocument = RawJSONDocument(data: data)
        exportName = named
        exporting = true
    }

    private func run() {
        running = true
        errorText = nil
        record = nil
        let input = text
        let sourceFile = selectedFile?.truncated == false ? selectedFile : nil

        Task {
            defer { running = false }
            do {
                async let analysisTask: Data = client.fullStackRaw(text: input)
                async let certificateTask: Data = client.certifyRaw(text: input)
                let sourceRaw: Data?
                if let sourceFile {
                    sourceRaw = try await client.sourceRecordRaw(fileURL: sourceFile.url)
                } else {
                    sourceRaw = nil
                }
                let (analysisRaw, certificateRaw) = try await (analysisTask, certificateTask)
                let decoder = JSONDecoder()
                let analysis = try decoder.decode(FullStackRecord.self, from: analysisRaw)
                let certificate = try decoder.decode(Certificate.self, from: certificateRaw)
                let source: SourceRecord?
                if let sourceRaw, let sourceFile {
                    let decoded = try decoder.decode(SourceRecord.self, from: sourceRaw)
                    guard decoded.contentSHA256 == sourceFile.contentSHA256 else {
                        throw WorkspaceInputError.fileChangedAfterImport
                    }
                    source = decoded
                } else {
                    source = nil
                }
                record = WorkspaceRecord(
                    analysis: analysis,
                    analysisRaw: analysisRaw,
                    certificate: certificate,
                    certificateRaw: certificateRaw,
                    source: source,
                    sourceRaw: sourceRaw,
                    sourceFileName: sourceFile?.name
                )
            } catch {
                errorText = error.localizedDescription
            }
        }
    }
}

private struct WorkspaceRecord {
    let analysis: FullStackRecord
    let analysisRaw: Data
    let certificate: Certificate
    let certificateRaw: Data
    let source: SourceRecord?
    let sourceRaw: Data?
    let sourceFileName: String?
}

private enum WorkspaceInputError: LocalizedError {
    case fileChangedAfterImport

    var errorDescription: String? {
        switch self {
        case .fileChangedAfterImport:
            return "The selected file changed after import. It was not attached as provenance; choose it again and rerun."
        }
    }
}

private struct RawJSONDocument: FileDocument {
    static var readableContentTypes: [UTType] { [.json] }
    var data: Data

    init(data: Data) {
        self.data = data
    }

    init(configuration: ReadConfiguration) throws {
        data = configuration.file.regularFileContents ?? Data()
    }

    func fileWrapper(configuration: WriteConfiguration) throws -> FileWrapper {
        FileWrapper(regularFileWithContents: data)
    }
}

private struct SourceRecordPanel: View {
    let record: SourceRecord
    let fileName: String?
    @State private var spansExpanded = false

    private let visibleSpanLimit = 200

    var body: some View {
        GroupBox("Local source record") {
            VStack(alignment: .leading, spacing: 7) {
                HStack(spacing: 8) {
                    if let fileName {
                        Text(fileName)
                            .font(.callout.monospaced())
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    Text(record.schema)
                        .font(.caption.monospaced())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text(record.encoding.uppercased())
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                }
                Text(record.contentSHA256)
                    .font(.caption.monospaced())
                    .textSelection(.enabled)
                HStack(spacing: 8) {
                    StatTile(title: "bytes", value: "\(record.byteCount)")
                    StatTile(title: "characters", value: "\(record.characterCount)")
                    StatTile(title: "line spans", value: "\(record.lineSpans.count)")
                }
                DisclosureGroup(
                    "Line spans (\(min(record.lineSpans.count, visibleSpanLimit)) of \(record.lineSpans.count) shown)",
                    isExpanded: $spansExpanded
                ) {
                    Text("Offsets are zero-based and end-exclusive. Export the raw source record for every span.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 2) {
                            ForEach(Array(record.lineSpans.prefix(visibleSpanLimit)), id: \.line) { span in
                                Text("line \(span.line)  bytes \(span.byteStart)..<\(span.byteEnd)  chars \(span.characterStart)..<\(span.characterEnd)")
                                    .font(.caption.monospacedDigit())
                                    .textSelection(.enabled)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                    }
                    .frame(maxHeight: 180)
                }
                .font(.caption)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        }
    }
}

private struct AnalysisPane: View {
    let record: FullStackRecord

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Full-stack analysis")
                .font(.headline)
            HStack(spacing: 8) {
                ForEach(record.tally.keys.sorted(), id: \.self) { key in
                    StatTile(title: key, value: "\(record.tally[key] ?? 0)")
                }
                if !record.numericSurface.isEmpty {
                    StatTile(
                        title: "numeric surface",
                        value: record.numericSurface.map(String.init).joined(separator: " ")
                    )
                }
            }
            List {
                ForEach(groupedStages, id: \.offset) { group in
                    Section(group.layer.uppercased()) {
                        ForEach(group.stages, id: \.offset) { item in
                            WorkspaceStageRow(stage: item.stage)
                        }
                    }
                }
            }
            .listStyle(.inset)
        }
        .padding(.trailing, 8)
    }

    private var groupedStages: [(offset: Int, layer: String, stages: [(offset: Int, stage: StageResult)])] {
        var groups: [(Int, String, [(Int, StageResult)])] = []
        for (offset, stage) in record.results.enumerated() {
            if let last = groups.indices.last, groups[last].1 == stage.layer {
                groups[last].2.append((offset, stage))
            } else {
                groups.append((offset, stage.layer, [(offset, stage)]))
            }
        }
        return groups.map { group in
            (offset: group.0,
             layer: group.1,
             stages: group.2.map { (offset: $0.0, stage: $0.1) })
        }
    }
}

private struct WorkspaceStageRow: View {
    let stage: StageResult
    @State private var expanded = false

    var body: some View {
        DisclosureGroup(isExpanded: $expanded) {
            if let result = stage.result {
                JSONDetail(value: result).frame(maxHeight: 260)
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

private struct CertificatePane: View {
    let certificate: Certificate

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Exact certificate")
                .font(.headline)
            HStack(spacing: 8) {
                if let counts = certificate.counts {
                    StatTile(title: "checkable", value: "\(counts.checkable)")
                    StatTile(title: "VERIFIED", value: "\(counts.verified)")
                    StatTile(title: "REFUTED", value: "\(counts.refuted)")
                    StatTile(title: "REFUSED", value: "\(counts.refused)")
                }
                StatTile(title: "coverage", value: percent(certificate.coverage))
            }
            if let engine = certificate.engine {
                Text("\(engine.name) \(engine.version) · \(certificate.schema)")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
            }
            List(Array(certificate.claims.enumerated()), id: \.offset) { item in
                WorkspaceClaimRow(claim: item.element)
            }
            .listStyle(.inset)
            if let verdict = certificate.verdict {
                Text(verdict)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .textSelection(.enabled)
            }
        }
        .padding(.leading, 8)
    }
}

private struct WorkspaceClaimRow: View {
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
            if let reason = claim.reason ?? claim.detail {
                Text(reason)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 3)
    }
}
