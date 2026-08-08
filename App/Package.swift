// swift-tools-version:6.0
// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import PackageDescription

let package = Package(
    name: "ChironApp",
    // Two interfaces, one canonical core. ChironContract and ChironService
    // build for both platforms so the macOS app and the iOS app share one
    // decoding boundary and one endpoint policy. ChironKit stays macOS-only on
    // purpose: it launches `python3` through Foundation.Process, which iOS does
    // not have and must never appear to have.
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [
        .executable(name: "chiron-app", targets: ["ChironApp"]),
        // Both are linked by iOS/ChironMobile.xcodeproj. Neither carries a
        // verifier: the contract is a decoding boundary and the service target
        // is a bounded client for the versioned /v1 routes.
        .library(name: "ChironContract", targets: ["ChironContract"]),
        .library(name: "ChironService", targets: ["ChironService"]),
        // On-device model assistance. It proposes spans; it never disposes.
        .library(name: "ChironIntelligence", targets: ["ChironIntelligence"]),
    ],
    targets: [
        .target(name: "ChironContract"),
        .target(name: "ChironService", dependencies: ["ChironContract"]),
        // Deliberately depends on nothing: a proposer must not be able to
        // reach a client, an engine, or a certificate.
        .target(name: "ChironIntelligence"),
        .target(name: "ChironKit", dependencies: ["ChironContract"]),
        .executableTarget(name: "ChironApp",
                          dependencies: ["ChironKit", "ChironIntelligence"]),
        .testTarget(
            name: "ChironKitTests",
            dependencies: ["ChironKit", "ChironContract"],
            resources: [.copy("Fixtures")]
        ),
        .testTarget(
            name: "ChironServiceTests",
            dependencies: ["ChironService", "ChironContract"]
        ),
        .testTarget(
            name: "ChironIntelligenceTests",
            dependencies: ["ChironIntelligence"]
        ),
    ]
)
