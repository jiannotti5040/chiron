// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import UniformTypeIdentifiers
import CryptoKit

enum FileLoad {
    /// Match the source-provenance module's hard input limit. A complete file
    /// at or below this size can be registered as one canonical source; a
    /// larger file is only analysed as an explicitly marked prefix.
    static let maxBytes = 8 * 1024 * 1024

    struct Loaded {
        let url: URL
        let name: String
        let text: String
        let bytes: Int
        let analysedBytes: Int
        let sizeKnown: Bool
        let truncated: Bool
        /// Present only when `text` is the complete selected file, so a later
        /// source-record observation can be tied to the exact analysed bytes.
        let contentSHA256: String?
    }

    enum LoadError: LocalizedError {
        case invalidUTF8

        var errorDescription: String? {
            switch self {
            case .invalidUTF8:
                return "The selected file is not valid UTF-8 text. It was not imported."
            }
        }
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
        let truncated = (knownSize ?? raw.count) > maxBytes || raw.count > maxBytes
        let data = raw.prefix(maxBytes)
        let decoded = try strictUTF8Text(from: Data(data),
                                         mayEndMidCharacter: truncated)
        let contentSHA256 = truncated ? nil : SHA256.hash(data: data)
            .map { String(format: "%02x", $0) }
            .joined()
        return Loaded(url: url,
                      name: url.lastPathComponent,
                      text: decoded.text,
                      bytes: max(knownSize ?? raw.count, raw.count),
                      analysedBytes: decoded.bytes,
                      sizeKnown: knownSize != nil,
                      truncated: truncated,
                      contentSHA256: contentSHA256)
    }

    /// `String(decoding:as:)` repairs invalid UTF-8, which would turn a bad
    /// source into different text without saying so. Decode strictly instead.
    /// When a deliberately bounded read stops inside one multi-byte code
    /// point, remove only that provably incomplete suffix and report the exact
    /// byte count that was actually analysed.
    private static func strictUTF8Text(
        from data: Data,
        mayEndMidCharacter: Bool
    ) throws -> (text: String, bytes: Int) {
        if let text = String(data: data, encoding: .utf8) {
            return (text, data.count)
        }
        guard mayEndMidCharacter,
              let suffixLength = incompleteUTF8SuffixLength(Array(data)),
              suffixLength < data.count
        else { throw LoadError.invalidUTF8 }

        let prefix = Data(data.dropLast(suffixLength))
        guard let text = String(data: prefix, encoding: .utf8) else {
            throw LoadError.invalidUTF8
        }
        return (text, prefix.count)
    }

    /// Returns the byte count of a trailing UTF-8 sequence that was cut off
    /// before it could complete. Invalid bytes are never treated as a suffix.
    private static func incompleteUTF8SuffixLength(_ bytes: [UInt8]) -> Int? {
        guard !bytes.isEmpty else { return nil }
        var index = bytes.count - 1
        var continuations = 0
        while index >= 0, (bytes[index] & 0b1100_0000) == 0b1000_0000 {
            continuations += 1
            index -= 1
        }
        guard index >= 0 else { return nil }

        let requiredContinuations: Int
        switch bytes[index] {
        case 0xC2...0xDF: requiredContinuations = 1
        case 0xE0...0xEF: requiredContinuations = 2
        case 0xF0...0xF4: requiredContinuations = 3
        default: return nil
        }
        guard continuations < requiredContinuations else { return nil }
        return continuations + 1
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
            Text("Analysed a strict UTF-8 prefix of \(FileLoad.byteLabel(loaded.analysedBytes)) "
                 + "from \(total) in \(loaded.name) — the rest was not analysed.")
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
