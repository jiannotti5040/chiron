# Architecture

Chiron is **one engine in one file** with a small ring of companions. This is a
deliberate design choice, not an accident of growth, and this document explains
the shape and why it is kept that way.

![architecture](architecture.svg)

## The one file: `chiron.py`

The entire engine is defined natively in a single Python file — no `exec()` of
embedded source, no second hidden engine, no third-party packages in the core
path. Inside it, six concerns are organized as clearly separated sections:

1. **Invariant engine** — `collapse`, the hypothesis-class fitters, MDL ranking
   (`top_generators`), residual taxonomy, structural fingerprints, `articulate`
   (the inverse codec).
2. **Certifier** — gates each consequential claim for evidence, counterexamples,
   and provenance; emits the auditable certificate (`human_report`).
3. **Wisdom layer** — scores any explanation for condescension, unearned
   confidence, evasion, and opacity, and renders findings as *what was found, why
   it is believed, what would falsify it.*
4. **Twin / transfer** — same-generator detection across domains; structural
   correspondence.
5. **Executive** — an isolated, bounded agent; network off by default; anything
   irreversible escalates to a human.
6. **Memory (the Congress)** — verified rules persist as compact, owner-bound,
   order-independent records that pool across instances without trust.

### Why a single file

- **Portability and zero install.** One file runs anywhere Python does; the core
  has no dependencies (numpy/scipy are optional accelerators with pure-Python
  fallbacks).
- **Auditability.** A reviewer reads one artifact end to end. The self-test scans
  the core to prove properties (e.g. no network in the core path).
- **Owner-signed integrity.** Hashes and the Merkle root bind the whole record.

The single-file distribution stays canonical, but a modular **view** is now
available behind a build step: `build.py` losslessly splits `chiron.py` (and
`semic.py`) into section modules and recompiles them with a **byte-identical**
round-trip gate, so the file can be navigated and edited as modules without ever
costing the properties above (`python3 build.py verify-all`).

## The companions (storage and interface, not dependencies)

| file | role |
|---|---|
| `chiron_grow.py` | the shared grower — pulls from any source (Wikipedia / website / API / OEIS), continuous and self-resuming |
| `chiron_ciphers.py` | cipher/code solver; seeds a cryptography basis |
| `dashboard.html` | the offline operator console (served by `chiron.py serve`) |
| `chiron_memory.json` | the Congress (ships as a clean seed) |
| `parameters.json` + `grow-*/profiles/` | the configuration layer |

## The evaluation tools (additive; the engine is untouched by them)

