# What Primus still needs — grounded map (2026-07-07)

Reconciled against the AFTER_ACTION / STATUS_REPORT (07-04),
EXTERNAL_VALIDATION.md (through the v0.5.0 addendum), and the git state on
2026-07-07. *Published working record — a point-in-time roadmap, tracked as
part of the project's paper trail.*

## Headline (the honest part)

The engine and the gates are **mature and externally validated**. Full battery
green — stress 48/48, certify 27/27, fuzz 13/13, MCP 10/10, drift 37/37,
live-OEIS 20 verified / 0 false / 7 refused, Chiron green — plus the new twin
cross-lock (12/12). Zero false verifications has held through 4 versions and a
real external falsification (the repunit stamp) that was repaired at root.

So Primus does **not** need more engine, and it does **not** need the master
spec's new organism superstructure (Clifford-torus `PrimusOrganism`, crescere,
emergence tiers). Most of that is already inside `Chiron/chiron.py`
(twins_proof, origin-signature library, ductus registry, org roles), and the
rest is inward growth the vault's own discipline says not to build. What it
needs is **outward reach + a couple of author-machine validations + keeping
the two-copy drift closed.** In leverage order:

## 1. Right now — mechanical, ~2 min (this is literally "the rest")

- **Push the 2 local commits.** `main` is ahead of `origin/main` by two:
  `81087cd` (ci: track check_wheel_license) and `224bee1` (the twin cross-lock
  gate I just added). Use your **`bin/push-to-github.command`** (double-click) —
  I can't push from here (needs your GitHub credentials).
- **Confirm CI goes green** afterward. The new twin cross-lock runs in the
  `chiron` job (3.12); it imports `chiron`, so it's deliberately *not* in the
  3.9/3.13 `primus` matrix.

## 2. Outward validation — highest leverage (your own "natural next escalation")

- **Full-corpus live OEIS sweep:** `python3 oeis_live.py --live --keyword-core`
  (~180 keyword:core sequences). The harness already ships ready for it; it
  needs network on *your* machine (the sandbox blocks oeis.org). This is also
  Paper `TODO(author)` at line 221. Turning "24-sequence curated battery" into
  "~180-sequence live sweep, still zero false stamps" is the single biggest
  credibility gain available.
- **PySR head-to-head:** `python3 bench_pysr.py` (needs Julia/PySR) →
  fills `SYMREG_RESULTS.md`. Paper `TODO(author)` at line 231. Extends the
  gplearn comparison (16-exact/0-wrong vs 2/22) to the stronger baseline.

## 3. Reach — make other people able to run/check it (the AAR's stated top value)

- **GitHub Pages + browser-check `playground.html`** (parked follow-up). One
  deploy, one open-in-browser sanity pass on the real-engine demo.
- **Show HN draft** — the repunit falsify-and-repair story is the hook. You
  said you'd write it with me; the raw material is in EXTERNAL_VALIDATION.md.

## 4. Release — optional, your explicit "contact before capability" call

- **Tag + PyPI.** Currently **untagged** (no `v*` tags exist). `release.yml`
  triggers on a tag, verifies `pyproject` version == tag, reruns all gates, and
  checks the LICENSE ships inside the wheel. When you want it published:
  register on PyPI, then `git tag v0.5.0` matching pyproject.

## 5. Keep-closed risks — maintenance, not features

- **Two-copy drift.** The seed (`Primus/src/primus/engine.py`) and the flagship
  (`Chiron/chiron.py`) are two implementations of one engine, held together
  only by `drift_check.py` + the ledger. This has silently drifted *both*
  directions before (repunit; Motzkin). Keep porting capability promptly so the
  ledger stays empty; the long-term fix is fewer copies, not a wider tolerance.
- **Optional hardening:** the paper's third `TODO(author)` (line 270) floats a
  machine-checked/formal proof of the exact-arithmetic core. Deepens "exact
  means exact"; not required for anything shipping.

## 6. Parked capability — explicitly deprioritized by you

- **Candor as a standalone second product.** It already exists as a verb
  (`python3 chiron.py audit "..."`, the Wisdom/anti-patronization layer) but is
  **not** a `primus`-level front door like `certify`. Packaging it that way is
  the next parked build after Apéry (which shipped in v0.5.0).
- Then the **full-OEIS atlas pipeline**.

## Non-goals (resist these — they're the last session's failure mode)

Do not rebuild the organism as a new top-level layer, and do not port the
labeled prototype (`outputs/primus_prototype.py`) into the vault. The vault
grows outward — users, external validation, exactness — not inward. Overclaiming
is the one style error this project cannot afford.

---
Bottom line: **push the two commits, then run the full live-OEIS sweep on your
machine.** Everything else is reach and polish, and none of it is urgent.
