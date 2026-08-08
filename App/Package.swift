// swift-tools-version:6.0
// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import PackageDescription

let package = Package(
    name: "ChironApp",
    // The contract and URLSession client are portable to the future iOS
    // surface. ChironKit remains the macOS-only local-process adapter.
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [
        .library(name: "ChironContract", targets: ["ChironContract"]),
        .library(name: "ChironRemote", targets: ["ChironRemote"]),
        .library(name: "ChironKit", targets: ["ChironKit"]),
        .executable(name: "chiron-app", targets: ["ChironApp"]),
    ],
    targets: [
        .target(name: "ChironContract"),
        .target(name: "ChironRemote", dependencies: ["ChironContract"]),
        .target(name: "ChironKit", dependencies: ["ChironContract"]),
        .executableTarget(name: "ChironApp", dependencies: ["ChironKit"]),
        .testTarget(
            name: "ChironKitTests",
            dependencies: ["ChironKit", "ChironContract"],
            resources: [.copy("Fixtures")]
        ),
        .testTarget(
            name: "ChironRemoteTests",
            dependencies: ["ChironRemote", "ChironContract"]
        ),
    ]
)
