# Continuation record

**Written 2026-08-08.** This file exists so work can resume after an
interrupted session without re-deriving the repository. It records what is
observed, what is not, and the exact next action. It is an evidence record,
not a roadmap.

Read [`AGENTS.md`](../AGENTS.md) and [`notes/SOP.md`](../notes/SOP.md) first —
they carry the inviolable law (**zero false verifications**) and the gate
battery. Nothing below overrides them.

## Where the work is

| Fact | Value |
|---|---|
| Repository | `~/Desktop/Intellectual/Jacob-s-Portfolio-Vault` |
| Working branch | `codex/macos-recovery-20260808` |
| Commits this session | `bc199e8` consolidation → `60d76ce` iOS restoration → `ac6e17a` this record → `2b3a2c0` on-device model → `58afc31` readiness record |
| Baseline | Python 54/54 green, Swift 33 deterministic gates green, iOS builds, macOS app runs |

## Restart in one minute

```bash
cd ~/Desktop/Intellectual/Jacob-s-Portfolio-Vault
git log --oneline -3
python3 bin/chiron test --full
cd App && swift test --scratch-path /tmp/chiron-build
```

To rebuild and run the macOS app:

```bash
cd App && ./make_app.sh && open build/Chiron.app
```

To build the iOS app (Xcode 27, iOS 27 simulator):

```bash
xcodebuild -project iOS/ChironMobile.xcodeproj -scheme ChironMobile \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=27.0' \
  -derivedDataPath /tmp/chiron-ios-dd build
```

To reproduce the end-to-end slice (two terminals):

```bash
PYTHONPATH=Primus/src python3 -m primus.engine_server --port 8765
CHIRON_LOCAL_API_URL=http://127.0.0.1:8765 \
  swift test --scratch-path /tmp/chiron-build
```

## Observed this session

These were run, and the stated result was seen. Nothing here is inferred.

| Check | Result |
|---|---|
| `python3 bin/chiron test --full` | GATE BATTERY GREEN — 54/54 modules through the fold |
| `swift test` (App package) | 33 deterministic gates green (11 ChironKit, 10 ChironService, 12 ChironIntelligence) |
| `swift test` with a live server | 3 live gates green; certify returned `VERIFIED` + `REFUTED` unaltered; collapse recovered the order-2 recurrence with zero residual |
| `swift test` offline | the 4 live gates skip; they never pass with nothing listening |
| `CHIRON_LIVE_MODEL=1 swift test` | on-device model ran; every surviving span was verbatim source text, including the false claim the engine refutes |
| on-device model availability | `available` on this host |
| `xcodebuild … ChironMobile … build` | **BUILD SUCCEEDED** at this revision. Not a first: `APP_STORE_READINESS.md` already recorded a completed Simulator build from an earlier pass. |
| `./make_app.sh` | built `App/build/Chiron.app`, ad-hoc signed |
| `open build/Chiron.app` | launched and stayed running |
| `curl /v1/capabilities`, `/v1/certify` | real `chiron.local_api/1` envelopes from Primus 0.7.2 |
| **MCP invoked by a real client** | Claude Code called `chiron.catalog` (6 reviewed tools returned) and `chiron.certify`, which refuted "product of 6 and 7 is 41" with `expected: 42` |
| App Intent registration | `Metadata.appintents/extract.actionsdata` in the built bundle contains `CertifyTextIntent` and the Siri phrase |
| Privacy manifest | `PrivacyInfo.xcprivacy` present inside the built `ChironMobile.app` |
| macOS proposal panel | `swift build` clean; rebuilt bundle launches and stays running |
| iOS `xcodebuild test`, retried | **still stalls** — zero bytes of output after restarting CoreSimulatorService and re-booting the device |

## Mandate coverage

The original mandate is long. This is an honest map of it against the
repository, so a continuation agent does not redo finished work or inherit an
overclaim. **Most of the mandate was already implemented before this session**
by earlier work on this branch.

### Implemented and tested

- Canonical Python core — Primus engine, certify gate, Chiron modules, the
  generated monolith, and the parity check that proves spine and fold agree.
