// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import XCTest
@testable import ChironContract
@testable import ChironRemote

final class MobileAPIClientTests: XCTestCase {
    func testCertifyAndCollapseUseOnlyTheVersionedHTTPContract() async throws {
        let transport = RecordingTransport(responses: [
            envelope(operation: "certify", result: certifyResult),
            envelope(operation: "collapse", result: collapseResult),
        ])
        let client = try makeClient(transport: transport)

        let certification = try await client.certify(text: "2+2=4")
        let collapse = try await client.collapse(surface: [1, 1, 2, 3, 5, 8])

        XCTAssertEqual(certification.envelope.operation, .certify)
        XCTAssertEqual(collapse.envelope.operation, .collapse)
        let requests = transport.recordedRequests
        XCTAssertEqual(requests.count, 2)

        XCTAssertEqual(requests[0].httpMethod, "POST")
        XCTAssertEqual(requests[0].url?.path, "/gateway/v1/certify")
        XCTAssertEqual(requests[0].value(forHTTPHeaderField: "Content-Type"), "application/json")
        XCTAssertEqual(requests[0].value(forHTTPHeaderField: "Authorization"), nil)
        let certifyBody = try JSONSerialization.jsonObject(with: try XCTUnwrap(requests[0].httpBody))
            as? [String: Any]
        XCTAssertEqual(certifyBody?["text"] as? String, "2+2=4")

        XCTAssertEqual(requests[1].httpMethod, "POST")
        XCTAssertEqual(requests[1].url?.path, "/gateway/v1/collapse")
        let collapseBody = try JSONSerialization.jsonObject(with: try XCTUnwrap(requests[1].httpBody))
            as? [String: Any]
        XCTAssertEqual(collapseBody?["surface"] as? [Int], [1, 1, 2, 3, 5, 8])

        // The raw token from the certificate survives the client rather than
        // becoming an inexact Double in a SwiftUI rendering path.
        let certificate = try XCTUnwrap(collapse.certificate.objectValue)
        guard case .number(let large)? = certificate["description_bits"] else {
            return XCTFail("missing raw certificate number")
        }
        XCTAssertEqual(large.rawValue, "9007199254740993")
    }

    func testCapabilitiesUsesGETAndExposesOnlyFixedOperations() async throws {
        let transport = RecordingTransport(responses: [
            envelope(operation: "capabilities", result: capabilitiesResult),
        ])
        let client = try makeClient(transport: transport)

        let capabilities = try await client.capabilities()
        XCTAssertEqual(capabilities.operations.map(\.operation), ["collapse", "certify"])
        let request = try XCTUnwrap(transport.recordedRequests.first)
        XCTAssertEqual(request.httpMethod, "GET")
        XCTAssertEqual(request.url?.path, "/gateway/v1/capabilities")
        XCTAssertNil(request.httpBody)
    }

    func testCapabilitiesNeverRequestsOrSendsABearer() async throws {
        let transport = RecordingTransport(responses: [
            envelope(operation: "capabilities", result: capabilitiesResult),
        ])
        let client = try MobileAPIClient(
            baseURL: URL(string: "https://gateway.example.test")!,
            authorizer: MobileAPIAuthorizer(nextBearerToken: {
                throw AuthorizationProbe.invoked
            }),
            transport: transport)

        _ = try await client.capabilities()
        XCTAssertNil(transport.recordedRequests.first?
            .value(forHTTPHeaderField: "Authorization"))
    }

