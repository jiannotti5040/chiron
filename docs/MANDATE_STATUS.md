# Mandate status

**2026-08-08.** This answers the reconstruction mandate's §26 reporting format
against observed evidence, and its §24 definition of done item by item. Every
"done" here was run and seen. Everything else is marked plainly.

Companion records: [`CONTINUATION.md`](CONTINUATION.md) for how to resume,
[`RECONSTRUCTION.md`](RECONSTRUCTION.md) for the boundary record,
[`RESEARCH_MAP.md`](RESEARCH_MAP.md) for the evidence hierarchy,
[`APP_STORE_READINESS.md`](APP_STORE_READINESS.md) for release state.

## 1–3. Inspected, implemented, architecture

Five repositories exist under `~/Desktop/Intellectual`. `Jacob-s-Portfolio-Vault`
is the canonical one; `chiron`, `chiron-launch`, `Acciaio`, and
`operational-readiness-gate` are separate concerns and were left alone.

The inherited state was a working tree with 52 uncommitted changes on
`codex/macos-recovery-20260808` and **nothing committed**. The Python core was
already green; the break was in Swift.

Architecture now in place:

| Module | Platform | Role |
|---|---|---|
| `Primus/` + `Chiron/` (Python) | — | **Canonical core.** Engine, certify gate, modules, generated monolith, parity check. |
| `Chiron Monolith/` | — | Generated fold. Never hand-edited. |
| `App/Sources/ChironContract` | macOS + iOS | Shared records, exact JSON-token parser. |
| `App/Sources/ChironService` | macOS + iOS | One `/v1` client for both interfaces. |
| `App/Sources/ChironIntelligence` | macOS + iOS | On-device model as proposer only. |
| `App/Sources/ChironKit` | macOS only | Spawns `python3`. iOS must not appear to have this. |
| `App/Sources/ChironApp` | macOS | SwiftUI workspace. |
| `iOS/ChironMobile` | iOS | SwiftUI app + App Intents. |
| `Chiron/mcp_server.py` | — | stdio MCP, reviewed allowlist. |
| `bin/chiron` | — | CLI. |
| `primus.engine_server` | — | Versioned local HTTP `/v1`. |

The mandate's suggested module names were followed where repository evidence
supported them and not where it did not: there is no `ChironEngines` Swift
target, because the engines are Python and duplicating them in Swift would
violate the vault's own law against a second stamping implementation.

## 4. Consolidated, migrated, removed

- `ChironRemote` → `ChironService`, and the `Mobile*` API vocabulary →
  `LocalService*`, to match the renamed `chiron.local_api/1` contract.
  Restoring the old names verbatim would have **failed against the current
  server**, which emits `local_api`; the client validated `mobile_api`.
- Restored ~970 lines of tested Swift and the entire iOS app, which the prior
  pass had deleted while leaving `ChironMobile.xcodeproj` on disk with zero
  sources.
- Restored `docs/APP_STORE_READINESS.md`, deleted in the same pass.
- Added `App/.swiftpm/` to `.gitignore`.

## 5–6. What builds, runs, and passes

| Check | Result |
|---|---|
| `python3 bin/chiron test --full` | **GATE BATTERY GREEN**, 54/54 modules through the fold |
| `swift test` | **33 deterministic gates green** (11 ChironKit, 10 ChironService, 12 ChironIntelligence) |
| `swift test` + live server | 3 live gates green |
| `CHIRON_LIVE_MODEL=1 swift test` | live on-device model gate green |
| iOS `xcodebuild … build` | **BUILD SUCCEEDED** (a prior pass had also completed an iOS Simulator build; this one is at the current revision, after the target was restored) |
| macOS `./make_app.sh` → `open` | builds, launches, stays running |
| iOS bundle contents | `Metadata.appintents` + `PrivacyInfo.xcprivacy` present |

Live end-to-end, through the same client the iOS app links: certify returned
claims `["VERIFIED","REFUTED"]`, counts `verified: 1, refuted: 1`; collapse
recovered `linear_recurrence_order2` with `residual_bits: 0.0`.

## 7. MCP status and exact tested clients

**Tested client: Claude Code (this session), stdio transport.** Real
invocations, not a mock:

- `catalog` → 7 reviewed tools with authority, side-effect posture, and
  canonical implementation per tool; arbitrary module dispatch unavailable.
