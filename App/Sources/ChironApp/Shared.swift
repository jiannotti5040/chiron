// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit

/// VERIFIED green, REFUTED red — and REFUSED deliberately neutral, because
/// refusal is the honest answer, not a failure state.
struct VerdictBadge: View {
    let verdict: Verdict

    private var color: Color {
        switch verdict {
        case .verified: .green
        case .refuted: .red
        case .refused: .secondary
        default: .orange
        }
    }

    private var symbol: String {
        switch verdict {
        case .verified: "checkmark.seal.fill"
        case .refuted: "xmark.seal.fill"
        case .refused: "hand.raised.fill"
        default: "questionmark.circle"
        }
    }

    var body: some View {
        Label(verdict.rawValue, systemImage: symbol)
            .font(.caption.weight(.semibold))
            .foregroundStyle(color)
            .padding(.horizontal, 8)
            .padding(.vertical, 3)
            .background(color.opacity(0.12), in: Capsule())
    }
}

struct StatusIcon: View {
    let status: StageStatus

    var body: some View {
        switch status {
        case .ok:
            Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
        case .skipped:
            Image(systemName: "minus.circle").foregroundStyle(.secondary)
        case .error:
            Image(systemName: "exclamationmark.triangle.fill").foregroundStyle(.red)
        default:
            Image(systemName: "questionmark.circle").foregroundStyle(.orange)
        }
    }
}

struct StatTile: View {
    let title: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(title)
                .font(.caption)
                .foregroundStyle(.secondary)
            Text(value)
                .font(.title3.weight(.semibold).monospacedDigit())
        }
        .padding(10)
        .frame(minWidth: 90, alignment: .leading)
        .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 8))
    }
}

struct JSONDetail: View {
    let value: JSONValue

    var body: some View {
        ScrollView([.vertical, .horizontal]) {
            Text(value.rendered())
                .font(.system(.caption, design: .monospaced))
                .textSelection(.enabled)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(8)
        }
        .background(.quaternary.opacity(0.3), in: RoundedRectangle(cornerRadius: 6))
    }
}

struct ErrorBanner: View {
    let text: String

    var body: some View {
        Label(text, systemImage: "exclamationmark.triangle")
            .font(.callout)
            .foregroundStyle(.red)
            .textSelection(.enabled)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(8)
            .background(.red.opacity(0.08), in: RoundedRectangle(cornerRadius: 6))
    }
}

func percent(_ x: Double?) -> String {
    guard let x else { return "—" }
    return "\(Int((x * 100).rounded()))%"
}
