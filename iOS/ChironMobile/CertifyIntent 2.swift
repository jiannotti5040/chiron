// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import AppIntents
import Foundation
import ChironContract
import ChironService

/// Siri / Shortcuts / Spotlight entry point for the one operation that is
/// proven end to end: certify a piece of text.
///
/// The intent is deliberately read-only. It sends text the user supplied to
/// the service the user configured, and reports the engine's own disposition.
/// It stores nothing, mutates nothing, and — like every other interface here —
/// never restates a verdict in softer words.
@available(iOS 17.0, *)
struct CertifyTextIntent: AppIntent {
    static let title: LocalizedStringResource = "Certify Text"

    static let description = IntentDescription(
        """
        Checks the exactly checkable claims in a piece of text and reports \
        how many were verified, refuted, or refused. A pass means nothing \
        checkable was refuted — not that the text is true.
        """,
        categoryName: "Verification",
        searchKeywords: ["certify", "verify", "check", "claim", "chiron"])

    /// Nothing is sent anywhere until the user runs the intent, and the text
    /// is whatever they supplied to it.
    @Parameter(title: "Text", description: "The text whose claims should be certified.",
               inputOptions: String.IntentInputOptions(multiline: true))
    var text: String

    /// A verification result is worth reading, so surface it rather than
    /// silently succeeding in the background.
    static let openAppWhenRun: Bool = false

    func perform() async throws -> some IntentResult & ProvidesDialog {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else {
            return .result(dialog: "There was no text to certify.")
        }
        guard let raw = UserDefaults.standard.string(forKey: "chiron.service.endpoint"),
              let endpoint = try? ServiceEndpoint(text: raw) else {
            // An unconfigured endpoint is a setup state, not a verdict. Do not
            // let it read as "nothing was wrong with the text".
            return .result(dialog: """
                Chiron has no service configured yet. Open Chiron and set a \
                service endpoint under Connection, then run this again.
                """)
        }

        do {
            let client = try LocalServiceClient(
                baseURL: endpoint.url,
                authorizer: LocalServiceAuthorizer(nextBearerToken: {
                    KeychainTokenStore.read(for: endpoint.url)
                }))
            let certification = try await client.certify(text: trimmed)
            return .result(dialog: IntentDialog(stringLiteral: Self.summary(of: certification)))
        } catch let error as LocalServiceClientError {
            return .result(dialog: IntentDialog(stringLiteral: Self.message(for: error)))
        } catch {
            return .result(dialog: "The certification request could not be completed.")
        }
    }

    /// Reports the engine's counts in the engine's own vocabulary. It does not
    /// invent a score, a percentage of truth, or a pass/fail badge.
    static func summary(of certification: LocalServiceCertification) -> String {
        guard case .object(let certificate) = certification.certificate,
              case .object(let counts)? = certificate["counts"] else {
            return "A certificate came back, but it carried no counts to read."
        }
        func number(_ key: String) -> String {
            if case .number(let value)? = counts[key] { return value.rawValue }
            return "0"
        }
        let checkable = number("checkable")
        guard checkable != "0" else {
            return """
                Nothing in that text was exactly checkable, so nothing was \
                certified. That is not a statement that the text is correct.
                """
        }
        let refuted = number("refuted")
        let verified = number("verified")
        let refused = number("refused")
        let head = refuted == "0"
            ? "Nothing checkable was refuted."
            : "\(refuted) claim(s) were refuted."
        return """
            \(head) Of \(checkable) checkable claim(s): \(verified) verified, \
            \(refuted) refuted, \(refused) refused. The remaining free text is \
            unverifiable by exact methods and was not certified.
            """
    }

    static func message(for error: LocalServiceClientError) -> String {
        switch error {
        case .refusal(let refusal), .httpRefusal(_, let refusal):
            // A refusal is a result. Report it as one.
            return "The engine refused: \(refusal.reason)"
        case .transport(.offline):
            return "The Chiron service could not be reached from this device."
        case .transport(.timedOut):
            return "The Chiron service did not answer in time."
        case .requestTooLarge(let limit, _):
            return "That text is larger than the \(limit)-byte request bound."
        case .invalidEndpoint:
            return "The configured service endpoint is not valid."
        case .authorizationUnavailable, .invalidAuthorization:
            return "The stored credential for that service could not be used."
        default:
            return "The certification request could not be completed."
        }
    }
}

/// Exactly one phrase, for the one proven operation. Additional shortcuts are
/// not added speculatively: an intent that cannot complete is worse than an
/// intent that does not exist.
@available(iOS 17.0, *)
struct ChironShortcuts: AppShortcutsProvider {
    static var appShortcuts: [AppShortcut] {
        AppShortcut(
            intent: CertifyTextIntent(),
            phrases: [
                "Certify text with \(.applicationName)",
                "Check a claim with \(.applicationName)",
            ],
            shortTitle: "Certify Text",
            systemImageName: "checkmark.seal")
    }
}
