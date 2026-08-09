// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

/// # Cloud proposers
///
/// OpenAI and Anthropic reach the vault through exactly the same door the
/// on-device model uses: they return spans of the user's own text, and
/// `GroundingFilter` rejects anything that is not literally present before it
/// can go anywhere near the engine. A frontier model that invents a plausible
/// sentence is discarded by the same code that discards an on-device one.
///
/// Nothing here can express a verdict, for the same structural reason stated
/// in `ClaimProposal.swift`: `ProposedClaim` has no field for one.
///
/// Two things a cloud proposer must do that a local one does not:
///
/// 1. **Never run implicitly.** Sending a user's document to a third party is
///    a disclosure. It requires a credential *and* explicit network
///    authorization, and the absence of either is reported rather than
///    silently downgraded.
/// 2. **Never ship its own key.** Credentials come from a store the operator
///    controls. There is no bundled key and no default endpoint override.

/// Which model provider a proposer speaks to.
public enum ProviderKind: String, Sendable, Equatable, CaseIterable {
    case appleOnDevice
    case openAI
    case anthropic

    public var displayName: String {
        switch self {
        case .appleOnDevice: "Apple on-device"
        case .openAI: "OpenAI"
        case .anthropic: "Anthropic"
        }
    }

    /// Whether using this provider discloses the user's text off the device.
    /// The router treats this as a privacy classification, not a preference.
    public var leavesTheDevice: Bool { self != .appleOnDevice }
}

/// Where a provider credential comes from. Never the app bundle.
///
/// The app supplies a Keychain-backed implementation; the CLI and tests supply
/// an environment-backed one. Keeping this a protocol is what stops a key from
/// being compiled into a shipped binary — there is no concrete default that
/// could hold one.
public protocol ProviderCredentialStore: Sendable {
    func credential(for provider: ProviderKind) -> String?
}

/// Reads `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` from the process environment.
///
/// Suitable for the CLI and for a developer machine. Not suitable for a
/// shipped app: on iOS the environment is not where an operator can put a
/// secret, and Keychain is.
public struct EnvironmentCredentialStore: ProviderCredentialStore {
    public init() {}

    public func credential(for provider: ProviderKind) -> String? {
        let name: String
        switch provider {
        case .openAI: name = "OPENAI_API_KEY"
        case .anthropic: name = "ANTHROPIC_API_KEY"
        case .appleOnDevice: return nil
        }
        guard let value = ProcessInfo.processInfo.environment[name],
              !value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
        else { return nil }
        return value
    }
}

/// An explicit, operator-controlled switch for leaving the device at all.
///
/// Separate from the credential on purpose. Holding a key is not consent to
/// use it, and a build that is configured must still be able to run entirely
/// offline without silently reaching the network.
public struct NetworkAuthorization: Sendable, Equatable {
    public let allowsProviderCalls: Bool
    public init(allowsProviderCalls: Bool) {
        self.allowsProviderCalls = allowsProviderCalls
    }
    /// The default posture. Deterministic checking is unaffected by it.
    public static let denied = NetworkAuthorization(allowsProviderCalls: false)
    public static let granted = NetworkAuthorization(allowsProviderCalls: true)
}

/// The HTTP dependency, injected so adapter behaviour is testable without a
/// network, an account, or a bill.
public protocol ProviderTransport: Sendable {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

public struct URLSessionTransport: ProviderTransport {
    let session: URLSession
    public init(session: URLSession = .shared) { self.session = session }

    public func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        let (data, response) = try await session.data(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw ProposerError.generationFailed
        }
        return (data, http)
    }
}

/// A proposer backed by a hosted model.
///
/// The prompt asks for verbatim spans and a check kind drawn from a closed
/// list. Unlike the on-device path there is no compiler-enforced schema, so
/// the response is decoded into the same closed shape and anything that does
/// not fit is dropped rather than coerced — an unrecognised kind becomes
/// `undetermined`, never a guess, and never a verdict.
public struct CloudClaimProposer: ClaimProposer {
    public let provider: ProviderKind
    let credentials: ProviderCredentialStore
    let authorization: NetworkAuthorization
    let transport: ProviderTransport
    let model: String

    public init(provider: ProviderKind,
                credentials: ProviderCredentialStore,
                authorization: NetworkAuthorization,
                transport: ProviderTransport = URLSessionTransport(),
                model: String? = nil) {
        self.provider = provider
        self.credentials = credentials
        self.authorization = authorization
        self.transport = transport
        self.model = model ?? Self.defaultModel(for: provider)
    }

    /// Current default models. Named in one place so a change is one edit and
    /// not a search through call sites.
    static func defaultModel(for provider: ProviderKind) -> String {
        switch provider {
        case .openAI: "gpt-5.1"
        case .anthropic: "claude-sonnet-5"
        case .appleOnDevice: ""
        }
    }

    /// Larger than the on-device bound: a hosted context window is bigger.
    /// Still bounded — the caller chunks, this type refuses rather than
    /// silently truncating a document into a misleading excerpt.
    public static let maximumInputBytes = 100_000

    public var availability: ProposerAvailability {
        guard provider.leavesTheDevice else { return .frameworkUnavailable }
        guard authorization.allowsProviderCalls else { return .networkNotAuthorized }
        guard credentials.credential(for: provider) != nil else {
            return .credentialMissing(provider)
        }
        return .available
    }

