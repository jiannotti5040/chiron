// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import UniformTypeIdentifiers
import ChironContract
import ChironRemote

struct ContentView: View {
    // The endpoint is not a credential, so user-controlled endpoint selection
    // can persist normally. Tokens stay exclusively in Keychain.
    @AppStorage("chiron.mobile.endpoint") private var endpointText = ""
    @State private var sourceText = "The sum of 2 and 2 is 4. The product of 3 and 4 is 11."
    @State private var result: JSONValue?
    @State private var requestID: String?
    @State private var errorText: String?
    @State private var working = false
    @State private var importing = false
    @State private var showSettings = false

    private var endpointIsConfigured: Bool {
        (try? MobileEndpoint(text: endpointText)) != nil
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    capabilityNotice
                    inputSection
                    actionSection
                    outputSection
                }
                .padding()
            }
            .navigationTitle("Chiron")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Connection", systemImage: "gearshape") {
                        showSettings = true
                    }
                }
            }
            .sheet(isPresented: $showSettings) {
                ConnectionSettings(endpointText: $endpointText)
            }
            .fileImporter(isPresented: $importing,
                          allowedContentTypes: [.plainText, .text, .json],
                          allowsMultipleSelection: false) { load(result: $0) }
        }
    }

    private var capabilityNotice: some View {
        VStack(alignment: .leading, spacing: 6) {
            Label("Deterministic certification through the Chiron service", systemImage: "checkmark.seal")
                .font(.headline)
            Text("This iOS client sends only the text you choose to the versioned /v1 certify route. "
                 + "It never runs Python, imports a vault path, or re-evaluates certificate numbers on device.")
                .font(.callout)
                .foregroundStyle(.secondary)
            if endpointText.isEmpty {
                Label("Configure an HTTPS gateway before sending a request.", systemImage: "lock")
                    .font(.caption)
                    .foregroundStyle(.orange)
            } else if !endpointIsConfigured {
                Label("This endpoint is invalid. Use HTTPS, or an exact loopback HTTP address for local development.",
                      systemImage: "exclamationmark.triangle")
                    .font(.caption)
                    .foregroundStyle(.red)
            } else {
                Text("Endpoint: \(endpointText)")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(.quaternary.opacity(0.55), in: RoundedRectangle(cornerRadius: 12))
    }

    private var inputSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("Text to certify")
                    .font(.headline)
                Spacer()
                Button("Import text…", systemImage: "doc.badge.plus") { importing = true }
                    .font(.callout)
            }
            TextEditor(text: $sourceText)
                .font(.body)
                .frame(minHeight: 180)
                .padding(4)
                .overlay(RoundedRectangle(cornerRadius: 8).strokeBorder(.quaternary))
            Text("Imports are user-selected and must fit the service's bounded inline-text contract. "
                 + "Unsupported or oversized files are not silently truncated.")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }

    private var actionSection: some View {
        HStack(spacing: 12) {
            Button {
                certify()
            } label: {
                Label(working ? "Certifying…" : "Certify", systemImage: "checkmark.seal")
            }
            .buttonStyle(.borderedProminent)
            .disabled(working || sourceText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                      || !endpointIsConfigured)
            if working { ProgressView().controlSize(.small) }
            Spacer()
        }
    }

    @ViewBuilder
    private var outputSection: some View {
        if let errorText {
            Label(errorText, systemImage: "exclamationmark.triangle")
                .foregroundStyle(.red)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
                .background(.red.opacity(0.08), in: RoundedRectangle(cornerRadius: 10))
        }
        if let result {
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Certificate")
                        .font(.headline)
                    Spacer()
                    if let requestID {
                        Text("request \(requestID.prefix(12))…")
                            .font(.caption.monospaced())
                            .foregroundStyle(.secondary)
                    }
                }
                ScrollView(.horizontal) {
                    Text(result.rendered())
                        .font(.system(.caption, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(10)
                }
                .background(.quaternary.opacity(0.4), in: RoundedRectangle(cornerRadius: 8))
            }
        } else if errorText == nil {
            ContentUnavailableView("No certificate yet",
                                   systemImage: "checkmark.seal",
                                   description: Text("A response can verify, refute, or honestly refuse the supplied claims."))
                .frame(maxWidth: .infinity)
                .padding(.vertical, 30)
        }
    }

    private func certify() {
        errorText = nil
        result = nil
        requestID = nil
        let text = sourceText
        do {
            try MobileTextInput.validate(text)
        } catch {
            errorText = error.localizedDescription
            return
        }
        working = true
        let endpoint = endpointText
        Task {
            defer { working = false }
            do {
                let configuredEndpoint = try MobileEndpoint(text: endpoint).url
                let client = try MobileAPIClient(
                    baseURL: configuredEndpoint,
                    authorizer: MobileAPIAuthorizer(nextBearerToken: {
                        KeychainTokenStore.read(for: configuredEndpoint)
                    }))
                let certified = try await client.certify(text: text)
                result = certified.certificate
                requestID = certified.envelope.requestID
            } catch let error as MobileAPIClientError {
                errorText = message(for: error)
            } catch {
                errorText = "The certification request could not be completed."
            }
        }
    }

    private func load(result: Result<[URL], Error>) {
        do {
            guard let url = try result.get().first else { return }
            let scoped = url.startAccessingSecurityScopedResource()
            defer { if scoped { url.stopAccessingSecurityScopedResource() } }
            sourceText = try MobileTextInput.read(from: url)
            errorText = nil
        } catch {
            errorText = error.localizedDescription
        }
    }
}

