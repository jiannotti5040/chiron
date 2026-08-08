// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
import ChironContract

/// The operations deliberately exposed by the compact `/v1` local-service
/// boundary documented in `Primus/LOCAL_API.md`.
/// There is no client fallback to a local process, dynamic module, or path.
public enum LocalServiceOperation: String, Sendable, CaseIterable {
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

public struct LocalServiceEngine: Sendable, Equatable {
    public let primusVersion: String
    public let certificateSchema: String
}

public struct LocalServiceEnvelope: Sendable, Equatable {
    public let schema: String
    public let requestID: String
    public let operation: LocalServiceOperation
    public let engine: LocalServiceEngine
}

/// A decoded, schema-validated service response. `result` remains JSON rather
/// than being re-evaluated on-device; certificate numbers keep their exact
/// JSON token through `JSONValue`. The client never restates a verdict.
public struct LocalServiceResponse: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: LocalServiceEnvelope
    public let result: JSONValue
}

public struct LocalServiceCertification: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: LocalServiceEnvelope
    public let certificate: JSONValue
}

public struct LocalServiceCollapse: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: LocalServiceEnvelope
    public let certificate: JSONValue
}

public struct LocalServiceCapability: Sendable, Equatable {
    public let operation: String
    public let method: String
    public let path: String
    public let body: JSONValue
}

public struct LocalServiceCapabilities: Sendable, Equatable {
    public let statusCode: Int
    public let envelope: LocalServiceEnvelope
    public let operations: [LocalServiceCapability]
    public let limits: JSONValue
    public let authentication: JSONValue
}

/// A refusal is an honest result at the engine level, but it is never a
/// successful client call. HTTP-level refusals retain their status separately.
public struct LocalServiceRefusal: Sendable, Equatable {
    public let error: String
    public let reason: String
}

public enum LocalServiceTransportFailure: Sendable, Equatable {
    case cancelled
    case timedOut
    case offline
    case other
}

public enum LocalServiceClientError: Error, Sendable, Equatable {
    case invalidEndpoint
    case invalidConfiguration
    case requestTooLarge(limit: Int, actual: Int)
    case responseTooLarge(limit: Int)
    case authorizationUnavailable
    case invalidAuthorization
    case transport(LocalServiceTransportFailure)
    case redirected(statusCode: Int)
    case unexpectedContentType
    case httpStatus(Int)
    case httpRefusal(statusCode: Int, refusal: LocalServiceRefusal)
    case refusal(LocalServiceRefusal)
    case decodeFailed
    case malformedEnvelope
    case schemaMismatch(expected: String, actual: String?)
    case operationMismatch(expected: LocalServiceOperation, actual: String?)
    case engineSchemaMismatch(expected: String, actual: String?)
    case toolMismatch(expected: LocalServiceOperation, actual: String?)
    case certificateSchemaMismatch(expected: String, actual: String?)
}

/// Limits held by the client, independent from a gateway's own controls.
/// The request default matches Primus's 128 KiB HTTP door. The response cap is
/// deliberately larger because a bounded certificate can contain evidence.
public struct LocalServiceClientConfiguration: Sendable, Equatable {
    public let maximumRequestBytes: Int
    public let maximumResponseBytes: Int
    public let timeout: TimeInterval

    public init(maximumRequestBytes: Int = 128 * 1024,
                maximumResponseBytes: Int = 2 * 1024 * 1024,
                timeout: TimeInterval = 30) throws {
        guard maximumRequestBytes > 0, maximumResponseBytes > 0,
              timeout > 0, timeout <= 600
        else { throw LocalServiceClientError.invalidConfiguration }
        self.maximumRequestBytes = maximumRequestBytes
        self.maximumResponseBytes = maximumResponseBytes
        self.timeout = timeout
    }

    public static let standard: LocalServiceClientConfiguration = {
        // Constants above are local and validated at construction time.
        try! LocalServiceClientConfiguration()
    }()
}

/// The token is requested at the moment a request is made. The client has no
/// string-token initializer and does not persist a token; an app injects its
/// short-lived credential source (for example, a gateway session) at runtime.
public struct LocalServiceAuthorizer: Sendable {
    private let nextBearerToken: @Sendable () async throws -> String?

