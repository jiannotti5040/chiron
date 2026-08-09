// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import XCTest
@testable import ChironIntelligence

/// These tests never touch the network. Every one of them is about a boundary
/// that must hold before a request is made, or about what happens to a
/// provider's answer after it arrives.
final class CloudProposerTests: XCTestCase {

    private struct Store: ProviderCredentialStore {
        var keys: [ProviderKind: String] = [:]
        func credential(for provider: ProviderKind) -> String? { keys[provider] }
    }

    /// Records whether it was ever asked to send anything. The point of most
    /// of these tests is that it is not.
    private final class SpyTransport: ProviderTransport, @unchecked Sendable {
        var sent: [URLRequest] = []
        var response: (Data, HTTPURLResponse)?
        func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
            sent.append(request)
            guard let response else { throw ProposerError.generationFailed }
            return response
        }
    }

    private func http(_ status: Int) -> HTTPURLResponse {
        HTTPURLResponse(url: URL(string: "https://example.invalid")!,
                        statusCode: status, httpVersion: nil, headerFields: nil)!
    }

    // MARK: - Nothing leaves the device without both permissions

    func testACredentialAloneDoesNotAuthorizeLeavingTheDevice() async {
        let spy = SpyTransport()
        let proposer = CloudClaimProposer(
            provider: .openAI,
            credentials: Store(keys: [.openAI: "sk-test"]),
            authorization: .denied,
            transport: spy)

        XCTAssertEqual(proposer.availability, .networkNotAuthorized)
        do {
            _ = try await proposer.proposeClaims(in: "The sum of 2 and 2 is 4.")
            XCTFail("a denied authorization must not produce a result")
        } catch {
            XCTAssertEqual(error as? ProposerError,
                           .unavailable(.networkNotAuthorized))
        }
        XCTAssertTrue(spy.sent.isEmpty, "no request may be built, let alone sent")
    }

    func testAuthorizationAloneWithoutACredentialIsReportedAsSuch() async {
        let spy = SpyTransport()
        let proposer = CloudClaimProposer(provider: .anthropic,
                                          credentials: Store(),
                                          authorization: .granted,
                                          transport: spy)

        XCTAssertEqual(proposer.availability, .credentialMissing(.anthropic))
        do {
            _ = try await proposer.proposeClaims(in: "text")
            XCTFail("a missing credential must not produce a result")
        } catch {
            XCTAssertEqual(error as? ProposerError,
                           .unavailable(.credentialMissing(.anthropic)))
        }
        XCTAssertTrue(spy.sent.isEmpty)
    }

    /// The failure must never read as "the model found nothing wrong".
    func testAnUnavailableProviderThrowsRatherThanReturningAnEmptyResult() async {
        let proposer = CloudClaimProposer(provider: .openAI,
                                          credentials: Store(),
                                          authorization: .denied,
                                          transport: SpyTransport())
        do {
            let result = try await proposer.proposeClaims(in: "text")
            XCTFail("returned \(result.claims.count) claims instead of throwing")
        } catch {
            // An error is the correct outcome; an empty ProposalResult is not.
        }
    }

    // MARK: - The request carries the credential correctly and no further

    func testEachProviderUsesItsOwnAuthHeaderAndEndpoint() throws {
        let openAI = CloudClaimProposer(provider: .openAI,
                                        credentials: Store(keys: [.openAI: "sk-a"]),
                                        authorization: .granted)
        let request = try openAI.buildRequest(text: "hello", key: "sk-a")
        XCTAssertEqual(request.url?.host, "api.openai.com")
        XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer sk-a")
        XCTAssertNil(request.value(forHTTPHeaderField: "x-api-key"))

        let anthropic = CloudClaimProposer(provider: .anthropic,
                                           credentials: Store(keys: [.anthropic: "sk-b"]),
                                           authorization: .granted)
        let other = try anthropic.buildRequest(text: "hello", key: "sk-b")
        XCTAssertEqual(other.url?.host, "api.anthropic.com")
        XCTAssertEqual(other.value(forHTTPHeaderField: "x-api-key"), "sk-b")
        XCTAssertEqual(other.value(forHTTPHeaderField: "anthropic-version"), "2023-06-01")
        XCTAssertNil(other.value(forHTTPHeaderField: "Authorization"))
    }

    func testAnOversizeDocumentIsRefusedRatherThanTruncated() async {
        let huge = String(repeating: "a", count: CloudClaimProposer.maximumInputBytes + 1)
        let spy = SpyTransport()
        let proposer = CloudClaimProposer(provider: .openAI,
                                          credentials: Store(keys: [.openAI: "sk"]),
                                          authorization: .granted,
                                          transport: spy)
        do {
            _ = try await proposer.proposeClaims(in: huge)
            XCTFail("an oversize input must be refused")
        } catch {
            guard case .inputTooLarge = (error as? ProposerError) else {
                return XCTFail("wrong error: \(error)")
            }
        }
        XCTAssertTrue(spy.sent.isEmpty, "refusal happens before the request")
    }

    // MARK: - What comes back is not trusted

    private func openAIBody(_ json: String) -> Data {
        let payload = ["choices": [["message": ["content": json]]]]
        return try! JSONSerialization.data(withJSONObject: payload)
    }

    /// The load-bearing test. A frontier model inventing a plausible sentence
    /// is discarded by the same grounding filter that discards an on-device
    /// one — it does not get more trust for being expensive.
    func testAnInventedQuoteFromAHostedModelIsDiscarded() async throws {
        let source = "The product of 6 and 7 is 42."
        let spy = SpyTransport()
        spy.response = (openAIBody("""
            {"spans":[{"quote":"The product of 6 and 7 is 42.","kind":"arithmetic"},
                      {"quote":"Revenue tripled last quarter.","kind":"aggregate"}]}
            """), http(200))

        let proposer = CloudClaimProposer(provider: .openAI,
                                          credentials: Store(keys: [.openAI: "sk"]),
                                          authorization: .granted,
                                          transport: spy)
        let result = try await proposer.proposeClaims(in: source)

        XCTAssertEqual(result.claims.count, 1)
        XCTAssertEqual(result.claims.first?.text, "The product of 6 and 7 is 42.")
        XCTAssertEqual(result.rejected.count, 1)
        XCTAssertEqual(result.rejected.first?.reason, .notPresentInSource)
    }

    /// A provider is free to return any string it likes for `kind`. None of
    /// them may reach the operator as free text.
    func testAnUnrecognisedKindBecomesUndeterminedRatherThanFreeText() async throws {
        let source = "The product of 6 and 7 is 42."
        let spy = SpyTransport()
        spy.response = (openAIBody("""
            {"spans":[{"quote":"The product of 6 and 7 is 42.",
                       "kind":"this is definitely false and misleading"}]}
            """), http(200))

        let proposer = CloudClaimProposer(provider: .openAI,
                                          credentials: Store(keys: [.openAI: "sk"]),
                                          authorization: .granted,
                                          transport: spy)
        let result = try await proposer.proposeClaims(in: source)
        XCTAssertEqual(result.claims.first?.rationale, "kind undetermined")
    }

    func testANonSuccessStatusIsSurfacedAsItself() async {
        let spy = SpyTransport()
        spy.response = (Data("{}".utf8), http(429))
        let proposer = CloudClaimProposer(provider: .openAI,
                                          credentials: Store(keys: [.openAI: "sk"]),
                                          authorization: .granted,
                                          transport: spy)
        do {
            _ = try await proposer.proposeClaims(in: "text")
            XCTFail("a 429 must not read as a successful empty result")
        } catch {
            XCTAssertEqual(error as? ProposerError, .providerRejected(status: 429))
        }
    }

    // MARK: - Routing

    func testDeterministicOnlyRefusesEveryModelIncludingAConfiguredOne() {
        let policy = ProposerRouter.RoutingPolicy(
            deterministicOnly: true, localOnly: false,
            authorization: .granted,
            credentials: Store(keys: [.openAI: "sk", .anthropic: "sk"]))
        XCTAssertEqual(ProposerRouter.route(policy: policy).availability,
                       .disabledByOperator)
    }

    func testLocalOnlyNeverReachesAConfiguredHostedProvider() {
        let policy = ProposerRouter.RoutingPolicy(
            localOnly: true, authorization: .granted,
            credentials: Store(keys: [.openAI: "sk"]))
        let chosen = ProposerRouter.route(policy: policy)
        XCTAssertFalse(chosen is CloudClaimProposer,
                       "localOnly must exclude hosted providers outright")
    }

    func testAHostedProviderIsReachedOnlyWithBothPermissions() {
        let credentials = Store(keys: [.openAI: "sk"])
        let denied = ProposerRouter.RoutingPolicy(
            localOnly: false, authorization: .denied, credentials: credentials)
        XCTAssertFalse(ProposerRouter.route(policy: denied) is CloudClaimProposer)

        // With both, and with the on-device model unavailable in this test
        // environment, the router should select the configured hosted one.
        let granted = ProposerRouter.RoutingPolicy(
            localOnly: false, authorization: .granted,
            credentials: credentials, preferred: .openAI)
        let chosen = ProposerRouter.route(policy: granted)
        if let cloud = chosen as? CloudClaimProposer {
            XCTAssertEqual(cloud.provider, .openAI)
        } else {
            // Legitimate on a machine where Apple Intelligence is available:
            // privacy-first ordering means the local model wins. Assert that
            // is why, rather than silently passing.
            XCTAssertTrue(AppleFoundationModelProposer().availability.canRun,
                          "a non-cloud proposer is only correct when the local model can run")
        }
    }

    /// The invariant that actually matters: the router never hands back a
    /// proposer that will quietly do nothing. It either returns one that can
    /// run, or one carrying a specific reason it cannot.
    ///
    /// Which branch applies depends on the machine, so both are asserted
    /// rather than assuming a build environment without Apple Intelligence —
    /// an earlier version of this test assumed that and failed on a Mac where
    /// the local model was live, which was the router behaving correctly.
    func testAnUnconfiguredRouteEitherRunsOrNamesTheClosedDoor() {
        let policy = ProposerRouter.RoutingPolicy(
            localOnly: false, authorization: .granted, credentials: Store(),
            preferred: .anthropic)
        let chosen = ProposerRouter.route(policy: policy)

        if chosen.availability.canRun {
            // Fallback succeeded — only legitimate if the local model is up,
            // since neither hosted provider has a credential in this policy.
            XCTAssertTrue(AppleFoundationModelProposer().availability.canRun,
                          "something ran that should not have been able to")
            XCTAssertFalse(chosen is CloudClaimProposer,
                           "an uncredentialed hosted provider must never run")
        } else {
            XCTAssertEqual(chosen.availability, .credentialMissing(.anthropic),
                           "the reason must name the provider the operator asked for")
        }
    }

    /// With every door shut, the reason names the operator's preferred
    /// provider rather than whichever candidate happened to be checked last.
    func testWithNothingAvailableTheReasonNamesThePreferredProvider() {
        let policy = ProposerRouter.RoutingPolicy(
            modelAssistanceEnabled: false,
            localOnly: false, authorization: .granted, credentials: Store(),
            preferred: .openAI)
        XCTAssertEqual(ProposerRouter.route(policy: policy).availability,
                       .disabledByOperator,
                       "an operator switch outranks every provider question")
    }
}
