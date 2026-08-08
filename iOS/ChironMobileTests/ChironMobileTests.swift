// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import XCTest
@testable import ChironMobile

final class ChironMobileTests: XCTestCase {
    func testEndpointPolicyUsesTheSharedRemoteClientRules() throws {
        XCTAssertEqual(try MobileEndpoint(text: "https://gateway.example.test/v1").url.scheme, "https")
        XCTAssertEqual(try MobileEndpoint(text: "http://127.0.0.1:8790").url.host, "127.0.0.1")
        XCTAssertEqual(try MobileEndpoint(text: "http://[::1]:8790").url.host, "::1")
        XCTAssertThrowsError(try MobileEndpoint(text: "http://gateway.example.test"))
        XCTAssertThrowsError(try MobileEndpoint(text: "http://localhost:8790"))
        XCTAssertThrowsError(try MobileEndpoint(text: "not a URL"))
    }

    func testBoundedTextInputRejectsOversizeAndInvalidUTF8WithoutMutation() throws {
        let exact = Data(repeating: 65, count: MobileTextInput.maximumBytes)
        XCTAssertEqual(try MobileTextInput.decode(exact).utf8.count,
                       MobileTextInput.maximumBytes)

        let oversized = Data(repeating: 65, count: MobileTextInput.maximumBytes + 1)
        XCTAssertThrowsError(try MobileTextInput.decode(oversized)) { error in
            XCTAssertEqual(error as? MobileTextInputError,
                           .tooLarge(limit: MobileTextInput.maximumBytes))
        }
        XCTAssertThrowsError(try MobileTextInput.decode(Data([0xc3, 0x28]))) { error in
            XCTAssertEqual(error as? MobileTextInputError, .invalidUTF8)
        }
    }
}
