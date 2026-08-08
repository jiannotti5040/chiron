// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import ChironContract

/// The operations deliberately exposed by the compact mobile-safe boundary.
/// There is no client fallback to a local process, dynamic module, or path.
public enum MobileAPIOperation: String, Sendable, CaseIterable {
    case capabilities
    case collapse
    case certify

    fileprivate var path: String {
        switch self {
        case .capabilities: "v1/capabilities"
        case .collapse: "v1/collapse"
        case .certify: "v1/certify"
        }
    }
}

public struct MobileAPIEngine: Sendable, Equatable {
    public let primusVersion: String
    public let certificateSchema: String
}

public struct MobileAPIEnvelope: Sendable, Equatable {
    public let schema: String
    public let requestID: String
    public let operation: MobileAPIOperation
    public let engine: MobileAPIEngine
}

/// A decoded, schema-validated mobile response. `result` remains JSON rather
/// than being re-evaluated on-device; certificate numbers keep their exact
/// JSON token through `JSONValue`.
public struct MobileAPIResponse: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: MobileAPIEnvelope
    public let result: JSONValue
}

public struct MobileCertification: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: MobileAPIEnvelope
    public let certificate: JSONValue
}

public struct MobileCollapse: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: MobileAPIEnvelope
    public let certificate: JSONValue
}

public struct MobileAPICapability: Sendable, Equatable {
    public let operation: String
    public let method: String
    public let path: String
    public let body: JSONValue
}

public struct MobileAPICapabilities: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: MobileAPIEnvelope
    public let operations: [MobileAPICapability]
    public let limits: JSONValue
    public let authentication: JSONValue
}

/// A refusal is an honest result at the engine level, but it is never a
/// successful client call. HTTP-level refusals retain their status separately.
public struct MobileAPIRefusal: Sendable, Equatable {
    public let error: String
    public let reason: String
}

public enum MobileAPITransportFailure: Sendable, Equatable {
    case cancelled
    case timedOut
    case offline
    case other
}

public enum MobileAPIClientError: Error, Sendable, Equatable {
    case invalidEndpoint
    case invalidConfiguration
    case requestTooLarge(limit: Int, actual: Int)
    case responseTooLarge(limit: Int)
    case authorizationUnavailable
    case invalidAuthorization
    case transport(MobileAPITransportFailure)
    case redirected(statusCode: Int)
    case unexpectedContentType
    case httpStatus(Int)
    case httpRefusal(statusCode: Int, refusal: MobileAPIRefusal)
    case refusal(MobileAPIRefusal)
    case decodeFailed
    case malformedEnvelope
    case schemaMismatch(expected: String, actual: String?)
    case operationMismatch(expected: MobileAPIOperation, actual: String?)
    case engineSchemaMismatch(expected: String, actual: String?)
    case toolMismatch(expected: MobileAPIOperation, actual: String?)
    case certificateSchemaMismatch(expected: String, actual: String?)
}

/// Limits held by the client, independent from a gateway's own controls.
/// The request default matches Primus's 128 KiB HTTP door. The response cap is
/// deliberately larger because a bounded certificate can contain evidence.
public struct MobileAPIClientConfiguration: Sendable, Equatable {
    public let maximumRequestBytes: Int
    public let maximumResponseBytes: Int
    public let timeout: TimeInterval

    public init(maximumRequestBytes: Int = 128 * 1024,
                maximumResponseBytes: Int = 2 * 1024 * 1024,
                timeout: TimeInterval = 30) throws {
        guard maximumRequestBytes > 0, maximumResponseBytes > 0,
              timeout > 0, timeout <= 600
        else { throw MobileAPIClientError.invalidConfiguration }
        self.maximumRequestBytes = maximumRequestBytes
        self.maximumResponseBytes = maximumResponseBytes
        self.timeout = timeout
    }

    public static let standard: MobileAPIClientConfiguration = {
        // Constants above are local and validated at construction time.
        try! MobileAPIClientConfiguration()
    }()
}

