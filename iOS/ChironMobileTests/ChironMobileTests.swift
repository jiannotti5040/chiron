// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import XCTest
@testable import ChironMobile

final class ChironMobileTests: XCTestCase {
    func testEndpointPolicyUsesTheSharedRemoteClientRules() throws {
        XCTAssertEqual(try ServiceEndpoint(text: "https://gateway.example.test/v1").url.scheme, "https")
        XCTAssertEqual(try ServiceEndpoint(text: "http://127.0.0.1:8790").url.host, "127.0.0.1")
        XCTAssertEqual(try ServiceEndpoint(text: "http://[::1]:8790").url.host, "::1")
        XCTAssertThrowsError(try ServiceEndpoint(text: "http://gateway.example.test"))
        XCTAssertThrowsError(try ServiceEndpoint(text: "http://localhost:8790"))
        XCTAssertThrowsError(try ServiceEndpoint(text: "not a URL"))
    }

    func testBoundedTextInputRejectsOversizeAndInvalidUTF8WithoutMutation() throws {
        let exact = Data(repeating: 65, count: ServiceTextInput.maximumBytes)
        XCTAssertEqual(try ServiceTextInput.decode(exact).utf8.count,
                       ServiceTextInput.maximumBytes)

        let oversized = Data(repeating: 65, count: ServiceTextInput.maximumBytes + 1)
        XCTAssertThrowsError(try ServiceTextInput.decode(oversized)) { error in
            XCTAssertEqual(error as? ServiceTextInputError,
                           .tooLarge(limit: ServiceTextInput.maximumBytes))
        }
        XCTAssertThrowsError(try ServiceTextInput.decode(Data([0xc3, 0x28]))) { error in
            XCTAssertEqual(error as? ServiceTextInputError, .invalidUTF8)
        }
    }
}
