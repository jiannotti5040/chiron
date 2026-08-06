# Chiron for macOS

A native SwiftUI front end for the vault. Status: implemented and tested —
`swift build` clean, fixture and live end-to-end tests green against the
repository's own engines.

The app contains **no verification logic**. Every screen shells out to the
vault's own entry points and renders the record that comes back; the Swift
side can never disagree with the engines it fronts, because it never
recomputes them.

| Screen | What it runs | Record |
|---|---|---|
| Full Stack | `Chiron/full_stack.py --json` | `chiron.full_stack/1` |
| Attest | `attest.attest()` via a stdin shim | `chiron.attestation/1` |
| Certify | `primus certify --json -` | `primus.certificate/2` |
| Gates | the vault's own selftests | exit codes, verbatim output |

## Run

```bash
cd App
swift run chiron-app                 # the app window
swift run chiron-app run "text …"    # headless full stack, same record
swift run chiron-app certify "The sum of 2 and 2 is 4."
swift test                           # fixture decodes + live end-to-end
```

If this checkout lives under an iCloud-synced folder (Desktop or Documents
with "Desktop & Documents" on), `swift test` fails at the codesign step with
*"resource fork, Finder information, or similar detritus not allowed"* — the
file provider stamps `com.apple.FinderInfo` on the freshly built `.xctest`
bundle. Build outside the synced tree:

```bash
swift test --scratch-path /tmp/chiron-build
```

Or open `App/Package.swift` in Xcode and press Run. Requires macOS 14+,
a Swift 6 toolchain, and `python3` on the machine. The app finds the vault
by walking up from its working directory; a double-clicked binary instead
uses `CHIRON_VAULT` (and optionally `CHIRON_PYTHON`), or the in-app folder
picker.

## What it refuses to do

The vocabulary is the vault's, unchanged: **VERIFIED · REFUTED · REFUSED**
at claim scale. REFUSED renders neutral, not red — refusal is the honest
answer, not a failure state. The Attest screen never reports a probability
that text is machine-written; attribution is always relative to candidate
inputs you supply, and with none the answer is REFUSED.