    func testSchemaAndOperationDriftAreRejected() async throws {
        let wrongSchema = RecordingTransport(responses: [
            envelope(operation: "certify", result: certifyResult, schema: "other.mobile/1"),
        ])
        let schemaClient = try makeClient(transport: wrongSchema)
        await assertError(.schemaMismatch(expected: "chiron.mobile_api/1", actual: "other.mobile/1")) {
            _ = try await schemaClient.certify(text: "2+2=4")
        }

        let wrongOperation = RecordingTransport(responses: [
            envelope(operation: "collapse", result: collapseResult),
        ])
        let operationClient = try makeClient(transport: wrongOperation)
        await assertError(.operationMismatch(expected: .certify, actual: "collapse")) {
            _ = try await operationClient.certify(text: "2+2=4")
        }

        let wrongEngineSchema = RecordingTransport(responses: [
            envelope(operation: "certify", result: #"{"schema":"other.engine/1","tool":"certify","certificate":{"schema":"primus.certificate/2"}}"#),
        ])
        let engineClient = try makeClient(transport: wrongEngineSchema)
        await assertError(.engineSchemaMismatch(expected: "primus.engine_server/1",
                                                 actual: "other.engine/1")) {
            _ = try await engineClient.certify(text: "2+2=4")
        }
    }

    func testEngineRefusalAndHTTPAuthRateRefusalsStayDistinct() async throws {
        let engineRefusal = refusalResult(error: "refused", reason: "nothing checkable")
        let transport = RecordingTransport(responses: [
            envelope(operation: "certify", result: engineRefusal, statusCode: 200),
            envelope(operation: "certify", result: refusalResult(error: "unauthorized", reason: "missing bearer"), statusCode: 401),
            envelope(operation: "certify", result: refusalResult(error: "rate limited", reason: "retry later"), statusCode: 429),
        ])
        let client = try makeClient(transport: transport)

        await assertError(.refusal(.init(error: "refused", reason: "nothing checkable"))) {
            _ = try await client.certify(text: "no arithmetic")
        }
        await assertError(.httpRefusal(statusCode: 401,
                                       refusal: .init(error: "unauthorized", reason: "missing bearer"))) {
            _ = try await client.certify(text: "2+2=4")
        }
        await assertError(.httpRefusal(statusCode: 429,
                                       refusal: .init(error: "rate limited", reason: "retry later"))) {
            _ = try await client.certify(text: "2+2=4")
        }
    }

    func testRedirectResponsesAreRejectedWithoutEnvelopeParsing() async throws {
        let redirected = RecordingTransport(responses: [
            MobileHTTPResponse(statusCode: 302,
                               headers: ["Content-Type": "text/html"],
                               body: Data()),
        ])
        let client = try makeClient(transport: redirected)

        await assertError(.redirected(statusCode: 302)) {
            _ = try await client.certify(text: "2+2=4")
        }
        XCTAssertEqual(redirected.recordedRequests.count, 1)
    }

    func testURLSessionTransportDoesNotFollowRedirects() async throws {
        RedirectProbeURLProtocol.reset()
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [RedirectProbeURLProtocol.self]
        let client = try MobileAPIClient(
            baseURL: URL(string: "https://redirect-probe.example.test")!,
            transport: URLSessionMobileAPITransport(configuration: configuration))

        await assertError(.redirected(statusCode: 302)) {
            _ = try await client.certify(text: "2+2=4")
        }
        XCTAssertEqual(RedirectProbeURLProtocol.requestCount, 1,
                       "a redirect target must never receive a second request")
    }

    func testMalformedOutputAndTransportFailureNeverFallBack() async throws {
        let malformed = RecordingTransport(responses: [
            MobileHTTPResponse(statusCode: 200,
                               headers: ["Content-Type": "application/json"],
                               body: Data("{not-json".utf8)),
        ])
        let malformedClient = try makeClient(transport: malformed)
        await assertError(.decodeFailed) {
            _ = try await malformedClient.certify(text: "2+2=4")
        }
        XCTAssertEqual(malformed.recordedRequests.count, 1)

        let unavailable = FailingTransport(error: URLError(.timedOut))
        let unavailableClient = try makeClient(transport: unavailable)
        await assertError(.transport(.timedOut)) {
            _ = try await unavailableClient.certify(text: "2+2=4")
        }
        XCTAssertEqual(unavailable.callCount, 1, "the remote client must not retry or fall back")
    }

    func testBoundsAndRuntimeInjectedAuthorization() async throws {
        let oversizedTransport = RecordingTransport(responses: [
            envelope(operation: "certify", result: certifyResult),
        ])
        let tinyRequestLimit = try MobileAPIClientConfiguration(
            maximumRequestBytes: 16, maximumResponseBytes: 4_096, timeout: 5)
        let oversizedClient = try MobileAPIClient(
            baseURL: URL(string: "https://gateway.example.test")!,
            configuration: tinyRequestLimit,
            transport: oversizedTransport)
        await assertError(.requestTooLarge(limit: 16, actual: 111)) {
            _ = try await oversizedClient.certify(text: String(repeating: "x", count: 100))
        } matching: { error in
            guard case .requestTooLarge(let limit, let actual) = error else { return false }
            return limit == 16 && actual > 16
        }
        XCTAssertEqual(oversizedTransport.recordedRequests.count, 0)

        let responseLimit = try MobileAPIClientConfiguration(
            maximumRequestBytes: 4_096, maximumResponseBytes: 32, timeout: 5)
        let largeResponseTransport = RecordingTransport(responses: [
            envelope(operation: "certify", result: certifyResult),
        ])
        let limitedClient = try MobileAPIClient(
            baseURL: URL(string: "https://gateway.example.test")!,
            configuration: responseLimit,
            transport: largeResponseTransport)
        await assertError(.responseTooLarge(limit: 32)) {
            _ = try await limitedClient.certify(text: "2+2=4")
        }

        let authorizedTransport = RecordingTransport(responses: [
            envelope(operation: "certify", result: certifyResult),
        ])
        let authorizedClient = try MobileAPIClient(
            baseURL: URL(string: "https://gateway.example.test")!,
            authorizer: MobileAPIAuthorizer(nextBearerToken: { "runtime-short-lived" }),
            transport: authorizedTransport)
        _ = try await authorizedClient.certify(text: "2+2=4")
        XCTAssertEqual(authorizedTransport.recordedRequests.first?
            .value(forHTTPHeaderField: "Authorization"), "Bearer runtime-short-lived")
    }

    func testPlaintextHTTPIsLimitedToExactLoopbackDevelopmentHosts() throws {
        XCTAssertThrowsError(
            try MobileAPIClient(baseURL: URL(string: "http://gateway.example.test")!,
                                transport: RecordingTransport(responses: []))
        ) { error in
            XCTAssertEqual(error as? MobileAPIClientError, .invalidEndpoint)
        }
        XCTAssertThrowsError(
            try MobileAPIClient(baseURL: URL(string: "http://127.0.0.1.nip.io")!,
                                transport: RecordingTransport(responses: []))
        ) { error in
            XCTAssertEqual(error as? MobileAPIClientError, .invalidEndpoint)
        }

        XCTAssertThrowsError(
            try MobileAPIClient(baseURL: URL(string: "http://localhost:8790")!,
                                transport: RecordingTransport(responses: []))
        ) { error in
            XCTAssertEqual(error as? MobileAPIClientError, .invalidEndpoint)
        }
        for endpoint in ["http://127.0.0.1:8790", "http://[::1]:8790"] {
            XCTAssertNoThrow(
                try MobileAPIClient(baseURL: URL(string: endpoint)!,
                                    transport: RecordingTransport(responses: [])),
                "\(endpoint) is an explicit loopback development endpoint")
        }
    }

    private func makeClient(transport: any MobileAPITransport) throws -> MobileAPIClient {
        try MobileAPIClient(baseURL: URL(string: "https://gateway.example.test/gateway")!,
                            transport: transport)
    }

    private func assertError(_ expected: MobileAPIClientError,
                             operation: () async throws -> Void) async {
        await assertError(expected, operation: operation, matching: { $0 == expected })
    }

    private func assertError(_ expected: MobileAPIClientError,
                             operation: () async throws -> Void,
                             matching: (MobileAPIClientError) -> Bool) async {
        do {
            try await operation()
            XCTFail("expected \(expected)")
        } catch let error as MobileAPIClientError {
            XCTAssertTrue(matching(error), "expected \(expected), got \(error)")
        } catch {
            XCTFail("unexpected error \(error)")
        }
    }
}

private let certifyResult = #"""
{"schema":"primus.engine_server/1","tool":"certify","certificate":{"schema":"primus.certificate/2","claims":[]}}
"""#

private let collapseResult = #"""
{"schema":"primus.engine_server/1","tool":"collapse","certificate":{"verified":true,"description_bits":9007199254740993}}
"""#

private let capabilitiesResult = #"""
{"operations":[{"operation":"collapse","method":"POST","path":"/v1/collapse","body":{"required":["surface"]}},{"operation":"certify","method":"POST","path":"/v1/certify","body":{"required":["text"]}}],"limits":{"body_bytes":131072},"authentication":{"post_bearer":"optional_static","configured":false}}
"""#

private enum AuthorizationProbe: Error, Sendable {
    case invoked
}

private func refusalResult(error: String, reason: String) -> String {
    #"{"schema":"primus.engine_server/1","status":"REFUSED","error":""# + error + #"","reason":""# + reason + #""}"#
}

private func envelope(operation: String,
                      result: String,
                      schema: String = "chiron.mobile_api/1",
                      statusCode: Int = 200) -> MobileHTTPResponse {
    let json = """
    {"schema":"\(schema)","request_id":"0123456789abcdef0123456789abcdef","operation":"\(operation)","engine":{"primus_version":"0.7.0","certificate_schema":"primus.certificate/2"},"result":\(result)}
    """
    return MobileHTTPResponse(statusCode: statusCode,
                              headers: ["Content-Type": "application/json; charset=utf-8"],
                              body: Data(json.utf8))
}

private final class RecordingTransport: MobileAPITransport, @unchecked Sendable {
    private let lock = NSLock()
    private var responses: [MobileHTTPResponse]
    private var requests: [URLRequest] = []

    init(responses: [MobileHTTPResponse]) {
        self.responses = responses
    }

    func send(_ request: URLRequest,
              maximumResponseBytes: Int) async throws -> MobileHTTPResponse {
        try lock.withLock {
            requests.append(request)
            guard !responses.isEmpty else { throw URLError(.badServerResponse) }
            return responses.removeFirst()
        }
    }

    var recordedRequests: [URLRequest] {
        lock.lock()
        defer { lock.unlock() }
        return requests
    }
}

private final class FailingTransport: MobileAPITransport, @unchecked Sendable {
    private let lock = NSLock()
    private let error: Error
    private var count = 0

    init(error: Error) { self.error = error }

    func send(_ request: URLRequest,
              maximumResponseBytes: Int) async throws -> MobileHTTPResponse {
        let storedError: Error = lock.withLock {
            count += 1
            return error
        }
        throw storedError
    }

    var callCount: Int {
        lock.lock()
        defer { lock.unlock() }
        return count
    }
}

/// A URLProtocol-level redirect probe keeps the redirect test local and
/// deterministic. It records every load; if URLSession followed the Location
/// despite the production delegate, the count would be two.
private final class RedirectProbeURLProtocol: URLProtocol, @unchecked Sendable {
    private static let lock = NSLock()
    // Access is serialized by `lock`; Swift cannot infer that from the
    // external Foundation callback, so state the synchronization boundary.
    private nonisolated(unsafe) static var count = 0

    static func reset() {
        lock.withLock { count = 0 }
    }

    static var requestCount: Int {
        lock.withLock { count }
    }

    override class func canInit(with request: URLRequest) -> Bool {
        request.url?.host == "redirect-probe.example.test" ||
            request.url?.host == "redirect-target.example.test"
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        let loadNumber = Self.lock.withLock { () -> Int in
            Self.count += 1
            return Self.count
        }
        guard let url = request.url else {
            client?.urlProtocol(self, didFailWithError: URLError(.badURL))
            return
        }
        if loadNumber == 1 {
            let response = HTTPURLResponse(
                url: url,
                statusCode: 302,
                httpVersion: "HTTP/1.1",
                headerFields: ["Location": "https://redirect-target.example.test/blocked"]
            )!
            let redirect = URLRequest(url: URL(string: "https://redirect-target.example.test/blocked")!)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, wasRedirectedTo: redirect, redirectResponse: response)
            client?.urlProtocolDidFinishLoading(self)
        } else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
        }
    }

    override func stopLoading() {}
}

private extension JSONValue {
    var objectValue: [String: JSONValue]? {
        guard case .object(let value) = self else { return nil }
        return value
    }
}
