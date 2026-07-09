# Chiron: Exact Generator Recovery with Honest Abstention

**Jacob Iannotti** · PolyForm Noncommercial 1.0.0 · draft, not peer-reviewed

## Abstract

Chiron is a deterministic engine that takes a codified surface — an integer
sequence, a ciphertext, a string, a graph, source code — and recovers the exact
generator beneath it under a Minimum Description Length (MDL) criterion in exact
rational arithmetic, verifying each recovery by predicting held-out terms with
exact equality, and **abstaining** when no generator in its hypothesis classes is
confirmed. We report a reproducible benchmark: on 29 OEIS-core sequences it
recovers all 22 that are algebraically generated and abstains on the 7 that are
not, with **zero false positives**; on 44 classical-cipher instances it recovers
the plaintext ciphertext-only in 42; and across roughly 5,070 scored cases —
including a 5,000-case randomized fuzz and an adversarial suite — it produces
**zero false verifications**. A naive finite-difference polynomial baseline, which
cannot abstain, recovers only the 11 pure polynomials and is confidently wrong on
the other 18. The contribution is not novel mathematics — the recovered rules are
rediscoveries of known structure — but a system whose defining property is that it
never claims a rule it cannot prove.

## 1. Problem

Given a finite prefix of a codified surface, recover the **exact** rule that
generates it, or report honestly that no such rule is found. The failure mode that
matters in practice is the confident-but-wrong answer: a method that always returns
*a* generator will return a wrong one on inputs it cannot actually model, and the
error surfaces downstream as a missed prediction. We therefore treat abstention as
a first-class output and measure false positives, not merely recall.

## 2. Approach

For a surface *s*, Chiron searches a fixed set of hypothesis classes (Section 3.2),
fitting each in exact `fractions.Fraction` arithmetic. Each candidate is scored by
a two-part MDL cost: the bits to describe the model plus the bits of residual it
leaves. The minimal-cost candidate is selected, with ties broken toward the
canonically simpler class and the margin reported.

A candidate is accepted as **verified** only if it predicts **held-out** terms of
*s* exactly — equality, not tolerance. If no candidate verifies, Chiron returns a
classified residual and abstains. This held-out gate is the mechanism behind the
zero-false-positive result: a spurious fit on a prefix is rejected when it fails to
predict the withheld continuation.

Decoding is the same operation. Given a ciphertext, recovering the cipher is
recovering the transform that generated it; given a plaintext/ciphertext pair, the
key is recovered directly.

## 3. Implementation

### 3.1 Form
The engine is a single Python file with no third-party dependencies in its core
path (numpy/scipy are optional accelerators with exact pure-Python fallbacks). It
runs offline and deterministically and is owner-signed end to end. See
[ARCHITECTURE.md](ARCHITECTURE.md).

### 3.2 Hypothesis classes
Constant; arithmetic; geometric; polynomial of any degree; linear recurrences
(C-finite, including sums/products of polynomial × geometric); periodic;
multiplicative (factorial-type); alternating; holonomic / P-recursive (Catalan-,
central-binomial-class); and interleaved composites (k independent lanes shuffled
by position). Anything none of these compress is returned as a classified residual.

### 3.3 Verification, certificate, memory
Every analysis yields a two-view certificate — a machine view (model class,
fingerprints, MDL margin, residual kind) and a human view (*what was discovered,
why it is believed, what would falsify it*). Verified rules persist in a
content-addressed store (the "Congress") as compact, owner-bound, order-independent
records that merge idempotently across instances.

## 4. Benchmarks

All numbers below are produced by `benchmark.py`, `compare.py`, and `verify.py`,
offline and deterministically. Ground truth for sequences is generated from first
principles in the harness and cited by OEIS A-number.

### 4.1 OEIS-core sequence recovery
Method: 29 OEIS-core sequences, each split into a training prefix and a held-out
tail of 4 terms. Chiron sees only the prefix and must predict the tail exactly or
abstain.

| outcome | count |
|---|---|
| recovered (verified, held-out predicted exactly) | 22 |
| abstained (no verified rule) | 7 |
| **false positives (verified but wrong)** | **0** |

