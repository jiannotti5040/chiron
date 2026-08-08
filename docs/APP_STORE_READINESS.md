# App Store and release readiness

**Decision (inspection date: 2026-08-08): not ready for App Store submission
or public macOS distribution.** This checkout now contains two development
interfaces: a locally tested macOS SwiftUI front end for a separately
installed Python vault, and a native iOS SwiftUI client for the narrow,
versioned Primus `/v1` service contract. An earlier iOS Simulator build was
observed, but the local Xcode build service stalled before compiler output on
a repeat after final hardening; no deployed authenticated gateway, completed
iOS test run, release archive, signing evidence, or App Review evidence exists. A locally
built `.app` is not an App Store candidate.

This is an evidence record for this checkout and the local artifacts inspected
at the time. It is not an assertion about an Apple account, App Review, legal
approval, a project-operated service, or a production identity system that
cannot be observed from source control.

## Readiness at a glance

| Route | Status | Evidence-based reason |
|---|---|---|
| Local macOS developer use | **Implemented and tested** | The SwiftPM app runs the local vault through `python3`; the package suite has exercised the macOS flow and shared remote-client contract locally. |
| Native iOS development target | **Implemented; earlier simulator build observed** | `iOS/ChironMobile.xcodeproj` links a URLSession-only client to the fixed `/v1` contract. The Simulator build succeeded earlier, but a repeat Xcode build service and the Xcode test runner both stalled without a completed result. |
| End-to-end mobile service use | **Not demonstrated** | There is no project-operated authenticated HTTPS gateway, owner-issued credential, or observed device/client-to-service request. |
| Direct macOS distribution | **Not ready** | The inspected bundle is ad-hoc signed, has no Hardened Runtime evidence, is rejected by Gatekeeper, and has not been notarized. |
| Mac App Store | **Not ready** | No App Sandbox entitlement, Apple distribution signing, archive/export pipeline, valid store versioning, privacy submission record, or review evidence exists. |
| iOS App Store | **Not ready** | The development target has no release signing/provisioning/archive/privacy/review evidence; its authenticated service boundary is not deployed or exercised end to end; and its AppIcon asset set has no assigned 1024 px image. |

## What is present and proven locally

### macOS app

- `App/Package.swift` contains a macOS 14+ executable (`chiron-app`) and the
  local-process `ChironKit` adapter. `VaultClient` deliberately contains no
  duplicate verification logic: it launches the canonical Python entry points
  with `Foundation.Process`, discovering a local `python3` and a vault that
  contains `Chiron/` and `Primus/`. A shipped bundle therefore does **not**
  currently contain a self-sufficient engine.
- The UI uses normal file import/drop flows, bounds reads at 2 MB, preserves a
  truncation warning, and uses stdin for the Full Stack flow. It persists the
  user-selected vault *path* in `UserDefaults`; a release data-flow inventory
  must account for that behavior.
- The original local macOS inspection recorded **13 tests in 3 suites**
  passing. The current SwiftPM suite also includes ten deterministic
  `ChironRemote` client-contract tests; it has been observed green as a
  23-test suite in this checkout. These are local development checks, not
  evidence of an archive, sandboxed execution, signing, notarization, or App
  Review.

### Shared contract and iOS development target

- `ChironContract` holds the shared record types and exact JSON-token parser.
  `ChironRemote` is a URLSession-only client: it does not import
  `Foundation.Process`, launch Python, discover a vault path, dynamically
  invoke a tool, recompute certificate values on device, or follow HTTP
  redirects. Its plaintext development exception is literal `127.0.0.1` or
  `::1`; all other endpoints require HTTPS.
- The client can request the three deliberately fixed operations in the
  [local mobile-safe contract](../Primus/MOBILE_API.md): `GET
  /v1/capabilities`, `POST /v1/collapse`, and `POST /v1/certify`. It bounds
  requests and streamed responses, validates the response envelope/schema,
  preserves raw JSON number tokens, and has no local-process fallback.
