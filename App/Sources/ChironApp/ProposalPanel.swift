// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import ChironKit
import ChironIntelligence

/// On-device model assistance, rendered so that its status can never be
/// mistaken for a result.
///
/// The panel shows two visually distinct things. A **proposal** is a span the
/// model pointed at: it carries no colour, no badge, and no disposition. A
/// **verdict** appears only after the canonical engine has certified that
/// span. Nothing in this view can put a badge on a proposal, because a
/// proposal has no status field to read.
struct ProposalPanel: View {
    let client: VaultClient
    let sourceText: String

    @State private var availability: ProposerAvailability = .frameworkUnavailable
    @State private var proposals: ProposalResult?
    @State private var certified: [Int: CertifiedSpan] = [:]
    @State private var proposing = false
    @State private var errorText: String?

    /// The engine's answer for one proposed span. Held separately from the
    /// proposal so the two can never be conflated in state either.
    private struct CertifiedSpan {
        let verdicts: [Verdict]
        let refuted: Int
        let summary: String
    }

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 9) {
                header
                availabilityRow
                if let errorText { ErrorBanner(text: errorText) }
                if let proposals { results(proposals) }
            }
            .frame(maxWidth: .infinity, alignment: .leading)
        } label: {
            Label("On-device suggestions", systemImage: "sparkles")
        }
        .task { availability = ProposerRouter.proposer().availability }
    }

    private var header: some View {
        HStack(spacing: 10) {
            Button {
                propose()
            } label: {
                Label(proposing ? "Reading…" : "Suggest claims", systemImage: "sparkles")
            }
            .disabled(proposing || !availability.canRun
                      || sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            if proposing { ProgressView().controlSize(.small) }
            Spacer()
            Text("The model points at text. It never decides.")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
    }

    /// The availability sentence is shown verbatim from the model layer, so a
    /// screen cannot soften or dramatize the reason a model is unavailable.
    private var availabilityRow: some View {
        Label {
            Text(availability.explanation)
        } icon: {
            Image(systemName: availability.canRun ? "checkmark.seal" : "info.circle")
        }
        .font(.caption)
        .foregroundStyle(availability.canRun ? Color.secondary : Color.orange)
    }

    @ViewBuilder
    private func results(_ result: ProposalResult) -> some View {
        if result.claims.isEmpty && result.rejected.isEmpty {
            Text("The model proposed nothing in this text. That is a normal outcome, "
                 + "and it is not a statement that the text is correct.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        if !result.claims.isEmpty {
            VStack(alignment: .leading, spacing: 7) {
                Text("Proposed spans — candidates, not results")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                ForEach(Array(result.claims.enumerated()), id: \.offset) { item in
                    proposalRow(index: item.offset, claim: item.element)
                }
            }
        }
        if !result.rejected.isEmpty {
            // Shown rather than swallowed: a discarded invention is exactly the
            // thing an operator should get to see.
            DisclosureGroup("Discarded by grounding (\(result.rejected.count))") {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(Array(result.rejected.enumerated()), id: \.offset) { item in
                        VStack(alignment: .leading, spacing: 1) {
                            Text(item.element.text)
                                .font(.caption.monospaced())
                                .textSelection(.enabled)
                            Text(reason(item.element.reason))
                                .font(.caption2)
                                .foregroundStyle(.orange)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.top, 3)
            }
            .font(.caption)
        }
    }

    private func proposalRow(index: Int, claim: ProposedClaim) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack(alignment: .top, spacing: 8) {
                Text(claim.text)
                    .font(.system(.callout, design: .monospaced))
                    .textSelection(.enabled)
                    .frame(maxWidth: .infinity, alignment: .leading)
                Button("Certify") { certify(index: index, claim: claim) }
                    .controlSize(.small)
                    .disabled(certified[index] != nil)
            }
            Text("bytes \(claim.byteRange.lowerBound)..<\(claim.byteRange.upperBound) · \(claim.rationale)")
                .font(.caption2.monospacedDigit())
                .foregroundStyle(.tertiary)
            if let outcome = certified[index] {
                HStack(spacing: 6) {
                    // A badge exists only once the engine has spoken.
                    ForEach(Array(outcome.verdicts.enumerated()), id: \.offset) { item in
                        VerdictBadge(verdict: item.element)
                    }
                    Text(outcome.summary)
                        .font(.caption)
                        .foregroundStyle(outcome.refuted > 0 ? Color.red : Color.secondary)
                }
            }
        }
        .padding(.vertical, 3)
    }

    private func reason(_ reason: RejectedProposal.Reason) -> String {
        switch reason {
        case .notPresentInSource:
            "not present in the source — the model wrote something the document does not say"
        case .empty:
            "empty proposal"
        case .tooLong(let limit):
            "longer than \(limit) bytes; a whole document is not a claim"
        }
    }

    private func propose() {
        proposing = true
        errorText = nil
        proposals = nil
        certified = [:]
        let text = sourceText
        Task {
            defer { proposing = false }
            do {
                proposals = try await ProposerRouter.proposer().proposeClaims(in: text)
            } catch ProposerError.unavailable(let reported) {
                availability = reported
                errorText = reported.explanation
            } catch ProposerError.inputTooLarge(let limit, let actual) {
                errorText = "This text is \(actual) bytes; on-device suggestion is bounded to "
                    + "\(limit). Certification itself is unaffected."
            } catch {
                errorText = "The on-device model could not complete a suggestion."
            }
        }
    }

    /// Sends the proposed span to the same canonical engine the rest of the
    /// app uses. The model's rationale is deliberately not forwarded: the
    /// engine certifies text, never a justification for it.
    private func certify(index: Int, claim: ProposedClaim) {
        Task {
            do {
                let raw = try await client.certifyRaw(text: claim.text)
                let certificate = try JSONDecoder().decode(Certificate.self, from: raw)
                let verdicts = certificate.claims.map(\.status)
                let counts = certificate.counts
                certified[index] = CertifiedSpan(
                    verdicts: verdicts,
                    refuted: counts?.refuted ?? 0,
                    summary: certificate.claims.isEmpty
                        ? "nothing exactly checkable in this span"
                        : "\(counts?.verified ?? 0) verified · \(counts?.refuted ?? 0) refuted")
            } catch {
                errorText = "That span could not be certified: \(error.localizedDescription)"
            }
        }
    }
}
