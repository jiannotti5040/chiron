// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

/// A JSON number represented as source text rather than a binary floating
/// point value.  Certificates can contain integers larger than a `Double`
/// represents exactly; a client must render those values, not round or
/// recompute them.
public struct JSONNumber: Sendable, Hashable, Codable, CustomStringConvertible {
    public let rawValue: String

    /// Creates a number only when `rawValue` is one complete JSON number.
    /// Keeping the lexical form is intentional: `9007199254740993` must not
    /// become `9007199254740992` merely because a UI decoded it.
    public init(_ rawValue: String) throws {
        guard isValidJSONNumber(rawValue) else {
            throw JSONValueError.invalidNumber
        }
        self.rawValue = rawValue
    }

    public init(integer: Int) {
        self.rawValue = String(integer)
    }

    public init(integer: Int64) {
        self.rawValue = String(integer)
    }

    public var description: String { rawValue }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let value = try? container.decode(Int64.self) {
            self.init(integer: value)
            return
        }
        if let value = try? container.decode(UInt64.self) {
            try self.init(String(value))
            return
        }

        // Codable containers do not expose the original JSON token.  This
        // fallback supports ordinary decimal values for legacy local records,
        // while the mobile HTTP client uses `JSONValue.parse(_:)` below so it
        // retains the exact token from the wire.
        if let value = try? container.decode(Decimal.self) {
            let rendered = NSDecimalNumber(decimal: value).stringValue
            guard isValidJSONNumber(rendered) else {
                throw DecodingError.dataCorruptedError(
                    in: container, debugDescription: "number is not valid JSON")
            }
            try self.init(rendered)
            return
        }
        throw DecodingError.typeMismatch(
            JSONNumber.self,
            .init(codingPath: decoder.codingPath,
                  debugDescription: "JSON number cannot be represented without rounding"))
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        if let value = Int64(rawValue) {
            try container.encode(value)
            return
        }
        if let value = UInt64(rawValue) {
            try container.encode(value)
            return
        }
        guard let value = Decimal(string: rawValue,
                                  locale: Locale(identifier: "en_US_POSIX"))
        else {
            // `Encoder` cannot accept an already-serialized numeric token.
            // Refuse instead of silently sending a rounded Double.  Callers
            // that need a byte-for-byte wire representation use
            // `JSONValue.encodedData()`.
            throw EncodingError.invalidValue(
                self,
                .init(codingPath: encoder.codingPath,
                      debugDescription: "number cannot be encoded without rounding"))
        }
        try container.encode(value)
    }
}

public enum JSONValueError: Error, Sendable, Equatable {
    case invalidNumber
    case malformedJSON
    case maximumDepthExceeded
    case duplicateObjectKey
}

/// Arbitrary JSON.  The mobile boundary preserves numeric source values;
/// consumers render the returned certificate rather than evaluating it on the
/// client.  The legacy Codable conformance remains for the local macOS bridge.
public enum JSONValue: Sendable, Equatable {
    case null
    case bool(Bool)
    case number(JSONNumber)
    case string(String)
    case array([JSONValue])
    case object([String: JSONValue])
}

extension JSONValue: Codable {
    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            self = .null
        } else if let value = try? container.decode(Bool.self) {
            self = .bool(value)
        } else if let value = try? container.decode(String.self) {
            self = .string(value)
        } else if let value = try? container.decode(JSONNumber.self) {
            self = .number(value)
        } else if let values = try? container.decode([JSONValue].self) {
            self = .array(values)
        } else if let values = try? container.decode([String: JSONValue].self) {
            self = .object(values)
        } else {
            throw DecodingError.dataCorruptedError(
                in: container, debugDescription: "value is not JSON")
        }
    }

    public func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        switch self {
        case .null: try container.encodeNil()
        case .bool(let value): try container.encode(value)
        case .number(let value): try container.encode(value)
        case .string(let value): try container.encode(value)
        case .array(let value): try container.encode(value)
        case .object(let value): try container.encode(value)
        }
    }
}

extension JSONValue {
    /// Parses JSON directly from its bytes, preserving every number token.
    /// The decoder rejects duplicate object keys and deeply nested documents,
    /// so an ambiguous or pathological service response is never accepted as
    /// a certificate.
    public static func parse(_ data: Data, maximumDepth: Int = 128) throws -> JSONValue {
        guard maximumDepth >= 0 else { throw JSONValueError.maximumDepthExceeded }
        var parser = JSONValueParser(bytes: Array(data), maximumDepth: maximumDepth)
        return try parser.parseDocument()
    }

    /// Serializes this value without turning `JSONNumber` into a binary float.
    /// Object keys are sorted for deterministic tests and stable diagnostics.
    public func encodedData() throws -> Data {
        var bytes: [UInt8] = []
        try appendJSON(to: &bytes)
        return Data(bytes)
    }

