# Why Chiron

A three-minute read. No philosophy, no lore — what problem this solves, how it
differs from the usual tools, and exactly where it stops.

## The problem

You have a codified surface — an integer sequence, a ciphertext, a column of
data, a string, a graph — and you need the **exact rule that generates it**, not
a model that approximately fits it. "Approximately" is the failure mode that
matters: a method that always returns *an* answer will confidently return a
wrong one, and you find out downstream when a prediction misses.

## Existing methods, and where they fall short

- **Curve fitting / regression / interpolation** always produces an answer. Fit
  a high-degree polynomial through any points and it reproduces them perfectly —
  then extrapolates to nonsense. It cannot say "I don't know."
- **General-purpose compressors (gzip, bz2, lzma)** shrink the *bytes* you show
  them but never recover the *generator*. They cannot produce the next term, and
  their output grows with the length of the input even when the input is, say,
  the powers of two.
- **Statistical / ML pattern finders (TF-IDF, embeddings, clustering)** surface
  correlation and similarity, not an exact, replayable law. They are excellent at
  "what is this like?" and silent on "what rule produced this, exactly?"
- **Hand-written extractors (regex, parsers)** are exact but brittle: each one is
  built for a single known pattern and recovers nothing it wasn't told to expect.

## The gap

There is no widely-used tool that takes an arbitrary codified surface, searches a
space of *exact* generators, returns the minimal one **with a proof**, and —
critically — **abstains** when it has no proof. Exactness, minimality, and honest
refusal in one move.

## What Chiron does

`collapse(surface)` searches competing hypothesis classes (constant, arithmetic,
geometric, polynomial, linear-recurrence, holonomic, periodic, and more), picks
the **minimal** generator under a two-part Minimum Description Length criterion in
**exact** rational arithmetic, and **verifies** it by predicting held-out terms
*exactly* — equality, not tolerance. Whatever it cannot compress is returned as a
**classified residual**, never hidden. Decoding a cipher is the same move:
ciphertext in, the cipher out.

It is one portable file, runs offline with zero installs, and is owner-signed end
to end.

## What you get — measured, reproducibly (`python3 benchmark.py`)

- **OEIS-core sequences: 22 of 29 recovered, 0 false positives.** It recovers
  every one of the 22 that is algebraically generated and **abstains** on all 7
  that are not (primes, partitions, Euler totient, divisor counts and sums, Bell
  numbers, nⁿ). The textbook polynomial baseline recovers only the 11 pure
  polynomials and is **confidently wrong on the other 18**.
- **Classical ciphers: 42 of 44 recovered, ciphertext-only** (a rot13-only
  baseline gets 4).
- **Zero false positives across ~5,070 scored cases**, including a 5,000-case
  randomized fuzz and the labeled gauntlet.
- **Compression vs. understanding** (`python3 compare.py`): on an algebraic
  sequence Chiron's stored law is a handful of bytes *and can regenerate term one
  million*; gzip/bz2/lzma store a blob that grows with the input and can
  regenerate nothing past it.

The single number that matters is the **0**: it never claimed a rule it could not
predict.

## Where it stops (the honest part)

Chiron is a structure recoverer, not a general AI. On natural-language **prose**
its exact-recovery yield is low by design — prose rarely has an exact generator,
so it mostly, correctly, abstains. The rules it recovers are **rediscoveries of
known structure**, not novel mathematics. The certification and theory layers are
self-developed and **not externally audited**. Full detail, including the cases
where it fails, is in [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## Verify it yourself

```bash
python3 chiron.py selftest     # the embedded gate suite, offline
python3 benchmark.py           # OEIS-core + ciphers, scored for false positives
python3 compare.py             # Chiron vs gzip/bz2/lzma
python3 trace.py "1 1 2 3 5 8 13"   # the full reasoning path for one surface
```