/// The token is requested at the moment a request is made. The client has no
/// string-token initializer and does not persist a token; an app injects its
/// short-lived credential source (for example, a gateway session) at runtime.
public struct MobileAPIAuthorizer: Sendable {
    private let nextBearerToken: @Sendable () async throws -> String?

    public init(nextBearerToken: @escaping @Sendable () async throws -> String? = { nil }) {
        self.nextBearerToken = nextBearerToken
    }

    fileprivate func bearerToken() async throws -> String? {
        try await nextBearerToken()
    }
}

public struct MobileHTTPResponse: Sendable {
    public let statusCode: Int
    public let headers: [String: String]
    public let body: Data

    public init(statusCode: Int, headers: [String: String] = [:], body: Data) {
        self.statusCode = statusCode
        // HTTP field names are case-insensitive. Do not let an injected or
        // malformed response with duplicate spellings trap the client.
        var normalized: [String: String] = [:]
        for (key, value) in headers { normalized[key.lowercased()] = value }
        self.headers = normalized
        self.body = body
    }
}

public enum MobileAPITransportError: Error, Sendable, Equatable {
    case responseTooLarge(limit: Int)
    case nonHTTPResponse
}

/// The tiny seam used by deterministic tests and by the URLSession adapter.
/// It accepts a cap from the client, so a substitute transport cannot silently
/// bypass the response budget (the client checks it again defensively).
public protocol MobileAPITransport: Sendable {
    func send(_ request: URLRequest,
              maximumResponseBytes: Int) async throws -> MobileHTTPResponse
}

/// Blocks every redirect. The compact v1 boundary has no redirect semantics;
/// following one could otherwise forward user text or an Authorization header
/// to a host which was never checked by `MobileAPIClient`'s endpoint policy.
private final class RedirectRejectingDelegate: NSObject, URLSessionTaskDelegate, @unchecked Sendable {
    func urlSession(_ session: URLSession,
                    task: URLSessionTask,
                    willPerformHTTPRedirection response: HTTPURLResponse,
                    newRequest request: URLRequest,
                    completionHandler: @escaping @Sendable (URLRequest?) -> Void) {
        completionHandler(nil)
    }
}

/// URLSession transport for iOS/macOS. It rejects redirects, reads the body as
/// an async byte sequence, and stops before a response can grow past the
/// configured budget. Tests inject `MobileAPITransport` directly; callers
/// cannot supply a redirect-following session to this production transport.
public struct URLSessionMobileAPITransport: MobileAPITransport, Sendable {
    private let session: URLSession
    // URLSession's delegate lifetime is implementation-owned; retain it here
    // explicitly so the redirect guard remains live for every request.
    private let redirectDelegate: RedirectRejectingDelegate

    public init(configuration: URLSessionConfiguration = .ephemeral) {
        let delegate = RedirectRejectingDelegate()
        self.redirectDelegate = delegate
        self.session = URLSession(configuration: configuration,
                                  delegate: delegate,
                                  delegateQueue: nil)
    }

    public func send(_ request: URLRequest,
                     maximumResponseBytes: Int) async throws -> MobileHTTPResponse {
        let (bytes, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw MobileAPITransportError.nonHTTPResponse
        }
        if response.expectedContentLength > Int64(maximumResponseBytes) {
            throw MobileAPITransportError.responseTooLarge(limit: maximumResponseBytes)
        }

        var body = Data()
        if response.expectedContentLength > 0 {
            body.reserveCapacity(min(maximumResponseBytes,
                                     Int(response.expectedContentLength)))
        }
        for try await byte in bytes {
            guard body.count < maximumResponseBytes else {
                throw MobileAPITransportError.responseTooLarge(limit: maximumResponseBytes)
            }
            body.append(byte)
        }

        var headers: [String: String] = [:]
        for (key, value) in http.allHeaderFields {
            headers[String(describing: key).lowercased()] = String(describing: value)
        }
        return MobileHTTPResponse(statusCode: http.statusCode, headers: headers, body: body)
    }
}

