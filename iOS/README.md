# Chiron Mobile — development target

`ChironMobile.xcodeproj` is a native iOS 17+ SwiftUI application target. It
is a deliberately narrow client for Chiron's versioned local-service contract,
not a Swift port of the Python verification engine and not an App Store
release candidate.

## Boundary

The app links `ChironContract` and `ChironService` from `../App`. It does not
link the macOS-only `ChironKit` adapter and therefore cannot launch Python,
discover or read a vault path, invoke a dynamic module, or recompute a
certificate on device.

The interface has two screens. **Certify** sends user-entered or imported
UTF-8 text to `POST /v1/certify` and shows the certificate exactly as
returned, including exact JSON number tokens and with no second on-device
verdict. Oversized imports are refused rather than silently truncated.

**Workbench** reaches the rest of the service. `ChironService` exposes every
operation the dispatch defines — 16 of them, including `ingest`, `relate`,
`solve_for`, `discover_map`, `attest`, `falsifiers` and
`propose_experiment` — and the workbench drives them against either a document
or a table. A result carries the engine's own record; the screen counts and
renders, and never restates a verdict in softer words.

The client bounds requests and streamed responses, validates the `/v1`
envelope, and has no local-process fallback. The server contract is documented
in [`../Primus/LOCAL_API.md`](../Primus/LOCAL_API.md).

## Endpoint and credentials

Set the service to a **base prefix before `/v1`**, such as
`https://gateway.example`. Do **not** enter `https://gateway.example/v1`: the
shared client adds the fixed `v1/...` path itself.

HTTPS is required for deployed endpoints. Plain HTTP is accepted only for
literal `127.0.0.1` or `::1` development addresses; resolver names such as
`localhost` still require HTTPS. The URLSession transport refuses redirects.
A user-provided bearer token is retrieved at request time from Keychain,
scoped to the exact configured base URL, and uses
`kSecAttrAccessibleWhenUnlockedThisDeviceOnly`; it is not embedded in the app
or retained in `UserDefaults`.

This is deliberately not a production authentication design. There is no
project-operated gateway, identity flow, token issuer, scope model, expiry or
refresh behavior, rotation/revocation system, TLS termination, or production
service credential in this repository. The Primus server's optional static
`CHIRON_API_TOKEN` is a local development control, not mobile authorization.

## Building and running

```bash
xcodebuild -project iOS/ChironMobile.xcodeproj -scheme ChironMobile \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath /tmp/chiron-ios build

xcrun simctl install booted /tmp/chiron-ios/Build/Products/Debug-iphonesimulator/ChironMobile.app
xcrun simctl launch booted com.jacobiannotti.chiron.mobile
```

Substitute an installed simulator name if that one is unavailable. The same
target builds for macOS with `-destination 'platform=macOS'`.

The app needs the service running:

```bash
python3 Chiron/service.py --port 8765
```

The simulator shares the host's loopback, so the default endpoint
`http://127.0.0.1:8765` reaches a service running on the same Mac. A deployed
gateway must be HTTPS; loopback is the only plaintext address the endpoint
policy admits.

**`xcodebuild test` has not produced a completed result on the development
host.** The runner stalls before emitting output, including after restarting
CoreSimulatorService and re-booting the device, while `build` succeeds on the
same host and destination. No iOS test pass is claimed. Device testing and
any signed distribution require an Apple Developer account and are likewise
unclaimed.

