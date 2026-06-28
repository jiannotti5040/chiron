# Jacob Iannotti — Portfolio

A year of work on a single question: **what must a machine prove before it deserves influence over a human decision?**

A year ago I was not a programmer. I became concerned that increasingly capable AI systems were
becoming increasingly persuasive while remaining fundamentally probabilistic — confident without
being accountable. The work in this repository is an attempt to build the opposite: deterministic
systems that recover structure exactly, certify what they conclude, preserve provenance, measure
ambiguity, and decline to claim what they cannot prove. I approach it as a systems architect — the
emphasis is on how knowledge is represented, how decisions are justified, and what a persuasive
machine owes the people affected by its outputs.

At the center is **Chiron**, a portable, offline, deterministic engine that recovers the exact rule
beneath a codified surface, verifies it by exact prediction, and abstains when no rule is confirmed.
The surrounding systems extend that discipline to certification, governance, ambiguity, value, and
meaning.

## Mathematical compendium

Every mathematical object across the portfolio — the invariant engine, the semantic calculus, the
continuity theory, the physical substrate, the governance rules, and the derived measures — is
collected in one formal document, with each result tagged by its epistemic status (standard result,
implemented and tested, proof-of-concept, or self-developed theory):

**[Mathematical_Compendium.pdf](Mathematical_Compendium.pdf)**

## Chiron — the flagship

Chiron takes an ambiguous codified surface (an integer sequence, a string, a ciphertext, source
code) and recovers the minimal generator beneath it under a Minimum Description Length criterion in
exact rational arithmetic. A result is *verified* only when the recovered rule predicts withheld
terms at exact equality; anything it cannot compress is returned as a classified residual rather
than a confident guess. It is a single self-contained file with no third-party dependencies in its
core path, owner-signed end to end, and it returns an auditable certificate on every run.

**Measured, reproducibly** — `python3 Chiron/benchmark.py`:

| Benchmark | Result |
|---|---|
| OEIS-core sequences | 22 / 22 algebraically-generated recovered (held-out predicted exactly); 7 / 7 non-closed-form correctly abstained |
| Classical ciphers | 42 / 44 plaintexts recovered ciphertext-only |
| Randomized fuzz + labeled gauntlet | ~5,070 scored cases — **0 false verifications**, 0 crashes |

The figure that matters is the zero: across roughly 5,070 scored cases the engine never certified a
rule it could not predict. A finite-difference baseline, by contrast, recovers only the pure
polynomials and is confidently wrong on the rest.

- `python3 Chiron/compare.py` — head-to-head against gzip / bz2 / lzma; Chiron stores a
  constant-size law that regenerates terms the general compressors cannot produce.
- `python3 Chiron/bench_suite.py` — the same recovery architecture across four independent
  domains (integer sequences, proverb semantics, protocol/automaton inference, and governance),
  each beating a simpler baseline and abstaining rather than guess.
- `python3 Chiron/trace.py "1 1 2 3 5 8"` — the full ranked-candidate reasoning path: why the
  winner won and how it was verified.
- Scope and failure modes are stated plainly in
  [WHY_CHIRON.md](Chiron/WHY_CHIRON.md) and [KNOWN_LIMITATIONS.md](Chiron/KNOWN_LIMITATIONS.md).

## Components

Each system stands alone in its folder, with its own README; together they form one lineage.

| System | Role |
|---|---|
| **Chiron** | Deterministic invariant recovery, certification, and bounded growth under governance — the flagship. |
| **JDICert** | High-stakes decision certification: regulatory and governance gates (EU AI Act, GDPR, NIST AI RMF, ISO/IEC 42001), a free-energy filter against unsupported conclusions, and cryptographically-signed, Merkle-chained certificates. |
| **Veritas** | The exact-arithmetic core of *collapse / same-origin / cast*, with multi-hypothesis ranking, residual taxonomy, and a layer that renders every finding as *what was discovered, why it is believed, and what would falsify it.* |
| **Candor** | An anti-patronization audit that scores reasoning across condescension, unearned confidence, evasion, and opacity, and traces each point of the score to the span that caused it. |
| **Infectatrum** | Ambiguity and information-loss measurement over any codified object; reading-spectrum cardinality and entropy, origin signatures, and the transcribed Caramuel *Primus Calamus* (1663) atlas. |
| **semic** | The Semantic Invariant Calculus — the Chiron recovery discipline lifted from integer sequences to meaning, exact and fully offline. |
| **President** | A bounded executive, deliberately isolated from the deterministic core; it gathers and deliberates over public archives and escalates anything irreversible to a human. |

## Theoretical foundations

The engineering grew from a body of self-developed theory: **Holographic Continuity Theory** and the
**Projection Calculus** (identity persistence under transformation, provenance as a conservation law,
significance as geometric curvature); **SoCPM — A Standard of Care for Persuasive Machines** and
**LexGuard** (the governance doctrine); **UMA** (the computational-physics field substrate); the
**Projection–Innovation Hierarchy** (a variational principle for dynamical systems with endogenous
uncertainty); and the **Calculus series** with the **Compendium** (the first-principles ground).

These are constructive, self-developed explorations that informed the build. They are **not
externally validated or peer-reviewed**, and are offered as such; the independently verifiable
claims are the engine and its benchmark above.

## Scope

The exact-recovery core and the measures marked *implemented and tested* are reproducible and covered
by self-tests. The certification, governance, and theoretical layers are working prototypes designed
to civilian standards and have not undergone external or third-party audit. This is a single-author
body of work, developed with LLM-augmented tooling under human architecture and review.

## License and contact

Licensed under the **PolyForm Noncommercial License 1.0.0** (see [LICENSE.md](LICENSE.md)): free to
use, modify, and share for any noncommercial purpose; all commercial rights reserved to Jacob
Iannotti. Commercial licensing and other inquiries: jiannotti5040@gmail.com
