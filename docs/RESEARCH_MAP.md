# Research map

This repository contains different kinds of work. They are useful only when
their evidentiary status stays visible. A passing local test, a finite
computation, a self-authored draft, and an independent empirical confirmation
are not interchangeable.

## 1. Executable verification evidence

The strongest operational claims concern the exact-checking contract in
Primus and Chiron. A stamp is warranted only for a defined property that the
engine checked exactly; otherwise the result is `REFUSED` or `REFUTED`.

| Record | What it supports | What it does not support |
|---|---|---|
| [`Primus/EXTERNAL_VALIDATION.md`](../Primus/EXTERNAL_VALIDATION.md) | A reproducible OEIS protocol, its historical false stamps, root-cause repairs, and later re-runs. | A claim that every OEIS sequence, or arbitrary mathematical statement, is solved. |
| [`Chiron/docs/KNOWN_LIMITATIONS.md`](../Chiron/docs/KNOWN_LIMITATIONS.md) | The implemented hypothesis classes, abstention behavior, performance limits, and provenance limits. | General semantic truth, legal admissibility, authorship detection, or reliable behavior outside the listed scope. |
| [`Paper/abstain_or_prove.tex`](../Paper/abstain_or_prove.tex) | The July 2026 draft's method, historical experiments, and bibliography. | A peer-reviewed publication or a current-status dashboard; its dated figures must be read alongside the external-validation record. |
| `python3 bin/chiron test --full` and `python3 bin/chiron parity` | Reproducible local gate evidence for a checkout. | Independent replication or a claim beyond the assertions those gates actually test. |

The external-validation record is intentionally chronological: it retains the
failures that falsified earlier claims. Its current cached-corpus section
distinguishes the default 29-sequence run from the separate 35-sequence
historical cache. Read the protocol and dated result together rather than
lifting a number out of context.

### Literature behind the executable core

The paper draft cites the relevant intellectual lineage rather than presenting
the engine as an isolated invention: J. Rissanen's 1978 work on minimum
description length; R. Solomonoff's 1964 induction framework; C. Chow's 1970
reject-option result; El-Yaniv and Wiener's work on selective classification;
and work on sequence recognition and symbolic regression including GFUN,
gplearn, PySR, and AI Feynman. Those references motivate method choices; they
do not independently validate this implementation. The complete bibliography
is in the [paper source](../Paper/abstain_or_prove.tex).

## 2. Bounded computation and replay capsules

[`studies/capsules/a063880-n10000000/`](../studies/capsules/a063880-n10000000/)
is a model for a careful finite computation. It freezes its source inputs,
hashes its code and outputs, and replays two independently written
exact-integer scans plus a direct divisor audit:

```bash
python3 studies/a063880_capsule.py verify
```

Its statement is deliberately finite: for the pinned A063880 input and
`1 <= n <= 10,000,000`, the replay checks the recorded residue and primitive
member obligations. The capsule reports 28,141 enumerated members and records
the non-claims explicitly: it is not a proof of unbounded Lean statements, a
solution of an open problem, or formal verification of the programs. See the
[capsule README](../studies/capsules/a063880-n10000000/README.md) and
[manifest](../studies/capsules/a063880-n10000000/manifest.json).

## 3. Experimental theory and falsification handles

[`Chiron/docs/LITERATURE.md`](../Chiron/docs/LITERATURE.md) maps the
author-developed HCT, Projection Calculus, PIH, governance, and philosophical
documents to code locations. It labels those texts as self-developed drafts,
not peer-reviewed work. Running code or a local test suite is evidence for a
particular implementation behavior; it is not confirmation of the broader
theory.

The [UMA proof and falsification checkpoints](../UMA%20Suite/uma_build_v4/docs/PROOF_AND_FALSIFICATION_CHECKPOINTS.md)
are useful precisely because they separate algebraic derivations, numerical
checks, empirical predictions, conjectural assumptions, and withdrawn claims.
The stated empirical hinge is an observation against real LIGO/LISA data; that
observation is not recorded as completed. The document therefore supports a
claim that the framework exposes falsification conditions, not that it is a
confirmed physical theory.

## How to cite or describe this work honestly

- Cite a command and its versioned input when discussing a reproducible local
  result.
- Call a finite replay **bounded evidence**, and state its bounds.
- Call the paper a **draft** unless and until an independent publication exists.
- Call theory **experimental** or **conjectural** where its own checkpoint says
  so.
- Preserve negative results, refusals, and withdrawn claims with the positive
  ones; they define the boundary of what has actually been shown.

This map does not replace the source records. It directs a reader to the
appropriate record before they make a stronger claim than the evidence can
bear.
