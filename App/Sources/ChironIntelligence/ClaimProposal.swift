// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

/// # The boundary this module exists to enforce
///
/// A language model is an interpretation layer here, never an authority. It
/// may point at text that *looks* checkable; only the canonical Primus engine
/// decides whether something is `VERIFIED`, `REFUTED`, or `REFUSED`.
///
/// That rule is enforced structurally rather than by convention: nothing in
/// this file can express a verdict. `ProposedClaim` has no status, no score,
/// no confidence, and no certificate. The only thing a proposer can do is
/// hand back a span of the user's own text for the engine to certify.
///
/// A model that says "this is true" is therefore not merely discouraged — it
/// has no field in which to say it.

/// Why a proposer can or cannot run right now. Reported honestly: a
/// proposer that cannot run must say so rather than return an empty result
/// that reads like "nothing to check here".
public enum ProposerAvailability: Sendable, Equatable {
    case available
    /// The framework exists but this OS is older than the model requires.
    case unsupportedOS
    /// Built without the framework at all (for example, Linux).
    case frameworkUnavailable
    case deviceNotEligible
    case appleIntelligenceNotEnabled
    case modelNotReady
    /// The operator turned model assistance off. Deterministic paths remain.
    case disabledByOperator
    /// A hosted provider is configured but leaving the device has not been
    /// authorized. Holding a key is not consent to use it.
    case networkNotAuthorized
    /// Network use is authorized but no credential exists for this provider.
    case credentialMissing(ProviderKind)

    public var canRun: Bool { self == .available }

    /// Text intended for a user, not a log line. It never implies that an
    /// unavailable model would have produced a better answer.
    public var explanation: String {
        switch self {
        case .available:
            "The on-device model is available. It proposes claims; the engine still decides."
        case .unsupportedOS:
            "This system is older than the on-device model requires. Deterministic checking is unaffected."
        case .frameworkUnavailable:
            "This build has no on-device model framework. Deterministic checking is unaffected."
        case .deviceNotEligible:
            "This device does not support the on-device model. Deterministic checking is unaffected."
        case .appleIntelligenceNotEnabled:
            "Apple Intelligence is not enabled in Settings. Deterministic checking is unaffected."
        case .modelNotReady:
            "The on-device model is still downloading or preparing. Deterministic checking is unaffected."
        case .disabledByOperator:
            "Model assistance is turned off. Deterministic checking is unaffected."
        case .networkNotAuthorized:
            "Sending text to a hosted model is not authorized, so no request was made. Deterministic checking is unaffected."
        case .credentialMissing(let provider):
            "No \(provider.displayName) credential is configured, so no request was made. Deterministic checking is unaffected."
        }
    }
}

/// A span of the *source text* that a proposer believes is worth certifying.
///
/// `text` is required to be a verbatim substring of the input. It is not a
/// paraphrase, not a normalization, and not a restatement — because the engine
/// certifies text, and a paraphrase is a different claim than the one the user
/// actually wrote.
public struct ProposedClaim: Sendable, Equatable {
    /// Verbatim source text. Checked against the input by `GroundingFilter`.
    public let text: String
    /// UTF-8 byte offsets into the source, so a caller can highlight the span
    /// without re-searching and without trusting the model's arithmetic.
    public let byteRange: Range<Int>
    /// Why the proposer surfaced this span. Explanatory only; it is never
    /// evidence, and it never travels into a certificate.
    public let rationale: String

    public init(text: String, byteRange: Range<Int>, rationale: String) {
        self.text = text
        self.byteRange = byteRange
        self.rationale = rationale
    }
}

/// What a proposer rejected, and why. Kept because a silently dropped
/// hallucination is indistinguishable from a model that found nothing.
public struct RejectedProposal: Sendable, Equatable {
    public enum Reason: Sendable, Equatable {
        /// The model returned text that does not occur in the source at all.
        case notPresentInSource
        /// The text *is* in the source, but every occurrence was already
        /// claimed by an earlier proposal. Distinct from `notPresentInSource`
        /// on purpose: reporting a duplicate as an invention is a false
        /// accusation against the model, and a gate that invents errors is
        /// worth no more than one that misses them.
        case alreadyAttributed
        case empty
        case tooLong(limit: Int)
    }

    public let text: String
    public let reason: Reason
}

public struct ProposalResult: Sendable, Equatable {
    public let claims: [ProposedClaim]
    public let rejected: [RejectedProposal]

    public init(claims: [ProposedClaim], rejected: [RejectedProposal]) {
        self.claims = claims
        self.rejected = rejected
    }
}