/// URLSession-only client for the intentionally small remote surface. It
/// never shells out to Python and it never attempts a local fallback.
public struct MobileAPIClient: Sendable {
    public static let schema = "chiron.mobile_api/1"
    public static let engineSchema = "primus.engine_server/1"
    public static let certificateSchema = "primus.certificate/2"

    public let baseURL: URL
    public let configuration: MobileAPIClientConfiguration
    private let transport: any MobileAPITransport
    private let authorizer: MobileAPIAuthorizer

    public init(baseURL: URL,
                configuration: MobileAPIClientConfiguration = .standard,
                authorizer: MobileAPIAuthorizer = MobileAPIAuthorizer(),
                transport: any MobileAPITransport = URLSessionMobileAPITransport()) throws {
        guard let scheme = baseURL.scheme?.lowercased(),
              let host = baseURL.host?.lowercased(),
              ["http", "https"].contains(scheme),
              // A runtime credential must never be sent over plaintext to a
              // network host. HTTP is retained only for explicit local
              // development against the engine server.
              scheme == "https" || Self.loopbackHosts.contains(host),
              baseURL.user == nil,
              baseURL.password == nil,
              baseURL.query == nil,
              baseURL.fragment == nil
        else { throw MobileAPIClientError.invalidEndpoint }
        self.baseURL = baseURL
        self.configuration = configuration
        self.authorizer = authorizer
        self.transport = transport
    }

    public func capabilities() async throws -> MobileAPICapabilities {
        let response = try await perform(operation: .capabilities, body: nil)
        guard let result = response.result.objectValue,
              let operationValues = result["operations"]?.arrayValue,
              let limits = result["limits"],
              let authentication = result["authentication"]
        else { throw MobileAPIClientError.malformedEnvelope }

        var operations: [MobileAPICapability] = []
        for value in operationValues {
            guard let object = value.objectValue,
                  let operation = object["operation"]?.stringValue,
                  let method = object["method"]?.stringValue,
                  let path = object["path"]?.stringValue,
                  let body = object["body"]
            else { throw MobileAPIClientError.malformedEnvelope }
            operations.append(.init(operation: operation, method: method,
                                    path: path, body: body))
        }
        // The endpoint is only useful to this client if it says the two fixed
        // operations still exist. Do not infer a substitute from a drifted
        // capability document.
        guard Set(operations.map(\.operation)) == Set(["collapse", "certify"]),
              operations.count == 2
        else { throw MobileAPIClientError.malformedEnvelope }

        return MobileAPICapabilities(statusCode: response.statusCode,
                                     envelope: response.envelope,
                                     operations: operations,
                                     limits: limits,
                                     authentication: authentication)
    }

    public func certify(text: String) async throws -> MobileCertification {
        let body = try encode(CertifyRequest(text: text))
        let response = try await perform(operation: .certify, body: body)
        let certificate = try certificate(in: response, operation: .certify)
        guard certificate["schema"]?.stringValue == Self.certificateSchema else {
            throw MobileAPIClientError.certificateSchemaMismatch(
                expected: Self.certificateSchema,
                actual: certificate["schema"]?.stringValue)
        }
        return MobileCertification(statusCode: response.statusCode,
                                   envelope: response.envelope,
                                   certificate: .object(certificate))
    }

    public func collapse(surface: String) async throws -> MobileCollapse {
        let body = try encode(CollapseTextRequest(surface: surface))
        return try await collapse(body: body)
    }

    public func collapse(surface: [Int]) async throws -> MobileCollapse {
        let body = try encode(CollapseArrayRequest(surface: surface))
        return try await collapse(body: body)
    }

    private func collapse(body: Data) async throws -> MobileCollapse {
        let response = try await perform(operation: .collapse, body: body)
        let certificate = try certificate(in: response, operation: .collapse)
        return MobileCollapse(statusCode: response.statusCode,
                              envelope: response.envelope,
                              certificate: .object(certificate))
    }

    private func encode<T: Encodable>(_ value: T) throws -> Data {
        let data = try JSONEncoder().encode(value)
        guard data.count <= configuration.maximumRequestBytes else {
            throw MobileAPIClientError.requestTooLarge(
                limit: configuration.maximumRequestBytes, actual: data.count)
        }
        return data
    }