private struct ConnectionSettings: View {
    @Environment(\.dismiss) private var dismiss
    @Binding var endpointText: String
    @State private var tokenDraft = ""
    @State private var message: String?

    private var configuredEndpoint: URL? {
        try? MobileEndpoint(text: endpointText).url
    }

    private var hasStoredToken: Bool {
        configuredEndpoint.map { KeychainTokenStore.read(for: $0) != nil } ?? false
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Service endpoint") {
                    TextField("https://gateway.example service root", text: $endpointText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .keyboardType(.URL)
                    Text("Enter the gateway base URL before `/v1`; the client adds the versioned route. Use HTTPS for a deployed service. The only permitted HTTP endpoints are exact loopback development addresses.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Section("Gateway session") {
                    SecureField("Short-lived bearer token", text: $tokenDraft)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    HStack {
                        Button("Save in Keychain") { saveToken() }
                            .disabled(tokenDraft.isEmpty)
                        Button("Remove stored token", role: .destructive) { removeToken() }
                            .disabled(!hasStoredToken)
                    }
                    Text("This client never ships a token. A saved token is bound to this exact gateway base URL. A production gateway, identity flow, expiry, and scopes are outside this local app configuration.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                if let message {
                    Section { Text(message).foregroundStyle(.secondary) }
                }
            }
            .navigationTitle("Connection")
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
        }
    }

    private func saveToken() {
        do {
            guard let endpoint = configuredEndpoint else {
                throw MobileAPIClientError.invalidEndpoint
            }
            try KeychainTokenStore.save(tokenDraft, for: endpoint)
            tokenDraft = ""
            message = "Gateway token stored in Keychain."
        } catch {
            message = error.localizedDescription
        }
    }

    private func removeToken() {
        do {
            guard let endpoint = configuredEndpoint else {
                throw MobileAPIClientError.invalidEndpoint
            }
            try KeychainTokenStore.remove(for: endpoint)
            message = "Stored gateway token removed."
        } catch {
            message = error.localizedDescription
        }
    }
}

private func message(for error: MobileAPIClientError) -> String {
    switch error {
    case .refusal(let refusal):
        return "REFUSED: \(refusal.reason)"
    case .httpRefusal(let status, let refusal):
        return "Service refused the request (HTTP \(status)): \(refusal.reason)"
    case .transport(.offline):
        return "The service could not be reached. Check the endpoint and network connection."
    case .transport(.timedOut):
        return "The service did not respond before the client timeout."
    case .transport(.cancelled):
        return "The certification request was cancelled."
    case .redirected:
        return "The service attempted a redirect, which this client refuses for credential safety."
    case .responseTooLarge:
        return "The service response exceeded this client's safe display limit."
    case .requestTooLarge:
        return "The selected text exceeds this client's bounded request limit."
    case .invalidEndpoint:
        return "Use an HTTPS service endpoint, or an exact loopback HTTP address for development."
    default:
        return "The service response did not match the expected Chiron v1 contract."
    }
}