    public init(nextBearerToken: @escaping @Sendable () async throws -> String? = { nil }) {
        self.nextBearerToken = nextBearerToken
    }

    fileprivate func bearerToken() async throws -> String? {
        try await nextBearerToken()
    }
}

public struct LocalServiceHTTPResponse: Sendable {
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

public enum LocalServiceTransportError: Error, Sendable, Equatable {
    case responseTooLarge(limit: Int)
    case nonHTTPResponse
}

/// The tiny seam used by deterministic tests and by the URLSession adapter.
/// It accepts a cap from the client, so a substitute transport cannot silently
/// bypass the response budget (the client checks it again defensively).
public protocol LocalServiceTransport: Sendable {
    func send(_ request: URLRequest,
              maximumResponseBytes: Int) async throws -> LocalServiceHTTPResponse
}

/// Blocks every redirect. The compact v1 boundary has no redirect semantics;
/// following one could otherwise forward user text or an Authorization header
/// to a host which was never checked by `LocalServiceClient`'s endpoint policy.
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
/// configured budget. Tests inject `LocalServiceTransport` directly; callers
/// cannot supply a redirect-following session to this production transport.
public struct URLSessionLocalServiceTransport: LocalServiceTransport, Sendable {
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
                     maximumResponseBytes: Int) async throws -> LocalServiceHTTPResponse {
        let (bytes, response) = try await session.bytes(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw LocalServiceTransportError.nonHTTPResponse
        }
        if response.expectedContentLength > Int64(maximumResponseBytes) {
            throw LocalServiceTransportError.responseTooLarge(limit: maximumResponseBytes)
        }

        var body = Data()
        if response.expectedContentLength > 0 {
            body.reserveCapacity(min(maximumResponseBytes,
                                     Int(response.expectedContentLength)))
        }
        for try await byte in bytes {
            guard body.count < maximumResponseBytes else {
                throw LocalServiceTransportError.responseTooLarge(limit: maximumResponseBytes)
            }
            body.append(byte)
        }

        var headers: [String: String] = [:]
        for (key, value) in http.allHeaderFields {
            headers[String(describing: key).lowercased()] = String(describing: value)
        }
        return LocalServiceHTTPResponse(statusCode: http.statusCode, headers: headers, body: body)
    }
}

/// URLSession-only client for the intentionally small `/v1` surface. It never
/// shells out to Python and it never attempts a local fallback. It is the one
/// client shared by the macOS app and the iOS app, so the two interfaces
/// cannot drift on endpoint policy, bounds, or schema validation.
public struct LocalServiceClient: Sendable {
    public static let schema = "chiron.local_api/1"
    public static let engineSchema = "primus.engine_server/1"
    public static let certificateSchema = "primus.certificate/2"

    public let baseURL: URL
    public let configuration: LocalServiceClientConfiguration
    private let transport: any LocalServiceTransport
    private let authorizer: LocalServiceAuthorizer

    public init(baseURL: URL,
                configuration: LocalServiceClientConfiguration = .standard,
                authorizer: LocalServiceAuthorizer = LocalServiceAuthorizer(),
                transport: any LocalServiceTransport = URLSessionLocalServiceTransport()) throws {
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
        else { throw LocalServiceClientError.invalidEndpoint }
        self.baseURL = baseURL
        self.configuration = configuration
        self.authorizer = authorizer
        self.transport = transport
    }

    public func capabilities() async throws -> LocalServiceCapabilities {
        let response = try await perform(operation: .capabilities, body: nil)
        guard let result = response.result.objectValue,
              let operationValues = result["operations"]?.arrayValue,
              let limits = result["limits"],
              let authentication = result["authentication"]
        else { throw LocalServiceClientError.malformedEnvelope }

        var operations: [LocalServiceCapability] = []
        for value in operationValues {
            guard let object = value.objectValue,
                  let operation = object["operation"]?.stringValue,
                  let method = object["method"]?.stringValue,
                  let path = object["path"]?.stringValue,
                  let body = object["body"]
            else { throw LocalServiceClientError.malformedEnvelope }
            operations.append(.init(operation: operation, method: method,
                                    path: path, body: body))
        }
        // The endpoint is only useful to this client if it says the two fixed
        // operations still exist. Do not infer a substitute from a drifted
        // capability document.
        guard Set(operations.map(\.operation)) == Set(["collapse", "certify"]),
              operations.count == 2
        else { throw LocalServiceClientError.malformedEnvelope }

        return LocalServiceCapabilities(statusCode: response.statusCode,
                                     envelope: response.envelope,
                                     operations: operations,
                                     limits: limits,
                                     authentication: authentication)
    }

