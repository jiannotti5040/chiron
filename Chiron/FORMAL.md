# Formal soundness

This document states the property Chiron is built to guarantee, the argument for
why it holds, how it is checked, and — honestly — what is *not* claimed.

## The property

> **Soundness.** If `collapse(s).verified` is true, then the recovered generator
> reproduces every observed term of `s` exactly *and* predicted the held-out terms
> of `s` exactly (equality in exact rational arithmetic, not a tolerance).

Equivalently: **the engine never reports "verified" for a rule that mispredicts.**
A false positive — a confident, wrong answer — is therefore impossible for any
surface on which verification succeeded. When no generator passes the test, the
engine abstains and returns a classified residual.

## Why it holds (argument)

1. **Exactness.** All fitting is done in `fractions.Fraction`, so there is no
   floating-point error to mask a mismatch; equality is true equality.
2. **Held-out gate.** A candidate is accepted only after it predicts terms that
   were withheld from the fit. A rule that merely interpolates the training prefix
   but does not generate the sequence fails this gate and is rejected.
3. **No silent fallback.** If every hypothesis class fails the gate, the result is
   `verified = false` with the input returned as residual. There is no branch that
   emits a "best guess" as verified.

Together these make the soundness property a structural consequence of the design,
not a tuning parameter.

## How it is checked

`formal_check.py` exercises the property over thousands of generated cases and
exits nonzero on any violation:

- **In-class generators** (arithmetic, geometric, polynomial, recurrence) — must
  verify. (Coverage / sanity.)
- **Shuffled controls** — the same multiset of values in scrambled order must not
  verify-and-mispredict.
- **Corrupted sequences** — an in-class generator with one interior term perturbed
  must not verify-and-mispredict; it must abstain.

This is corroborated by the wider suites: `benchmark.py` (OEIS-core + ciphers +
adversarial), the embedded `fuzz_test` (default 10,000 cases) and `gauntlet`. Every
suite reports **zero** false verifications.

```bash
python3 formal_check.py        # VERDICT: SOUND  (exit 0) or VIOLATION (exit 1)
```

## What is NOT claimed

- **Not completeness.** Soundness says verified rules are correct; it does *not*
  say every recoverable rule is found. Chiron abstains on anything outside its
  hypothesis classes (primes, partitions, prose, …). Abstention is not a soundness
  violation — it is the honest default.
- **Not a machine-checked proof.** This is property-based verification over a large
  generated sample, not a proof in Coq/Lean/Isabelle. The argument above is informal.
  A mechanized proof of the held-out gate is a candidate for future work.
- **Not a probabilistic-model guarantee.** The property concerns exact symbolic
  recovery. It says nothing about approximate or noisy-data regimes, which use a
  separate, weaker path (see [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md)).

The honest one-line summary: *within its classes, when Chiron says it knows, it can
prove it; otherwise it says it does not know.*
