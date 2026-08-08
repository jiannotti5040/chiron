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
- Never `git add -A` at the vault root: `Jacob Dylan Iannotti/` is deliberately
  untracked and contains an embedded Git repository.
- Label work plainly as implemented-and-tested, prototype, bounded evidence,
  or theory. Overclaiming is a defect in code, docs, and commit messages.