    private func perform(operation: MobileAPIOperation,
                         body: Data?) async throws -> MobileAPIResponse {
        let request = try await makeRequest(operation: operation, body: body)
        let response: MobileHTTPResponse
        do {
            response = try await transport.send(request,
                                                maximumResponseBytes: configuration.maximumResponseBytes)
        } catch let error as MobileAPITransportError {
            switch error {
            case .responseTooLarge:
                throw MobileAPIClientError.responseTooLarge(limit: configuration.maximumResponseBytes)
            case .nonHTTPResponse:
                throw MobileAPIClientError.transport(.other)
            }
        } catch is CancellationError {
            throw MobileAPIClientError.transport(.cancelled)
        } catch let error as URLError {
            throw MobileAPIClientError.transport(Self.transportFailure(for: error))
        } catch {
            throw MobileAPIClientError.transport(.other)
        }

        // A test/injected transport must not be able to sneak a larger body
        // past the client just because it did not implement streaming bounds.
        guard response.body.count <= configuration.maximumResponseBytes else {
            throw MobileAPIClientError.responseTooLarge(limit: configuration.maximumResponseBytes)
        }
        // The transport rejects redirect following, but an injected transport
        // can still model a 3xx response. Never decode it as a valid envelope.
        guard !(300...399).contains(response.statusCode) else {
            throw MobileAPIClientError.redirected(statusCode: response.statusCode)
        }
        guard response.headers["content-type"]?.lowercased()
            .split(separator: ";", maxSplits: 1).first == "application/json"
        else { throw MobileAPIClientError.unexpectedContentType }

        let parsed = try decodeEnvelope(response.body, expectedOperation: operation)
        let clientResponse = MobileAPIResponse(statusCode: response.statusCode,
                                               envelope: parsed.envelope,
                                               result: parsed.result)
        if let refusal = try refusal(in: parsed.result) {
            if !(200...299).contains(response.statusCode) {
                throw MobileAPIClientError.httpRefusal(statusCode: response.statusCode,
                                                        refusal: refusal)
            }
            throw MobileAPIClientError.refusal(refusal)
        }
        guard (200...299).contains(response.statusCode) else {
            throw MobileAPIClientError.httpStatus(response.statusCode)
        }
        if operation != .capabilities {
            try validateEngineResult(parsed.result, operation: operation)
        }
        return clientResponse
    }

