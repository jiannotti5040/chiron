// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Jacob Iannotti. See LICENSE.

// Keep the app and the local-process adapter on the same Codable records.
// ChironContract stays internal to this macOS package; callers go through
// ChironKit rather than carrying a second transport surface.
@_exported import ChironContract