    public func proposeClaims(in text: String) async throws -> ProposalResult {
        // Re-checked at call time, not just at construction: authorization can
        // be withdrawn between the two, and the failure must be an error the
        // caller sees rather than an empty result that reads like "nothing to
        // check here".
        let current = availability
        guard current.canRun else { throw ProposerError.unavailable(current) }

        let byteCount = text.utf8.count
        guard byteCount <= Self.maximumInputBytes else {
            throw ProposerError.inputTooLarge(limit: Self.maximumInputBytes,
                                              actual: byteCount)
        }
        guard let key = credentials.credential(for: provider) else {
            throw ProposerError.unavailable(.credentialMissing(provider))
        }

        let request = try buildRequest(text: text, key: key)
        let (data, response) = try await transport.send(request)
        guard (200..<300).contains(response.statusCode) else {
            throw ProposerError.providerRejected(status: response.statusCode)
        }
        let spans = try Self.decodeSpans(from: data, provider: provider)
        let proposals = spans.map { (text: $0.quote, rationale: $0.kind.label) }
        // The same grounding gate the on-device path uses. A hosted model gets
        // no more trust than a local one.
        return GroundingFilter.ground(proposals: proposals, in: text)
    }

    // MARK: - Wire format

    func buildRequest(text: String, key: String) throws -> URLRequest {
        var request: URLRequest
        var body: [String: Any]

        switch provider {
        case .openAI:
            request = URLRequest(url: URL(string: "https://api.openai.com/v1/chat/completions")!)
            request.setValue("Bearer \(key)", forHTTPHeaderField: "Authorization")
            body = [
                "model": model,
                "messages": [
                    ["role": "system", "content": Self.instructions],
                    ["role": "user", "content": text],
                ],
                "response_format": ["type": "json_object"],
            ]
        case .anthropic:
            request = URLRequest(url: URL(string: "https://api.anthropic.com/v1/messages")!)
            request.setValue(key, forHTTPHeaderField: "x-api-key")
            request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
            body = [
                "model": model,
                "max_tokens": 2048,
                "system": Self.instructions,
                "messages": [["role": "user", "content": text]],
            ]
        case .appleOnDevice:
            throw ProposerError.unavailable(.frameworkUnavailable)
        }

        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONSerialization.data(withJSONObject: body)
        request.timeoutInterval = 60
        return request
    }

    /// What the hosted model is asked for. Deliberately the same shape the
    /// on-device `@Generable` type enforces, so both paths return the same
    /// thing and the grounding filter does not need to know which ran.
    static let instructions = """
        You are given a document. Return JSON of the form
        {"spans":[{"quote":"...","kind":"..."}]}.

        Each `quote` must be copied from the document word for word, with no \
        changes, corrections, or paraphrase. Do not quote anything that is not \
        in the document.

        Each `kind` must be exactly one of: aggregate, arithmetic, binomial, \
        closed_form, date_arithmetic, modular, percentage, primality, \
        sequence, sequence_continuation, undetermined.

        Never state whether a statement is true or false. You are selecting \
        which statements are worth checking, not checking them. Return an \
        empty list if nothing in the document is a checkable factual claim.
        """

    struct WireSpan { let quote: String; let kind: ProposedKind }

    /// The closed kind list, mirrored for the cloud path where no compiler
    /// enforces it. An unrecognised string becomes `undetermined` rather than
    /// being passed through — free text from a provider never reaches the UI.
    enum ProposedKind: String {
        case aggregate, arithmetic, binomial
        case closedForm = "closed_form"
        case dateArithmetic = "date_arithmetic"
        case modular, percentage, primality, sequence
        case sequenceContinuation = "sequence_continuation"
        case undetermined

        var label: String {
            switch self {
            case .aggregate: "aggregate"
            case .arithmetic: "arithmetic"
            case .binomial: "binomial"
            case .closedForm: "closed form"
            case .dateArithmetic: "date arithmetic"
            case .modular: "modular"
            case .percentage: "percentage"
            case .primality: "primality"
            case .sequence: "sequence"
            case .sequenceContinuation: "sequence continuation"
            case .undetermined: "kind undetermined"
            }
        }
    }

    static func decodeSpans(from data: Data, provider: ProviderKind) throws -> [WireSpan] {
        guard let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { throw ProposerError.generationFailed }

        // Both providers wrap the model's text differently; unwrap to the
        // JSON string the model actually produced.
        let payload: String?
        switch provider {
        case .openAI:
            let choices = root["choices"] as? [[String: Any]]
            let message = choices?.first?["message"] as? [String: Any]
            payload = message?["content"] as? String
        case .anthropic:
            let content = root["content"] as? [[String: Any]]
            payload = content?.first(where: { $0["type"] as? String == "text" })?["text"] as? String
        case .appleOnDevice:
            payload = nil
        }
        guard let payload,
              let inner = try? JSONSerialization.jsonObject(with: Data(payload.utf8))
                as? [String: Any],
              let raw = inner["spans"] as? [[String: Any]]
        else { throw ProposerError.generationFailed }

        return raw.compactMap { entry in
            guard let quote = entry["quote"] as? String, !quote.isEmpty else { return nil }
            let kind = ProposedKind(rawValue: (entry["kind"] as? String) ?? "") ?? .undetermined
            return WireSpan(quote: quote, kind: kind)
        }
    }
}
