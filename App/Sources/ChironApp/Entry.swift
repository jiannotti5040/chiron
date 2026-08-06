// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

@main
enum Entry {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        if let verb = args.first, ["run", "certify", "catalog", "call"].contains(verb) {
            exit(await Headless.main(args))
        }
        ChironUIApp.main()
    }
}

/// Headless mode exists so the whole path — locate vault, spawn python,
/// decode the record — is provable from a terminal and from CI:
///
///     swift run chiron-app run --json "text …"
///     swift run chiron-app certify "The sum of 2 and 2 is 4."
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

        // `catalog` takes no text; everything else needs some.
        if args[0] == "catalog" {
            do {
                let cat = try await client.catalog()
                print("schema: \(cat.schema)")
                print("\(cat.importedCount)/\(cat.modules.count) modules import clean · "
                      + "\(cat.entrypointCount) entrypoints · "
                      + "\(cat.modules.flatMap(\.functions).filter(\.isRunnable).count) runnable from one input")
                for m in cat.modules where m.status != "OK" {
                    print("  FAILED \(m.name): \(m.error ?? "")")
                }
                return 0
            } catch {
                FileHandle.standardError.write(Data("chiron-app: \(error.localizedDescription)\n".utf8))
                return 1
            }
        }

        if args[0] == "call" {
            guard rest.count >= 3 else {
                FileHandle.standardError.write(Data(
                    "usage: chiron-app call <module> <function> <text>\n".utf8))
                return 2
            }
            let mod = rest[0], fn = rest[1]
            let text = rest.dropFirst(2).joined(separator: " ")
            do {
                let cat = try await client.catalog()
                guard let info = cat.modules.first(where: { $0.name == mod })?
                    .functions.first(where: { $0.name == fn }) else {
                    FileHandle.standardError.write(Data("chiron-app: no \(mod).\(fn)\n".utf8))
                    return 2
                }
                let r = try await client.call(module: mod, function: fn,
                                              text: text, kind: info.firstArgKind)
                print("[\(r.status)] \(r.module).\(r.function) \(Int(r.ms ?? 0)) ms")
                if let v = r.result { print(v.rendered()) }
                if let e = r.error { print(e) }
                return r.status == "OK" ? 0 : 1
            } catch {
                FileHandle.standardError.write(Data("chiron-app: \(error.localizedDescription)\n".utf8))
                return 1
            }
        }

        // A bare argument that names a readable file is treated as that file.
        // Analysing a file is the ordinary case, not a special mode.
        var text = rest.joined(separator: " ")
        if rest.count == 1, FileManager.default.fileExists(atPath: rest[0]),
           let data = FileManager.default.contents(atPath: rest[0]) {
            text = String(decoding: data.prefix(FileLoad.maxBytes), as: UTF8.self)
            FileHandle.standardError.write(Data(
                "chiron-app: read \(data.count) bytes from \(rest[0])\n".utf8))
        }
        guard !text.isEmpty else {
            FileHandle.standardError.write(Data(
                "usage: chiron-app run|certify [--json] <text|file> | catalog | call <module> <fn> <text>\n".utf8))
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
