# App Store readiness

State of the iOS/macOS target against Apple's submission requirements.
Submission is deferred by decision, not blocked by engineering; this records
what is in place and what is not.

Regenerate the surrounding repository facts with `python3 ci/state.py`.

## In place

| Requirement | Value |
|---|---|
| Bundle identifier | `com.jacobiannotti.chiron.mobile` |
| Marketing version | `0.1.0` |
| Build number | `1` |
| App icon | `AppIcon.appiconset` carries a 1024×1024 PNG; compiles into `Assets.car` |
| Privacy manifest | `iOS/ChironMobile/PrivacyInfo.xcprivacy`, reaching the target through the synchronized root group |
| Export compliance | `ITSAppUsesNonExemptEncryption = NO` declared in the project |
| App Intents | `CertifyTextIntent` registers; `Metadata.appintents` present in the built bundle |
| Transport security | HTTPS required; plaintext permitted only for literal loopback |
| Credential storage | Keychain, `WhenUnlockedThisDeviceOnly`, scoped to the endpoint URL |
| Builds | iOS Simulator and macOS both build clean from the same target |

## Not in place

| Requirement | State |
|---|---|
| Signing identity | `CODE_SIGN_STYLE = Automatic` with no usable team; ad-hoc signing only |
| Notarization | Not performed |
| Archive validation | Not performed |
| TestFlight | Not configured |
| App Store Connect record | Not created; no privacy disclosure submitted |
| Screenshots, description, category | Not prepared |
| `xcodebuild test` | Has never produced a completed result on the development host — the runner stalls before output while `build` succeeds on the same destination. No iOS test pass is claimed. |
| Device testing | Not performed |

## What requires the account owner

Every remaining item needs an Apple Developer account and cannot be completed
from a checkout:

1. A signing identity and provisioning profile.
2. Notarization and archive validation.
3. The App Store Connect record, privacy disclosure, and any TestFlight build.

## Data collection, for the privacy disclosure

The app collects nothing and transmits only what the operator submits.

- Text the operator types or imports is sent to the endpoint they configure,
  and nowhere else. There is no analytics SDK, crash reporter, or advertising
  identifier.
- The default endpoint is loopback, which cannot leave the device.
- A bearer token, if the operator sets one, is stored in Keychain and sent
  only on POST requests to the exact endpoint it was bound to.
- No file is uploaded as a file. An imported document becomes text in the
  request body only when the operator runs an operation.
