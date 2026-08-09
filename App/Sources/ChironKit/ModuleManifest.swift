// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

/// # The module catalog, restored as a reader
///
/// An earlier `Catalog.swift` built this by shipping a Python introspection
/// shim inside a Swift string literal: it imported every module in `Chiron/`
/// and reflected over it at runtime. Beside it sat a second shim that could
/// call any function it found. Both were deleted during the workspace
/// consolidation and neither is coming back in that form.
///
/// Two reasons. The shim was a second implementation of something the vault
/// already does — `Chiron/build_manifest.py` writes `Chiron/manifest.json`,
/// and CI fails on a stale one, so it is the fresher and more authoritative
/// answer. And arbitrary module dispatch is deliberately unavailable: the MCP
/// server exposes a reviewed static allowlist for exactly that reason, so an
/// app-side path that could call any function undermines a boundary the rest
/// of the system maintains.
///
/// This type therefore *reads* the manifest and offers no way to run
/// anything. `VaultClient` remains the only path to execution, and it reaches
/// the same reviewed operations everything else does.
public struct ModuleManifest: Codable, Sendable {
    public let system: String?
    public let owner: String?
    public let generatedUTC: String?
    public let mode: String?
    public let summary: Summary
    public let scripts: [Script]

    enum CodingKeys: String, CodingKey {
        case system, owner, mode, summary, scripts
        case generatedUTC = "generated_utc"
    }

    public struct Summary: Codable, Sendable {
        public let runnableScripts: Int
        public let withSelftest: Int
        public let stdlibOnly: Int
        public let withSPDXHeader: Int
        public let emittingArtifacts: Int
        public let internalEdges: Int

        enum CodingKeys: String, CodingKey {
            case runnableScripts = "runnable_scripts"
            case withSelftest = "with_selftest"
            case stdlibOnly = "stdlib_only"
            case withSPDXHeader = "with_spdx_header"
            case emittingArtifacts = "emitting_artifacts"
            case internalEdges = "internal_edges"
        }
    }

    public struct Script: Codable, Sendable, Identifiable {
        public var id: String { script }

        public let script: String
        public let path: String
        public let purpose: String?
        public let title: String?
        public let lines: Int
        public let hasSelftest: Bool
        public let stdlibOnly: Bool
        public let imports: [String]
        public let dependencies: [String]
        public let lens: Lens?

        enum CodingKeys: String, CodingKey {
            case script, path, purpose, title, lines, imports, dependencies, lens
            case hasSelftest = "has_selftest"
            case stdlibOnly = "stdlib_only"
        }

        /// Three readings of the same module. Present for most scripts and
        /// absent for some; optional rather than defaulted, because an
        /// invented description would be worse than a missing one.
        public struct Lens: Codable, Sendable {
            public let math: String?
            public let prog: String?
            public let concept: String?
        }

        /// Whether this module carries its own executable evidence. Shown
        /// because "has a self-test" and "is correct" are different claims,
        /// and only the first is observable from a manifest.
        public var carriesOwnEvidence: Bool { hasSelftest }
    }

    /// Modules with no third-party import. Reported because the dependency
    /// surface is a security property, not a style preference.
    public var pureStdlib: [Script] { scripts.filter(\.stdlibOnly) }

    public func matching(_ query: String) -> [Script] {
        let needle = query.lowercased()
        guard !needle.isEmpty else { return scripts }
        return scripts.filter {
            $0.script.lowercased().contains(needle)
            || ($0.purpose ?? "").lowercased().contains(needle)
            || ($0.title ?? "").lowercased().contains(needle)
        }
    }
}

public enum ModuleManifestError: Error, Sendable, Equatable {
    case notFound(path: String)
    case unreadable(String)
}

extension ModuleManifest {
    /// Load the manifest the vault generates. Never generates one itself: a
    /// stale manifest is a CI failure by design, and quietly rebuilding it
    /// here would hide exactly the drift that failure exists to catch.
    public static func load(vaultRoot: URL) throws -> ModuleManifest {
        let url = vaultRoot.appendingPathComponent("Chiron/manifest.json")
        guard FileManager.default.fileExists(atPath: url.path) else {
            throw ModuleManifestError.notFound(path: url.path)
        }
        do {
            return try JSONDecoder().decode(ModuleManifest.self,
                                            from: Data(contentsOf: url))
        } catch {
            throw ModuleManifestError.unreadable(String(describing: error))
        }
    }
}