- Exact-or-refuse contract — `VERIFIED` / `REFUTED` / `REFUSED` preserved end
  to end; no interface restates a verdict or converts one to a score.
- MCP server — stdio JSON-RPC with a reviewed allowlist (`analyze`, `attest`,
  `certify`, `collapse`, `trace`, `catalog`); arbitrary module dispatch is
  deliberately unavailable. 20/20 protocol gates.
- CLI — `bin/chiron` with build, test, parity, verify, serve, benchmark, plan.
- Local service — versioned `/v1` HTTP contract, bounded bodies, closed
  routes, documented in `Primus/LOCAL_API.md`.
- Provenance — source registration, spans, and metadata-only local records.
- macOS app — SwiftUI over the canonical vault through `Foundation.Process`;
  contains no independent verifier.
- iOS app — restored this session; builds; links one shared client.
- LLM provider adapters — configuration-gated; the model proposes, the engine
  disposes.
- Foundry/AIP — a typed, non-delivering boundary that refuses without a
  transport, and a gate that proves it still refuses.

### Not implemented (real gaps)

| Gap | Status | Why it matters |
|---|---|---|
| iOS test runner | **blocked, reproducible** | `xcodebuild test` produced zero bytes twice, including after killing `CoreSimulatorService` and re-booting the device. `build` succeeds on the same host and destination, so this is an environment fault, not a source defect. No completed iOS test result exists. |
| Signing, notarization, archive | **absent** | Ad-hoc signing only. Requires an Apple Developer account — an external blocker, not an engineering one. |
| macOS App Intents | **absent by decision** | The SwiftPM bundle has no `ExtractAppIntentsMetadata` phase, so a macOS intent would not register. Adding one needs an Xcode app target for macOS; the iOS intent is real and verified. |
| Codex MCP client | **not observed** | Claude Code was observed invoking the tools. Codex was not tried. |
| SBOM | **absent** | The dependency surface is small (no third-party Swift packages; Python stdlib), but that is an observation, not a generated bill of materials. |
| Audit log | **absent** | No record of MCP or service invocations is kept. |

### Closed since this record was first written

- **Apple Foundation Models** — implemented as `ChironIntelligence`, gated and
  tested; `availability == available` on this host and a live generation was
  observed. The model proposes spans and structurally cannot express a verdict.
- **`docs/APP_STORE_READINESS.md`** — restored and re-dated to observed
  evidence.

## Known environment blockers

- **CoreSimulator is wedged on this host.** `xcodebuild test` produced no
  output for ten minutes and `xcrun simctl install` hung indefinitely, while
  `xcodebuild build` and `simctl boot` both worked. The earlier readiness
  record described the same symptom, so this is reproducible rather than a
  one-off. A reboot of `CoreSimulatorService` is the first thing to try:
  `sudo pkill -9 -f CoreSimulator` then re-boot the device.
- **Xcode is a beta at a non-standard path**
  (`~/Downloads/Xcode-beta.app`). `xcode-select -p` points there.
- The end-to-end slice was therefore proven through the shared Swift client
  rather than by driving the simulator UI. The iOS app links that exact
  client, so the code path is the same; the *interaction* is unobserved.

## The exact next autonomous action

1. **Wire `ChironIntelligence` into the macOS workspace.** The adapter is
   tested but unreached by any UI. Add a "suggest claims" affordance to
   `WorkspaceView` that calls `ProposerRouter.proposer()`, shows the
   availability explanation verbatim when it cannot run, and sends surviving
   spans to the existing certify path. Show rejected proposals too — a
   discarded hallucination is information the operator should see. Do not let
   a proposal render as a verdict anywhere in the view.
2. **Unwedge CoreSimulator and close the iOS test gate:**
   `sudo pkill -9 -f CoreSimulator`, re-boot the device, then retry
   `xcodebuild … test`. If it stalls again, record the retry rather than
   inferring a pass.
3. **Then App Intents** — "certify selected text" first, since that path is
   already proven end to end.

Do not widen a gate, mute a test, or convert a refusal into a score to make
any of this look finished.
