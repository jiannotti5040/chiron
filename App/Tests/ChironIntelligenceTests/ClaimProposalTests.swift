// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import XCTest
@testable import ChironIntelligence

/// These gates run on any machine, including one with no Apple Intelligence
/// hardware, because the property under test is not "the model is smart" — it
/// is "nothing the model says can become a claim unless the user wrote it".
final class GroundingFilterTests: XCTestCase {
    private let source = "The sum of 2 and 2 is 4. The product of 3 and 4 is 11."

    func testVerbatimSpansAreKeptWithCorrectByteRanges() {
        let result = GroundingFilter.ground(
            proposals: [("The sum of 2 and 2 is 4", "arithmetic"),
                        ("The product of 3 and 4 is 11", "arithmetic")],
            in: source)

        XCTAssertTrue(result.rejected.isEmpty)
        XCTAssertEqual(result.claims.count, 2)
        // The offsets must actually address the quoted text, so a caller can
        // highlight the span without trusting the model's arithmetic.
        let bytes = Array(source.utf8)
        for claim in result.claims {
            let slice = String(decoding: bytes[claim.byteRange], as: UTF8.self)
            XCTAssertEqual(slice, claim.text)
        }
    }

    /// The failure this whole module exists to prevent: a fluent model
    /// producing a sentence that was never in the document.
    func testInventedTextIsRejectedRatherThanCertified() {
        let result = GroundingFilter.ground(
            proposals: [("The sum of 5 and 5 is 10", "arithmetic")],
            in: source)

        XCTAssertTrue(result.claims.isEmpty,
                      "text absent from the source must never become a claim")
        XCTAssertEqual(result.rejected.first?.reason, .notPresentInSource)
    }

    /// A near-miss is the dangerous case: a model that "helpfully" corrects
    /// 11 to 12 would otherwise get its own correction certified as the
    /// user's claim, and the refutation would silently disappear.
    func testASilentCorrectionIsRejectedBecauseItIsNotWhatTheSourceSays() {
        let result = GroundingFilter.ground(
            proposals: [("The product of 3 and 4 is 12", "arithmetic")],
            in: source)

        XCTAssertTrue(result.claims.isEmpty)
        XCTAssertEqual(result.rejected.first?.reason, .notPresentInSource)
    }

    /// Normalization is the same failure wearing a different hat.
    func testParaphraseAndReNormalizationAreRejected() {
        let result = GroundingFilter.ground(
            proposals: [("the sum of two and two is four", "paraphrase"),
                        ("2 + 2 = 4", "normalized")],
            in: source)

        XCTAssertTrue(result.claims.isEmpty)
        XCTAssertEqual(result.rejected.count, 2)
    }

    /// Regression from a live on-device run: the model returned
    /// "the product of 3 and 4 is 11" where the source capitalizes "The".
    /// Recovering that span is a recall win with no honesty cost, because the
    /// claim carried forward is the source's own text, not the model's.
    func testCapitalizationDriftRecoversTheSpanButQuotesTheSource() {
        let result = GroundingFilter.ground(
            proposals: [("the product of 3 and 4 is 11", "arithmetic")],
            in: source)

        XCTAssertTrue(result.rejected.isEmpty)
        XCTAssertEqual(result.claims.first?.text, "The product of 3 and 4 is 11",
                       "the claim must be the document's text, not the model's")
        let bytes = Array(source.utf8)
        let claim = try! XCTUnwrap(result.claims.first)
        XCTAssertEqual(String(decoding: bytes[claim.byteRange], as: UTF8.self), claim.text)
    }

    /// Case folding must forgive capitalization and nothing else. A changed
    /// digit is a different claim, and stays rejected.
    func testCaseFoldingDoesNotForgiveAChangedNumber() {
        let result = GroundingFilter.ground(
            proposals: [("the product of 3 and 4 is 12", "corrected")],
            in: source)

        XCTAssertTrue(result.claims.isEmpty)
        XCTAssertEqual(result.rejected.first?.reason, .notPresentInSource)
    }

    func testARepeatedProposalCannotDoubleCountTheSameSpan() {
        let result = GroundingFilter.ground(
            proposals: [("The sum of 2 and 2 is 4", "first"),
                        ("The sum of 2 and 2 is 4", "again")],
            in: source)

        XCTAssertEqual(result.claims.count, 1)
        // The de-duplication is the point of this test and still holds: one
        // claim, not two. But the *reason* given for the discard used to be
        // `.notPresentInSource` — the filter could not tell "the document
        // never said this" apart from "the document said it once and it is
        // already spoken for", and reported both as an invention. This
        // assertion pinned that conflation in place.
        XCTAssertEqual(result.rejected.first?.reason, .alreadyAttributed)
    }

