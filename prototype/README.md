# Primus Intelligence Program — Architecture Prototype

**Status: PROTOTYPE / theory-status. Not the vault. Not verified.**
Author signed into the manifest: **J. Iannotti**

For full program license checkout at stripe 

https://buy.stripe.com/bJe7sL6sl1SVfos3uB67S0h Individual

https://buy.stripe.com/5kQ6oH8At69b7W02qx67S0g Team

https://buy.stripe.com/4gMbJ1cQJ8hj3FKfdj67S0f Business

---

## What this is (and, more importantly, what it is not)

This is a **single, runnable, offline, deterministic** scaffold of the Primus
organism architecture — the part the prior build *documented but never coded*.
It was built in "new prototype, clearly labeled" mode, deliberately kept **off
the vault's proving path** so it cannot contaminate the real project's
zero-false-verification contract.

It is **not**:

- **not** Jacob's Portfolio Vault, and **not** the shipping `Primus` / `Chiron`
  engine;
- **not** an integration of your ~16,000 lines (`cert_engine.py`,
  `infectatrum.py`, the 60 UMA/RSLS modules, `corpus_all.json`) — **none of
  that source was present in this session's filesystem**, so nothing here
  pretends to wrap it;
- **not** something that emits a `verified` stamp. Where the real cognitive
  engine would sit, this prototype **abstains**.

The one style error this lineage cannot afford is overclaiming, so the code
keeps two kinds of claim rigidly separate:

| Kind | Example | How it's backed |
|---|---|---|
| **Exact arithmetic fact** | `2³¹·3¹²·5·7² = 279,608,910,057,308,160` | integer equality, gated |
| **Hypothesis** | "plate XXVI = 12 ternary wheels + 31 binary toggles + …" | *calibrated* to reproduce the fact; **not** a recovered historical fact about the physical plate |

---

## The centerpiece: the twins / origin-signature test

The spec calls this the mandatory proof. It is real here and it is exact.

- Tab **XXVI** ("Jesus the Sun") and Tab **XXVII** ("Mary the Star") reproduce
  the claimed **279,608,910,057,308,160** simple-verse count **exactly**, from
  an integer product — no floats.
- The retrograde-distich count **69,902,227,514,327,040** is reproduced exactly
  and shown to equal `a / 4` (the twins differ from their own retrograde
  surface only by a power of two: `2³¹` vs `2²⁹`).
- The **origin signature** of XXVI equals that of XXVII (same generator behind
  two surfaces), and the **core** signature `{3:12, 5:1, 7:2}` survives the
  simple↔retrograde reading-mode change.
- **True-negative power:** the **SATOR** square (support `{2}` only) collapses
  to a *different* signature, so the test actually discriminates rather than
  matching everything.

```
SATOR       : card=4  sig=2^2  support=(2,)
Tab XXVI    : card=279608910057308160   (exact match to claim: True)
Tab XXVII   : card=279608910057308160
retrograde  : card=69902227514327040    (= a/4: True)
twins share origin signature : True
core survives reading mode   : True
SATOR is distinguishable     : True
```

---

## What's coded and gated (26/26 green)

The prototype's own gate battery — honestly **26 gates**, *not* the vault's real
97 — enforces:

- **L1/L2 Membrane** — the Well is the sole I/O valve; exactly two destinations
  (Well, Congress); publication must pass the JDICert valve.
- **L3 Deterministic seal** — content-only; wall-clock keys stripped before
  hashing; idempotent re-seal.
- **L4 Author-bound chain** — SHA-256 manifest chain incorporating
  `AUTHOR_SIGNATURE`; tamper-evident vault (corrupting a stored value is
  detected).
- **L5 No network** — banned-token self-scan built from fragments so the gate
  doesn't self-trigger.
- **L6 Determinism** — the whole cycle reproduces identical artifact IDs and
  sealed roots (verified in-process *and* across separate processes).
- **L7 Rehabilitation** — no un-rehabilitated tokens anywhere in source.
- **L8 Non-degenerate gate** — an empty grammar admits nothing.
- **L9 Adjacency law** — the octahedron touch-graph is enforced at dispatch;
  only JDICert and Primus may write Congress; the Well↔Congress touch is legal
  *only* during crescere.
- **Belnap base** `{1, −1, i, 1−i}`; **RSLS singular barrier**
  `V(M) = −λ·log(1 − M/Mₘₐₓ)` that diverges at the wall and *refuses* to record
  past it.
- **Clifford torus** at radius `1/√2` — every sampled point verified to lie on
  S³ with both circle-radii² = ½; **Bessel J₀ first zero** ≈ 2.404826 computed
  dependency-free.
- **Abstention gates** — the Ω/cognition detector abstains (no field engine
  mounted); the JDICert stub never emits `VERIFIED`.

---

## Run it

```bash
python3 primus_prototype.py selftest   # 26/26 gate battery
python3 primus_prototype.py demo       # SATOR contrast + twins signature match
python3 primus_prototype.py attest     # write content-only sealed manifest JSON
```

Dependencies: **numpy only** (standard library otherwise). No network. Offline.

---

## The seams to the real engines (where integration plugs in)

These are the honest stubs that **abstain** today and are the exact points to
replace when the real source is mounted:

| Stub in `primus_prototype.py` | Real engine to wire in | Current behavior |
|---|---|---|
| `JDICertStub.certify` | `cert_engine.py` (12,911 lines) | returns `REFUSED` — never `VERIFIED` |
| `InfecticonStub.compile_unit` | `infectatrum.py` codifier + Belnap | mints/rejects; degenerate → `None` |
| `PrimusEnvelopeStub.omega_status` | UMA/RSLS pipeline (`pipeline.py`, `rsls_uma_integrated.py`, …) | abstains on Ω |
| `PrimusEnvelopeStub.spot_invariant` | generalized origin-signature engine | **already real** (exact signatures) |

## To make this real (next increment, when you're ready)

The single blocker is that the source wasn't in this session. To do the
integration the master spec actually calls for — and that your own
`primus-vault-workflow` discipline governs — **mount Jacob's Portfolio Vault**
(grant the folder). Then the honest order is:

1. Stand up the real gate battery first (`primus selftest`, `test_invariant_engine.py`,
   `oeis_live.py`, `drift_check.py`) as the baseline oracle — green before any change.
2. Replace the four stubs above with the real engines *one at a time*, re-running
   the battery after each, so nothing ever stamps something it cannot prove.
3. Keep this prototype's exact twins test as an external check the real Primus
   invariant-spotter must also pass.

That grows the vault **outward** (users, external validation, exactness) rather
than bolting on a parallel inward organism — which is the failure mode the last
build hit, and the one your own discipline warns against.