    public func certify(text: String) async throws -> LocalServiceCertification {
        let body = try encode(CertifyRequest(text: text))
        let response = try await perform(operation: .certify, body: body)
        let certificate = try certificate(in: response, operation: .certify)
        guard certificate["schema"]?.stringValue == Self.certificateSchema else {
            throw LocalServiceClientError.certificateSchemaMismatch(
                expected: Self.certificateSchema,
                actual: certificate["schema"]?.stringValue)
        }
        return LocalServiceCertification(statusCode: response.statusCode,
                                   envelope: response.envelope,
                                   certificate: .object(certificate))
    }

    public func collapse(surface: String) async throws -> LocalServiceCollapse {
        let body = try encode(CollapseTextRequest(surface: surface))
        return try await collapse(body: body)
    }

    public func collapse(surface: [Int]) async throws -> LocalServiceCollapse {
        let body = try encode(CollapseArrayRequest(surface: surface))
        return try await collapse(body: body)
    }

    private func collapse(body: Data) async throws -> LocalServiceCollapse {
        let response = try await perform(operation: .collapse, body: body)
        let certificate = try certificate(in: response, operation: .collapse)
        return LocalServiceCollapse(statusCode: response.statusCode,
                              envelope: response.envelope,
                              certificate: .object(certificate))
    }

    private func encode<T: Encodable>(_ value: T) throws -> Data {
        let data = try JSONEncoder().encode(value)
        guard data.count <= configuration.maximumRequestBytes else {
            throw LocalServiceClientError.requestTooLarge(
                limit: configuration.maximumRequestBytes, actual: data.count)
        }
        return data
    }

    private func perform(operation: LocalServiceOperation,
                         body: Data?) async throws -> LocalServiceResponse {
        let request = try await makeRequest(operation: operation, body: body)
        let response: LocalServiceHTTPResponse
        do {
            response = try await transport.send(request,
                                                maximumResponseBytes: configuration.maximumResponseBytes)
        } catch let error as LocalServiceTransportError {
            switch error {
            case .responseTooLarge:
                throw LocalServiceClientError.responseTooLarge(limit: configuration.maximumResponseBytes)
            case .nonHTTPResponse:
                throw LocalServiceClientError.transport(.other)
            }
        } catch is CancellationError {
            throw LocalServiceClientError.transport(.cancelled)
        } catch let error as URLError {
            throw LocalServiceClientError.transport(Self.transportFailure(for: error))
        } catch {
            throw LocalServiceClientError.transport(.other)
        }

        // A test/injected transport must not be able to sneak a larger body
        // past the client just because it did not implement streaming bounds.
        guard response.body.count <= configuration.maximumResponseBytes else {
            throw LocalServiceClientError.responseTooLarge(limit: configuration.maximumResponseBytes)
        }
        // The transport rejects redirect following, but an injected transport
        // can still model a 3xx response. Never decode it as a valid envelope.
        guard !(300...399).contains(response.statusCode) else {
            throw LocalServiceClientError.redirected(statusCode: response.statusCode)
        }
        guard response.headers["content-type"]?.lowercased()
            .split(separator: ";", maxSplits: 1).first == "application/json"
        else { throw LocalServiceClientError.unexpectedContentType }

        let parsed = try decodeEnvelope(response.body, expectedOperation: operation)
        let clientResponse = LocalServiceResponse(statusCode: response.statusCode,
                                               envelope: parsed.envelope,
                                               result: parsed.result)
        if let refusal = try refusal(in: parsed.result) {
            if !(200...299).contains(response.statusCode) {
                throw LocalServiceClientError.httpRefusal(statusCode: response.statusCode,
                                                        refusal: refusal)
            }
            throw LocalServiceClientError.refusal(refusal)
        }
        guard (200...299).contains(response.statusCode) else {
            throw LocalServiceClientError.httpStatus(response.statusCode)
        }
        if operation != .capabilities {
            try validateEngineResult(parsed.result, operation: operation)
        }
        return clientResponse
    }

