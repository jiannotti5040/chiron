// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import SwiftUI
import Observation
import ChironKit

@MainActor
@Observable
final class AppModel {
    var client: VaultClient?

    init() {
        // A path the user picked earlier beats discovery; discovery beats
        // nothing. Both are re-validated — a stale path never half-works.
        if let saved = UserDefaults.standard.string(forKey: "vaultPath") {
            let url = URL(fileURLWithPath: saved)
            if VaultLocator.isVaultRoot(url), let runner = PythonRunner.locate() {
                client = VaultClient(vaultRoot: url, runner: runner)
                return
            }
        }
        client = VaultClient.discover()
    }

    /// Returns false when the chosen folder is not a vault root.
    func setVault(_ url: URL) -> Bool {
        guard VaultLocator.isVaultRoot(url), let runner = PythonRunner.locate() else {
            return false
        }
        client = VaultClient(vaultRoot: url, runner: runner)
        UserDefaults.standard.set(url.path, forKey: "vaultPath")
        return true
    }
}
