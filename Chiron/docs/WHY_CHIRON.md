# What Chiron does and does not do

This is a concise scope note for the local exact-recovery engine. For dated
benchmark evidence and failures, read
[Primus/EXTERNAL_VALIDATION.md](../../Primus/EXTERNAL_VALIDATION.md) alongside
this page.

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

## The narrower problem addressed here

Chiron addresses a narrow task: given a supported codified surface, search a
fixed space of exact generators and return a candidate only when its held-out
terms reproduce exactly. It reports a classified residual when that condition
is not met. The task is not arbitrary inference, general semantic truth, or a
proof that no other generator exists.

## What Chiron does

`collapse(surface)` searches competing hypothesis classes (constant, arithmetic,
geometric, polynomial, linear-recurrence, holonomic, periodic, and more), picks
the **minimal** generator under a two-part Minimum Description Length criterion in
**exact** rational arithmetic, and **verifies** it by predicting held-out terms
*exactly* — equality, not tolerance. Whatever it cannot compress is returned as a
**classified residual**, never hidden. Decoding a cipher is the same move:
ciphertext in, the cipher out.

The core can run offline. It is implementation evidence, not independent
validation or a universal guarantee.

## Historical local benchmark snapshots

`benchmark.py`, `compare.py`, and the self-tests are useful local regression
tools. Their historical outputs are not a substitute for an independent
replication, and a zero-false-positive count in a finite test corpus is not a
universal soundness claim. The external-validation record retains the failures
that invalidated earlier counts and is the correct source for the current dated
protocol and result.

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
