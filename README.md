# Chiron — recover exactly, verify, refuse, certify

**What must a machine prove before it deserves influence over a human decision?**

This repository answers that with engineering, not policy. At its center is **Chiron**: a portable,
offline, deterministic engine that recovers the exact rule beneath a codified surface, verifies it by
exact prediction of withheld data, and **refuses** when no rule is confirmed. The defining property
is not maximal recall — it is the discipline of declining to certify what cannot be exactly verified,
a checkable standard of care that curve-fitting and neural embeddings structurally lack.

The surrounding systems are not separate projects. They are the same contract — **recover structure →
verify exactly → refuse otherwise → certify provenance** — instantiated across meaning, governance,
ambiguity, value, and certification, and made explicit as one interface in
[`Chiron/epistemic.py`](Chiron/epistemic.py).

## Proof first — measured and reproducible

`python3 Chiron/benchmark.py`:

| Benchmark | Result |
|---|---|
| OEIS-core sequences | 22 / 22 algebraically-generated recovered (held-out predicted exactly); 7 / 7 non-closed-form correctly abstained |
| Classical ciphers | 42 / 44 plaintexts recovered ciphertext-only |
| Randomized fuzz + labeled gauntlet | ~5,070 scored cases — **0 false verifications**, 0 crashes |

The number that matters is the zero: across roughly 5,070 scored cases the engine never certified a
rule it could not predict.

`python3 Chiron/bench_suite.py` runs the same architecture across **six independent tasks** — integer
sequences, proverb semantics, protocol/automaton inference, governance, symbolic regression (vs
polynomial regression), and authorship attribution — each beating or matching an established baseline
and refusing rather than guess where refusal applies.

## How it works

Chiron takes an ambiguous surface (an integer sequence, a string, a ciphertext, source code) and
recovers the minimal generator beneath it under a Minimum Description Length criterion in **exact
rational arithmetic**. A result is *verified* only when the recovered rule predicts withheld terms at
exact equality; anything it cannot compress is returned as a classified residual, never a confident
guess. The core is a single self-contained file with no third-party dependencies, owner-signed end to
end, and it emits an auditable certificate on every run.

- `python3 Chiron/epistemic.py` — the contract (Surface → Hypothesis → Constraint → Verify →
  Certificate) as one interface, with the integer engine, the semantic calculus, the governance
  layer, and a probabilistic (energy) layer as four instances of it.
- `python3 Chiron/compare.py` — head-to-head vs gzip / bz2 / lzma: Chiron stores a constant-size law
  that regenerates terms the general compressors cannot produce.
- `python3 Chiron/trace.py "1 1 2 3 5 8"` — the full ranked-candidate reasoning path: why the winner
  won and how it was verified.
- `python3 Chiron/llm_certify.py "..."` — wrap a language-model output: audit its honesty, exactly
  verify the checkable claims, refuse to call free text "correct." The discipline as an LLM wrapper.
- **Run everything with one command:** `cd Chiron && python3 vault.py`, then open
  http://127.0.0.1:8765 — the operator console with **Analyze**, **Run** (run any function), **Chat**
  (natural language over the engine), and **Feed** (start/stop/point the grower). Full guide:
  **[RUNNING.md](Chiron/RUNNING.md)**.
- **The Chat assistant is provider-pluggable and free.** It tries a fallback chain of LLMs — set any
  one key (`GEMINI_API_KEY`, `OPENROUTER_API_KEY` for Llama/Qwen/GPT, `GROQ_API_KEY`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, …) in your shell, **or paste it right in the Chat tab’s “Add your own API key”
  panel**. The model only proposes; the exact engine still verifies. See `Chiron/llm_providers.py`.
