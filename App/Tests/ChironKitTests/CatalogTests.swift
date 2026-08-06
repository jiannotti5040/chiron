// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import Testing
@testable import ChironKit

@Suite struct CatalogTests {

    private func client() -> VaultClient? { VaultClient.discover() }

    @Test func numericSurfaceMatchesTheVault() {
        // full_stack.py derives its surface with \b\d[\d,]*\b — commas inside
        // a number are part of it, and the Swift side must agree or the two
        // halves of the app would analyse different numbers.
        #expect(VaultClient.numericSurface(of: "4200 and 1,400 then 25.")
                == [4200, 1400, 25])
        #expect(VaultClient.numericSurface(of: "no digits here").isEmpty)
    }

    @Test func liveCatalogCoversTheWholeVault() async throws {
        guard let client = client() else {
            Issue.record("SKIP: vault or python3 not found — nothing was proven")
            return
        }
        let cat = try await client.catalog()
        #expect(cat.schema == "chiron.app.catalog/1")
        // The catalog is discovered, so this asserts a floor, not an exact
        // count — adding a module must never fail this test.
        #expect(cat.modules.count >= 70)
        #expect(cat.importedCount == cat.modules.count)
        #expect(cat.entrypointCount > 500)
        #expect(cat.modules.contains { $0.name == "attest" })
        #expect(Set(cat.modules.map(\.name)).count == cat.modules.count)
    }

    @Test func liveCallDispatchesTextAndSurface() async throws {
        guard let client = client() else {
            Issue.record("SKIP: vault or python3 not found — nothing was proven")
            return
        }
        let text = try await client.call(module: "language", function: "readability",
                                         text: "A short sentence. Another one.",
                                         kind: "text")
        #expect(text.status == "OK")

        let surface = try await client.call(module: "aesthetics", function: "aesthetic",
                                            text: "1, 4, 9, 16, 25", kind: "surface")
        #expect(surface.status == "OK")
    }

    @Test func liveCallReportsFailureRatherThanSubstituting() async throws {
        guard let client = client() else {
            Issue.record("SKIP: vault or python3 not found — nothing was proven")
            return
        }
        // A function that does not exist must come back as an ERROR record —
        // never as an empty-but-OK result, which would read as a clean run.
        let r = try await client.call(module: "language", function: "no_such_function",
                                      text: "x", kind: "text")
        #expect(r.status == "ERROR")
        #expect(r.result == nil)
        #expect(r.error != nil)
    }
}
