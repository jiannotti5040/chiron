# Status — what is done, what is not

Plain checklist. Every "done" here was run and observed; nothing is marked
done because the code looks like it should work.

Generated state is in `docs/STATE.json`; regenerate with `python3 ci/state.py`.

## How to run it

**macOS — double-click `run-chiron.command`.** It starts the service, waits
for health, and opens the app. That is the whole procedure.

Or by hand:

```bash
python3 Chiron/service.py --port 8765    # terminal 1
open build/Chiron.app                     # terminal 2
```

In the app: gear icon → endpoint `http://127.0.0.1:8765` → Done → **Workbench**
tab.

**iOS — simulator:**

```bash
xcodebuild -project iOS/ChironMobile.xcodeproj -scheme ChironMobile \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -derivedDataPath /tmp/chiron-ios build
xcrun simctl install booted /tmp/chiron-ios/Build/Products/Debug-iphonesimulator/ChironMobile.app
xcrun simctl launch booted com.jacobiannotti.chiron.mobile
```

Same endpoint setup. The simulator shares the host's loopback, so
`127.0.0.1:8765` reaches the service running on your Mac.

**Terminal only, no app:**

```bash
python3 bin/chiron verify "1,240 units at 25 dollars each is 31,000."
python3 bin/chiron falsify 1 1 2 3 5 8 13 21
python3 bin/chiron engines
```

## Done — observed

| # | Item | Evidence |
|---|---|---|
| 1 | macOS app builds **and runs** | `BUILD SUCCEEDED`; process `ChironMobile` live |
| 2 | iOS app builds **and runs** | launched in simulator, driven by hand |
| 3 | End-to-end certify from the app | 2 VERIFIED · 1 REFUTED · 0 REFUSED, coverage 62.7% |
| 4 | Grounded claims work | `Readiness fell to 74%` VERIFIED against a supplied fact |
| 5 | One multiplatform target | `ChironMobile` builds for iOS **and** macOS |
| 6 | Full service surface | `Chiron/service.py`, every operation in the dispatch, 15/15 self-test on a real socket |
| 7 | One dispatch | app, CLI, and MCP all route through `mcp_server.py:_IMPL` |
| 8 | MCP server | 20/20 transport gates; Claude Code reports Connected |
| 9 | CLI | 18 verbs, all exercised |
| 10 | Gate battery | `GATE BATTERY GREEN`, 61/61 modules through the fold |
| 11 | Parity | 138 gates, identical through both incarnations |
| 12 | Swift tests | 27 XCTest + 16 swift-testing, 0 failures |
| 13 | Apple on-device model | `SystemLanguageModel.default.availability == available` |
| 14 | OpenAI / Anthropic adapters | 12 tests; credential and network are separate switches |
| 15 | SBOM | `ci/sbom.py --check`, gated in the battery |
| 16 | PDF text extraction | `Chiron/pdf_text.py`, refuses by name rather than guessing |
| 17 | No secrets committed | every blob in all 436 commits scanned, not just the working tree |
| 18 | Publication gates | `ci/check_publishable.py` and `ci/check_duplicates.py`, each verified against a planted failure |
| 19 | Pushed to GitHub | `main` and `chiron/mandate-20260809` in sync; CI green |

## Recently added capability

| Thing | What it does |
|---|---|
| `grounded.py` | Claims whose truth lives outside the sentence, checked exactly against supplied facts. Coverage on operational prose **0.0% → 91.8%** |
| `falsify.py` | What observation would overturn a result; for a refusal, the **specific** evidence nobody supplied. `propose_experiment` ranks by cost class and returns nothing when nothing is actionable |
| `service.py` | The whole vault over HTTP, so a device can reach more than certify |
| `pdf_text.py` | Text layer only, with named refusals — `unreliable-encoding` refuses text that decodes plausibly but wrong |
| prose arithmetic | The extractor reads the forms reports actually use — `1,240 units at 25 dollars each for a total of 31,000`, `from 84 to 96, an increase of 12`, `310 of 1,240, or 25 percent` — not only text that already looks like arithmetic homework |
| rounding discipline | A percentage that is the correct rounding of the exact value is REFUSED, not REFUTED. `1 of 3, or 33 percent` is not a lie; the document never states its convention |

Exact-or-refuse governs ingestion, attribution, comparison, and graph
construction, not only the verification layer.

## Not done

| Item | State |
|---|---|
| PyPI | 0.9.0 is live and was verified by installing from PyPI. **0.10.0 is built, `twine check` clean, and verified from a clean install outside the repo — not uploaded.** Publishing needs a fresh API token; see below |
| `chiron-app` (SwiftPM macOS workstation) | still exists beside `ChironMobile`; retiring it is a deletion, not done without approval |
| Conversation UI, result history, onboarding | absent |
| Web retrieval boundary (§17) | absent |
| Chunking, persistent index, retrieval | absent |
| ~~App icon~~ | generated and compiling into `Assets.car` |
| ~~Export compliance~~ | `ITSAppUsesNonExemptEncryption = NO` declared |
| Signing / notarization / archive | absent; needs an Apple account |
| Codex MCP client | not installed in the development environment; config written, unverified |
| Foundry function publish | needs a token from a browser session |
| UI tests, prompt-injection tests, performance tests | absent |

## Publishing 0.10.0

The distribution is built and validated but deliberately not uploaded — a
released version cannot be replaced, and the token used for 0.9.0 was pasted
in plaintext and should be treated as compromised. With a fresh token:

```bash
python3 -m build --outdir dist Primus
python3 -m twine check dist/*
python3 -m twine upload dist/primus_intelligence-0.10.0*
```

## Requires account credentials

- Apple signing identity — notarization and archive validation.
- Foundry API token — live Ontology reads.
- Codex installation — to verify its MCP configuration rather than assert it.
