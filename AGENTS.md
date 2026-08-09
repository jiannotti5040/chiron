# Agent instructions — Chiron / Primus vault

Read [`notes/SOP.md`](notes/SOP.md) before changing the vault. It is the
operating manual; this file is the short gate summary.

## Architecture and boundaries

The Python vault is canonical. The macOS app is a local SwiftUI operator
surface that invokes the vault through a local process; it must not become a
second stamping implementation. Preserve the canonical claim vocabulary:
`VERIFIED`, `REFUTED`, and `REFUSED`.

Do not claim a cloud provider, public service, Foundry/AIP delivery, signing,
notarization, or distribution integration without its own observed evidence.
`docs/RECONSTRUCTION.md` is the current local-boundary record;
`docs/RESEARCH_MAP.md` separates executable evidence from bounded research and
theory.

## The inviolable law

**Zero false verifications.** A change that makes any engine stamp what it
cannot exactly prove is wrong. Refusal is a feature. When recall and honesty
conflict, choose honesty.

## Before claiming a change works

Run the relevant gates. For a broad change from the repository root:

```bash
python3 bin/chiron test --full
python3 bin/chiron parity
cd App && swift test --scratch-path /tmp/chiron-build
```

**Run them one at a time.** The full battery regenerates
`Chiron/artifacts/*/latest.json` while other gates read them, so racing it
against a Swift build or the Primus gates produces failures that do not
reproduce. `unit: chiron` and `CLI contract` failing together, while both pass
individually, is that race and not a regression.

**The `--scratch-path` is load-bearing, not a preference.** This checkout lives
under an iCloud-synced Desktop, and the file provider stamps
`com.apple.FinderInfo` onto the `.xctest` bundles faster than it can be
stripped. `codesign` then rejects them — "resource fork, Finder information, or
similar detritus not allowed" — and `swift test` fails with `error: fatalError`
that looks like a code fault and is not. Build outside the synced tree. The
same applies to `swift build` when it produces signed products.

A failing gate is information: find the root cause. Never widen a tolerance or
mute a gate to obtain green.

## Hard rules

- Exact arithmetic only on the stamping path: use fractions and exact integer
  equality; float predictions beyond 2^53 are refused, not trusted.
- Edit sources of truth only. Never hand-edit
  `Chiron Monolith/chiron_monolith.py`; regenerate it after a Chiron change:
  `cd "Chiron Monolith" && python3 build_monolith.py`, then run its self-test.
- After a module-set or gate change, run
  `python3 Chiron/build_manifest.py --run && python3 Chiron/build_encyclopedia.py`.
- Seed/Chiron divergence must be recorded in `Primus/drift_check.py`'s
  `SEED_AHEAD_LEDGER`, with a dated reason, or the build fails by design.
- Do not build a parallel verifier, dashboard, or copy of an existing engine.
  Grow outward through users, external validation, and exactness.
- **One dispatch.** `Chiron/mcp_server.py:_IMPL` is the single place a tool name
  becomes a call. `bin/chiron`'s reading verbs (`analyze`, `attest`, `collapse`,
  `trace`) and every MCP client go through it, and `engines` reads the same
  `TOOLS` table the server advertises. Adding a surface means routing it there,
  never reimplementing the operation beside it.
- `chiron mcp` must never print to stdout. Stdio MCP requires stdout to carry
  framed JSON-RPC and nothing else; the `[chiron] $ …` banner every other verb
  prints goes to stderr for this one, and the process is replaced with `execv`.
- Model output is a proposal, never an authority. Anything a model emits into a
  typed schema must be a closed symbol the app can render, not free text the UI
  displays verbatim — a `@Guide` sentence asking a model not to judge is not a
  boundary. `ProposedCheckKind` is the pattern.
- Attribution and checkability are independent. A span may trace to a source
  with cosine 1.00 and still be `REFUSED` because no exact checker covers its
  domain. Never render such a span as unattributed, and never report any
  probability that text is machine-written.
- Never `git add -A` at the vault root: `Jacob Dylan Iannotti/` is deliberately
  untracked and contains an embedded Git repository.
- Label work plainly as implemented-and-tested, prototype, bounded evidence,
  or theory. Overclaiming is a defect in code, docs, and commit messages.
