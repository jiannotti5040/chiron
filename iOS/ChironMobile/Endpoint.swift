// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import ChironService

/// A user-selected service endpoint. Validation is deliberately delegated to
/// `LocalServiceClient`, so the application and the shared client cannot drift
/// on the HTTPS/loopback policy.
struct ServiceEndpoint: Sendable, Equatable {
    /// Where the local service listens by default.
    ///
    /// The app used to start with no endpoint at all, which meant a first run
    /// showed "configure an HTTPS gateway" and offered no way forward unless
    /// you already knew the port. A client whose only out-of-the-box state is
    /// an error is not a product.
    ///
    /// Loopback HTTP is the one plaintext case the endpoint policy permits,
    /// precisely because it cannot leave the machine. Anything else still has
    /// to be HTTPS, and this default is overridden the moment an operator
    /// types a real gateway.
    static let localDefault = "http://127.0.0.1:8765"

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
