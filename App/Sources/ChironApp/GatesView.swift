// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

private enum GateState {
    case idle
    case running
    case finished(PythonResult)
    case failed(String)
}

struct GatesView: View {
    let client: VaultClient
    @State private var states: [String: GateState] = [:]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(Screen.gates.subtitle)
                .foregroundStyle(.secondary)
            Text("A gate's verdict is its exit code — the app reports it, it does not grade output. "
                 + "A failing gate is information: investigate, never widen a tolerance.")
                .font(.caption)
                .foregroundStyle(.secondary)
            List(GateSpec.standard) { gate in
                GateRow(gate: gate, state: states[gate.id] ?? .idle) {
                    run(gate)
                }
            }
            .listStyle(.inset)
        }
        .padding()
    }

    private func run(_ gate: GateSpec) {
        states[gate.id] = .running
        Task {
            do { states[gate.id] = .finished(try await client.runGate(gate)) }
            catch { states[gate.id] = .failed(error.localizedDescription) }
        }
    }
}

private struct GateRow: View {
    let gate: GateSpec
    let state: GateState
    let onRun: () -> Void
    @State private var expanded = false

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                statusView
                VStack(alignment: .leading, spacing: 1) {
                    Text(gate.title)
                    Text(commandLine)
                        .font(.caption.monospaced())
                        .foregroundStyle(.tertiary)
                }
                Spacer()
                Button("Run") { onRun() }
                    .disabled(isRunning)
            }
            switch state {
            case .finished(let result):
                DisclosureGroup("output", isExpanded: $expanded) {
                    ScrollView {
                        Text(result.stdoutText + (result.stderrText.isEmpty ? "" : "\n" + result.stderrText))
                            .font(.system(.caption, design: .monospaced))
                            .textSelection(.enabled)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                    .frame(maxHeight: 240)
                }
                .font(.caption)
            case .failed(let why):
                ErrorBanner(text: why)
            default:
                EmptyView()
            }
        }
        .padding(.vertical, 4)
    }

    private var isRunning: Bool {
        if case .running = state { return true }
        return false
    }

    private var commandLine: String {
        let cd = gate.workingSubdir.map { "\($0)/ " } ?? ""
        let env = gate.extraEnvironment.map { "\($0.key)=\($0.value) " }.joined()
        return cd + env + "python3 " + gate.arguments.joined(separator: " ")
    }

    @ViewBuilder
    private var statusView: some View {
        switch state {
        case .idle:
            Image(systemName: "circle.dotted").foregroundStyle(.secondary)
        case .running:
            ProgressView().controlSize(.small)
        case .finished(let r):
            if r.exitCode == 0 {
                Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
            } else {
                Image(systemName: "xmark.circle.fill").foregroundStyle(.red)
            }
        case .failed:
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.red)
        }
    }
}
