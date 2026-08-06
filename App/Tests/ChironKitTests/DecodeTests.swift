// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import Testing
@testable import ChironKit

// Fixtures are real engine output captured from the vault at build time of
// this package — not hand-written JSON, so a drifted decoder fails here
// before it fails in front of a user.
private func fixture(_ name: String) throws -> Data {
    let url = try #require(Bundle.module.url(
        forResource: name, withExtension: "json", subdirectory: "Fixtures"))
    return try Data(contentsOf: url)
}

@Suite struct DecodeTests {

    @Test func fullStackRecordDecodes() throws {
        let rec = try JSONDecoder().decode(FullStackRecord.self,
                                           from: fixture("full_stack_sample"))
        #expect(rec.schema == "chiron.full_stack/1")
        #expect(rec.stagesRun == 28)
        #expect(rec.results.count == 28)
        #expect(rec.tally["OK"] == 28)
        // Every status in the fixture is one the UI knows how to draw.
        let known: Set<StageStatus> = [.ok, .skipped, .error]
        #expect(rec.results.allSatisfy { known.contains($0.status) })
    }

    @Test func repeatedSpansDecodeAsDistinctEntries() throws {
        // attest returns one span per sentence, so a repeated sentence is a
        // repeated span with identical content. Nothing may collapse them —
        // the views index by position for exactly this reason.
        let json = """
        {"schema":"chiron.attestation/1","spans":[
          {"text":"The tank is full.","verdict":"REFUSED"},
          {"text":"The tank is full.","verdict":"REFUSED"}]}
        """
        let rec = try JSONDecoder().decode(AttestationRecord.self, from: Data(json.utf8))
        #expect(rec.spans.count == 2)
    }

    @Test func attestationRecordDecodes() throws {
        let rec = try JSONDecoder().decode(AttestationRecord.self,
                                           from: fixture("attest_sample"))
        #expect(rec.schema == "chiron.attestation/1")
        #expect(!rec.spans.isEmpty)
        let known: Set<Verdict> = [.verified, .refuted, .refused]
        #expect(rec.spans.allSatisfy { known.contains($0.verdict) })
        // The fixture had candidates yet still refused every span — refusal
        // decoding intact is exactly what this test protects.
        #expect(rec.spans.allSatisfy { $0.verdict == .refused })
        #expect(rec.traceableWordFraction != nil)
    }

    @Test func certificateDecodes() throws {
        let cert = try JSONDecoder().decode(Certificate.self,
                                            from: fixture("certify_sample"))
        #expect(cert.schema == "primus.certificate/2")
        #expect(cert.counts?.verified == 1)
        #expect(cert.claims.contains { $0.status == .verified })
        #expect(cert.attestation?.kind == "tamper-evident-hash")
    }

    @Test func unknownVerdictSurvivesDecoding() throws {
        // The wrapper preserves an unexpected word instead of crashing —
        // and instead of silently mapping it onto the real vocabulary.
        let v = try JSONDecoder().decode(Verdict.self,
                                         from: Data("\"SOMETHING_NEW\"".utf8))
        #expect(v.rawValue == "SOMETHING_NEW")
        #expect(v != .verified && v != .refuted && v != .refused)
    }
}
