// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
import ChironContract

#if os(macOS)

/// The one bridge between the app and the vault. Every call shells out to
/// the vault's own entry points; nothing is recomputed on the Swift side,
/// so the app can never disagree with the engines it fronts.
public struct VaultClient: Sendable {
    public let vaultRoot: URL
    public let runner: PythonRunner

    public init(vaultRoot: URL, runner: PythonRunner) {
        self.vaultRoot = vaultRoot
        self.runner = runner
    }

    public static func discover(
        environment: [String: String] = ProcessInfo.processInfo.environment,
        extraCandidates: [URL] = []
    ) -> VaultClient? {
        guard let runner = PythonRunner.locate(environment: environment),
              let root = VaultLocator.locate(environment: environment,
                                             extraCandidates: extraCandidates)
        else { return nil }
        return VaultClient(vaultRoot: root, runner: runner)
    }

    private static let decoder = JSONDecoder()

    // MARK: - Full stack (chiron.full_stack/1)

    /// Raw bytes straight from `full_stack.py --json --stdin` — the headless
    /// mode prints these untouched so nothing is lost in translation. Files
    /// are bounded by the UI, but still travel on stdin: sending them as one
    /// argv element would fail before Python starts on hosts with a smaller
    /// ARG_MAX than the accepted file bound.
    public func fullStackRaw(text: String) async throws -> Data {
        let res = try await runner.run(
            arguments: ["Chiron/full_stack.py", "--json", "--stdin"],
            stdin: Data(text.utf8),
            currentDirectory: vaultRoot)
        guard res.exitCode == 0 else {
            throw VaultError.processFailed(exitCode: res.exitCode, stderr: res.stderrText)
        }
        return res.stdout
    }

    public func fullStack(text: String) async throws -> FullStackRecord {
        let data = try await fullStackRaw(text: text)
        do { return try Self.decoder.decode(FullStackRecord.self, from: data) }
        catch { throw VaultError.decodeFailed(String(describing: error)) }
    }

    // MARK: - Attest (chiron.attestation/1)

    // attest.py exposes attest() as a function; the CLI only ships demo and
    // selftest. This shim calls the function and prints its record — it adds
    // no logic of its own. The payload travels on stdin so no user text ever
    // touches a shell or an argv.
    private static let attestShim = """
    import sys, json
    sys.path.insert(0, sys.argv[1])
    import attest
    payload = json.load(sys.stdin)
    rec = attest.attest(payload["output"],
                        inputs=payload.get("inputs") or None,
                        ground_truth=payload.get("ground_truth"))
    print(json.dumps(rec, default=str))
    """

    public func attest(
        output: String,
        inputs: [String: String] = [:],
        groundTruth: [String: JSONValue]? = nil
    ) async throws -> AttestationRecord {
        var payload: [String: JSONValue] = [
            "output": .string(output),
            "inputs": .object(inputs.mapValues { .string($0) }),
        ]
        if let groundTruth { payload["ground_truth"] = .object(groundTruth) }
        let body = try JSONEncoder().encode(JSONValue.object(payload))

        let chironDir = vaultRoot.appendingPathComponent("Chiron").path
        let res = try await runner.run(
            arguments: ["-c", Self.attestShim, chironDir],
            stdin: body,
            currentDirectory: vaultRoot)
        guard res.exitCode == 0 else {
            throw VaultError.processFailed(exitCode: res.exitCode, stderr: res.stderrText)
        }
        do { return try Self.decoder.decode(AttestationRecord.self, from: res.stdout) }
        catch { throw VaultError.decodeFailed(String(describing: error)) }
    }

    // MARK: - Certify (primus.certificate/2)

