// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import UniformTypeIdentifiers

enum FileLoad {
    /// Files can be arbitrarily large and are not all text. Read a bounded
    /// prefix and say so rather than hanging or pretending the whole file
    /// was analysed.
    static let maxBytes = 2_000_000

    struct Loaded {
        let name: String
        let text: String
        let bytes: Int
        let sizeKnown: Bool
        let truncated: Bool
    }

    static func read(_ url: URL) throws -> Loaded {
        // A URL from the open panel may need its security scope claimed;
        // one from a drag usually does not. Asking twice is harmless.
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }

        let resourceValues = try? url.resourceValues(forKeys: [.fileSizeKey])
        let knownSize = resourceValues?.fileSize
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        // Read one byte past the visible bound. File metadata is normally
        // available, but this makes truncation truthful even when a file
        // provider cannot report the size.
        let raw = try handle.read(upToCount: maxBytes + 1) ?? Data()
        let truncated = raw.count > maxBytes
        let data = raw.prefix(maxBytes)
        return Loaded(name: url.lastPathComponent,
                      text: String(decoding: data, as: UTF8.self),
                      bytes: max(knownSize ?? raw.count, raw.count),
                      sizeKnown: knownSize != nil,
                      truncated: truncated)
    }

    static func byteLabel(_ n: Int) -> String {
        n < 1024 ? "\(n) B"
            : n < 1024 * 1024 ? String(format: "%.0f KB", Double(n) / 1024)
            : String(format: "%.1f MB", Double(n) / 1_048_576)
    }
}

/// A bounded read is useful only when the boundary remains visible at the
/// point of analysis. Reuse this for picker, drag/drop, and multi-file flows.
struct FileLoadWarning: View {
    let loaded: FileLoad.Loaded

    var body: some View {
        if loaded.truncated {
            let total = loaded.sizeKnown
                ? FileLoad.byteLabel(loaded.bytes)
                : "at least \(FileLoad.byteLabel(loaded.bytes))"
            Text("Read the first \(FileLoad.byteLabel(FileLoad.maxBytes)) of \(total) "
                 + "from \(loaded.name) — "
                 + "the rest was not analysed.")
                .font(.caption)
                .foregroundStyle(.orange)
        }
    }
}

/// "Analyse a file" as a first-class action beside the text box: a button,
/// a drop target, and an honest note when the file was only partly read.
struct FileLoadBar: View {
    let label: String
    @Binding var text: String
    let onLoad: (FileLoad.Loaded) -> Void
    @State private var importing = false
    @State private var loaded: FileLoad.Loaded?
    @State private var errorText: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(spacing: 8) {
                Button {
                    importing = true
                } label: {
                    Label(label, systemImage: "doc.badge.plus")
                }
                if let loaded {
                    Text(loaded.name)
                        .font(.caption.monospaced())
                        .lineLimit(1)
                        .truncationMode(.middle)
                    Text(FileLoad.byteLabel(loaded.bytes) + (loaded.sizeKnown ? "" : "+"))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text("or drop a file on the text box")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            if let errorText { ErrorBanner(text: errorText) }
        }
        .fileImporter(isPresented: $importing,
                      allowedContentTypes: [.plainText, .text, .data, .sourceCode, .json],
                      allowsMultipleSelection: false) { result in
            switch result {
            case .success(let urls):
                if let url = urls.first { load(url) }
            case .failure(let error):
                errorText = error.localizedDescription
            }
        }
    }

    func load(_ url: URL) {
        do {
            let l = try FileLoad.read(url)
            loaded = l
            text = l.text
            onLoad(l)
            errorText = nil
        } catch {
            errorText = "Could not read \(url.lastPathComponent): \(error.localizedDescription)"
        }
    }

}

/// Drop-to-load for any text box.
struct FileDropModifier: ViewModifier {
    @Binding var text: String
    let onLoad: (FileLoad.Loaded) -> Void
    let onError: (String) -> Void
    @State private var targeted = false

    func body(content: Content) -> some View {
        content
            .overlay(RoundedRectangle(cornerRadius: 6)
                .strokeBorder(targeted ? Color.accentColor : Color.clear, lineWidth: 2))
            .onDrop(of: [.fileURL], isTargeted: $targeted) { providers in
                guard let provider = providers.first else { return false }
                _ = provider.loadObject(ofClass: URL.self) { url, _ in
                    guard let url else { return }
                    do {
                        let loaded = try FileLoad.read(url)
                        Task { @MainActor in
                            text = loaded.text
                            onLoad(loaded)
                        }
                    } catch {
                        let detail = "Could not read \(url.lastPathComponent): \(error.localizedDescription)"
                        Task { @MainActor in onError(detail) }
                    }
                }
                return true
            }
    }
}

extension View {
    func acceptsFileDrop(
        text: Binding<String>,
        onLoad: @escaping (FileLoad.Loaded) -> Void = { _ in },
        onError: @escaping (String) -> Void = { _ in }
    ) -> some View {
        modifier(FileDropModifier(text: text, onLoad: onLoad, onError: onError))
    }
}