public enum ProposerError: Error, Sendable, Equatable {
    case unavailable(ProposerAvailability)
    case inputTooLarge(limit: Int, actual: Int)
    case generationFailed
    /// The provider answered with a non-2xx status. Surfaced as itself rather
    /// than folded into `generationFailed`, because a 401 and a 429 call for
    /// different operator action and neither is a modelling failure.
    case providerRejected(status: Int)
}

/// Anything that can point at candidate spans. Deliberately tiny: a proposer
/// takes text and returns spans of that same text.
public protocol ClaimProposer: Sendable {
    var availability: ProposerAvailability { get }
    func proposeClaims(in text: String) async throws -> ProposalResult
}

/// Rejects any proposal that is not literally present in the source.
///
/// This is the load-bearing defence against a fluent model inventing a
/// plausible sentence and having it certified as though the user wrote it. It
/// is pure and synchronous precisely so it can be tested without a model, on
/// any machine, including one with no Apple Intelligence hardware.
public enum GroundingFilter {
    /// Longest span accepted from a proposer. A model that returns the whole
    /// document has not proposed a claim.
    public static let maximumClaimBytes = 2_000

    public static func ground(proposals: [(text: String, rationale: String)],
                              in source: String) -> ProposalResult {
        let sourceBytes = Array(source.utf8)
        var claims: [ProposedClaim] = []
        var rejected: [RejectedProposal] = []
        // A source span is consumed once, so a model repeating itself cannot
        // inflate the claim count for the same sentence.
        var consumed: [Range<Int>] = []

        for proposal in proposals {
            let trimmed = proposal.text.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty else {
                rejected.append(.init(text: proposal.text, reason: .empty))
                continue
            }
            let needle = Array(trimmed.utf8)
            guard needle.count <= maximumClaimBytes else {
                rejected.append(.init(text: trimmed,
                                      reason: .tooLong(limit: maximumClaimBytes)))
                continue
            }
            guard let range = firstOccurrence(of: needle, in: sourceBytes,
                                              skipping: consumed) else {
                // Two different failures reach this branch. Either the
                // document does not say this — the model invented it, or
                // corrected it — or the document does say it and every
                // occurrence is already spoken for. Only the first is the
                // model's fault, so they are not reported as the same thing.
                let stillAbsent = firstOccurrence(of: needle, in: sourceBytes,
                                                  skipping: []) == nil
                rejected.append(.init(text: trimmed,
                                      reason: stillAbsent ? .notPresentInSource
                                                          : .alreadyAttributed))
                continue
            }
            consumed.append(range)
            // Always quote the *source*, never the model's rendering of it.
            // A live on-device run returned "the product of 6 and 7 is 41"
            // where the document says "The product…"; matching ASCII-case
            // -insensitively recovers that span, but the text carried forward
            // is the document's own bytes, so nothing downstream ever certifies
            // a string the user did not write.
            let verbatim = String(decoding: sourceBytes[range], as: UTF8.self)
            claims.append(.init(text: verbatim, byteRange: range,
                                rationale: proposal.rationale))
        }
        return ProposalResult(claims: claims, rejected: rejected)
    }

    /// ASCII case folding only. Unicode case conversion can change a string's
    /// byte length, which would silently corrupt the offsets this type
    /// promises; non-ASCII bytes are therefore compared exactly. Digits are
    /// unaffected by folding, so a model that "fixes" 41 to 42 still fails to
    /// match — the correction is rejected, only the capitalization is forgiven.
    private static func foldASCII(_ byte: UInt8) -> UInt8 {
        (65...90).contains(byte) ? byte + 32 : byte
    }

    private static func firstOccurrence(of needle: [UInt8], in haystack: [UInt8],
                                        skipping consumed: [Range<Int>]) -> Range<Int>? {
        guard !needle.isEmpty, needle.count <= haystack.count else { return nil }
        let folded = needle.map(foldASCII)
        let last = haystack.count - needle.count
        var start = 0
        while start <= last {
            let candidate = start..<(start + needle.count)
            if haystack[candidate].map(foldASCII) == folded,
               !consumed.contains(where: { $0.overlaps(candidate) }) {
                return candidate
            }
            start += 1
        }
        return nil
    }
}

/// The proposer used when no model can run. It reports the real reason and
/// refuses, rather than returning an empty list that a caller might read as
/// "the model checked and found nothing".
public struct UnavailableProposer: ClaimProposer {
    public let availability: ProposerAvailability

    public init(availability: ProposerAvailability) {
        self.availability = availability
    }

    public func proposeClaims(in text: String) async throws -> ProposalResult {
        throw ProposerError.unavailable(availability)
    }
}
