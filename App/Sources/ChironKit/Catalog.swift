// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

// The catalog is discovered, never enumerated. Drop a module into Chiron/ and
// it appears in the app with no edit here — the same discipline full_stack.py
// applies to its stage table.

public struct ModuleCatalog: Codable, Sendable {
    public let schema: String
    public let modules: [ModuleInfo]

    public var importedCount: Int { modules.filter { $0.status == "OK" }.count }
    public var entrypointCount: Int { modules.reduce(0) { $0 + $1.functions.count } }
}

public struct ModuleInfo: Codable, Sendable, Identifiable {
    public var id: String { name }

    public let name: String
    public let status: String
    public let doc: String?
    public let error: String?
    public let functions: [FunctionInfo]
    public let hasSelftest: Bool

    enum CodingKeys: String, CodingKey {
        case name, status, doc, error, functions
        case hasSelftest = "has_selftest"
    }
}

public struct FunctionInfo: Codable, Sendable, Identifiable {
    public var id: String { name }

    public let name: String
    public let doc: String?
    public let params: [String]
    /// How many arguments the function requires. Only 1-argument entrypoints
    /// can be driven from a single input box; the rest are listed but not run.
    public let requiredArity: Int
    /// What the first parameter appears to want, inferred from its name and
    /// annotation: "text", "surface", or "unknown".
    public let firstArgKind: String

    enum CodingKeys: String, CodingKey {
        case name, doc, params
        case requiredArity = "required_arity"
        case firstArgKind = "first_arg_kind"
    }

    public var isRunnable: Bool {
        requiredArity <= 1 && firstArgKind != "unknown"
    }
}

/// One invocation of one vault function.
public struct ModuleCallResult: Codable, Sendable {
    public let module: String
    public let function: String
    public let status: String          // OK | ERROR
    public let ms: Double?
    public let error: String?
    public let result: JSONValue?
}
