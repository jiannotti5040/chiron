// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import ChironRemote

/// A user-selected service endpoint. Validation is deliberately delegated to
/// `MobileAPIClient`, so the application and the shared client cannot drift
/// on the HTTPS/loopback policy.
struct MobileEndpoint: Sendable, Equatable {
    let url: URL

    init(text: String) throws {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed) else {
            throw MobileAPIClientError.invalidEndpoint
        }
        // Constructing the client performs the canonical endpoint-policy
        // validation without sending a request or storing a credential.
        _ = try MobileAPIClient(baseURL: url)
        self.url = url
    }
}
