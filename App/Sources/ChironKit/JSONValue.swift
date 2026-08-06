// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

/// Arbitrary JSON, preserved losslessly. Stage results in a
/// `chiron.full_stack/1` record vary by module and are trimmed server-side;
/// the app renders whatever the vault returned rather than assuming a shape.
public enum JSONValue: Sendable, Equatable {
    case null
    case bool(Bool)
    case number(Double)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])
}

extension JSONValue: Codable {
    public init(from decoder: Decoder) throws {
        let c = try decoder.singleValueContainer()
        if c.decodeNil() {
            self = .null
        } else if let b = try? c.decode(Bool.self) {
            self = .bool(b)
        } else if let n = try? c.decode(Double.self) {
            self = .number(n)
        } else if let s = try? c.decode(String.self) {
            self = .string(s)
        } else if let a = try? c.decode([JSONValue].self) {
            self = .array(a)
        } else if let o = try? c.decode([String: JSONValue].self) {
            self = .object(o)
        } else {
            throw DecodingError.dataCorruptedError(
                in: c, debugDescription: "value is not JSON")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.singleValueContainer()
        switch self {
        case .null: try c.encodeNil()
        case .bool(let b): try c.encode(b)
        case .number(let n): try c.encode(n)
        case .string(let s): try c.encode(s)
        case .array(let a): try c.encode(a)
        case .object(let o): try c.encode(o)
        }
    }
}

extension JSONValue {
    /// Human-readable rendering for the detail panes. Keys sorted so the
    /// same record always renders the same way.
    public func rendered(indent: Int = 0) -> String {
        let pad = String(repeating: "  ", count: indent)
        switch self {
        case .null: return "null"
        case .bool(let b): return b ? "true" : "false"
        case .number(let n):
            if n == n.rounded(), abs(n) < 1e15 {
                return String(Int64(n))
            }
            return String(n)
        case .string(let s): return s
        case .array(let a):
            if a.isEmpty { return "[]" }
            let inner = a.map { "\(pad)  - \($0.rendered(indent: indent + 1))" }
            return "\n" + inner.joined(separator: "\n")
        case .object(let o):
            if o.isEmpty { return "{}" }
            let inner = o.keys.sorted().map {
                "\(pad)  \($0): \(o[$0]!.rendered(indent: indent + 1))"
            }
            return "\n" + inner.joined(separator: "\n")
        }
    }
}