    private func makeRequest(operation: MobileAPIOperation,
                             body: Data?) async throws -> URLRequest {
        let url = baseURL.appendingPathComponent(operation.path)
        var request = URLRequest(url: url)
        request.httpMethod = operation == .capabilities ? "GET" : "POST"
        request.timeoutInterval = configuration.timeout
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        // The documented local static bearer applies to POST only. A public
        // capability read must neither depend on nor disclose a runtime
        // credential to an intermediary that might log GET requests.
        if operation != .capabilities {
            let token: String?
            do {
                token = try await authorizer.bearerToken()
            } catch {
                throw MobileAPIClientError.authorizationUnavailable
            }
            if let token {
                guard !token.isEmpty,
                      !token.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 })
                else { throw MobileAPIClientError.invalidAuthorization }
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
        }
        return request
    }

    private func decodeEnvelope(_ data: Data,
                                expectedOperation: MobileAPIOperation) throws -> ParsedEnvelope {
        let root: JSONValue
        do { root = try JSONValue.parse(data) }
        catch { throw MobileAPIClientError.decodeFailed }
        guard let object = root.objectValue,
              let schema = object["schema"]?.stringValue,
              let requestID = object["request_id"]?.stringValue,
              let operation = object["operation"]?.stringValue,
              let engineObject = object["engine"]?.objectValue,
              let primusVersion = engineObject["primus_version"]?.stringValue,
              let certificateSchema = engineObject["certificate_schema"]?.stringValue,
              let result = object["result"]
        else { throw MobileAPIClientError.malformedEnvelope }

        guard schema == Self.schema else {
            throw MobileAPIClientError.schemaMismatch(expected: Self.schema, actual: schema)
        }
        guard Self.isRequestID(requestID) else { throw MobileAPIClientError.malformedEnvelope }
        guard operation == expectedOperation.rawValue else {
            throw MobileAPIClientError.operationMismatch(expected: expectedOperation,
                                                         actual: operation)
        }
        guard certificateSchema == Self.certificateSchema else {
            throw MobileAPIClientError.certificateSchemaMismatch(
                expected: Self.certificateSchema, actual: certificateSchema)
        }
        return ParsedEnvelope(
            envelope: .init(schema: schema, requestID: requestID,
                            operation: expectedOperation,
                            engine: .init(primusVersion: primusVersion,
                                          certificateSchema: certificateSchema)),
            result: result)
    }

    private func refusal(in result: JSONValue) throws -> MobileAPIRefusal? {
        guard let object = result.objectValue else {
            throw MobileAPIClientError.malformedEnvelope
        }
        guard object["status"]?.stringValue == "REFUSED" else { return nil }
        let schema = object["schema"]?.stringValue
        guard schema == Self.engineSchema else {
            throw MobileAPIClientError.engineSchemaMismatch(expected: Self.engineSchema,
                                                            actual: schema)
        }
        guard let error = object["error"]?.stringValue,
              let reason = object["reason"]?.stringValue
        else { throw MobileAPIClientError.malformedEnvelope }
        return MobileAPIRefusal(error: error, reason: reason)
    }

    private func validateEngineResult(_ result: JSONValue,
                                      operation: MobileAPIOperation) throws {
        guard let object = result.objectValue else {
            throw MobileAPIClientError.malformedEnvelope
        }
        let schema = object["schema"]?.stringValue
        guard schema == Self.engineSchema else {
            throw MobileAPIClientError.engineSchemaMismatch(expected: Self.engineSchema,
                                                            actual: schema)
        }
        let tool = object["tool"]?.stringValue
        guard tool == operation.rawValue else {
            throw MobileAPIClientError.toolMismatch(expected: operation, actual: tool)
        }
        guard object["certificate"]?.objectValue != nil else {
            throw MobileAPIClientError.malformedEnvelope
        }
    }

    private func certificate(in response: MobileAPIResponse,
                             operation: MobileAPIOperation) throws -> [String: JSONValue] {
        try validateEngineResult(response.result, operation: operation)
        guard let object = response.result.objectValue,
              let certificate = object["certificate"]?.objectValue
        else { throw MobileAPIClientError.malformedEnvelope }
        return certificate
    }

    private static func transportFailure(for error: URLError) -> MobileAPITransportFailure {
        switch error.code {
        case .cancelled: return .cancelled
        case .timedOut: return .timedOut
        case .notConnectedToInternet, .networkConnectionLost,
             .cannotFindHost, .cannotConnectToHost, .dnsLookupFailed:
            return .offline
        default: return .other
        }
    }

    private static func isRequestID(_ value: String) -> Bool {
        value.count == 32 && value.utf8.allSatisfy {
            (48...57).contains($0) || (97...102).contains($0)
        }
    }

    // Do not accept `localhost`: it is a resolver name and can be remapped by
    // host configuration. The plaintext development exception is literal IP
    // loopback only.
    private static let loopbackHosts: Set<String> = ["127.0.0.1", "::1"]

    private struct ParsedEnvelope {
        let envelope: MobileAPIEnvelope
        let result: JSONValue
    }

    private struct CertifyRequest: Encodable { let text: String }
    private struct CollapseTextRequest: Encodable { let surface: String }
    private struct CollapseArrayRequest: Encodable { let surface: [Int] }
}

private extension JSONValue {
    var objectValue: [String: JSONValue]? {
        guard case .object(let value) = self else { return nil }
        return value
    }

    var arrayValue: [JSONValue]? {
        guard case .array(let value) = self else { return nil }
        return value
    }

    var stringValue: String? {
        guard case .string(let value) = self else { return nil }
        return value
    }
}
