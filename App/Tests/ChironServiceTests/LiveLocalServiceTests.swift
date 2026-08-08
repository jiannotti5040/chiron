// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import XCTest
@testable import ChironContract
@testable import ChironService

/// End-to-end evidence for the one vertical slice that both interfaces use:
/// a real URLSession request from the shared client, over real HTTP, into the
/// canonical Primus engine, returning a real certificate.
///
/// The deterministic suite in `LocalServiceClientTests` injects a transport and
/// never opens a socket. This suite is the opposite: it is skipped unless an
/// operator points it at a server they started themselves, because a test that
/// silently passes when nothing is listening is not evidence.
///
///     PYTHONPATH=Primus/src python3 -m primus.engine_server --port 8765 &
///     CHIRON_LOCAL_API_URL=http://127.0.0.1:8765 \
///       swift test --scratch-path /tmp/chiron-build
///
/// The iOS app links this exact client, so a pass here exercises the same
/// endpoint policy, bounds, envelope validation, and schema checks that the
/// device build runs.
final class LiveLocalServiceTests: XCTestCase {
    private var baseURL: URL? {
        guard let raw = ProcessInfo.processInfo.environment["CHIRON_LOCAL_API_URL"],
              !raw.isEmpty, let url = URL(string: raw)
        else { return nil }
        return url
    }

    private func liveClient() throws -> LocalServiceClient? {
        guard let baseURL else { return nil }
        return try LocalServiceClient(baseURL: baseURL)
    }

    func testLiveCapabilitiesReportTheTwoFixedOperations() async throws {
        guard let client = try liveClient() else {
            throw XCTSkip("Set CHIRON_LOCAL_API_URL to a running engine_server to run live tests.")
        }
        let capabilities = try await client.capabilities()

        XCTAssertEqual(capabilities.envelope.schema, LocalServiceClient.schema)
        XCTAssertEqual(capabilities.envelope.engine.certificateSchema,
                       LocalServiceClient.certificateSchema)
        XCTAssertEqual(Set(capabilities.operations.map(\.operation)), ["collapse", "certify"])
    }

    /// The claim under test is deliberately mixed: one arithmetic statement is
    /// true and one is false. A client that quietly "helped" — by rounding,
    /// re-deciding, or reporting a score — would not produce this exact pair.
    func testLiveCertifyReturnsVerifiedAndRefutedClaimsUnaltered() async throws {
        guard let client = try liveClient() else {
            throw XCTSkip("Set CHIRON_LOCAL_API_URL to a running engine_server to run live tests.")
        }
        let certification = try await client.certify(
            text: "The sum of 2 and 2 is 4. The product of 3 and 4 is 11.")

        XCTAssertTrue((200...299).contains(certification.statusCode))
        XCTAssertEqual(certification.envelope.operation, .certify)

        guard case .object(let certificate) = certification.certificate else {
            return XCTFail("the certificate must decode as a JSON object")
        }
        XCTAssertEqual(certificate["schema"], .string(LocalServiceClient.certificateSchema))

        guard case .array(let claims)? = certificate["claims"] else {
            return XCTFail("the certificate must carry a claims array")
        }
        let statuses: [String] = claims.compactMap { claim in
            guard case .object(let fields) = claim,
                  case .string(let status)? = fields["status"] else { return nil }
            return status
        }
        // The canonical vocabulary, not a translation of it.
        XCTAssertEqual(statuses, ["VERIFIED", "REFUTED"],
                       "the engine's own dispositions must survive the wire unchanged")

        guard case .object(let counts)? = certificate["counts"] else {
            return XCTFail("the certificate must carry counts")
        }
        XCTAssertEqual(counts["verified"], .number(JSONNumber(integer: 1)))
        XCTAssertEqual(counts["refuted"], .number(JSONNumber(integer: 1)))
    }

    /// Collapse either recovers a structure it checked exactly, or it refuses.
    /// A collapse certificate carries the recovered model rather than the
    /// `schema`/`status` pair a certify certificate uses, so this asserts the
    /// recovery contract itself: the Fibonacci surface must come back as an
    /// order-2 linear recurrence marked verified, with zero residual.
    func testLiveCollapseRecoversAnExactStructureOrRefuses() async throws {
        guard let client = try liveClient() else {
            throw XCTSkip("Set CHIRON_LOCAL_API_URL to a running engine_server to run live tests.")
        }
        do {
            let collapse = try await client.collapse(surface: [1, 1, 2, 3, 5, 8, 13])
            guard case .object(let certificate) = collapse.certificate else {
                return XCTFail("the certificate must decode as a JSON object")
            }
            XCTAssertEqual(certificate["model_class"], .string("linear_recurrence_order2"))

            guard case .object(let structure)? = certificate["structure"] else {
                return XCTFail("a recovered collapse must describe its structure")
            }
            XCTAssertEqual(structure["family"], .string("linear_recurrence"))
            XCTAssertEqual(structure["verified"], .bool(true),
                           "an unverified recovery must not be returned as a recovery")
            XCTAssertEqual(certificate["residual_bits"], .number(try JSONNumber("0.0")),
                           "an exact recovery leaves no residual to explain")
        } catch LocalServiceClientError.refusal(let refusal) {
            // Equally correct: refusal is a result, not a transport failure.
            XCTAssertFalse(refusal.reason.isEmpty,
                           "a refusal must explain itself rather than fail silently")
        }
    }
}
