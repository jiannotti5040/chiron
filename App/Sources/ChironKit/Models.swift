// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

// The vault's vocabulary, unchanged: VERIFIED / REFUTED / REFUSED. Kept as a
// raw-value wrapper rather than an enum so an engine that one day emits a new
// word does not crash the decoder — but no synonym set is ever invented here.
public struct Verdict: RawRepresentable, Codable, Sendable, Hashable {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }

    public static let verified = Verdict(rawValue: "VERIFIED")
    public static let refuted = Verdict(rawValue: "REFUTED")
    public static let refused = Verdict(rawValue: "REFUSED")
}

public struct StageStatus: RawRepresentable, Codable, Sendable, Hashable {
    public let rawValue: String
    public init(rawValue: String) { self.rawValue = rawValue }

    public static let ok = StageStatus(rawValue: "OK")
    public static let skipped = StageStatus(rawValue: "SKIPPED")
    public static let error = StageStatus(rawValue: "ERROR")
}

// MARK: - chiron.full_stack/1

public struct FullStackRecord: Codable, Sendable {
    public let schema: String
    public let text: String
    public let numericSurface: [Int]
    public let stagesRun: Int
    public let tally: [String: Int]
    public let elapsedMs: Double
    public let layers: [String]
    public let results: [StageResult]
    public let scope: String

    enum CodingKeys: String, CodingKey {
        case schema, text, tally, layers, results, scope
        case numericSurface = "numeric_surface"
        case stagesRun = "stages_run"
        case elapsedMs = "elapsed_ms"
    }
}

// Deliberately NOT Identifiable. A record can legitimately contain two
// stages, spans, or claims with identical content — attest returns one span
// per sentence, and a repeated sentence is a repeated span. Views index by
// position instead, so nothing depends on content being unique.
public struct StageResult: Codable, Sendable {
    public let layer: String
    public let module: String
    public let fn: String
    public let asks: String
    public let status: StageStatus
    public let ms: Double?
    public let reason: String?
    public let error: String?
    public let result: JSONValue?
}

// MARK: - chiron.attestation/1

public struct AttestationRecord: Codable, Sendable {
    public let schema: String
    public let spans: [AttestSpan]
    public let counts: [String: Int]?
    public let spanTotal: Int?
    public let attributed: Int?
    public let unattributable: Int?
    public let contentWords: Int?
    public let novelContentWords: Int?
    public let traceableWordFraction: Double?
    public let machineWarranted: Double?
    public let humanOwned: Double?
    public let candidateInputs: [String]?
    public let scope: String?

    enum CodingKeys: String, CodingKey {
        case schema, spans, counts, attributed, unattributable, scope
        case spanTotal = "span_total"
        case contentWords = "content_words"
        case novelContentWords = "novel_content_words"
        case traceableWordFraction = "traceable_word_fraction"
        case machineWarranted = "machine_warranted"
        case humanOwned = "human_owned"
        case candidateInputs = "candidate_inputs"
    }
}

public struct AttestSpan: Codable, Sendable {
    public let text: String
    public let verdict: Verdict
    public let origin: String?
    public let originDelta: Double?
    public let originCosine: Double?
    public let originMargin: Double?
    public let checkedAgainst: String?
    public let groundTruth: JSONValue?
    public let asserted: JSONValue?
    public let reason: String?
    public let owner: String?
    public let blame: [String]?
    public let tokens: [JSONValue]?
    public let novelContentWords: [String]?
    public let traceableFraction: Double?

    enum CodingKeys: String, CodingKey {
        case text, verdict, origin, reason, owner, blame, tokens, asserted
        case originDelta = "origin_delta"
        case originCosine = "origin_cosine"
        case originMargin = "origin_margin"
        case checkedAgainst = "checked_against"
        case groundTruth = "ground_truth"
        case novelContentWords = "novel_content_words"
        case traceableFraction = "traceable_fraction"
    }
}

// MARK: - primus.certificate/2

public struct Certificate: Codable, Sendable {
    public let schema: String
    public let engine: Engine?
    public let owner: String?
    public let createdUTC: String?
    public let input: InputDigest?
    public let claims: [Claim]
    public let counts: Counts?
    public let coverage: Double?
    public let claimsCapped: Bool?
    public let unverifiableRemainder: Bool?
    public let verdict: String?
    public let attestation: Attestation?

    enum CodingKeys: String, CodingKey {
        case schema, engine, owner, input, claims, counts, coverage
        case verdict, attestation
        case createdUTC = "created_utc"
        case claimsCapped = "claims_capped"
        case unverifiableRemainder = "unverifiable_remainder"
    }

    public struct Engine: Codable, Sendable {
        public let name: String
        public let version: String
    }

    public struct InputDigest: Codable, Sendable {
        public let sha256: String
        public let chars: Int
        public let truncated: Bool
    }

    public struct Counts: Codable, Sendable {
        public let checkable: Int
        public let verified: Int
        public let refuted: Int
        public let refused: Int
    }

    public struct Attestation: Codable, Sendable {
        public let sha256: String
        public let kind: String
    }

    public struct Claim: Codable, Sendable {
        public let kind: String
        public let text: String
        public let status: Verdict
        public let span: [Int]?
        public let operation: String?
        public let nValues: Int?
        public let expected: JSONValue?
        public let reason: String?
        public let detail: String?

        enum CodingKeys: String, CodingKey {
            case kind, text, status, span, operation, expected, reason, detail
            case nValues = "n_values"
        }
    }
}
