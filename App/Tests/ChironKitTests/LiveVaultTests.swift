// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import Testing
@testable import ChironKit

// End-to-end against the real vault: locate it, spawn its python, decode
// what comes back. When the vault or python3 is absent (CI without the
// repo checked out beside the package) these record a skip, not a pass —
// absence must never look like green.
@Suite struct LiveVaultTests {

    private func client() -> VaultClient? { VaultClient.discover() }

    @Test func liveFullStack() async throws {
        guard let client = client() else {
            Issue.record("SKIP: vault or python3 not found — nothing was proven")
            return
        }
        let rec = try await client.fullStack(
            text: "Fuel on hand 4200, burn 1400. Check: 1, 4, 9, 16, 25.")
        #expect(rec.schema == "chiron.full_stack/1")
        #expect(rec.stagesRun > 0)
        #expect(rec.results.count == rec.stagesRun)
    }

    @Test func liveAttestRefusesWithoutInputs() async throws {
        guard let client = client() else {
            Issue.record("SKIP: vault or python3 not found — nothing was proven")
            return
        }
        let rec = try await client.attest(output: "A sentence with no candidates.")
        #expect(rec.schema == "chiron.attestation/1")
        // The module's contract: no candidate inputs, no attribution — REFUSED.
        #expect(rec.spans.allSatisfy { $0.verdict == .refused })
    }

    // A child that exits without reading its stdin breaks the write end. If
    // SIGPIPE were not ignored this test would not fail — it would kill the
    // whole test process, which is the point of proving it here.
    @Test func earlyChildExitDoesNotKillTheProcess() async throws {
        guard let runner = PythonRunner.locate() else {
            Issue.record("SKIP: python3 not found — nothing was proven")
            return
        }
        let big = Data(String(repeating: "x", count: 4_000_000).utf8)
        let res = try await runner.run(
            arguments: ["-c", "import sys; sys.exit(3)"], stdin: big, timeout: 60)
        #expect(res.exitCode == 3)
    }

    @Test func liveCertify() async throws {
        guard let client = client() else {
            Issue.record("SKIP: vault or python3 not found — nothing was proven")
            return
        }
        let cert = try await client.certify(text: "The sum of 2 and 2 is 4.")
        #expect(cert.schema == "primus.certificate/2")
        #expect(cert.counts?.verified == 1)
        #expect(cert.counts?.refuted == 0)
    }
}
