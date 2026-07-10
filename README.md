# Chiron — recover exactly, verify, refuse, certify

[![gates](https://github.com/jiannotti5040/Jacob-s-Portfolio-Vault/actions/workflows/ci.yml/badge.svg)](https://github.com/jiannotti5040/Jacob-s-Portfolio-Vault/actions/workflows/ci.yml)

> **New here? → [START_HERE.md](START_HERE.md) is the 90-second, plain-English tour** — what it is, a 20-second demo, and why it matters. No domain background needed.
>
> **In plain terms:** an offline engine that finds the exact rule behind an ambiguous input, *proves* it on data it never saw, and *refuses* rather than guess — so you can tell what an AI answer has **proven** from what it merely **asserts**. It ships as an installable tool with 155+ passing gates and zero false verifications. Architecture at a glance: **[architecture.svg](architecture.svg)**.

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

## The front door: a verifier that refuses, as a package

The discipline is installable. In the agent era, the missing primitive is not a model
that answers — it is a gate that separates what an answer *proves* from what it merely
*asserts*. That gate is the `primus` package (the seed engine plus its certificate layer):

```bash
pip install ./Primus
```

```python
from primus import certify
cert = certify(model_output)          # any LLM/agent answer
cert["counts"]                        # every checkable claim: VERIFIED / REFUTED / REFUSED
cert["unverifiable_remainder"]        # free text is reported honestly, never blessed
```

```bash
echo "<model output>" | primus certify - --gate    # exit 1 if any claim is REFUTED
primus collapse "1 1 2 3 5 8 13 21"                # the engine itself, one command
```

It refuses to call free text "correct," refutes what is exactly false, and stamps only
what it exactly verifies on data it never saw. And it speaks MCP: `primus-mcp` serves
`certify` + `collapse` over stdio, so Claude Code (`claude mcp add primus -- primus-mcp`),
Claude Desktop, Cowork, or any MCP agent can call the gate natively.
See [Primus/README.md](Primus/README.md).

**Try it in a browser, no install:** [`playground.html`](playground.html) runs the
*real* engine sources on CPython/WebAssembly, entirely client-side — serve the repo
(`python3 -m http.server`) or enable GitHub Pages and open it.

## Proof first — measured and reproducible

`python3 Chiron/benchmark.py`:

| Benchmark | Result |
|---|---|
| OEIS-core sequences | 22 / 22 algebraically-generated recovered (held-out predicted exactly); 7 / 7 non-closed-form correctly abstained |
| Classical ciphers | 42 / 44 plaintexts recovered ciphertext-only |
| Randomized fuzz + labeled gauntlet | ~5,070 scored cases — **0 false verifications**, 0 crashes |
| **Live OEIS (external data)** | `python3 Primus/oeis_live.py` — 28 sequences fetched from oeis.org: **20 verified, all externally correct; 0 false stamps; 7 honest refusals** — incl. Motzkin, Schröder, and (deep tier) the Apéry and Franel numbers via exact P-recursion, with Bell correctly refusing even at 24 shown terms ([results + miss list](Primus/EXTERNAL_VALIDATION.md)) |
| **vs. symbolic regression** | Same live protocol vs gplearn GP: Primus 16 exact / **0 wrong** / 8 refused; the regressor 2 exact / 22 wrong ([details](Primus/SYMREG_RESULTS.md)) |

The number that matters is the zero — and it is now an *externally tested* zero. The first
live-OEIS run caught a false verification the ~5,070 internal cases never surfaced (float
drift in the recurrence path, fixed with exact rational arithmetic; the full story is told,
not buried, in [EXTERNAL_VALIDATION.md](Primus/EXTERNAL_VALIDATION.md)). The claim is
stronger for having been falsified and repaired in the open.

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
- **Run everything with one command:** `python3 bin/chiron serve` from the vault root, then open
  http://127.0.0.1:8765 — the operator console with **Analyze**, **Run** (run any function), **Chat**
  (natural language over the engine), and **Feed** (start/stop/point the grower). Full guide:
  **[RUNNING.md](Chiron/docs/RUNNING.md)**.
- **The Chat assistant is provider-pluggable and free.** It tries a fallback chain of LLMs — set any
  one key (`GEMINI_API_KEY`, `OPENROUTER_API_KEY` for Llama/Qwen/GPT, `GROQ_API_KEY`, `OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`, …) in your shell, **or paste it right in the Chat tab’s “Add your own API key”
  panel**. The model only proposes; the exact engine still verifies. See `Chiron/llm_providers.py`.
- Every script can leave a signed, falsifiable certificate under `Chiron/artifacts/`, indexed by
  `build_manifest.py` and browsable in the dashboard's **Verify → Certificates** stage — each tile names the module in Chiron
  vocabulary and explains it **mathematically, programmatically, and conceptually**. See
  [ARTIFACTS.md](Chiron/docs/ARTIFACTS.md). Four scripts (`semic`, `chiron`, `density_emotion`,
  `chiron_artifact`) emit as working proofs.
- **The whole spine in one file:** all 63 Chiron modules folded, byte-identical, into a single
  runnable file. `python3 "Chiron Monolith/chiron_monolith.py" serve` opens the same dashboard;
  `--selftest` runs the full gate sweep (identical coverage to the full build); run any module with
  `... <module> [args]`. The folder is self-contained. See
  [Chiron Monolith/README.md](Chiron%20Monolith/README.md).
- Scope and failure modes are stated plainly in [WHY_CHIRON.md](Chiron/docs/WHY_CHIRON.md) and
  [KNOWN_LIMITATIONS.md](Chiron/docs/KNOWN_LIMITATIONS.md).

## The vault at a glance

Five concepts, one interface:

| Concept | Where | Rule |
|---|---|---|
| **Source** | `Chiron/` (flat engine modules; guides in `Chiron/docs/`) + `Primus/` (the packaged seed) | you edit here, always |
| **CLI** | `bin/chiron` — `serve · test · build · verify · grow · benchmark · doctor` | the single way you interact |
| **Build** | `Chiron Monolith/build_monolith.py` + `Chiron/build_manifest.py`, driven by `chiron build` | reproducible; never guess |
| **Runtime** | `chiron serve` → console :8765, launcher :8768, assistant :8769, grow :8767/:8766 | one Ctrl-C stops everything |
| **Artifacts** | `Chiron Monolith/` (the self-contained fold), `Chiron/manifest.json`, `Chiron/artifacts/` | generated — run, ship, delete, rebuild, **never edit** |

```
START_HERE.md         the 90-second front door        playground.html   the engine in a browser
bin/chiron            the CLI — the product; the scripts behind it are implementation details
Chiron/               the flagship engine (source of truth) + docs/ + tests/ + artifacts/
Chiron Monolith/      generated artifact: the whole spine folded into one runnable file
Primus/               the packaged seed engine (pip install ./Primus) + its full gate battery
JDICert/ Veritas/ Candor/ Infectatrum/    the same contract in other domains
Governance/ UMA Suite/ Individual Programs/ Ontological & Philosophical Books/
Quack System Constructs/ Paper/           doctrine, theory, papers, salvage
docs/                 vault-level documents (Mathematical Compendium)
```

**Where this is going:** the long-horizon vision — dashboard flow, the run ledger, the President
as planner, certify-before-act for external agents, and the *Abstain or Prove* benchmark — lives in
**[docs/HORIZON.md](docs/HORIZON.md)**, every milestone with a falsifier attached. `chiron parity`
already proves the spine and the fold are one organism (138 identical gates through both).

## Components

Each system stands alone in its folder with its own README; together they are one contract in
different domains.

| System | Role |
|---|---|
| **Primus** | The installable seed: `pip install ./Primus` gives `collapse` (exact recovery with held-out proof) and `certify` (the accountability certificate over LLM/agent output) as a package, CLI, and agent tool-call. Externally validated against the live OEIS. |
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

**[docs/Mathematical_Compendium.pdf](docs/Mathematical_Compendium.pdf)** (source: `docs/Mathematical_Compendium.tex`).

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
