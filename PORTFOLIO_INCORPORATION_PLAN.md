# Portfolio incorporation — inventory + gameplan (for review)

*What across the whole portfolio is NOT yet wired into Chiron, and a phased plan to
incorporate all of it. Grounded in the actual files (capabilities and line counts
cited). Nothing is built here — this is the plan you review before we execute.*

---

## Framing is a dial, not a switch

Each capability below carries **two framings** — civilian and contractor/defense —
because the same mechanism serves both and the *title* should flex to the audience.
The engine stays one thing; the README/section title is what changes. (Where the
mechanism is genuinely dual-use, that's an asset, not a liability — JDICert's
Daubert-admissible, ROE-aware certification is *more* valuable to a defense
contractor framed as such, and to a hospital/bank framed as "high-stakes decision
assurance.")

---

## Part A — What is ALREADY incorporated (don't redo)

So the inventory is honest about the gap and not the whole:

- **Veritas** → fully native in `chiron.py` (collapse / same_origin / cast + the
  wisdom layer + Human Translation Layer + the O(1) quintillion-scale transcoder).
  README-only pointer. **Nothing to incorporate.**
- **Primus** → `invariant_engine.py` (1,218 lines) is the *lean ancestor* of
  Chiron's engine; superseded. The *Primus Calamus* combinatorics are now wired via
  `primus_atlas.py` / `primus_verses.py`. **Essentially incorporated.**
- **JDICert** → much deeper in Chiron than expected: the Daubert/FRE 702/FRCP 26
  analyzer, the SoCPM decision rule + threshold, LexGuard gates, Lean-4 proof
  sketches, HMAC attestation, and the regulatory corpus are all in `chiron.py`
  (the "280/280 integrated suite" is cert_engine's, running inside Chiron). **The
  certification *depth* is present** — but only invoked on a JDICert `DecisionContext`,
  never on a Chiron `collapse()` finding (see B-3).
- **UMA** → the RSLS physics core is ported into `chiron.py` (State machine, Cattaneo,
  Lyapunov gate at 19.4). Present but not fed by `collapse` — see
  [`UMA_CHIRON_EXPLORATION.md`](UMA_CHIRON_EXPLORATION.md).

## Part B — The master un-incorporated inventory

Ranked by size of the real gap.

### TIER 1 — genuine un-incorporated *code* capability

**B-1. Infectatrum's spectrum engine** (`Infectatrum/infectatrum.py`, 1,949 lines,
76 gates). *Confirmed absent from Chiron* (no spectrum/Infecticon/origin-signature
in `chiron.py`). This is the largest gap. Un-incorporated pieces:
- **Detect** — quantitative *ambiguity measurement*: spectrum cardinality |Σ|,
  Shannon entropy H(R), per-cell ambiguity load, mutual-information localization,
  excluded negative space. Chiron has *no* ambiguity metric today.
- **Resolve** — collapse-to-one-reading with a provenance-bearing audit trail
  (every resolution a recorded Transformation; "machine case law").
- **Generate** — synthesize structures bearing many *constraint-validated* valid
  readings (the inverse: deliberate, measured multiplicity).
- **Origin-signature engine** — a *second* same-origin test, distinct from Chiron's
  generator-fingerprint: a Bayesian fingerprint of the ambiguity distribution
  compared by Jensen–Shannon divergence (validated on real plates: XXVI/XXVII at
  JSD 0.333 vs 1.0 cross-family).
- **Adversarial-ambiguity detector** — separates natural degradation from
  *engineered* multiplicity (saturates → 1.0 on the synthetic-inflation plates).
- **K/U/Ω epistemic partition** (Knowns/Unknowns/Unknowables from vector math) and
  **Infecticon** (emergent vocabulary from the resolution quotient).
- It already ships **`export_to_cert_engine`** — a designed hand-off bundle into the
  certification layer that is *not currently wired through Chiron*.
- *Civilian:* spec/contract ambiguity measurement + audited disambiguation.
  *Contractor:* engineered-multiplicity / adversarial-input detection on instructions
  and signal feeds (telling a deliberate flood from natural noise).

**B-2. UMA → Chiron physics coupling** (already explored in `UMA_CHIRON_EXPLORATION.md`).
Map a recovered generator into the existing RSLS `State` crucible → a robustness
record (Lyapunov, decoherence half-life, detectability margin); the collapse → evolve
→ collapse persistence loop.
- *Civilian:* robustness/persistence of recovered structure under perturbation.
  *Contractor:* signal-integrity / structural stress-testing under noise and jamming.

### TIER 2 — present in Chiron but not *exposed* (surfacing, not new code)

**B-3. Certification of Chiron findings.** Chiron has the JDICert machinery but no
path that certifies a `collapse()` result (no `certify` / `judicial` CLI verb; the
18-section certificate + `generate_judicial_brief` + Daubert walk run only on a
`DecisionContext`). Surface it: a verb that takes a Chiron finding → full certificate
(belief-delta, admissibility, attestation, judicial brief).
- *Civilian:* "high-stakes decision assurance" certificate for a recovered
  conclusion. *Contractor:* Daubert-admissible, attested certificate for an
  autonomous-decision pipeline.

**B-4. Governance as standalone gates.** LexGuard's four-gate check (entropy /
standard-of-care / regulatory / counterfactual pressure) and SoCPM's
Map/Measure/Manage/Govern exist *inside* certify. Expose them as callable gates on
*any* finding or recommendation (a `chiron.py govern "<claim>"` / `lexguard` check),
not just JDICert decisions.
- *Civilian:* AI duty-of-care / standard-of-care gating. *Contractor:* ROE /
  policy-isolation compliance gating with an escalation path.