| file | answers |
|---|---|
| `benchmark.py` | does it work? (OEIS-core + ciphers + adversarial, scored for false positives) |
| `bench_suite.py` | does it generalize? — six tasks vs established baselines (sequences, semantics, protocols, governance, symbolic regression, authorship) |
| `compare.py` | compared to what? (vs gzip / bz2 / lzma) |
| `trace.py` | why does it work? (ranked candidates → winner → verification → residual) |
| `verify.py` | can I reproduce it? (records + determinism digest) |
| `profile.py` | where does the time go? |
| `export_graph.py` | export recovered structure as a knowledge graph (JSON-LD / Markdown / edges) |
| `discover.py` | cross-domain twins — surfaces that share one generator across domains |
| `mine_code.py` | code-repository mining — structural skeletons and clone detection |
| `ingest_pdf.py` | optional PDF source adapter (text + embedded-sequence recovery) |
| `formal_check.py` | property-based soundness check (see [FORMAL.md](FORMAL.md)) |
| `primus_atlas.py` | collapse Caramuel's whole transcribed atlas; cross-plate twins |
| `primus_verses.py` | run the labyrinth forward — proteus generation + native scansion |
| `fastops.py` + `chiron_fastops/` | optional Rust native hot-path with pure-Python fallback |
| `infectatrum_bridge.py` | ambiguity spectrum (\|Σ\|, entropy) + origin-signature + adversarial detector |
| `uma_bridge.py` | robustness of recovered structure under the RSLS dynamics |
| `certify_finding.py` | full certificate (Daubert / attestation) over a collapse finding |
| `govern.py` | SoCPM / LexGuard governance gate on any claim |
| `intake.py` | structured-intake front door (JSON / numeric / text) |
| `ontological.py` | V-Units + Harmony Functional scoring |
| `actionable_intelligence.py` | decision-ready brief: forecast + exact anomaly + governed call |
| `operator_calculus.py` | six epistemic operators over a Mystery Vector |
| `projection_stack.py` | project a finding P→C→E→S, identity preserved |
| `significance.py` | curvature-as-significance — where meaning concentrates |
| `density_emotion.py` | competing hypotheses decohere, Lindblad CPTP |
| `holographic.py` | recover structure from an erased boundary fragment |
| `aesthetics.py` | mathematical beauty — elegance · symmetry · resonance |
| `cross_examine.py` | adversarial reasonable-doubt search (jurisprudence) |
| `stare_decisis.py` | Merkle precedent ledger; departures flagged (jurisprudence) |
| `jurisdiction.py` | per-domain SoCPM admissibility threshold (jurisprudence) |
| `candor_bridge.py` | anti-patronization audit of an explanation |
| `provenance.py` | conserved-history DAG + minimal blame (HCT A3/T3) |
| `axioms.py` | runs the HCT axioms A1-A8 + theorems T1-T6, executed |
| `language.py` | offline NL: n-gram + PPMI semantics + prose brief (no API) |
| `discernment.py` | independent witnesses; confidence by convergence |
| `cross_examine.py` + `judgment.py` | jurisprudence suite: adversarial doubt + Earned-Finality Chief Justice |
| `legal_corpus.py` | hardcoded law/regulation/treaty/order corpus (67 provisions) |
| `semic.py` + `semic_bridge.py` | Semantic Invariant Calculus — collapse lifted to meaning (pure-stdlib, 56/56 gates; exact O(N·m) separable solver, typed classes H1–H5, constraint discovery) |
| `semic_energy.py` | the three-level stack — exact collapse, then Gibbs energy exploration on refusal (explicitly uncertified) |
| `epistemic.py` | the abstract primitive — Surface→Hypothesis→Constraint→Verify→Certificate, with chiron / semic / governance / energy as instances |
| `grow_clean.py` | unified grower over any file, the Wikipedia preset, or ingestion-driven search; LLM-aided (propose→verify) |
| `president_grow.py` | the compartmentalized LLM grow service — the model proposes, chiron verifies; nothing enters unverified |
| `llm_providers.py` | multi-provider LLM client — a fallback chain (gemini → openrouter → groq → openai → anthropic → perplexity), each keyed from its own env var; the proposer for the Chat assistant |
| `build.py` | lossless split/recompile of the single-file engines, byte-identical round-trip gate |
| `intake_salvage.py` | fault-tolerant ingestion over strict `intake.py` (never overwrites a good parse) |
| `vault.py` | one command that starts every local service and prints one URL (Ctrl-C stops all) |
| `console_server.py` | the launcher service — run any function from the dashboard Run tab (port 8768) |
| `assistant_server.py` | the natural-language assistant — intent → real engine actions (Chat tab, port 8769) |
| `grow_control.py` | start / stop / point the continuous grower from the dashboard (Feed tab, port 8767) |
| `llm_certify.py` | accountability certificate over an LLM output — audit + exactly verify its checkable claims |
| `chiron_artifact.py` + `build_manifest.py` | per-script signed, falsifiable certificates (`artifacts/`) + the manifest index the dashboard reads |
| `apply_license_headers.py` | idempotent SPDX header stamper across every `.py` |
| `vault_dashboard.html` | the certificate browser — one tile per script: its claim and what would falsify it |
| `examples/` | worked examples + certificates, regenerated from real output |

## The whole spine in one file (`Chiron Monolith/`)

The single-file property of `chiron.py` is extended to the **entire spine**: the sibling
`Chiron Monolith/` folder holds `chiron_monolith.py`, which embeds the byte-identical source of
all 63 Chiron modules and wraps them in a `sys.meta_path` loader so every cross-import
(`import chiron`, `import semic`, …) resolves to the embedded copy. Any module runs from the one
file — `python3 chiron_monolith.py <module> [args]` — and `--selftest` proves it: the core engine
battery and 43/43 selftest-bearing modules pass identically to the standalone scripts. It is a
**lossless fold** (round-trip asserted at build by `build_monolith.py`), not a rewrite, and adds no
logic; each module's `__file__` points back at the real `../Chiron/<name>.py` so self-source scans
and data files resolve exactly as they do standalone.

## Data flow

```
surface ──▶ collapse ──▶ verify on held-out terms ──▶ classify ──▶ Congress
                                   │                       (integral / general)
                                   ▼
                              certificate  ──▶ articulate (speak the rule back up)
```

Sources feed the grower; the grower feeds `assimilate`; verified rules become
laws in the Congress; the console and the certificate are how a human reads it.
Network is off by default and never essential — engine, Congress, console, and
gates all run fully offline and deterministically.
