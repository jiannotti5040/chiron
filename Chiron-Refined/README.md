# CHIRON

**Architect & sole owner: Jacob Iannotti. Proprietary — all rights reserved.**

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
```

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
