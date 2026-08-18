# Handoff

Start here when picking this repository up cold. Facts only; regenerate the
machine-readable half with `python3 ci/state.py`.

## What this is

An engine that recovers the exact law underneath data and proves it on
evidence it was not shown, or refuses.

- `primus.engine.collapse` — recovers a generator from a sequence under MDL,
  proves it on held-out terms.
- `primus.relate` — recovers `y = f(x1..xk)` across table columns, proves it
  on held-out rows, names the rows that break it (`PARTIAL`).
- `primus.invert` — inverts a VERIFIED law; recovers the map between tables.
- `primus.certify` — gates checkable claims in text.
- `Chiron/*` — analysis, provenance, attestation, adjudication over the above.

Dispositions: `VERIFIED`, `REFUTED`, `REFUSED`, `PARTIAL`. Exact rational
arithmetic on every deciding path; no tolerance, no residual threshold.

## Current state

`docs/STATE.json` carries the machine-readable version. At last write:

| | |
|---|---|
| PyPI | `primus-intelligence` — **0.9.0** live; **0.10.0** built, gated, and tagged for release (it repairs the issue #3 false verifications that 0.9.0 carries) |
| GitHub | `jiannotti5040/chiron`, `main` = local HEAD |
| MCP tools | 16, one dispatch (`Chiron/mcp_server.py:_IMPL`) |
| Chiron modules | 92 |
| Toolchain | Python 3.14, Swift 6.4, Xcode 27 |

## Verify a checkout

```bash
python3 bin/chiron test --full     # gate battery
python3 bin/chiron parity          # spine vs fold, 138 gates
cd App && swift test --scratch-path /tmp/chiron-build
```

Two environment facts that otherwise cost an hour each:

- **Swift builds need `--scratch-path` outside this tree.** The checkout is on
  an iCloud-synced Desktop; the file provider stamps `com.apple.FinderInfo`
  onto `.xctest` bundles and `codesign` rejects them. The failure looks like a
  code fault and is not.
- **The gate battery is not concurrency-safe.** It regenerates
  `Chiron/artifacts/*/latest.json` while other gates read them. Run it alone.

## After changing a Chiron module

```bash
python3 Chiron/build_manifest.py
cd "Chiron Monolith" && python3 build_monolith.py && python3 chiron_monolith.py --selftest
```

CI fails on a stale fold by design.

## Open work

Tracked in `STATUS.md` against observed evidence. Summary of what is not
built: evidence graph and contradiction records as first-class objects; web
retrieval; persistent corpus index; conversation UI; signing and notarization.

Blocked on credentials only the owner holds: Apple signing identity, Foundry
token, Codex install.

## Known defects in this repository's own documentation

Recorded because they are the active cleanup task, not as commentary.

1. **Prose written as session narration.** Several documents editorialise,
   narrate what an agent got wrong, or address the owner directly. This is a
   defect in a public repository. Rewrite as documentation of software.
2. **Invented conventions presented as project law.** Some rules in
   `AGENTS.md` and elsewhere were introduced by an agent mid-session and are
   not owner decisions. They must be marked as proposals or removed.
3. **App-centric prose in the core README.** The iOS/macOS app is App-Store
   bound; whether it belongs in this public repository is an open decision.
   The README should not read as an app announcement either way.

`docs/INVENTORY.json` records the per-area findings behind these.

## How to continue without repeating the last session's failures

- Do not report a build as working on `xcodebuild` exit code alone. Launch it
  and exercise it.
- Do not add a rule to `AGENTS.md` that the owner did not ask for.
- Do not write documentation that refers to the conversation that produced it.
- Run the gate battery before claiming any state; paste the counts.
