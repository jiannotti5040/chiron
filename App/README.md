# Chiron native interfaces

Chiron has two deliberately separate native surfaces:

- **Chiron for macOS** is an implemented-and-tested SwiftUI front end for a
  separately installed local Python vault.
- **Chiron Mobile** is a native iOS 17+ development target that is a narrow
  network client for the versioned Primus `/v1` service contract. It is not a
  packaged or App Store-ready product.

The macOS app contains **no verification logic**. Every screen shells out to
the vault's own entry points and renders the record that comes back; the Swift
side can never disagree with the engines it fronts, because it never
recomputes them.

| Screen | What it runs | Record |
|---|---|---|
| Full Stack | `Chiron/full_stack.py --json --stdin` | `chiron.full_stack/1` |
| Modules | every module in `Chiron/`, discovered by introspection | `chiron.app.catalog/1` |
| Attest | `attest.attest()` via a stdin shim | `chiron.attestation/1` |
| Certify | `primus certify --json -` | `primus.certificate/2` |
| Gates | the vault's own selftests | exit codes, verbatim output |

The Modules screen enumerates the currently discoverable vault at launch; its
module and entrypoint counts are runtime output, not a versioned promise in
this README. A module added to `Chiron/` appears without an edit here.
Entrypoints that need more than one argument are listed and say why they
cannot be run, rather than being hidden.

## Files

Every text box takes a file: drop one on it, or use the button beside it.
Files are read to a 2 MB bound and every picker, drop, and multi-file
candidate path carries the truncation warning through to the analysis screen
— a partly-read file must never look like a fully analysed one. Full Stack
uses stdin rather than a command-line argument, so this accepted file bound
does not collide with the host's `ARG_MAX` limit. The CLI takes a path
anywhere it takes text.

## Platform status

### macOS local-vault app

`chiron-app` remains the implemented local macOS workflow. It delegates to
the local Python vault through `Foundation.Process`; that is appropriate on
macOS but cannot run in an iOS sandbox. The local interface has no remote
authentication, no bundled engine, and no App Store distribution claim.

### iOS service client

[`../iOS/ChironMobile.xcodeproj`](../iOS/ChironMobile.xcodeproj) is a native
iOS 17+ SwiftUI development target. It links the portable `ChironContract`
and `ChironRemote` libraries rather than `ChironKit`, so it cannot launch
Python, select a vault path, dynamically invoke a module, or recompute a
certificate on device.

The current UI is an intentionally small **Certify** vertical slice. It sends
only user-entered or user-imported text to `POST /v1/certify`, then displays
the returned record without re-evaluating its numbers. The shared remote
client also has fixed `capabilities`, `collapse`, and `certify` operations;
the mobile UI does not expose the first two yet.

Configure a service **base prefix before `/v1`**, for example
`https://gateway.example`, not `https://gateway.example/v1`: the client adds
the fixed `v1/...` path itself. A deployed endpoint must use HTTPS. Plain HTTP
is accepted only for literal `127.0.0.1` or `::1` development addresses, and
the URLSession transport refuses redirects. A user-supplied bearer token is
read at request time from Keychain and scoped to that exact base URL; no token
is embedded in the app or stored in `UserDefaults`. This is a storage boundary, not a production
identity system: gateway authentication, token issuance, expiry, revocation,
scopes, TLS termination, and service operation remain external work.

An earlier iOS Simulator build was observed, but a repeat after final local
hardening stalled in Xcode's build service before compiler output; its Xcode
test run also has not produced a completed result. The current shared and iOS
sources typecheck directly against the installed arm64 iOS Simulator SDK, but
that is not a current-revision bundle build, test pass, end-to-end service
test, device test, or release readiness. See [`../iOS/README.md`](../iOS/README.md),
[`docs/RECONSTRUCTION.md`](../docs/RECONSTRUCTION.md), and the evidence-based
[release readiness record](../docs/APP_STORE_READINESS.md).

## Run

```bash
cd App
swift run chiron-app                      # the app window
swift run chiron-app run "text …"         # headless full stack, same record
swift run chiron-app run ./notes.md       # …or a file
swift run chiron-app certify ./report.txt
swift run chiron-app catalog              # what the vault exposes
swift run chiron-app call language stylometry "some prose"
swift test                                # fixture decodes + live end-to-end
```

To build a double-clickable `Chiron.app`:

```bash
./make_app.sh
```

The bundle records the vault it was built against and passes it through as
`CHIRON_VAULT`, because a double-clicked app inherits no shell environment
and cannot find the vault by walking up from a working directory. It carries
no engine of its own.

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
picker. When no interpreter is specified, it prefers normal Homebrew or
`/usr/local` installations before PATH and ignores Xcode's bundled developer
Python there, so it does not accidentally replace the dependency-equipped
runtime.

## Build the iOS development target

The iOS project lives outside this Swift package because a deployable iOS app
needs an Xcode application target, not only a SwiftPM executable. Select an
installed simulator name and run, from the repository root:

```bash
xcodebuild -project iOS/ChironMobile.xcodeproj \
  -scheme ChironMobile \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0' \
  -derivedDataPath /tmp/chiron-ios-mobile-build \
  CODE_SIGNING_ALLOWED=NO build
```

That simulator build has been observed to succeed. A matching `xcodebuild …
test` invocation currently needs investigation because its runner stalled;
do not use a pending or stalled test process as test evidence. The target
requires an actual authenticated HTTPS gateway before it can make useful
production requests.

## What it refuses to do

The vocabulary is the vault's, unchanged: **VERIFIED · REFUTED · REFUSED**
at claim scale. REFUSED renders neutral, not red — refusal is the honest
answer, not a failure state. The Attest screen never reports a probability
that text is machine-written; attribution is always relative to candidate
inputs you supply, and with none the answer is REFUSED.