The 22 recovered are exactly the algebraically-generated sequences (100% of
in-scope). The 7 abstentions are primes, partitions, Euler totient, divisor counts,
divisor sums, Bell numbers, and nⁿ — none of which has a closed form in the
hypothesis classes. Baseline: a Newton forward-difference polynomial extrapolator
(no abstention) recovers 11 (the pure polynomials) and is confidently wrong on 18.

### 4.2 Classical ciphers
Method: 4 English plaintexts encoded with 9 schemes (Caesar at several shifts,
ROT13, Atbash, A1Z26, Base64, hex, binary, Morse, reversal), 44 instances total,
solved ciphertext-only.

| | cracked / total |
|---|---|
| Chiron solver | 42 / 44 |
| rot13-only baseline | 4 / 44 |

The two misses are decoder collisions (a hex/Base64 string is also a plausible
input to another decoder); they are reported, not hidden.

### 4.3 Adversarial and fuzz
Corrupted and noised sequences (a single flipped or perturbed term) must abstain
rather than fit the corruption: 4/4 abstained, 0 false positives. English prose is
not coerced into a numeric law; Python source collapses to a relabel-invariant AST
skeleton. A 5,000-case randomized property fuzz (in-class generators must verify;
shuffled values must not) yields 0 false verifications and 0 crashes. The embedded
labeled gauntlet recovers 12/14 with 0 false-verify on controls.

**Across all suites: 0 false positives in ~5,070 scored cases.**

### 4.4 Structure vs. compression
`compare.py` contrasts Chiron with gzip/bz2/lzma. To store the first 1,024 powers
of two, the general compressors need tens of kilobytes and can extrapolate nothing;
Chiron stores a 51-byte law that regenerates arbitrary future terms. On a random
(structureless) sequence Chiron abstains and the general compressors are the
appropriate tool — the correct division of labor.

### 4.5 Reproducibility and cost
`verify.py` records each run (input, generator, residual, score, fingerprint,
commit, timestamp) and a result digest that is stable across runs on the same
version. `profile.py` reports median collapse latency from sub-millisecond for
simple classes to ~17 ms for the heaviest holonomic case at 100 terms.

## 5. Failure cases and scope

Recovery yield on natural-language prose is low single digits by design — prose
rarely has an exact generator, and Chiron abstains. Number-theoretic sequences
without a closed form are out of scope. Recovery is exact-rational; genuine floats
fall to a weaker path. Very short inputs are weak evidence. The cipher solver
covers classical schemes only — not keyed or modern cryptography. The certification
layer is built to civilian regulatory standards but is **not externally audited**,
and the surrounding theoretical work is **self-developed and not peer-reviewed**.
Full detail in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## 6. Related work

Chiron is a tractable, exact restriction of the Kolmogorov/Solomonoff ideal of the
shortest generating program (uncomputable in general) to specific, decidable
hypothesis classes, scored by MDL (Rissanen). It differs from **symbolic
regression** (e.g. genetic/evolutionary formula search), which returns approximate
expressions under a tolerance, by requiring exact held-out equality and by
abstaining. It differs from **general compression** (LZ-family), which minimizes
bytes without recovering a runnable generator or the ability to extrapolate. It
overlaps in spirit with OEIS lookup/`Superseeker` but recovers and *proves* a
generator rather than matching a catalog, and with **program synthesis**, though
restricted to the above classes for exactness and speed.

## 7. Future work

Wider hypothesis classes (to lift the number-theoretic ceiling); a keyed/poly-
alphabetic cipher module; improved natural-language collapse and a richer residual
taxonomy; external audit of the certification layer and peer review of the theory;
and internal modularization behind a build step that preserves single-file
distribution. Each is staged so it cannot destabilize the verified core.

## 8. Reproducibility

```bash
python3 chiron.py selftest     # embedded gate suite
python3 benchmark.py           # Section 4.1–4.3
python3 compare.py             # Section 4.4
python3 verify.py              # Section 4.5 (records + determinism digest)
python3 examples/build_examples.py   # the worked examples, regenerated
```

All commands are offline and deterministic. The result digest from `verify.py`
lets a third party confirm byte-identical generator/residual/score output on the
same version.

## References (orienting, not exhaustive)

- A. N. Kolmogorov, "Three approaches to the quantitative definition of information."
- R. Solomonoff, "A formal theory of inductive inference."
- J. Rissanen, "Modeling by shortest data description" (MDL).
- N. J. A. Sloane, The On-Line Encyclopedia of Integer Sequences (OEIS).