**B-5. The intake layer** (`JDICert/primer.py` 1,153 lines + `intel_standardizer.txt`).
A multi-format ingestion/standardizer (sensor adapters, coordinate/timestamp
normalization, K/U classification, batch mode) that is *not* in Chiron. Could become
a general "structured-situation intake" adapter feeding either collapse or certify.
- *Civilian:* multi-source data standardizer. *Contractor:* multi-INT/feed
  standardizer to a common decision schema.

### TIER 3 — conceptual / theory grounding (lighter, optional)

**B-6. Ontological mechanisms.** The Harmony Functional and V-Units (from the
Compendium / five Calculus volumes) became operational only partially — *V* survives
as the SoCPM/emotive valence term. Incorporate the Harmony Functional and V-Units as
explicit, callable scoring primitives, and ground the lineage/identity machinery in
HCT / Projection Calculus (`JDICert/HOLOGRAPHIC_CONTINUITY_THEORY.md`, 626 lines, 12
axioms / 8 theorems — already the provenance theory).

**B-7. Quack salvage (where usable).** *The Resonant Manifold* (resonance-manifold
formalism) plausibly connects to UMA's acoustic-sphere resonance; the *White Paper*
and *Prime Epilogue* are mostly provenance. Salvage the one or two genuinely useful
seeds; keep the rest labeled as lineage. Low incorporation value by design.

**B-8. Primus lean engine as a teaching/reference implementation.** Ship
`invariant_engine.py` as the readable ~1k-line reference next to the 30k-line
monolith — pedagogy, not new capability.

## Part C — The gameplan (phased, for your review)

