// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
#if canImport(FoundationModels)
import FoundationModels
#endif

/// Apple's on-device system language model, used strictly as a proposer.
///
/// It is chosen here for the reasons it is actually good: the text never
/// leaves the device, it works offline, and it needs no credential. It is
/// *not* used as a judge. The engine still certifies every span it returns,
/// and `GroundingFilter` discards anything the model did not read verbatim
/// out of the user's own text.
///
/// Availability is reported rather than assumed. On a machine without Apple
/// Intelligence this type still compiles, still constructs, and still answers
/// `availability` honestly — it simply refuses to generate.
public struct AppleFoundationModelProposer: ClaimProposer {
    /// Bounded so a large document cannot be pushed into a context window it
    /// does not fit. The caller chunks; this type does not silently truncate.
    public static let maximumInputBytes = 8_000

    public init() {}

    public var availability: ProposerAvailability {
        #if canImport(FoundationModels)
        if #available(macOS 26.0, iOS 26.0, visionOS 26.0, *) {
            switch SystemLanguageModel.default.availability {
            case .available:
                return .available
            case .unavailable(let reason):
                switch reason {
                case .deviceNotEligible: return .deviceNotEligible
                case .appleIntelligenceNotEnabled: return .appleIntelligenceNotEnabled
                case .modelNotReady: return .modelNotReady
                @unknown default: return .modelNotReady
                }
            @unknown default:
                return .modelNotReady
            }
        } else {
            return .unsupportedOS
        }
        #else
        return .frameworkUnavailable
        #endif
    }

    public func proposeClaims(in text: String) async throws -> ProposalResult {
        let availability = availability
        guard availability.canRun else { throw ProposerError.unavailable(availability) }

        let byteCount = text.utf8.count
        guard byteCount <= Self.maximumInputBytes else {
            throw ProposerError.inputTooLarge(limit: Self.maximumInputBytes,
                                              actual: byteCount)
        }

        #if canImport(FoundationModels)
        if #available(macOS 26.0, iOS 26.0, visionOS 26.0, *) {
            let session = LanguageModelSession(instructions: Self.instructions)
            let response: LanguageModelSession.Response<ProposedSpans>
            do {
                response = try await session.respond(to: text, generating: ProposedSpans.self)
            } catch {
                throw ProposerError.generationFailed
            }
            let proposals = response.content.spans.map {
                (text: $0.quote, rationale: $0.kind.label)
            }
            // Everything the model said is now treated as untrusted text and
            // checked against the source before it can go any further.
            return GroundingFilter.ground(proposals: proposals, in: text)
        }
        #endif
        throw ProposerError.unavailable(.unsupportedOS)
    }

    /// The instructions deliberately forbid the one thing a fluent model most
    /// wants to do: answer. Its job is to locate, quote, and stop.
    static let instructions = """
        You locate checkable statements. You never evaluate them.

        Given a document, return the exact statements that a deterministic \
        arithmetic or logic checker could test — for example sums, products, \
        counts, totals, percentages, dates, and comparisons.

        Rules you must follow:
        - Quote each statement word for word from the document. Never rewrite, \
        correct, normalize, complete, or translate it.
        - Never say whether a statement is true or false. Something else \
        decides that.
        - If the document contains nothing checkable, return no spans. Do not \
        invent one to be helpful.
        """
}

#if canImport(FoundationModels)
/// The structured output the model must fill in. Typed generation is used
/// instead of prose parsing so a malformed answer fails as a decode error
/// rather than as a confidently wrong claim.
///
/// Note what this schema cannot represent: there is no verdict, no
/// confidence, and no correction field. The model is given no vocabulary for
/// deciding anything.
///
/// That sentence used to be aspirational. `reason` was a free `String` whose
/// only restraint was a `@Guide` sentence asking the model not to judge, and
/// the panel rendered it verbatim beside the claim — so a verdict was one
/// disobeyed instruction away from the operator's screen. A prompt is not a
/// boundary. The field is now a closed enum: the model selects a symbol and
/// the app supplies every word the operator reads.
@available(macOS 26.0, iOS 26.0, visionOS 26.0, *)
@Generable
struct ProposedSpans {
    @Guide(description: "Statements quoted word for word from the document.")
    var spans: [ProposedSpan]
}

@available(macOS 26.0, iOS 26.0, visionOS 26.0, *)
@Generable
struct ProposedSpan {
    @Guide(description: "The statement copied exactly from the document, with no changes.")
    var quote: String

    @Guide(description: "Which kind of exact check this statement would need.")
    var kind: ProposedCheckKind
}

/// The ten gate kinds `primus.certify` can actually discharge, plus an honest
/// abstention. Taken from `add(m, "...")` in `Primus/src/primus/certify.py`
/// rather than invented here, so the proposer cannot suggest a check the
/// engine has no gate for.
///
/// A closed enum is the point. `VERIFIED`, `REFUTED`, and `REFUSED` belong to
/// the engine; nothing the model can emit here is expressible as any of them.
@available(macOS 26.0, iOS 26.0, visionOS 26.0, *)
@Generable
enum ProposedCheckKind {
    case aggregate
    case arithmetic
    case binomial
    case closedForm
    case dateArithmetic
    case modular
    case percentage
    case primality
    case sequence
    case sequenceContinuation
    /// The model could not place the statement in any gate kind. Recorded as
    /// such rather than guessed at.
    case undetermined

    /// The operator-facing wording. App-authored, never model-authored.
    var label: String {
        switch self {
        case .aggregate: return "aggregate"
        case .arithmetic: return "arithmetic"
        case .binomial: return "binomial"
        case .closedForm: return "closed form"
        case .dateArithmetic: return "date arithmetic"
        case .modular: return "modular"
        case .percentage: return "percentage"
        case .primality: return "primality"
        case .sequence: return "sequence"
        case .sequenceContinuation: return "sequence continuation"
        case .undetermined: return "kind undetermined"
        }
    }
}
#endif

/// Selects a proposer without pretending an unavailable model ran.
///
/// This is the whole routing policy for on-device assistance: use the model
/// when it is genuinely available and the operator allows it; otherwise return
/// a proposer that states the real reason. Deterministic certification does
/// not depend on the outcome either way.
public enum ProposerRouter {
    public static func proposer(modelAssistanceEnabled: Bool = true) -> any ClaimProposer {
        guard modelAssistanceEnabled else {
            return UnavailableProposer(availability: .disabledByOperator)
        }
        let apple = AppleFoundationModelProposer()
        guard apple.availability.canRun else {
            return UnavailableProposer(availability: apple.availability)
        }
        return apple
    }
}