- `iOS/ChironMobile.xcodeproj` is a native iOS 17+ SwiftUI application and
  unit-test target. Its current UI exposes only the **Certify** vertical slice:
  user-entered or user-imported text goes to `POST /v1/certify`; the returned
  certificate is displayed, not re-evaluated. Both typing and import are
  bounded to 100,000 UTF-8 bytes; import reads only the bound plus one byte
  and rejects invalid UTF-8 rather than truncating or replacement-decoding it.
- A service setting is a **base prefix before `/v1`** — for example
  `https://gateway.example`, not `https://gateway.example/v1`. The remote
  client appends the fixed `v1/...` path. HTTPS is required for deployed
  endpoints; plain HTTP is allowed only for exact loopback development hosts.
- The endpoint setting can be retained in `UserDefaults`. A user-provided
  bearer token is read at request time from Keychain, scoped to the exact
  gateway base URL, and stored with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`;
  no token is embedded in the repository, project, or app defaults. This
  storage choice is not proof of
  an identity system, token lifecycle, or production authorization.
- The following Simulator build completed successfully in this environment:

  ```bash
  xcodebuild -project iOS/ChironMobile.xcodeproj \
    -scheme ChironMobile \
    -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0' \
    -derivedDataPath /tmp/chiron-ios-mobile-build \
    CODE_SIGNING_ALLOWED=NO build
  ```

  The matching test invocation has **not** yielded a completed result: its
  runner stalled. A later repeat build after local hardening also stalled in
  Xcode's build service before compiler output. The current shared and iOS
  sources were typechecked directly against the installed arm64 iOS Simulator
  SDK, but that is not a bundle build. Therefore this record makes no current-
  revision iOS build, test-pass, app-launch, device, network, or end-to-end
  assertion. That investigation is a release blocker, not a reason to infer
  success from a compiled test target.

### Local bundle inspected

`App/make_app.sh` makes a convenience macOS bundle by running `swift build -c
release`, copying the executable into `App/build/Chiron.app`, and calling
`codesign --sign -`. `App/build/` is ignored by Git; it is a local build
artifact, not a versioned release asset or archive.

The inspected bundle had these concrete properties:

| Check | Observed result | Release implication |
|---|---|---|
| Platform / architecture | `LSMinimumSystemVersion = 14.0`; `Chiron-bin` was `arm64` only | Apple-silicon support was demonstrated only at the binary level. Intel support needs a universal or separate x86_64 build/test, or an explicit Apple-silicon-only support decision. |
| Bundle identity | `com.jacobiannotti.chiron`; category `public.app-category.developer-tools` | A plausible local identity/category, but no proof that the identifier is registered to an Apple team or App Store record. |
| Version fields | Both fields used a `git describe` value | That is not a numeric App Store version/build format; use separately managed release and incrementing build numbers. [Apple documents the required formats.](https://developer.apple.com/documentation/BundleResources/Information-Property-List/CFBundleShortVersionString) |
| Build provenance | The embedded revision predated the then-inspected checkout | The bundle was not proof of a build from the current source state. Every candidate must be rebuilt from a recorded commit. |
| Vault configuration | `Info.plist` embedded a developer-machine `CHIRONVaultPath` | A distributable artifact must not ship a developer path or rely on a repository at that location. |
| Signature / entitlements | `Signature=adhoc`, `TeamIdentifier=not set`; no entitlement dictionary | It is not signed by an Apple Distribution or Developer ID identity and has no App Sandbox declaration. |
| Gatekeeper | `spctl -a -vv App/build/Chiron.app` reported `rejected` | The local bundle is not a public direct-distribution artifact. |
| Packaging workflow | No macOS archive/export configuration, provisioning profile, or privacy manifest was found | There is no repeatable macOS app archive, upload, or release gate. The separate iOS Xcode project is a development target, not release evidence. |

The icon is generated locally by `App/make_icon.py`; no downloaded art asset
was found in the macOS app build path. That observation does not replace a
product-name, trademark, or asset-rights review.

The iOS project declares an `AppIcon` asset set, but the set currently has no
assigned 1024×1024 image file. Simulator compilation tolerates that development
placeholder; an archive/App Store candidate needs a valid reviewed app icon in
the appropriate asset catalog as well as the other release evidence above.

## Why the current architectures cannot be submitted as-is

### Mac App Store path

Apple requires the App Sandbox capability for Mac App Store distribution. The
current macOS app has neither that entitlement nor a sandboxed-helper design.
Its core behavior is to execute a user/machine-selected Python interpreter
against a vault outside the app bundle. That may be a good developer-tool
workflow, but it is not evidence that the product works under App Sandbox.

Apple documents a supported *embedded helper* approach: the helper is part of
the signed app and inherits the app's sandbox. That is materially different
from finding arbitrary external `python3` and a separately checked-out vault.
The app also needs a tested user-selected file-access model; persisting a
selected vault requires deliberate security-scoped bookmark behavior if access
must survive relaunches. See Apple's guidance on [App Sandbox](https://developer.apple.com/documentation/security/app-sandbox),
[embedded helpers](https://developer.apple.com/documentation/xcode/embedding-a-helper-tool-in-a-sandboxed-app),
and [sandboxed file access](https://developer.apple.com/documentation/security/accessing-files-from-the-macos-app-sandbox).

### iOS App Store path

The native iOS target is intentionally not a port of the Python engine. It is
a client of a small service surface. That is a viable product boundary only
after an owner operates or approves an authenticated HTTPS gateway that
validates short-lived credentials, scopes access, terminates TLS, applies
rate/abuse controls, supports rotation/revocation, and has an auditable policy.
`CHIRON_API_TOKEN` on the local Primus server is explicitly a fixed
development control, not a mobile identity or authorization system.

The current iOS app has no built-in credentials and does not establish a
service's identity policy. It must also gain a completed test result, real
service integration tests, device/lifecycle/offline/accessibility testing,
production signing/provisioning, numeric versioning, an archive/export path,
and accurate privacy review before submission. A simulator compile only proves
that the sources compile for that destination with code signing disabled.

### Direct macOS path

For direct distribution outside the Mac App Store, a local ad-hoc signature is
not enough. Apple describes the Developer ID path as requiring a Developer ID
identity; its notarization guidance also calls for valid signatures and the
Hardened Runtime. No Developer ID certificate, secure timestamp, notarization
submission/log, stapled ticket, or clean-machine Gatekeeper result is present
in this repository. See Apple's [Developer ID overview](https://developer.apple.com/support/developer-id/)
and [notarization requirements](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

The product-definition problem remains on this route: an ordinary recipient
does not receive the Python vault or its runtime inside the current bundle. A
release must either package and version every required runtime component, or
make the external-installation contract explicit, reproducible, supportable,
and legally reviewable. A build that succeeds only because the developer's
checkout and interpreter are present is not a distributable product.

## Privacy, security, and legal work still required

No `PrivacyInfo.xcprivacy` file or App Store Connect privacy submission record
was found. The macOS app sends selected user text to a local Python process.
The iOS client can send user-entered/imported text and a runtime bearer token
to a user-configured HTTPS gateway using `URLSession`; its endpoint preference
and endpoint-scoped Keychain token behavior are part of the release data flow. Before
declaring any label or policy, map the actual release configuration's
collection, retention, logging, subprocess, network-provider, gateway,
credential, support, and analytics flows. Apple requires accurate App Store
Connect privacy disclosures for the app and integrated third parties; see
[App Privacy Details](https://developer.apple.com/app-store/app-privacy-details/).

The repository's code is Apache-2.0, with third-party materials called out in
`LICENSES.md` and `NOTICE`. That is not release clearance for a packaged
product. Before shipment, the owner must review the rights and notices for the
chosen Python interpreter, every Python/native dependency, any bundled
corpus/model/provider, the app name/icon, support terms, privacy policy,
export controls, and the jurisdictions in which the product will be offered.
No legal conclusion is made here.

## External blockers that source inspection cannot clear

- An authorized Apple Developer Program/App Store Connect team must own or
  approve the bundle identifiers, signing identities, agreements, regions,
  SKU, app metadata, screenshots, ratings, and submission. No account state
  is available in this checkout.
- An owner must choose and operate or approve the mobile service boundary:
  hosted endpoint, TLS termination, identity provider, credential issuer,
  scopes, expiry/refresh, rotation/revocation, logging/retention, rate/abuse
  controls, incident ownership, and support policy. There is no project-run
  public endpoint in this repository.
- The iOS test runner must finish successfully, then the app needs real
  endpoint and device testing. A user-supplied Keychain token field does not
  substitute for production authentication evidence.
- The team must choose a macOS distribution route. Mac App Store needs an
  Apple Distribution archive and sandbox review; independent distribution
  needs a Developer ID signing/notarization workflow. These are related but
  not interchangeable release paths.
- The inspected macOS artifact was arm64 only. If Intel Macs are in scope, a
  suitable build/test environment or CI runner is required; if not, the
  compatibility and support statement must say so.
- App Review, notarization logs, provisioning, hardware testing, external
  service credentials, and counsel's privacy/licensing review are external
  evidence. Their absence remains a blocker rather than being inferred from a
  green local test suite or a simulator build.

## Minimum engineering sequence before seeking release approval

1. **Choose and document the product boundary.** Decide whether the macOS
   release includes a signed sandbox-compatible helper/engine, a versioned
   service client, or a clearly supported non-store developer installation.
   Do not ship a bundle whose default behavior depends on one developer's
   vault path.
2. **Make the mobile service boundary real.** Before enabling an iOS release,
   deploy or approve an authenticated HTTPS gateway around the fixed `/v1`
   contract. Define issuer/audience validation, short-lived credentials,
   scopes, expiry/refresh, rotation/revocation, rate/abuse policy, monitoring,
   retention, and incident/support ownership. Keep all credentials out of Git
   and out of the application binary.
3. **Close the iOS local gates.** Resolve the stalled `xcodebuild test` run,
   exercise the exact service envelope/refusal behavior against a controlled
   endpoint, and test on supported devices for lifecycle, network failure,
   file import, Keychain, accessibility, and privacy behavior. Record the
   output; do not substitute a compile for these gates.
4. **Create reproducible app release targets.** Add maintained macOS and iOS
   archive/export configurations, numeric release/build inputs, recorded
   source revisions, and no-local-path configuration. Decide and test
   universal versus Apple-silicon-only macOS output.
5. **Make capability and data models explicit.** Add only entitlements that
   match the chosen boundaries; test sandboxed file-selection/bookmark
   behavior and the helper/service paths. Produce a data-flow inventory before
   completing privacy disclosures.
6. **Add release gates without credentials in Git.** Build fresh candidates,
   inspect their signatures/entitlements, exercise them on clean machines and
   devices, and verify version monotonicity. Let the authorized team perform
   signing, upload, notarization (for Developer ID), or App Store submission.
7. **Retain the existing engineering gates.** Run the Swift integration suite
   and canonical vault gates on the exact candidate revision; then retain
   their output alongside the signed artifact. A green source test is
   necessary evidence, not a substitute for release evidence.

## Useful local checks

These commands inspect or build development candidates; they do not create
Apple-account, public-service, or App Review evidence:

```bash
cd App && swift test --scratch-path /tmp/chiron-app-release
codesign -dvvv --entitlements :- App/build/Chiron.app
spctl -a -vv App/build/Chiron.app
plutil -p App/build/Chiron.app/Contents/Info.plist
file App/build/Chiron.app/Contents/MacOS/Chiron-bin

xcodebuild -project iOS/ChironMobile.xcodeproj \
  -scheme ChironMobile \
  -destination 'platform=iOS Simulator,name=iPhone 17,OS=27.0' \
  -derivedDataPath /tmp/chiron-ios-mobile-build \
  CODE_SIGNING_ALLOWED=NO build
```

For the mobile target's deliberately narrow boundary, see
[`iOS/README.md`](../iOS/README.md) and [`Primus/MOBILE_API.md`](../Primus/MOBILE_API.md).
For the broader architecture, see [`RECONSTRUCTION.md`](RECONSTRUCTION.md).
For macOS local development, see [`App/README.md`](../App/README.md).
