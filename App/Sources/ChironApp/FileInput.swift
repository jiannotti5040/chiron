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
        var truncated: Bool { bytes > maxBytes }
    }

    static func read(_ url: URL) throws -> Loaded {
        // A URL from the open panel may need its security scope claimed;
        // one from a drag usually does not. Asking twice is harmless.
        let scoped = url.startAccessingSecurityScopedResource()
        defer { if scoped { url.stopAccessingSecurityScopedResource() } }

        let size = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        let data = try handle.read(upToCount: maxBytes) ?? Data()
        return Loaded(name: url.lastPathComponent,
                      text: String(decoding: data, as: UTF8.self),
                      bytes: size)
    }
}

/// "Analyse a file" as a first-class action beside the text box: a button,
/// a drop target, and an honest note when the file was only partly read.
struct FileLoadBar: View {
    let label: String
    @Binding var text: String
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
                    Text(byteLabel(loaded.bytes))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Text("or drop a file on the text box")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
            if let loaded, loaded.truncated {
                Text("Read the first \(byteLabel(FileLoad.maxBytes)) of "
                     + "\(byteLabel(loaded.bytes)) — the rest was not analysed.")
                    .font(.caption)
                    .foregroundStyle(.orange)
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
            errorText = nil
        } catch {
            errorText = "Could not read \(url.lastPathComponent): \(error.localizedDescription)"
        }
    }

    private func byteLabel(_ n: Int) -> String {
        n < 1024 ? "\(n) B"
            : n < 1024 * 1024 ? String(format: "%.0f KB", Double(n) / 1024)
            : String(format: "%.1f MB", Double(n) / 1_048_576)
    }
}

/// Drop-to-load for any text box.
struct FileDropModifier: ViewModifier {
    @Binding var text: String
    @State private var targeted = false

    func body(content: Content) -> some View {
        content
            .overlay(RoundedRectangle(cornerRadius: 6)
                .strokeBorder(targeted ? Color.accentColor : Color.clear, lineWidth: 2))
            .onDrop(of: [.fileURL], isTargeted: $targeted) { providers in
                guard let provider = providers.first else { return false }
                _ = provider.loadObject(ofClass: URL.self) { url, _ in
                    guard let url else { return }
                    if let loaded = try? FileLoad.read(url) {
                        Task { @MainActor in text = loaded.text }
                    }
                }
                return true
            }
    }
}

extension View {
    func acceptsFileDrop(text: Binding<String>) -> some View {
        modifier(FileDropModifier(text: text))
    }
}