    public func certifyRaw(text: String) async throws -> Data {
        // '-' = stdin mode, so text that begins with a dash cannot be
        // mistaken for a flag.
        let res = try await runner.run(
            arguments: ["-m", "primus.cli", "certify", "--json", "-"],
            stdin: Data(text.utf8),
            currentDirectory: vaultRoot.appendingPathComponent("Primus"),
            extraEnvironment: ["PYTHONPATH": "src"])
        guard res.exitCode == 0 else {
            throw VaultError.processFailed(exitCode: res.exitCode, stderr: res.stderrText)
        }
        return res.stdout
    }

    public func certify(text: String) async throws -> Certificate {
        let data = try await certifyRaw(text: text)
        do { return try Self.decoder.decode(Certificate.self, from: data) }
        catch { throw VaultError.decodeFailed(String(describing: error)) }
    }

    // MARK: - Local source record (chiron.source_record/1)

    // `source_provenance.py` deliberately exposes a Python API rather than a
    // broad command surface. This fixed shim calls exactly that one API; the
    // app never reconstructs a hash, count, or line span in Swift.
    private static let sourceRecordShim = #"""
    import json, sys
    sys.path.insert(0, sys.argv[1])
    from source_provenance import register_local_text_file
    print(json.dumps(register_local_text_file(sys.argv[2]), sort_keys=True))
    """#

    /// Runs the canonical bounded registrar over a user-selected, complete
    /// local file. The caller owns authorization for this URL; this method
    /// only holds its security scope through the child-process invocation.
    public func sourceRecordRaw(fileURL: URL) async throws -> Data {
        let scoped = fileURL.startAccessingSecurityScopedResource()
        defer { if scoped { fileURL.stopAccessingSecurityScopedResource() } }

        let chiron = vaultRoot.appendingPathComponent("Chiron").path
        let res = try await runner.run(
            arguments: ["-c", Self.sourceRecordShim, chiron, fileURL.path],
            currentDirectory: vaultRoot)
        guard res.exitCode == 0 else {
            throw VaultError.processFailed(exitCode: res.exitCode, stderr: res.stderrText)
        }
        return res.stdout
    }

    public func sourceRecord(fileURL: URL) async throws -> SourceRecord {
        let data = try await sourceRecordRaw(fileURL: fileURL)
        do { return try Self.decoder.decode(SourceRecord.self, from: data) }
        catch { throw VaultError.decodeFailed(String(describing: error)) }
    }

    // MARK: - Gates

    public func runGate(_ gate: GateSpec, timeout: TimeInterval = 900) async throws -> PythonResult {
        let cwd = gate.workingSubdir.map { vaultRoot.appendingPathComponent($0) } ?? vaultRoot
        return try await runner.run(
            arguments: gate.arguments,
            currentDirectory: cwd,
            extraEnvironment: gate.extraEnvironment,
            timeout: timeout)
    }
}

/// One selftest the app can run and show. Pass/fail is the process exit
/// code — the app reports the gate's own verdict, it does not grade output.
public struct GateSpec: Sendable, Identifiable, Hashable {
    public let id: String
    public let title: String
    public let arguments: [String]
    public let workingSubdir: String?
    public let extraEnvironment: [String: String]

    public init(id: String, title: String, arguments: [String],
                workingSubdir: String? = nil,
                extraEnvironment: [String: String] = [:]) {
        self.id = id
        self.title = title
        self.arguments = arguments
        self.workingSubdir = workingSubdir
        self.extraEnvironment = extraEnvironment
    }

    public static let standard: [GateSpec] = [
        GateSpec(id: "chiron",
                 title: "Chiron selftest",
                 arguments: ["Chiron/chiron.py", "selftest"]),
        GateSpec(id: "fullstack",
                 title: "Full-stack selftest",
                 arguments: ["Chiron/full_stack.py", "selftest"]),
        GateSpec(id: "attest",
                 title: "Attest selftest",
                 arguments: ["Chiron/attest.py", "selftest"]),
        GateSpec(id: "primus",
                 title: "Primus selftest",
                 arguments: ["-m", "primus.cli", "selftest"],
                 workingSubdir: "Primus",
                 extraEnvironment: ["PYTHONPATH": "src"]),
    ]
}

#endif