    private func appendJSON(to bytes: inout [UInt8]) throws {
        switch self {
        case .null:
            bytes += Array("null".utf8)
        case .bool(let value):
            bytes += Array((value ? "true" : "false").utf8)
        case .number(let value):
            bytes += Array(value.rawValue.utf8)
        case .string(let value):
            bytes += try JSONEncoder().encode(value)
        case .array(let values):
            bytes.append(91) // [
            for (index, value) in values.enumerated() {
                if index > 0 { bytes.append(44) } // ,
                try value.appendJSON(to: &bytes)
            }
            bytes.append(93) // ]
        case .object(let values):
            bytes.append(123) // {
            for (index, key) in values.keys.sorted().enumerated() {
                if index > 0 { bytes.append(44) } // ,
                bytes += try JSONEncoder().encode(key)
                bytes.append(58) // :
                try values[key]!.appendJSON(to: &bytes)
            }
            bytes.append(125) // }
        }
    }

    /// Human-readable rendering for the detail panes. Keys are sorted so the
    /// same record always renders the same way. Numbers stay as delivered.
    public func rendered(indent: Int = 0) -> String {
        let pad = String(repeating: "  ", count: indent)
        switch self {
        case .null: return "null"
        case .bool(let value): return value ? "true" : "false"
        case .number(let value): return value.rawValue
        case .string(let value): return value
        case .array(let values):
            if values.isEmpty { return "[]" }
            let inner = values.map { "\(pad)  - \($0.rendered(indent: indent + 1))" }
            return "\n" + inner.joined(separator: "\n")
        case .object(let values):
            if values.isEmpty { return "{}" }
            let inner = values.keys.sorted().map {
                "\(pad)  \($0): \(values[$0]!.rendered(indent: indent + 1))"
            }
            return "\n" + inner.joined(separator: "\n")
        }
    }
}

private func isValidJSONNumber(_ value: String) -> Bool {
    let bytes = Array(value.utf8)
    var index = 0

    if index < bytes.count, bytes[index] == 45 { index += 1 } // -
    guard index < bytes.count else { return false }

    if bytes[index] == 48 { // 0
        index += 1
    } else if (49...57).contains(bytes[index]) {
        repeat { index += 1 } while index < bytes.count && (48...57).contains(bytes[index])
    } else {
        return false
    }

    if index < bytes.count, bytes[index] == 46 { // .
        index += 1
        let fractionStart = index
        while index < bytes.count && (48...57).contains(bytes[index]) { index += 1 }
        guard index > fractionStart else { return false }
    }

    if index < bytes.count, bytes[index] == 69 || bytes[index] == 101 { // E/e
        index += 1
        if index < bytes.count, bytes[index] == 43 || bytes[index] == 45 { index += 1 }
        let exponentStart = index
        while index < bytes.count && (48...57).contains(bytes[index]) { index += 1 }
        guard index > exponentStart else { return false }
    }
    return index == bytes.count
}

private struct JSONValueParser {
    let bytes: [UInt8]
    let maximumDepth: Int
    var index = 0

    mutating func parseDocument() throws -> JSONValue {
        skipWhitespace()
        let value = try parseValue(depth: 0)
        skipWhitespace()
        guard index == bytes.count else { throw JSONValueError.malformedJSON }
        return value
    }

    private mutating func parseValue(depth: Int) throws -> JSONValue {
        guard depth <= maximumDepth, index < bytes.count else {
            throw depth > maximumDepth ? JSONValueError.maximumDepthExceeded : JSONValueError.malformedJSON
        }
        switch bytes[index] {
        case 110: // n
            try consumeLiteral("null")
            return .null
        case 116: // t
            try consumeLiteral("true")
            return .bool(true)
        case 102: // f
            try consumeLiteral("false")
            return .bool(false)
        case 34: // "
            return .string(try parseString())
        case 91: // [
            return .array(try parseArray(depth: depth + 1))
        case 123: // {
            return .object(try parseObject(depth: depth + 1))
        case 45, 48...57:
            return .number(try parseNumber())
        default:
            throw JSONValueError.malformedJSON
        }
    }

    private mutating func parseArray(depth: Int) throws -> [JSONValue] {
        guard depth <= maximumDepth else { throw JSONValueError.maximumDepthExceeded }
        index += 1 // [
        skipWhitespace()
        if take(93) { return [] } // ]
        var values: [JSONValue] = []
        while true {
            skipWhitespace()
            values.append(try parseValue(depth: depth))
            skipWhitespace()
            if take(93) { return values }
            guard take(44) else { throw JSONValueError.malformedJSON } // ,
        }
    }

    private mutating func parseObject(depth: Int) throws -> [String: JSONValue] {
        guard depth <= maximumDepth else { throw JSONValueError.maximumDepthExceeded }
        index += 1 // {
        skipWhitespace()
        if take(125) { return [:] } // }
        var values: [String: JSONValue] = [:]
        while true {
            skipWhitespace()
            guard index < bytes.count, bytes[index] == 34 else {
                throw JSONValueError.malformedJSON
            }
            let key = try parseString()
            guard values[key] == nil else { throw JSONValueError.duplicateObjectKey }
            skipWhitespace()
            guard take(58) else { throw JSONValueError.malformedJSON } // :
            skipWhitespace()
            values[key] = try parseValue(depth: depth)
            skipWhitespace()
            if take(125) { return values }
            guard take(44) else { throw JSONValueError.malformedJSON } // ,
        }
    }