    private func makeRequest(operation: LocalServiceOperation,
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
                throw LocalServiceClientError.authorizationUnavailable
            }
            if let token {
                guard !token.isEmpty,
                      !token.unicodeScalars.contains(where: { $0.value < 32 || $0.value == 127 })
                else { throw LocalServiceClientError.invalidAuthorization }
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }
        }
        return request
    }

    private func decodeEnvelope(_ data: Data,
                                expectedOperation: LocalServiceOperation) throws -> ParsedEnvelope {
        let root: JSONValue
        do { root = try JSONValue.parse(data) }
        catch { throw LocalServiceClientError.decodeFailed }
        guard let object = root.objectValue,
              let schema = object["schema"]?.stringValue,
              let requestID = object["request_id"]?.stringValue,
              let operation = object["operation"]?.stringValue,
              let engineObject = object["engine"]?.objectValue,
              let primusVersion = engineObject["primus_version"]?.stringValue,
              let certificateSchema = engineObject["certificate_schema"]?.stringValue,
              let result = object["result"]
        else { throw LocalServiceClientError.malformedEnvelope }

        guard schema == Self.schema else {
            throw LocalServiceClientError.schemaMismatch(expected: Self.schema, actual: schema)
        }
        guard Self.isRequestID(requestID) else { throw LocalServiceClientError.malformedEnvelope }
        guard operation == expectedOperation.rawValue else {
            throw LocalServiceClientError.operationMismatch(expected: expectedOperation,
                                                         actual: operation)
        }
        guard certificateSchema == Self.certificateSchema else {
            throw LocalServiceClientError.certificateSchemaMismatch(
                expected: Self.certificateSchema, actual: certificateSchema)
        }
        return ParsedEnvelope(
            envelope: .init(schema: schema, requestID: requestID,
                            operation: expectedOperation,
                            engine: .init(primusVersion: primusVersion,
                                          certificateSchema: certificateSchema)),
            result: result)
    }

    private func refusal(in result: JSONValue) throws -> LocalServiceRefusal? {
        guard let object = result.objectValue else {
            throw LocalServiceClientError.malformedEnvelope
        }
        guard object["status"]?.stringValue == "REFUSED" else { return nil }
        let schema = object["schema"]?.stringValue
        guard schema == Self.engineSchema else {
            throw LocalServiceClientError.engineSchemaMismatch(expected: Self.engineSchema,
                                                            actual: schema)
        }
        guard let error = object["error"]?.stringValue,
              let reason = object["reason"]?.stringValue
        else { throw LocalServiceClientError.malformedEnvelope }
        return LocalServiceRefusal(error: error, reason: reason)
    }

    private func validateEngineResult(_ result: JSONValue,
                                      operation: LocalServiceOperation) throws {
        guard let object = result.objectValue else {
            throw LocalServiceClientError.malformedEnvelope
        }
        let schema = object["schema"]?.stringValue
        guard schema == Self.engineSchema else {
            throw LocalServiceClientError.engineSchemaMismatch(expected: Self.engineSchema,
                                                            actual: schema)
        }
        let tool = object["tool"]?.stringValue
        guard tool == operation.rawValue else {
            throw LocalServiceClientError.toolMismatch(expected: operation, actual: tool)
        }
        guard object["certificate"]?.objectValue != nil else {
            throw LocalServiceClientError.malformedEnvelope
        }
    }

    private func certificate(in response: LocalServiceResponse,
                             operation: LocalServiceOperation) throws -> [String: JSONValue] {
        try validateEngineResult(response.result, operation: operation)
        guard let object = response.result.objectValue,
              let certificate = object["certificate"]?.objectValue
        else { throw LocalServiceClientError.malformedEnvelope }
        return certificate
    }

    private static func transportFailure(for error: URLError) -> LocalServiceTransportFailure {
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
        let envelope: LocalServiceEnvelope
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
