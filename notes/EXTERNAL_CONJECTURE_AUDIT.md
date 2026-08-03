# External conjecture audit — DeepMind Formal Conjectures + OEIS

**Status:** bounded, reproducible computational evidence only. No proof, no
counterexample, no external submission, and no novelty claim follows from this
memo.

## Snapshot

- DeepMind's public `google-deepmind/formal-conjectures` repository, commit
  `f776d2f2039351b00737ffcafb9d7d7666e1d9af` (2026-07-27).
- The snapshot contains 850 Lean files. Its own README describes it as a
  collection of *statements* of conjectures, not proofs.
- OEIS was used only as external source data. Each finite screen below says
  exactly whether it inspected entry data or an uploaded b-file.

## Chiron result: A063880

The DeepMind file
`FormalConjectures/OEIS/63880.lean` marks two statements as research open:

1. Every `n` with `sigma(n) = 2 * usigma(n)` is `108 (mod 216)`.
2. `108` is the only primitive member of that set.

Chiron exhaustively inspected every positive integer through 10,000,000. The
reviewable artifact is a frozen, offline capsule: it runs two separately
written exact C99 sieve/factorization paths, requires their full membership
lists to agree, then directly enumerates divisors for every reported member.
The first 40 frozen OEIS terms match the enumerator exactly.

**Verdict:** `VERIFIED-TO-N`, `N = 10,000,000` — 28,141 members found; every
one was `108 (mod 216)`, and 108 was the only primitive member in that finite
interval. This does **not** prove either general statement.

The durable run history is in `studies/conjecture_ledger.json`; the stronger
reproducibility record is `studies/capsules/a063880-n10000000/`, which pins
source/input/code/output hashes and a complete member list. Verify it offline
with:

```bash
cd Jacob-s-Portfolio-Vault
python3 studies/a063880_capsule.py verify
```

The capsule refuses if a frozen input, implementation hash, output hash,
membership list, residue check, or direct-divisor audit disagrees. It remains
bounded computational evidence, not a Lean proof.

## Additional source-data screens

These are deliberately weaker screens. They did not evaluate an infinite
conjecture and are not entered as Chiron verdicts.

| Formal source | Source data examined | Exact screen | Result |
|---|---:|---|---|
| `OEIS/67720.lean` | 10,000-term uploaded A067720 b-file, through `k = 1,548,870` | Every listed term other than the stated exception `k = 8` has prime `k + 1`. | No contradiction in the b-file. |
| `OEIS/56777.lean` | 27 published A056777 entry terms, through `n = 3,061,962,209` | Each listed `n` was independently inverted as `p(p+8)`; `p,p+2,p+6,p+8` were all prime. | No contradiction in the entry data. |

If either screen ever produces a candidate, the next step is not publication:
recompute the formal predicate itself, then produce a target-specific,
executable witness checker with an independent implementation.

## Claimed-proof audit: A287616

The external corpus also contains A287616, which the pinned Formal Conjectures
snapshot still labels open. A new preprint claims a solution with two explicitly
non-kernel-checked dependencies. The source pin, statement-equivalence review,
and failed local build attempt are recorded in
[`A287616_AUDIT.md`](A287616_AUDIT.md). The only current conclusion is that a
serious claimed proof exists and needs independent audit; it must not be
reported here as solved.

## Publication gate

The current evidence is useful as a transparent bounded result, but not as an
announcement that an open problem was solved. A public issue, pull request, or
paper is appropriate only after an explicit `REFUTED` witness backed by a
target-specific replay checker (and a compiling Lean witness for a Formal
Conjectures statement), or after a complete proof is independently reviewed.
The legacy generic certificate artifacts are non-evidentiary and are not a
publication gate.
