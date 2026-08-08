// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

#if os(macOS)

public enum VaultLocator {
    /// A vault root is recognized by its own files, not by its folder name —
    /// the repository has been cloned under several names.
    public static func isVaultRoot(_ url: URL) -> Bool {
        let fm = FileManager.default
        return fm.fileExists(atPath: url.appendingPathComponent("Chiron/full_stack.py").path)
            && fm.fileExists(atPath: url.appendingPathComponent("Primus").path)
    }

    /// CHIRON_VAULT wins; otherwise walk up from each candidate directory.
    /// Running `swift run` anywhere inside the repository finds it; a
    /// double-clicked binary needs the environment variable or the in-app
    /// folder picker.
    public static func locate(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        extraCandidates: [URL] = []
    ) -> URL? {
        if let p = environment["CHIRON_VAULT"] {
            let u = URL(fileURLWithPath: p)
            if isVaultRoot(u) { return u }
        }
        var starts = extraCandidates
        starts.append(URL(fileURLWithPath: FileManager.default.currentDirectoryPath))
        if let exe = Bundle.main.executableURL {
            starts.append(exe.deletingLastPathComponent())
        }
        for start in starts {
            var dir = start.standardizedFileURL
            for _ in 0..<12 {
                if isVaultRoot(dir) { return dir }
                let parent = dir.deletingLastPathComponent()
                if parent.path == dir.path { break }
                dir = parent
            }
        }
        return nil
    }
}

#endif
