# A063880 bounded-computation capsule

This directory is a **reproducible bounded computation**, not a proof and not
an announcement that an open problem has been solved.

It evaluates the two research-open statements in the pinned
`FormalConjectures/OEIS/63880.lean` source only for positive integers
`n <= 10,000,000`:

- every enumerated A063880 member is `108 (mod 216)`;
- `108` is the only primitive member in that finite interval.

The source and OEIS entry response are frozen under `inputs/`. The `build`
command produces a complete sorted member list, 100,000-wide block digests,
and a manifest pinning source hashes, code hashes, interpreter details, and
the exact scope. The verifier uses no network and does not read the ignored
OEIS cache.

From the vault root:

```bash
python3 studies/a063880_capsule.py verify
```

Verification refuses if a frozen input, output hash, relevant source file, or
either full scan differs from the manifest. It compiles the tracked,
target-specific C99 source into a temporary directory, recomputes membership
with two separately written exact-integer sieve paths, compares the complete
list, and then direct-enumerates divisors for every reported member. A C99
compiler (`cc` by default, or `CC=/path/to/compiler`) is therefore required;
no compiled binary is stored in this repository. Agreement is useful
corroboration, but it is not a formal proof of the scan algorithms or of the
unbounded Lean theorems.

The frozen Lean source is copied from
`google-deepmind/formal-conjectures` commit
`f776d2f2039351b00737ffcafb9d7d7666e1d9af`; its Apache-2.0 notice is retained
in `inputs/formal-63880.lean`. The frozen OEIS response is source data only.
Its original live-fetch moment was not recorded retrospectively; the manifest
records the local cache timestamp and its exact content hash instead.

For an actual counterexample, this capsule is not enough: the publication gate
would require a small witness theorem that compiles against the pinned Lean
snapshot, plus independent human review.
