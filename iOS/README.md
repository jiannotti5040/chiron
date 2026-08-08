# Chiron Mobile — development target

`ChironMobile.xcodeproj` is a native iOS 17+ SwiftUI application target. It
is a deliberately narrow client for Chiron's versioned local-service contract,
not a Swift port of the Python verification engine and not an App Store
release candidate.

## Boundary

The app links `ChironContract` and `ChironRemote` from `../App`. It does not
link the macOS-only `ChironKit` adapter and therefore cannot launch Python,
discover or read a vault path, invoke a dynamic module, or recompute a
certificate on device.

The current user interface exposes one vertical slice:

- user-entered or user-imported UTF-8 text (at most 100,000 bytes) is sent to
  `POST /v1/certify`;
- oversized imports are refused rather than silently truncated; and
- the returned certificate is displayed as returned, including exact JSON
  number tokens, without a second on-device verdict.

`ChironRemote` also defines fixed `capabilities` and `collapse` operations,
but the current iOS UI intentionally does not expose them. It bounds requests
and streamed responses, validates the `/v1` response envelope, and has no
local-process fallback. The server contract is documented in
[`../Primus/MOBILE_API.md`](../Primus/MOBILE_API.md).

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

## Build evidence and current limitation

The following iOS Simulator build completed successfully earlier in this
reconstruction:

```bash
xcodebuild -project iOS/ChironMobile.xcodeproj \
  -scheme ChironMobile \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0' \
  -derivedDataPath /tmp/chiron-ios-mobile-build \
  CODE_SIGNING_ALLOWED=NO build
```

Choose an installed simulator name if that exact one is unavailable. A repeat
after final local hardening stalled in Xcode's build service before compiler
output, and the project’s `xcodebuild test` invocation also has not produced a
completed result because the runner stalled. The current shared and iOS source
files do typecheck directly against the installed arm64 iOS Simulator SDK, but
that is not a bundle build. There is consequently no claim of a current-
revision iOS build, iOS test pass, app launch, device test, or end-to-end
gateway test. Resolve those local Xcode gates before using this target as
release evidence.

For the full release gap — signing, provisioning, privacy, service operation,
archive/export, device testing, and App Review — see
[`../docs/APP_STORE_READINESS.md`](../docs/APP_STORE_READINESS.md).
