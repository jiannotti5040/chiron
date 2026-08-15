// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import Foundation
import ChironKit

@main
enum Entry {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        if let verb = args.first, ["run", "certify"].contains(verb) {
            exit(await Headless.main(args))
        }
        ChironUIApp.main()
    }
}

/// Headless mode exists so the whole path — locate vault, spawn python,
/// decode the record — is provable from a terminal and from CI:
///
///     swift run chiron-app run --json "text …"
///     swift run chiron-app certify "31,000 plus 2,180 is 33,180."
enum Headless {
    static func main(_ args: [String]) async -> Int32 {
        guard let client = VaultClient.discover() else {
            FileHandle.standardError.write(Data(
                "chiron-app: vault or python3 not found (set CHIRON_VAULT / CHIRON_PYTHON)\n".utf8))
            return 2
        }
        var rest = Array(args.dropFirst())
        let wantJSON = rest.contains("--json")
        rest.removeAll { $0 == "--json" }

        // A bare argument that names a readable file is treated as a bounded,
        // strictly decoded text input. The command is intentionally limited to
        // the same two canonical records shown by the macOS workspace.
        var text = rest.joined(separator: " ")
        if rest.count == 1, FileManager.default.fileExists(atPath: rest[0]) {
            do {
                let loaded = try FileLoad.read(URL(fileURLWithPath: rest[0]))
                text = loaded.text
                let scope = loaded.truncated
                    ? "strict UTF-8 prefix \(loaded.analysedBytes) of \(loaded.bytes) bytes"
                    : "\(loaded.bytes) strict UTF-8 bytes"
                FileHandle.standardError.write(Data(
                    "chiron-app: read \(scope) from \(rest[0])\n".utf8))
            } catch {
                FileHandle.standardError.write(Data(
                    "chiron-app: \(error.localizedDescription)\n".utf8))
                return 2
            }
        }
        guard !text.isEmpty else {
            FileHandle.standardError.write(Data(
                "usage: chiron-app run|certify [--json] <text|file>\n".utf8))
            return 2
        }
        do {
            switch args[0] {
            case "run":
                let raw = try await client.fullStackRaw(text: text)
                // Decode first: passing bytes through unexamined would make
                // "it printed" look like "it conformed".
                let rec = try JSONDecoder().decode(FullStackRecord.self, from: raw)
                if wantJSON {
                    FileHandle.standardOutput.write(raw)
                } else {
                    print("schema: \(rec.schema)")
                    print("stages: \(rec.stagesRun)  tally: \(rec.tally)  \(Int(rec.elapsedMs)) ms")
                    for r in rec.results {
                        let note = r.reason ?? r.error ?? ""
                        print("  [\(r.status.rawValue)] \(r.module).\(r.fn) \(note)")
                    }
                }
            case "certify":
                let raw = try await client.certifyRaw(text: text)
                let cert = try JSONDecoder().decode(Certificate.self, from: raw)
                if wantJSON {
                    FileHandle.standardOutput.write(raw)
                } else {
                    print("schema: \(cert.schema)")
                    if let c = cert.counts {
                        print("checkable: \(c.checkable)  verified: \(c.verified)  refuted: \(c.refuted)  refused: \(c.refused)")
                    }
                    for claim in cert.claims {
                        print("  [\(claim.status.rawValue)] \(claim.text)")
                    }
                    if let v = cert.verdict { print(v) }
                }
            default:
                return 2
            }
            return 0
        } catch {
            FileHandle.standardError.write(Data("chiron-app: \(error.localizedDescription)\n".utf8))
            return 1
        }
    }
}

struct ChironUIApp: App {
    @State private var model = AppModel()

    var body: some Scene {
        WindowGroup("Chiron") {
            ContentView()
                .environment(model)
                .frame(minWidth: 900, minHeight: 600)
        }
    }
}
