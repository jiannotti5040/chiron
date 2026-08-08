// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import Foundation
@testable import ChironKit

/// Xcode launches SwiftPM tests from DerivedData rather than from the package
/// checkout.  The test source path is the stable, checkout-local anchor for
/// live vault tests; production discovery remains environment/runtime based.
func testVaultRoot() -> URL {
    URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent() // ChironKitTests
        .deletingLastPathComponent() // Tests
        .deletingLastPathComponent() // App
        .deletingLastPathComponent() // vault root
}

func testVaultClient() -> VaultClient? {
    VaultClient.discover(extraCandidates: [testVaultRoot()])
}
