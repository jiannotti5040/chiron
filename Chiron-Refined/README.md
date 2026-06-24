# CHIRON

**Author: Jacob Iannotti. Licensed under PolyForm Noncommercial 1.0.0 — free to use, modify, and share for any noncommercial purpose; commercial rights reserved (see the repository-root [LICENSE.md](../LICENSE.md)).**

![offline](https://img.shields.io/badge/network-offline%20by%20default-1f6feb)
![core deps](https://img.shields.io/badge/core-zero%20dependencies-2ea043)
![python](https://img.shields.io/badge/python-3.8%2B-3776ab)
![self-test](https://img.shields.io/badge/self--test-green-2ea043)
![false positives](https://img.shields.io/badge/false%20positives-0%20%2F%20~5070-2ea043)
![license](https://img.shields.io/badge/license-PolyForm%20Noncommercial%201.0.0-blue)

One portable, offline, deterministic, self-certifying engine that does the work
nobody has automated: take an ambiguous, codified surface and **recover the exact
rule beneath it** — not match it, recover it — then **prove** the recovery and
refuse to overstate it.

This is the refined twin: the same engine, **stripped of every arbitrary title but
its own**, its memory **wiped to zero**, and reframed to what it actually is — so
its form is visible and it can be developed on its own terms.

## The core

```
collapse(surface)          -> the exact rule beneath it        (recover)
same_origin(a, b)          -> do two surfaces share one rule?  (equivalence)
cast(rule, target)         -> a new surface, same skeleton     (transfer)
articulate(rule)           -> speak the rule back up           (the inverse codec)
```

A *surface* is anything codified — integer sequences, ciphers, strings, graphs,
code, schemas. `collapse` returns the **minimal** rule under a two-part **Minimum
Description Length** criterion, in **exact** `fractions.Fraction` arithmetic, and
**verifies** it by predicting held-out terms exactly — equality, not tolerance.
Whatever it cannot compress is returned as a **classified residual**, never hidden.
Decoding is the same move: given a ciphertext, it recovers the cipher.

## In 60 seconds

```bash
python3 chiron.py collapse 1 2 4 8 16 32 64   # -> geometric (ratio 2), verified; predicts 128, 256, ...
python3 chiron.py solve "WKLV LV D VHFUHW"    # -> caesar_shift_3: THIS IS A SECRET
python3 trace.py "1 1 2 3 5 8 13"             # -> the ranked candidates, the winner, the proof
```

**Why not just fit a curve, or run gzip?** A curve-fit never says "I don't know" —
it returns a confident wrong answer on anything it cannot actually model; gzip
shrinks the bytes but cannot tell you the rule or predict the next term. Chiron
returns the **exact** generator with a held-out proof, or an honest abstention.
See `compare.py` and [WHY_CHIRON.md](WHY_CHIRON.md).

## What it's made of (function, not names)

- **the invariant engine** — rule recovery, MDL, multi-hypothesis ranking, residual
  taxonomy, structural fingerprints.
- **the certifier** — every consequential claim is gated for evidence,
  counterexamples, and provenance; reproducibility, not trust.
- **the honesty layer** — scores reasoning for condescension, unearned confidence,
  evasion, and opacity, and renders every finding as *what was found, why it is
  believed, what would falsify it.*
- **the twin / transfer layer** — same-rule detection across domains.
- **the executive** — an isolated, bounded agent; network off by default; anything
  irreversible escalates to a human.
- **the memory** — verified rules persist as compact, owner-bound, order-independent
  records that pool across instances without trust. It organizes what it learns by
  **subject**, classifies each finding **integral** (a verified, reusable rule) or
  **general** (retained knowledge), and tracks cross-domain transfer and reuse.

## Run it

```bash
python3 chiron.py serve                       # offline operator console (auto-opens 127.0.0.1:8765)
python3 chiron.py selftest                    # the full embedded gate suite
python3 chiron.py collapse 1 1 2 3 5 8 13     # recover + prove a rule
python3 chiron.py articulate 1 1 2 3 5 8 13   # speak it back up (the codec)
python3 chiron.py solve "WKLV LV D WHVW"      # crack a cipher / code, ciphertext-only
python3 chiron.py same-origin "1 2 3" :: "9 18 27"
python3 chiron.py guide "1 1 2 3" --expect "5 8 13 21"   # DIRECTED: steer the search with the answer you expect
python3 chiron.py recall "2 4 8 16 32" --memory chiron_memory.json   # is this rule already proven?
python3 chiron.py compact --memory chiron_memory.json    # value-dense: distill the memory, keep the proofs
python3 benchmark.py                          # reproducible benchmark: OEIS-core + ciphers + adversarial, scored for false positives
python3 compare.py                            # head-to-head vs gzip / bz2 / lzma
python3 trace.py "1 1 2 3 5 8 13"             # the full ranked-candidate reasoning path
python3 discover.py                           # cross-domain twins: one rule across numeric + string
python3 mine_code.py                          # structural skeletons + clone detection over a codebase
python3 formal_check.py                       # property-based soundness check (see FORMAL.md)
python3 primus_atlas.py                       # collapse Caramuel's 21 transcribed plates; cross-plate twins
python3 primus_verses.py                      # run the labyrinth forward — verses + proteus generation
python3 fastops.py                            # optional native hot-path (Rust) with pure-Python fallback
```

**Directed recovery** lets the operator steer: give the terms you expect to come
next and the engine recovers the rule consistent with both your sequence and that
continuation — or honestly reports that none fits. Proven rules are stored with
their parameters (replayable, recognized on sight), and `compact` keeps the
memory value-dense — a proven rule and an unparsed paragraph no longer cost the same.

## Measured (reproducible)

One command, offline and deterministic — `python3 benchmark.py`:

- **OEIS-core sequences — 22/29 recovered, 0 false positives.** On 29 real
  OEIS-core entries the engine sees only a training prefix and must predict four
  held-out terms *exactly*. It recovers **every one of the 22 that is algebraically
  generated** (constant, arithmetic, geometric, polynomial, linear-recurrence,
  holonomic) and **abstains on all 7 that are not** — primes, partitions, Euler
  totient, divisor counts, divisor sums, Bell numbers, nⁿ — rather than guess.
  The textbook finite-difference baseline recovers only the 11 pure polynomials
  and is **confidently wrong on the other 18** (it cannot abstain). Recovering the
  rule *and refusing to overstate it* is the whole point.
- **Classical ciphers — 42/44 recovered, ciphertext-only.** English plaintexts
  encoded with nine schemes (Caesar, ROT13, Atbash, A1Z26, Base64, hex, binary,
  Morse, reversal), handed to the solver with no key; it recovers the plaintext in
  42 of 44 (a rot13-only baseline gets 4). The two misses are decoder collisions,
  reported, not hidden.
- **Zero false positives across every suite.** A 5,000-case randomized fuzz
  (in-class sequences must verify; shuffled values must not) and the labeled
  gauntlet add **0** false-verifications and **0** crashes.

The number that matters is the **0**: across ~5,070 scored cases the engine never
once claimed a rule it could not predict.

Why it is built this way, and exactly where it stops — including the cases it
fails — is in [WHY_CHIRON.md](WHY_CHIRON.md) and [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).
A comparison to conventional compression is in `compare.py`; the full reasoning
path for any surface is in `trace.py`.

It **grows**. One shared grower feeds it from any source — Wikipedia, any website,
any JSON API, or the OEIS (structured integer sequences, where rule-recovery is
near-total) — under a chosen subject, growing the memory and pushing it back as it
fills, resuming exactly where it left off:

```bash
python3 chiron_grow.py --serve                                  # crawl + live dashboard
python3 chiron_grow.py --params grow-public/profiles/oeis.json --once   # structured: high yield
python3 chiron_ciphers.py                                       # seed a cryptography basis
```

It can grow itself, on a leash: it forms cross-domain concepts from proven rules,
and can propose changes to its own source that are applied **only** if a reversible
backup is taken and the full self-test still passes — so it can improve itself but
never take anything away.

## This twin starts empty

Memory here is a **clean seed** — zero learned. Point it at a source and it builds
its own. Everything runs offline and deterministically; the only network is the
operator-directed grower, and only when you run it.

## Verifying

```bash
python3 chiron.py selftest
```

Runs green, offline, exact, owner-signed end to end — the invariant-operation
gates and the core gates all pass. One file. One rule over anything codified.
