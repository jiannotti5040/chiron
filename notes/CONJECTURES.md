# Conjecture campaign — bounded exhaustive search

**Author: Jacob Iannotti. Apache-2.0.**

**This file is GENERATED** from `studies/conjecture_ledger.json` by
`studies/conjecture_runner.py`. Do not hand-edit it — it is a
projection of the run ledger. Regenerate it instead of hand-editing
it when the recorded execution changes.

## What a verdict means

| Verdict | Meaning |
|---|---|
| `REFUTED` | An explicit counterexample was found and re-checked. |
| `VERIFIED-TO-N` | A bounded region was exhausted with no counterexample. **This is not a proof.** |
| `REFUSED` | No finite search can settle the statement, or the encoder failed validation. |

A verdict follows from the conjecture's **logical form**, not its
difficulty. `∀n P(n)` is refutable by one counterexample, so a bounded
search is informative. *"Infinitely many x"* and *"∃N₀ ∀n≥N₀"* are
settled by no finite computation, so they are `REFUSED` no matter how
much confirming evidence accumulates. This is enforced in code.

**Every encoder is validated before it is trusted** — against published
OEIS terms, representation counts, or hand-checkable cases. An encoder
that fails validation refuses to run, because an unvalidated encoder
manufactures counterexamples.

## Results

| Conjecture | Form | Verdict | Bound reached | Prior art |
|---|---|---|---:|---|
| OEIS A000041 | `FORALL` | `VERIFIED-TO-N` | 100,000 | Open. No partition number is known to be a perfect power. |
| DeepMind FormalConjectures A063880 | `FORALL` | `VERIFIED-TO-N` | 10,000,000 | DeepMind Formal Conjectures marks the residue and unique-primitive statements fo |
| OEIS A280831 | `FORALL` | `VERIFIED-TO-N` | 8,000 | Zhi-Wei Sun prize 1,680 RMB; open. 83.35% of n reduce to Gauss-Legendre via y=0; |
| OEIS A281976 | `FORALL` | `VERIFIED-TO-N` | 20,000 | Zhi-Wei Sun prize $2,400; open. |

## Detail

### OEIS A000041  — `VERIFIED-TO-N`

- **Logical form:** `FORALL`
- **Bound reached:** 100,000
- **Encoder validation:** pentagonal-recurrence partition numbers reproduce the first 21 published A000041 terms exactly; p(100) = 190,569,292
- **Result:** no p(k) for k in [2, 100,000] is a perfect power
- **Prior art:** Open. No partition number is known to be a perfect power.
- **Runtime:** 12.7s

### DeepMind FormalConjectures A063880  — `VERIFIED-TO-N`

- **Logical form:** `FORALL`
- **Bound reached:** 10,000,000
- **Encoder validation:** first 40 published A063880 members match exactly; their sigma/usigma values also agree with independent divisor enumeration
- **Result:** all 28,141 members in [1,10,000,000] are 108 mod 216; 108 is the only primitive member in that interval
- **Prior art:** DeepMind Formal Conjectures marks the residue and unique-primitive statements for A063880 as research open; finite evidence only.
- **Runtime:** 14.9s

- **Replay capsule:** [frozen inputs and independent replay](../studies/capsules/a063880-n10000000/README.md)

### OEIS A280831  — `VERIFIED-TO-N`

- **Logical form:** `FORALL`
- **Bound reached:** 8,000
- **Encoder validation:** representation COUNTS reproduce the first 35 published terms of A280831 exactly (a tighter check than mere existence)
- **Result:** every n in [0, 8,000] has at least one representation
- **Prior art:** Zhi-Wei Sun prize 1,680 RMB; open. 83.35% of n reduce to Gauss-Legendre via y=0; only 4^k(8m+7) is searched.
- **Runtime:** 27.5s

### OEIS A281976  — `VERIFIED-TO-N`

- **Logical form:** `FORALL`
- **Bound reached:** 20,000
- **Encoder validation:** representation COUNTS reproduce the first 35 published terms of A281976 exactly (a tighter check than mere existence)
- **Result:** every n in [0, 20,000] has at least one representation
- **Prior art:** Zhi-Wei Sun prize $2,400; open.
- **Runtime:** 11.8s

---

*29 runs recorded; 4 conjectures at their best bound; **0 refutations.***

*Bounds are not novelty claims. Each row carries its source and prior-art
status so no number can be read as more than its stated scope.*
