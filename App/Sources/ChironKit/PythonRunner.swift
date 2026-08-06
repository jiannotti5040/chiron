// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation

public struct PythonResult: Sendable {
    public let stdout: Data
    public let stderrText: String
    public let exitCode: Int32
    public var stdoutText: String { String(decoding: stdout, as: UTF8.self) }
}

public enum VaultError: Error, LocalizedError, Sendable {
    case pythonNotFound
    case vaultNotFound
    case timedOut(seconds: Double)
    case processFailed(exitCode: Int32, stderr: String)
    case decodeFailed(String)

    public var errorDescription: String? {
        switch self {
        case .pythonNotFound:
            return "No python3 found. Install Python 3, or set CHIRON_PYTHON to its path."
        case .vaultNotFound:
            return "Vault not found. Open the app from inside the repository, or set CHIRON_VAULT to its root."
        case .timedOut(let s):
            return "The vault process did not finish within \(Int(s))s and was stopped."
        case .processFailed(let code, let stderr):
            return "Vault process exited \(code): \(stderr.suffix(400))"
        case .decodeFailed(let why):
            return "Could not decode the vault's record: \(why)"
        }
    }
}

// Process, Pipe, and friends are not Sendable; each is confined to one run()
// call and touched from at most one thread at a time. The box makes that
// containment explicit to the compiler.
private final class Box<T>: @unchecked Sendable {
    let value: T
    init(_ value: T) { self.value = value }
}

private final class Flag: @unchecked Sendable {
    private let lock = NSLock()
    private var on = false
    func set() { lock.lock(); on = true; lock.unlock() }
    func isSet() -> Bool { lock.lock(); defer { lock.unlock() }; return on }
}

/// Runs the vault's own Python. This is the whole integration strategy:
/// the app never reimplements a module, it invokes them and renders what
/// they return.
public struct PythonRunner: Sendable {
    public let pythonPath: String

    public init(pythonPath: String) {
        self.pythonPath = pythonPath
        Self.ignoreSIGPIPEOnce
    }

    // A child that exits before reading its stdin — an import error inside
    // the vault, say — leaves the write end broken. The default SIGPIPE
    // disposition would then kill the app instead of surfacing the child's
    // error. Ignoring it turns that into the EPIPE the writer already
    // handles.
    private static let ignoreSIGPIPEOnce: Void = {
        signal(SIGPIPE, SIG_IGN)
    }()

    /// CHIRON_PYTHON wins, then PATH, then the usual macOS install locations.
    public static func locate(
        environment: [String: String] = ProcessInfo.processInfo.environment
    ) -> PythonRunner? {
        let fm = FileManager.default
        if let p = environment["CHIRON_PYTHON"], fm.isExecutableFile(atPath: p) {
            return PythonRunner(pythonPath: p)
        }
        var candidates: [String] = []
        if let path = environment["PATH"] {
            candidates += path.split(separator: ":").map { "\($0)/python3" }
        }
        candidates += [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
        ]
        for c in candidates where fm.isExecutableFile(atPath: c) {
            return PythonRunner(pythonPath: c)
        }
        return nil
    }

    public func run(
        arguments: [String],
        stdin: Data? = nil,
        currentDirectory: URL? = nil,
        extraEnvironment: [String: String] = [:],
        timeout: TimeInterval = 600
    ) async throws -> PythonResult {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: pythonPath)
        process.arguments = arguments
        if let currentDirectory { process.currentDirectoryURL = currentDirectory }

        var env = ProcessInfo.processInfo.environment
        env.merge(extraEnvironment) { _, new in new }
        env["PYTHONUNBUFFERED"] = "1"
        process.environment = env

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe
        let inPipe: Pipe? = stdin == nil ? nil : Pipe()
        if let inPipe { process.standardInput = inPipe }

        try process.run()

        if let inPipe, let stdin {
            let writeBox = Box(inPipe.fileHandleForWriting)
            DispatchQueue.global().async {
                try? writeBox.value.write(contentsOf: stdin)
                try? writeBox.value.close()
            }
        }

        let procBox = Box(process)
        let timedOut = Flag()
        let watchdog = DispatchWorkItem {
            if procBox.value.isRunning {
                timedOut.set()
                procBox.value.terminate()
            }
        }
        DispatchQueue.global().asyncAfter(deadline: .now() + timeout, execute: watchdog)

        // Drain both pipes concurrently while waiting — a full pipe buffer
        // would otherwise deadlock a chatty stage.
        async let outData = Self.readAll(Box(outPipe))
        async let errData = Self.readAll(Box(errPipe))
        await Self.waitForExit(procBox)
        watchdog.cancel()

        let out = await outData
        let err = String(decoding: await errData, as: UTF8.self)
        if timedOut.isSet() { throw VaultError.timedOut(seconds: timeout) }
        return PythonResult(stdout: out, stderrText: err,
                            exitCode: procBox.value.terminationStatus)
    }

    private static func readAll(_ pipe: Box<Pipe>) async -> Data {
        await withCheckedContinuation { cont in
            DispatchQueue.global().async {
                let data = (try? pipe.value.fileHandleForReading.readToEnd()) ?? Data()
                cont.resume(returning: data)
            }
        }
    }

    private static func waitForExit(_ process: Box<Process>) async {
        await withCheckedContinuation { (cont: CheckedContinuation<Void, Never>) in
            DispatchQueue.global().async {
                process.value.waitUntilExit()
                cont.resume()
            }
        }
    }
}
