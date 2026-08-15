// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

/// The one bounded, byte-preserving text intake shared by typing and import.
/// The service accepts inline text only; a client must never turn an oversized
/// or invalid byte stream into a silently altered request.
enum ServiceTextInput {
    static let maximumBytes = 100_000

    static func validate(_ text: String) throws {
        guard text.utf8.count <= maximumBytes else {
            throw ServiceTextInputError.tooLarge(limit: maximumBytes)
        }
    }

    static func read(from url: URL) throws -> String {
        let handle = try FileHandle(forReadingFrom: url)
        defer { try? handle.close() }
        // One extra byte establishes oversize without loading the remainder
        // of an arbitrarily large user-selected file into memory.
        let data = try handle.read(upToCount: maximumBytes + 1) ?? Data()
        return try decode(data)
    }

    static func decode(_ data: Data) throws -> String {
        guard data.count <= maximumBytes else {
            throw ServiceTextInputError.tooLarge(limit: maximumBytes)
        }
        guard let text = String(data: data, encoding: .utf8) else {
            throw ServiceTextInputError.invalidUTF8
        }
        return text
    }
}

enum ServiceTextInputError: LocalizedError, Equatable {
    case tooLarge(limit: Int)
    case invalidUTF8

    var errorDescription: String? {
        switch self {
        case .tooLarge(let limit):
            return "The selected text is larger than \(limit) UTF-8 bytes. No partial request was sent."
        case .invalidUTF8:
            return "The selected file is not valid UTF-8 text, so no altered text was sent for certification."
        }
    }
}
