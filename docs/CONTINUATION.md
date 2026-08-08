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
| Last commits | `bc199e8` consolidation, `60d76ce` iOS restoration |
| Baseline | Python gate battery green, Swift package green, iOS builds |

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
| `swift test` (App package) | 10 XCTest gates + 11 swift-testing gates green |
| `swift test` with a live server | 3 live gates green; certify returned `VERIFIED` + `REFUTED` unaltered; collapse recovered the order-2 recurrence with zero residual |
| `swift test` offline | the 3 live gates skip; they never pass with nothing listening |
| `xcodebuild … ChironMobile … build` | **BUILD SUCCEEDED** — the first completed iOS build recorded here |
| `./make_app.sh` | built `App/build/Chiron.app`, ad-hoc signed |
| `open build/Chiron.app` | launched and stayed running |
| `curl /v1/capabilities`, `/v1/certify` | real `chiron.local_api/1` envelopes from Primus 0.7.2 |

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
| Apple Foundation Models | **absent** — no `FoundationModels` or `SystemLanguageModel` reference exists in any Swift file | Mandate item 10. Needs `#if canImport` + `@available` gating and honest availability reporting. |
| App Intents / Siri / Shortcuts | **absent** — no `AppIntent` or `AppShortcut` type exists | Mandate item 19. |
| `docs/APP_STORE_READINESS.md` | **deleted** on this branch | It was an honest evidence record; it should be restored and re-dated, not dropped. |
| iOS test runner | **blocked** | `xcodebuild test` stalls without output on this host; `simctl install` hangs. CoreSimulator appears wedged. No completed iOS test result exists. |
| MCP client validation | **not observed** | `.mcp.json` registers both servers, but no Claude Code / Codex client was observed invoking a tool this session. |
| Signing, notarization, archive | **absent** | Ad-hoc signing only. No distribution evidence of any kind. |

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

1. Add the Apple Foundation Models adapter behind `#if canImport(FoundationModels)`
   and `@available`, with a mock path so it is testable where Apple
   Intelligence hardware is unavailable. It must never stamp a verdict: it
   proposes, and the canonical engine disposes.
2. Restore `docs/APP_STORE_READINESS.md`, re-dated, with the observed rows
   above and the not-ready verdicts that remain true.
3. Only then consider App Intents.

Do not widen a gate, mute a test, or convert a refusal into a score to make
any of this look finished.
