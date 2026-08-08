// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import Security

/// Stores a user-provided, short-lived gateway credential only in Keychain.
/// The app never ships a credential and never writes one to UserDefaults.
enum KeychainTokenStore {
    private static let service = "com.jacobiannotti.chiron.mobile"

    /// A bearer is scoped to the complete validated base URL.  The endpoint is
    /// user-configurable, so a token saved for one gateway must never be
    /// selected merely because the user later types another HTTPS host.
    static func read(for endpoint: URL) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account(for: endpoint),
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data,
              let token = String(data: data, encoding: .utf8),
              !token.isEmpty
        else { return nil }
        return token
    }

    static func save(_ token: String, for endpoint: URL) throws {
        guard !token.isEmpty else {
            throw TokenStoreError.emptyToken
        }
        let data = Data(token.utf8)
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account(for: endpoint),
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly,
        ]
        let update = SecItemUpdate(query as CFDictionary, attributes as CFDictionary)
        if update == errSecItemNotFound {
            var create = query
            attributes.forEach { create[$0.key] = $0.value }
            let status = SecItemAdd(create as CFDictionary, nil)
            guard status == errSecSuccess else { throw TokenStoreError.keychain(status) }
        } else if update != errSecSuccess {
            throw TokenStoreError.keychain(update)
        }
    }

    static func remove(for endpoint: URL) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account(for: endpoint),
        ]
        let status = SecItemDelete(query as CFDictionary)
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw TokenStoreError.keychain(status)
        }
    }

    private static func account(for endpoint: URL) -> String {
        // `MobileEndpoint` has already rejected credentials, query, and
        // fragments. Retaining the exact base URL, including a routing path,
        // prevents a bearer for `/tenant-a` being sent to `/tenant-b`.
        "gateway-bearer:\(endpoint.absoluteString)"
    }
}

enum TokenStoreError: LocalizedError {
    case emptyToken
    case keychain(OSStatus)

    var errorDescription: String? {
        switch self {
        case .emptyToken:
            return "Enter a gateway session token before saving it."
        case .keychain:
            return "The gateway session token could not be updated in Keychain."
        }
    }
}
