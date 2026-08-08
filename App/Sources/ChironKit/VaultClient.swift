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

    // MARK: - Catalog: every module, discovered not enumerated

    private static let catalogShim = #"""
    import sys, os, json, importlib, inspect
    chiron = sys.argv[1]
    sys.path.insert(0, chiron)

    TEXT_HINTS = ("text", "output", "s", "string", "prose", "passage", "content",
                  "sentence", "doc", "body", "claim", "message")
    SEQ_HINTS = ("surface", "seq", "sequence", "values", "terms", "nums",
                 "numbers", "data", "series", "xs")

    def kind_of(p):
        n = p.name.lower()
        ann = getattr(p.annotation, "__name__", str(p.annotation)).lower()
        if n in SEQ_HINTS or "list" in ann or "sequence" in ann or "iterable" in ann:
            return "surface"
        if n in TEXT_HINTS or "str" in ann:
            return "text"
        return "unknown"

    mods = sorted(f[:-3] for f in os.listdir(chiron) if f.endswith(".py"))
    out = []
    for name in mods:
        entry = {"name": name, "functions": [], "has_selftest": False}
        try:
            mod = importlib.import_module(name)
        except BaseException as exc:
            entry.update(status="FAILED", error="%s: %s" % (type(exc).__name__, exc))
            out.append(entry); continue
        entry["status"] = "OK"
        entry["doc"] = ((mod.__doc__ or "").strip().splitlines() or [""])[0][:200]
        fns = []
        for fname, obj in vars(mod).items():
            if fname.startswith("_") or not inspect.isfunction(obj):
                continue
            if getattr(obj, "__module__", None) != name:
                continue
            try:
                sig = inspect.signature(obj)
            except (ValueError, TypeError):
                continue
            params = list(sig.parameters.values())
            positional = [p for p in params
                          if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]
            required = [p for p in positional if p.default is p.empty]
            fns.append({
                "name": fname,
                "doc": ((obj.__doc__ or "").strip().splitlines() or [""])[0][:160],
                "params": [p.name for p in params],
                "required_arity": len(required),
                "first_arg_kind": kind_of(positional[0]) if positional else "unknown",
            })
        entry["functions"] = sorted(fns, key=lambda f: f["name"])
        entry["has_selftest"] = any(
            hasattr(mod, n) for n in ("_selftest", "selftest", "SELFTEST"))
        out.append(entry)

    print(json.dumps({"schema": "chiron.app.catalog/1", "modules": out}))
    """#

    public func catalog() async throws -> ModuleCatalog {
        let chiron = vaultRoot.appendingPathComponent("Chiron").path
        let res = try await runner.run(
            arguments: ["-c", Self.catalogShim, chiron],
            currentDirectory: vaultRoot,
            timeout: 300)
        guard res.exitCode == 0 else {
            throw VaultError.processFailed(exitCode: res.exitCode, stderr: res.stderrText)
        }
        do { return try Self.decoder.decode(ModuleCatalog.self, from: res.stdout) }
        catch { throw VaultError.decodeFailed(String(describing: error)) }
    }

    // Dispatch only. The shim chooses no behaviour of its own: it imports the
    // module the caller named, calls the function the caller named, and reports
    // exactly what came back — or the exception type, never a substitute value.
    private static let callShim = #"""
    import sys, os, json, importlib, time
    chiron = sys.argv[1]
    sys.path.insert(0, chiron)
    req = json.load(sys.stdin)

    def trim(o, d=0):
        if d > 4: return "..."
        if isinstance(o, dict): return {k: trim(v, d+1) for k, v in list(o.items())[:40]}
        if isinstance(o, (list, tuple)): return [trim(v, d+1) for v in o[:40]]
        if isinstance(o, (int, float, bool)) or o is None: return o
        if isinstance(o, str): return o if len(o) <= 4000 else o[:4000] + "..."
        return str(o)[:4000]

    rec = {"module": req["module"], "function": req["function"]}
    t0 = time.time()
    try:
        mod = importlib.import_module(req["module"])
        fn = getattr(mod, req["function"])
        arg = req["text"] if req["kind"] == "text" else req["surface"]
        out = fn(arg)
        rec.update(status="OK", result=trim(out))
    except BaseException as exc:
        rec.update(status="ERROR", error=("%s: %s" % (type(exc).__name__, exc))[:400])
    rec["ms"] = round((time.time() - t0) * 1000, 1)
    print(json.dumps(rec, default=str))
    """#

    public func call(module: String, function: String,
                     text: String, kind: String,
                     timeout: TimeInterval = 300) async throws -> ModuleCallResult {
        let surface = Self.numericSurface(of: text)
        let payload: JSONValue = .object([
            "module": .string(module),
            "function": .string(function),
            "kind": .string(kind),
            "text": .string(text),
            "surface": .array(surface.map { .number(JSONNumber(integer: $0)) }),
        ])
        let body = try JSONEncoder().encode(payload)
        let chiron = vaultRoot.appendingPathComponent("Chiron").path
        let res = try await runner.run(
            arguments: ["-c", Self.callShim, chiron],
            stdin: body,
            currentDirectory: vaultRoot,
            timeout: timeout)
        guard res.exitCode == 0 else {
            throw VaultError.processFailed(exitCode: res.exitCode, stderr: res.stderrText)
        }
        do { return try Self.decoder.decode(ModuleCallResult.self, from: res.stdout) }
        catch { throw VaultError.decodeFailed(String(describing: error)) }
    }

    /// The same numeric surface full_stack.py derives: every integer in the
    /// text, commas stripped, in order.
    public static func numericSurface(of text: String) -> [Int] {
        var out: [Int] = []
        var digits = ""
        for ch in text {
            if ch.isNumber { digits.append(ch) }
            else if ch == "," && !digits.isEmpty { continue }
            else {
                if let n = Int(digits) { out.append(n) }
                digits = ""
            }
        }
        if let n = Int(digits) { out.append(n) }
        return out
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