    private mutating func parseString() throws -> String {
        let start = index
        index += 1 // opening quote
        while index < bytes.count {
            let byte = bytes[index]
            if byte == 34 { // closing quote
                index += 1
                do {
                    return try JSONDecoder().decode(String.self,
                                                     from: Data(bytes[start..<index]))
                } catch {
                    throw JSONValueError.malformedJSON
                }
            }
            if byte < 32 { throw JSONValueError.malformedJSON }
            if byte == 92 { // backslash
                index += 1
                guard index < bytes.count else { throw JSONValueError.malformedJSON }
                if bytes[index] == 117 { // u
                    guard index + 4 < bytes.count else { throw JSONValueError.malformedJSON }
                    index += 5
                } else {
                    index += 1
                }
            } else {
                index += 1
            }
        }
        throw JSONValueError.malformedJSON
    }

    private mutating func parseNumber() throws -> JSONNumber {
        let start = index
        if take(45) {} // -
        guard index < bytes.count else { throw JSONValueError.malformedJSON }
        if take(48) { // 0
            // A following digit is left for the enclosing grammar to reject.
        } else {
            guard index < bytes.count, (49...57).contains(bytes[index]) else {
                throw JSONValueError.malformedJSON
            }
            repeat { index += 1 } while index < bytes.count && (48...57).contains(bytes[index])
        }
        if take(46) { // .
            let fractionStart = index
            while index < bytes.count && (48...57).contains(bytes[index]) { index += 1 }
            guard index > fractionStart else { throw JSONValueError.malformedJSON }
        }
        if index < bytes.count, bytes[index] == 69 || bytes[index] == 101 { // E/e
            index += 1
            if index < bytes.count, bytes[index] == 43 || bytes[index] == 45 { index += 1 }
            let exponentStart = index
            while index < bytes.count && (48...57).contains(bytes[index]) { index += 1 }
            guard index > exponentStart else { throw JSONValueError.malformedJSON }
        }
        guard let value = String(bytes: bytes[start..<index], encoding: .utf8) else {
            throw JSONValueError.malformedJSON
        }
        do { return try JSONNumber(value) }
        catch { throw JSONValueError.malformedJSON }
    }

    private mutating func consumeLiteral(_ literal: String) throws {
        let literalBytes = Array(literal.utf8)
        guard bytes.count - index >= literalBytes.count,
              bytes[index..<(index + literalBytes.count)].elementsEqual(literalBytes)
        else { throw JSONValueError.malformedJSON }
        index += literalBytes.count
    }

    private mutating func skipWhitespace() {
        while index < bytes.count, [9, 10, 13, 32].contains(bytes[index]) { index += 1 }
    }

    private mutating func take(_ byte: UInt8) -> Bool {
        guard index < bytes.count, bytes[index] == byte else { return false }
        index += 1
        return true
    }
}

public extension JSONValue {
    /// Typed reads of a decoded record.
    ///
    /// These were private to the service client, which meant any interface
    /// wanting to read a record had to write its own copy — and a second
    /// reader of the same bytes is a second chance to disagree about them.
    /// They belong with the type.
    ///
    /// Every one returns nil rather than coercing. A number is not silently a
    /// string and a missing key is not zero, because a record that reports
    /// `refuted: 0` and one that omits the field mean different things.
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

    var boolValue: Bool? {
        guard case .bool(let value) = self else { return nil }
        return value
    }

    /// Whole numbers only. A fractional value returns nil rather than
    /// truncating: a count that arrived as 2.5 is a contract violation worth
    /// seeing, not something to round.
    /// Whole numbers only, read from the number's own lexical form.
    ///
    /// `JSONNumber` keeps `rawValue` precisely so a large integer is not
    /// damaged by a decode it never asked for; going through Decimal here
    /// would reintroduce exactly that. A fractional value returns nil rather
    /// than truncating — a count that arrived as 2.5 is a contract violation
    /// worth seeing, not something to round.
    var intValue: Int? {
        guard case .number(let number) = self else { return nil }
        return Int(number.rawValue)
    }

    /// Lossy by nature and only for display. Never use this on a value that
    /// will be compared or certified.
    var doubleValue: Double? {
        guard case .number(let number) = self else { return nil }
        return Double(number.rawValue)
    }

    /// Parse a JSON string the operator typed. Returns nil on anything
    /// malformed rather than throwing, because the caller's next move is to
    /// leave the field out, not to crash.
    /// Whether this value is JSON `null`. Distinct from "absent": an engine
    /// that returns `null` for an operation's arguments is deliberately saying
    /// the operation must not be offered, which is different from not
    /// mentioning it.
    var isNull: Bool { if case .null = self { return true }; return false }

    static func decode(_ text: String) -> JSONValue? {
        try? JSONValue.parse(Data(text.utf8))
    }

    /// Stable, human-readable rendering for display.
    ///
    /// Sorted keys so the same record reads the same way twice — an operator
    /// comparing two runs should not have to discount key order.
    static func encodePretty(_ value: JSONValue) throws -> String {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
        return String(decoding: try encoder.encode(value), as: UTF8.self)
    }
}