- Every script can leave a signed, falsifiable certificate under `Chiron/artifacts/`, indexed by
  `build_manifest.py` and browsable in `vault_dashboard.html` — each tile names the module in Chiron
  vocabulary and explains it **mathematically, programmatically, and conceptually**. See
  [ARTIFACTS.md](Chiron/ARTIFACTS.md). Four scripts (`semic`, `chiron`, `density_emotion`,
  `chiron_artifact`) emit as working proofs.
- **The whole spine in one file:** `python3 "Chiron Monolith/chiron_monolith.py" --selftest` — all
  63 Chiron modules folded, byte-identical, into a single runnable file; run any of them with
  `python3 "Chiron Monolith/chiron_monolith.py" <module> [args]`. See
  [Chiron Monolith/README.md](Chiron%20Monolith/README.md).
- Scope and failure modes are stated plainly in [WHY_CHIRON.md](Chiron/WHY_CHIRON.md) and
  [KNOWN_LIMITATIONS.md](Chiron/KNOWN_LIMITATIONS.md).

## Components

Each system stands alone in its folder with its own README; together they are one contract in
different domains.

| System | Role |
|---|---|
| **Chiron** | Deterministic invariant recovery, certification, and bounded growth under governance — the flagship. |
| **semic** | The Semantic Invariant Calculus — the recovery discipline lifted from integer sequences to meaning, exact and fully offline, with a three-level energy layer that explores explicitly *uncertified* approximations only when exact collapse refuses. |
| **JDICert** | High-stakes decision certification: regulatory and governance gates (EU AI Act, GDPR, NIST AI RMF, ISO/IEC 42001), a free-energy filter against unsupported conclusions, and cryptographically-signed, Merkle-chained certificates. |
| **Veritas** | The exact-arithmetic core of *collapse / same-origin / cast* — multi-hypothesis ranking, residual taxonomy, and every finding rendered as *what was discovered, why it is believed, and what would falsify it.* |
| **Candor** | An anti-patronization audit scoring reasoning across condescension, unearned confidence, evasion, and opacity, tracing each point of the score to the span that caused it. |
| **Infectatrum** | Ambiguity and information-loss measurement over any codified object — reading-spectrum cardinality and entropy, origin signatures, and the transcribed Caramuel *Primus Calamus* (1663) atlas. |
| **President** | A bounded executive, deliberately isolated from the deterministic core; it gathers and deliberates over public archives and escalates anything irreversible to a human. |

## Mathematical compendium

Every formal object across the portfolio — the invariant engine, the semantic calculus, the
continuity theory, the physical substrate, the governance rules, and the derived measures — is
collected in one document, each result tagged by its epistemic status (standard result, implemented
and tested, proof-of-concept, or self-developed theory):

**[Mathematical_Compendium.pdf](Mathematical_Compendium.pdf)** (source: `Mathematical_Compendium.tex`).

## Theoretical foundations

The engineering grew from a body of self-developed theory: **Holographic Continuity Theory** and the
**Projection Calculus** (identity persistence under transformation, provenance as a conservation law,
significance as geometric curvature); **SoCPM — A Standard of Care for Persuasive Machines** and
**LexGuard** (the governance doctrine); **UMA** (the computational-physics field substrate); and the
**Projection–Innovation Hierarchy** (a variational principle for dynamical systems with endogenous
uncertainty). These are constructive explorations that informed the build; they are **not externally
validated or peer-reviewed**, and are labeled as such throughout. The independently verifiable claims
are the engine and the benchmarks above.

## Scope

The exact-recovery core and the measures marked *implemented and tested* are reproducible and covered
by self-tests. The certification, governance, and theoretical layers are working prototypes built to
civilian standards and have not undergone external or third-party audit. Epistemic status is labeled
explicitly rather than blurred — that labeling is the point.

## License

Licensed under the **PolyForm Noncommercial License 1.0.0** (see [LICENSE.md](LICENSE.md)): free to
use, modify, and share for any noncommercial purpose; all commercial rights reserved to Jacob
Iannotti. Commercial licensing and other inquiries: jiannotti1@gmail.com