- `certify` → on `"The sum of 2 and 2 is 4. The product of 6 and 7 is 41."`
  returned `VERIFIED` + `REFUTED` (expected 42), coverage 0.7963, with a
  tamper-evident attestation hash.

Codex was **not** tested. It is not installed on this machine (`codex:
command not found`), so its configuration in
[`MCP_CLIENTS.md`](MCP_CLIENTS.md) is written from the documented shape and
labelled untested. A later check confirmed Claude Code 2.1.216 reports both
`chiron` and `primus` Connected, and a direct stdio handshake returned
`chiron.mcp/2` on protocol 2025-06-18.

The loop closes across three interfaces: Apple's on-device model proposed the
span `"The product of 6 and 7 is 41"`, grounding kept the document's verbatim
bytes, and the MCP `certify` tool refuted it.

## 8–9. CLI, service, providers

CLI (`bin/chiron`) runs the repository verbs — `test`, `parity`, `build`,
`serve`, `benchmark`, `plan`, `dev`, `run`, `grow`, `doctor` — and a
user-facing reading surface added on this branch: `analyze`, `verify`,
`collapse`, `trace`, `attest`, `solve`, `engines`, `mcp`. The reading verbs
route through `Chiron/mcp_server.py:_IMPL`, the same dispatch MCP clients use,
so a terminal and an agent cannot disagree about what a tool does. `verify`
stays a thin adapter over `primus certify`. Local service runs and answers
`/v1/capabilities`, `/v1/collapse`, `/v1/certify` with bounded bodies and
closed routes. Provider adapters (`Chiron/llm_providers.py`, `llm_certify.py`)
are configuration-gated, 21 gates green; no live cloud provider call was made
or claimed.

## 10. Apple Intelligence

Implemented as `ChironIntelligence`. `availability == available` on this host.
Gated by `#if canImport(FoundationModels)` and `@available(macOS 26/iOS 26)`;
compiles and constructs on machines without it and reports the real reason.

The invariant is structural: `ProposedClaim` has no status, score, confidence,
or correction field, and the `@Generable` schema gives the model no vocabulary
for deciding anything, so a verdict is unrepresentable. That last clause was
aspirational when first written and is now true: `reason` was a free `String`
rendered verbatim to the operator, and is now `ProposedCheckKind`, an enum
closed over the ten gate kinds `certify` actually discharges. A live run drove a real
fix — the model returned `"the product…"` where the document capitalizes
`"The"`, and the span was rejected, losing a real checkable false claim to
capitalization. Matching now folds ASCII case only (Unicode folding would
change byte length and corrupt offsets), and always carries the document's own
bytes forward. A changed digit still fails to match.

## 11–13. Files, Palantir, App Store

- **Local files:** macOS import, drop, bounded reads, content hashing, and a
  source record with line spans are implemented and exercised by tests.
  PDF extraction and a persistent index are **not** implemented.
- **Palantir:** a typed, non-delivering boundary with a gate proving it still
  refuses without a transport. No credentials, ontology IDs, or endpoint were
  invented. This is honest scaffolding, not an integration.
- **App Store:** not ready, and the record says so per route. Bundle IDs,
  privacy manifest, and App Intents are in place; signing, notarization,
  archive, and review evidence are absent.

## 14. Security findings

No secrets are committed. The client refuses plaintext HTTP to anything but
literal `127.0.0.1`/`::1`, refuses redirects, bounds requests and streamed
responses, and never sends a bearer on the capability read. MCP tools are a
reviewed static allowlist with no arbitrary dispatch.

[`SECURITY_MODEL.md`](SECURITY_MODEL.md) documents the model and threat model
for §21, citing each control by the file that implements it. The **software
bill of materials now exists and is gated**: `ci/sbom.py` derives the
dependency surface from declarations in the tree and `--check` runs in the
battery. It found the error this section used to contain — the Python core is
not pure standard library; Primus declares and imports `numpy`.

An audit of this branch also corrected three understatements in the security
model: the local service has rate limiting (`Limiter`, sliding one-minute
window), keeps a per-request access log with a hashed body prefix, and closes
eight routes rather than three.

## 15. Commits

Eighteen, now carried on `chiron/mandate-20260809`, oldest first:

`e39194a` consolidation · `90c1b70` iOS restoration · `da2a7ac` continuation
record · `d7579da` on-device model · `3bd23d4` readiness record · `cc149d4`
record update · `db9bc85` fresh certificates · `126d196` gitignore ·
`b2c0817` proposal panel · `d71c0d9` App Intents · `e9cde57` privacy posture ·
`7fffbbf` security model · `3904e19` intent/manifest follow-up ·
`b693b0c` this report · `4a4d7d0` commit-list correction · `704a825` README ·
`d2515af` handoff prompt · `eacd590` first-claim correction.

An earlier revision of this section listed fourteen pre-rewrite hashes
(`bc199e8`, `60d76ce`, …). Those objects are real but no longer reachable from
any branch: a `git filter-branch` trailer strip rewrote every commit on this
branch after that list was written, changing all eighteen hashes. The hashes
above are the current, reachable ones. Verify with
`git log --format='%h %s' origin/main..HEAD --reverse`.

## 16. Genuine external blockers

1. **CoreSimulator is wedged.** `xcodebuild test` produced no output for ten
   minutes; `simctl install` hung; plain `build` and `simctl boot` work. The
   documented fix needs `sudo pkill -9 -f CoreSimulator`, which requires the
   owner's password. **This is the only reason no iOS test-runner result
   exists.**
2. **Signing, notarization, TestFlight, App Review** need an Apple Developer
   account and legal acceptance.
3. **Foundry/AIP** needs an authorized ontology, endpoint, and credential.
4. **Cloud provider keys** are absent, by design.

## 17. Not done — the honest remainder

These mandate items are **not** implemented. None are blocked; they ran out of
session, not feasibility.

| Item | § |
|---|---|
| `explore` and `compare` as distinct verbs; multi-candidate ranking across engines | 16 |
| Evidence graph and contradiction records as first-class objects | 14 |
| Controlled web retrieval boundary | 17 |
| PDF extraction, chunking, persistent index, retrieval | 13 |
| Prompt-injection and networking-policy test suites | 22 |
| macOS App Intents (the SPM bundle has no metadata-extraction phase; iOS has it) | 19 |
| Conversation UI, result history, onboarding | 12 |
| Codex MCP client validation | 6 |

### Closed since that list was written — 2026-08-09

| Item | § | Evidence |
|---|---|---|
| OpenAI and Anthropic adapters with configuration boundaries | 9, 24 | `CloudProposers.swift`; 12 tests, none touching the network |
| Intelligence router with a real policy | 9 | `ProposerRouter.RoutingPolicy` — `deterministicOnly`, `localOnly`, authorization, credentials, preferred |
| Software bill of materials | 21 | `ci/sbom.py`, gated by `--check` in the battery |
| Module catalog (the capability this branch had lost) | 12 | `ModuleManifest.swift` + `ModulesView.swift`, reader-only |
| File capability matrix | 13 | `docs/FILE_SUPPORT.md` |
| User-facing CLI verbs on the shared dispatch | 7 | `analyze`, `attest`, `collapse`, `trace`, `engines`, `mcp` |
| Client-verified MCP | 6 | Claude Code 2.1.216 reports both servers Connected; stdio handshake exercised directly |

## The exact next autonomous action

1. **Implement §16 `solve`** as a Python engine composing existing modules
   (`conjecture`, `collapse`, `certify`, `cross_examine`), returning ranked
   candidates with lineage. Expose it through `_IMPL` first — the CLI, every
   MCP client, and `engines` then pick it up together rather than one at a
   time, which is the whole reason that dispatch exists. This is now the
   largest single remaining item and the one that most changes what Chiron
   *is*: it is the difference between a system that checks and a system that
   solves under audit.
2. **`sudo pkill -9 -f CoreSimulator`**, re-boot the device, retry
   `xcodebuild … test`. Record the retry result either way. Note that
   `xcodebuild … build` succeeds today — it is the *test* action that is
   unobserved, and those are not the same claim.
3. **Evidence graph (§14)** as a first-class object. The pieces exist —
   `source_provenance`, `attest` spans, certificates — but nothing joins them
   into a traversable graph with contradiction records, which is what turns a
   pile of records into lineage.

Two facts that will otherwise cost an hour each, both recorded in AGENTS.md:
Swift builds need `--scratch-path` outside this iCloud-synced tree or codesign
rejects the test bundles, and the gate battery is not safe to run concurrently
with another vault job.

Do not widen a gate, mute a test, or convert a refusal into a score to make any
of this look finished.