Each phase is additive, isolated behind a membrane (the project's standing rule),
and gated on Chiron's self-test staying green. Ordered by value ÷ (cost × risk).

| Phase | What | Civilian title | Contractor title | Effort | Risk |
|---|---|---|---|---|---|
| **1** | **Infectatrum bridge** — wire `export_to_cert_engine` + Detect spectrum so Chiron can call ambiguity measurement on any surface; add a `chiron ambiguity "<x>"` path | Ambiguity & coherence measurement | Engineered-multiplicity / adversarial-input detection | M | low (additive module; Infectatrum stays standalone) |
| **2** | **Certify a finding (B-3)** — a `certify` verb mapping a `collapse()` result into the existing certificate path | High-stakes decision assurance | Daubert-admissible autonomous-decision certificate | M | low–med (reuses present code; just a new entry path) |
| **3** | **Governance gates (B-4)** — expose LexGuard 4-gate + SoCPM as standalone checks | AI standard-of-care gate | ROE / policy-isolation gate | S | low |
| **4** | **UMA coupling (B-2)** — the bridge module → robustness record + collapse→evolve→collapse | Structural robustness under perturbation | Signal-integrity stress test | M | med (numpy/scipy dep stays in UMA side; bridge only) |
| **5** | **Origin-signature + adversarial detector (rest of B-1)** — bring Infectatrum's JSD same-process + synthetic-inflation detector to Chiron findings | Provenance / source attribution + anomaly | Source attribution + flood/deception detection | M | low |
| **6** | **Intake adapter (B-5)** — generalize primer into a structured-intake front door | Multi-source standardizer | Multi-feed standardizer | M | low |
| **7** | **Ontological primitives (B-6)** — Harmony Functional + V-Units as scoring; HCT grounding doc | Value/coherence scoring | Mission-value scoring | S–M | low |
| **8** | **Quack salvage + Primus reference (B-7, B-8)** — extract usable seeds; ship the lean reference engine | Lineage + teaching reference | Lineage + reference | S | trivial |

Legend: S ≈ hours, M ≈ a session, effort is per piece; "risk" is to the green
self-test / the engines' isolation.

### The membrane rule (applies to every phase)

Do **not** merge subsystems into the monolith. Each incorporation is a *bridge
module* that imports the standalone engine (or a thin port) and maps data one-way,
exactly as `primus_atlas.py` already does for Infectatrum's corpus and as the UMA
plan specifies. This keeps Chiron's zero-dependency core intact, keeps each
subsystem's own test suite valid, and keeps the whole thing auditable.

### Verification gate (every phase)

After each: `chiron.py selftest` GREEN, `benchmark.py` VERDICT PASS, the bridged
subsystem's own suite still passes, and a one-line demo that the new capability runs
on a real input. No phase ships red.

## Part D — Framing strategy

One pass, late, produces **two title sets** over the *same* code: a civilian
`README`/section vocabulary and a contractor `README`/section vocabulary (kept as a
short alternate-titles table, or two short framing docs). The mechanism, the tests,
and the numbers are identical; only the nouns change. This recovers the
defense-relevant positioning you civilianized — without re-militarizing the default
public face. Recommended default: civilian public README, with a `FRAMING_DEFENSE.md`
(or a private grow doc) carrying the contractor vocabulary for targeted use.

## Part E — Honest notes

- **Biggest real win:** B-1 (Infectatrum) — it adds a capability Chiron genuinely
  lacks (quantitative ambiguity + a second, distribution-based origin test + an
  adversarial detector), and Infectatrum already built the bridge.
- **Cheapest wins:** B-3 and B-4 — the JDICert depth and the governance gates are
  *already in Chiron*; they need an entry path, not new logic.
- **Most novel:** B-2 (UMA) — the robustness axis; build last of the engine pieces
  because it carries the numpy/scipy weight and the most conceptual care.
- **Keep exploratory:** the deepest UMA mappings (AST→Menger) and any "this is the
  true physics" claim. Frame UMA as a *tested crucible*, per your own checkpoints.
- **What this is not:** none of this requires merging engines, breaking the
  single-file core, or re-opening the militarization you cleaned — the dual framing
  is a titling layer, deliberately chosen per audience, not baked into the code.

When you've reviewed and picked the order (or said "all, in this order"), I'll start
at Phase 1 and bring you each one verified and green.