    /// The two discard reasons must stay distinguishable: a sentence the
    /// document genuinely does not contain is the model's error, a second
    /// mention of a sentence it does contain is not.
    func testAnAbsentProposalAndARepeatAreNotGivenTheSameReason() {
        let result = GroundingFilter.ground(
            proposals: [("The sum of 2 and 2 is 4", "first"),
                        ("The sum of 2 and 2 is 4", "again"),
                        ("The sum of 2 and 2 is 5", "invented")],
            in: source)

        XCTAssertEqual(result.claims.count, 1)
        XCTAssertEqual(result.rejected.count, 2)
        XCTAssertEqual(result.rejected.first?.reason, .alreadyAttributed)
        XCTAssertEqual(result.rejected.last?.reason, .notPresentInSource)
    }

    func testWholeDocumentAndEmptyProposalsAreRefused() {
        let huge = String(repeating: "a", count: GroundingFilter.maximumClaimBytes + 1)
        let result = GroundingFilter.ground(
            proposals: [(huge, "everything"), ("   ", "nothing")],
            in: huge)

        XCTAssertTrue(result.claims.isEmpty)
        XCTAssertEqual(result.rejected.count, 2)
        XCTAssertEqual(result.rejected.first?.reason,
                       .tooLong(limit: GroundingFilter.maximumClaimBytes))
        XCTAssertEqual(result.rejected.last?.reason, .empty)
    }

    func testMultiByteSourceOffsetsStayValid() {
        let unicode = "Le total de 2 et 2 est 4 — vérifié. Naïve café 3 × 4 = 11."
        let result = GroundingFilter.ground(
            proposals: [("3 × 4 = 11", "arithmetic")], in: unicode)

        XCTAssertEqual(result.claims.count, 1)
        let bytes = Array(unicode.utf8)
        let claim = try! XCTUnwrap(result.claims.first)
        XCTAssertEqual(String(decoding: bytes[claim.byteRange], as: UTF8.self),
                       "3 × 4 = 11")
    }
}

final class ProposerAvailabilityTests: XCTestCase {
    /// An unavailable model must refuse, not return an empty result that a
    /// caller could read as "checked, nothing found".
    func testAnUnavailableProposerRefusesInsteadOfReturningNothing() async {
        let proposer = UnavailableProposer(availability: .appleIntelligenceNotEnabled)
        do {
            _ = try await proposer.proposeClaims(in: "The sum of 2 and 2 is 4.")
            XCTFail("an unavailable proposer must not return a result")
        } catch ProposerError.unavailable(let availability) {
            XCTAssertEqual(availability, .appleIntelligenceNotEnabled)
            XCTAssertFalse(availability.canRun)
        } catch {
            XCTFail("unexpected error: \(error)")
        }
    }

    func testOperatorDisabledRoutingNeverReachesTheModel() {
        let proposer = ProposerRouter.proposer(modelAssistanceEnabled: false)
        XCTAssertEqual(proposer.availability, .disabledByOperator)
    }

    /// Whatever this machine reports, the reason must be a real one and the
    /// explanation must never suggest deterministic checking is degraded.
    func testAvailabilityIsReportedHonestlyOnThisMachine() {
        let availability = AppleFoundationModelProposer().availability
        XCTAssertFalse(availability.explanation.isEmpty)
        if !availability.canRun {
            XCTAssertTrue(availability.explanation.contains("Deterministic checking is unaffected"),
                          "an unavailable model must not imply the engine is weakened")
        }
        // Record what this host actually reported, so a run on other hardware
        // is comparable rather than guessed at.
        print("[chiron] on-device model availability: \(availability)")
    }
}

/// Actually runs Apple's on-device model. Skipped unless an operator opts in,
/// because model output is nondeterministic and a gate that depends on it must
/// not be able to fail the build for the wrong reason.
///
///     CHIRON_LIVE_MODEL=1 swift test --scratch-path /tmp/chiron-build
///
/// What is asserted is not the model's taste — it is the invariant: whatever
/// it returns, every surviving claim is verbatim source text.
final class LiveAppleModelTests: XCTestCase {
    func testEveryClaimTheLiveModelProducesIsVerbatimSourceText() async throws {
        guard ProcessInfo.processInfo.environment["CHIRON_LIVE_MODEL"] == "1" else {
            throw XCTSkip("Set CHIRON_LIVE_MODEL=1 to exercise the on-device model.")
        }
        let proposer = AppleFoundationModelProposer()
        guard proposer.availability.canRun else {
            throw XCTSkip("On-device model unavailable here: \(proposer.availability)")
        }

        let source = """
            Q3 revenue was 4200 and Q4 revenue was 3100, so the total of 4200 \
            and 3100 is 7300. The product of 6 and 7 is 41. Morale improved.
            """
        let result = try await proposer.proposeClaims(in: source)

        let bytes = Array(source.utf8)
        for claim in result.claims {
            XCTAssertEqual(String(decoding: bytes[claim.byteRange], as: UTF8.self),
                           claim.text,
                           "a surviving claim must address its own span exactly")
            XCTAssertTrue(source.contains(claim.text),
                          "a surviving claim must be verbatim source text")
        }
        print("[chiron] live model kept \(result.claims.count), rejected \(result.rejected.count)")
        for claim in result.claims { print("  kept: \(claim.text)") }
        for reject in result.rejected { print("  rejected (\(reject.reason)): \(reject.text)") }
    }
}
