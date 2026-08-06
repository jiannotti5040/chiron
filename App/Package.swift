// swift-tools-version:6.0
// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.
import PackageDescription

let package = Package(
    name: "ChironApp",
    platforms: [.macOS(.v14)],
    products: [
        .library(name: "ChironKit", targets: ["ChironKit"]),
        .executable(name: "chiron-app", targets: ["ChironApp"]),
    ],
    targets: [
        .target(name: "ChironKit"),
        .executableTarget(name: "ChironApp", dependencies: ["ChironKit"]),
        .testTarget(
            name: "ChironKitTests",
            dependencies: ["ChironKit"],
            resources: [.copy("Fixtures")]
        ),
    ]
)
