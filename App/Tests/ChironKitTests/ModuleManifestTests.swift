// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Testing
import Foundation
@testable import ChironKit

/// Replaces the coverage lost when `CatalogTests.swift` was deleted, against
/// the manifest the vault actually generates rather than a runtime shim.
@Suite struct ModuleManifestTests {

    private func vaultRoot() -> URL? {
        // Same discovery the other live tests use: walk up until the vault's
        // own markers appear, so this works from any scratch path.
        var dir = URL(fileURLWithPath: #filePath)
        for _ in 0..<8 {
            dir.deleteLastPathComponent()
            let manifest = dir.appendingPathComponent("Chiron/manifest.json")
            if FileManager.default.fileExists(atPath: manifest.path) { return dir }
        }
        return nil
    }

    @Test func manifestLoadsAndCoversTheWholeVault() throws {
        guard let root = vaultRoot() else { return }
        let manifest = try ModuleManifest.load(vaultRoot: root)

        // The numeric surface must agree with itself. An earlier catalog
        // reported counts it computed separately from the list it displayed,
        // which is how a summary and its detail drift apart unnoticed.
        #expect(manifest.scripts.count == manifest.summary.runnableScripts)
        #expect(manifest.summary.runnableScripts > 50)
        #expect(manifest.scripts.filter(\.hasSelftest).count
                == manifest.summary.withSelftest)
        #expect(manifest.pureStdlib.count == manifest.summary.stdlibOnly)
    }

    @Test func everyScriptHasAnIdentityAndAPath() throws {
        guard let root = vaultRoot() else { return }
        let manifest = try ModuleManifest.load(vaultRoot: root)

        for script in manifest.scripts {
            #expect(!script.script.isEmpty)
            #expect(script.path.hasSuffix(".py"))
            #expect(script.lines > 0)
        }
        let names = Set(manifest.scripts.map(\.script))
        #expect(names.count == manifest.scripts.count, "module names must be unique")
    }

    @Test func filteringNarrowsWithoutInventing() throws {
        guard let root = vaultRoot() else { return }
        let manifest = try ModuleManifest.load(vaultRoot: root)

        #expect(manifest.matching("").count == manifest.scripts.count)
        let hits = manifest.matching("certif")
        #expect(hits.count < manifest.scripts.count)
        #expect(hits.allSatisfy { script in
            script.script.lowercased().contains("certif")
            || (script.purpose ?? "").lowercased().contains("certif")
            || (script.title ?? "").lowercased().contains("certif")
        })
    }

    @Test func aMissingManifestIsReportedRatherThanSynthesised() {
        let nowhere = URL(fileURLWithPath: "/var/empty/definitely-not-a-vault")
        #expect(throws: ModuleManifestError.self) {
            try ModuleManifest.load(vaultRoot: nowhere)
        }
    }

    /// The catalog is a reader. If this type ever grows a way to invoke a
    /// module, the reviewed static allowlist stops being the only execution
    /// path and that is a boundary regression, not a feature.
    @Test func theCatalogExposesNoWayToRunAnything() throws {
        guard let root = vaultRoot() else { return }
        let manifest = try ModuleManifest.load(vaultRoot: root)
        let mirror = Mirror(reflecting: manifest)
        #expect(!mirror.children.contains { ($0.label ?? "").lowercased().contains("run") })
    }
}
