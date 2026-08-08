// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.

// Keep existing macOS callers source-compatible while the Codable records
// live in the platform-neutral ChironContract target.  ChironRemote depends
// on ChironContract directly and has no Process/Python dependency.
@_exported import ChironContract
