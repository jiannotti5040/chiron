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

- `catalog` → 6 reviewed tools with authority, side-effect posture, and
  canonical implementation per tool; arbitrary module dispatch unavailable.
- `certify` → on `"The sum of 2 and 2 is 4. The product of 6 and 7 is 41."`
  returned `VERIFIED` + `REFUTED` (expected 42), coverage 0.7963, with a
  tamper-evident attestation hash.

Codex was **not** tested — it was not exercised in this environment.

The loop closes across three interfaces: Apple's on-device model proposed the
span `"The product of 6 and 7 is 41"`, grounding kept the document's verbatim
bytes, and the MCP `certify` tool refuted it.

## 8–9. CLI, service, providers

CLI (`bin/chiron`) runs: `test`, `parity`, `build`, `verify`, `serve`,
`benchmark`, `plan`, `dev`, `run`, `grow`. Local service runs and answers
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
for deciding anything, so a verdict is unrepresentable. A live run drove a real
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
for §21, citing each control by the file that implements it. A **software bill
of materials is still absent**; it is the remaining §21 item.

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
| Problem-solving mode: `solve` / `explore` / `compare` as distinct verbs with candidate generation, counterexample search, and ranking | 16 |
| Evidence graph and contradiction records as first-class objects | 14 |
| Controlled web retrieval boundary | 17 |
| PDF extraction, chunking, persistent index, retrieval | 13 |
| Software bill of materials (the security model itself is written) | 21 |
| Prompt-injection and networking-policy test suites | 22 |
| macOS App Intents (the SPM bundle has no metadata-extraction phase; iOS has it) | 19 |
| Conversation UI, result history, onboarding | 12 |
| Codex MCP client validation | 6 |

## The exact next autonomous action

1. `sudo pkill -9 -f CoreSimulator`, re-boot the device, retry
   `xcodebuild … test`. Record the retry result either way.
2. Implement §16 `solve` as a Python engine composing existing modules
   (`conjecture`, `collapse`, `certify`, `cross_examine`), returning ranked
   candidates with lineage — then expose it through CLI, MCP, and `/v1`
   together, so it lands on every interface at once rather than one.
3. Generate the §21 SBOM — the last item in an otherwise complete security
   section, and the cheapest remaining work with real value.

Do not widen a gate, mute a test, or convert a refusal into a score to make any
of this look finished.
