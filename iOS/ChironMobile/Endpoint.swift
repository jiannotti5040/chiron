// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import ChironService

/// A user-selected service endpoint. Validation is deliberately delegated to
/// `LocalServiceClient`, so the application and the shared client cannot drift
/// on the HTTPS/loopback policy.
struct ServiceEndpoint: Sendable, Equatable {
    let url: URL

    init(text: String) throws {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let url = URL(string: trimmed) else {
            throw LocalServiceClientError.invalidEndpoint
        }
        // Constructing the client performs the canonical endpoint-policy
        // validation without sending a request or storing a credential.
        _ = try LocalServiceClient(baseURL: url)
        self.url = url
    }
}
