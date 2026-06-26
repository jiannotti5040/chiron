# Vault Inventory + HCT Incorporation Gameplan

*Second-pass inventory of the entire portfolio vault, an honest accounting of what
the last incorporation pass missed, and a tiered gameplan to add the full
Holographic Continuity Theory layer — the epistemic operator calculus, the
jurisprudence suite, aesthetics, and the ontological / epistemological /
emotional / semantic / contextual substrates — as bridge modules, without touching
the green engine. For review before any building begins.*

**Framing note up front.** Per your direction, this is **not** a pivot to "Chiron as
a new mathematics" — that direction was explicitly rejected. The organizing idea is
the **Tripartite Machine** (Epistemology · Ontology · Axiology) realized as a
**discernment engine**: progressive elimination, independent witnesses, structural
humility, failure as information, explanation before assertion. HCT and the Projection
Calculus are the *language* the architecture speaks, not the thing it becomes.

---

## 0. Lockdown status (baseline frozen before any work)

| Engine | Check | Result |
|---|---|---|
| `Chiron/chiron.py` | `selftest` | **GREEN — 12/12 core gates** |
| `JDICert/cert_engine.py` | imports (numpy 2.2.6 + scipy) | **OK — carries its own 280-test suite** |
| Membrane rule | chiron.py byte-unchanged | held — all prior work additive |

Nothing below merges code into `chiron.py`. Every item is an additive bridge behind
the established one-way membrane, mirrored to both `Chiron/` and `Chiron-Refined/`.

---

## 1. Complete vault inventory (every top-level item)

Legend: **DONE** = incorporated/bridged · **PARTIAL** = fragments only, real gap remains
· **MISSING** = not incorporated at all · **REFERENCE** = lineage/theory, no code to bridge
· **STANDALONE** = intentionally separate.

| Folder / file | What it is | Status |
|---|---|---|
| `Chiron/` | The engine (branded canonical, grown memory) | DONE (the core) |
| `Chiron-Refined/` | De-branded clean twin | DONE (mirrors Chiron) |
| `Veritas/` | Truth-engine lineage | **DONE** — native in chiron.py |
| `Primus/` + `*Primus Calamus…(1663).pdf` | Caramuel combinatorics + `invariant_engine.py` | DONE — `primus_atlas.py`, `primus_verses.py`, `REFERENCE.md` |
| `Infectatrum/` | Reading-spectrum ambiguity engine + 21-plate corpus | DONE — `infectatrum_bridge.py` |
| `UMA Suite/` | RSLS metriplectic physics (v3/v4) | DONE — `uma_bridge.py` (physics also ported into chiron.py) |
| `Quack System Constructs/` | Early speculative constructs | DONE — `SALVAGE.md` (one seed kept) |
| `Governance/` | *Standard of Care for Persuasive Machines*, *LexGuard* (PDFs) | DONE (operationalized) — source for `govern.py`; **REFERENCE** otherwise |
| **`JDICert/`** | **`cert_engine.py` (12,907 lines) + `primer.py` + HCT theory** | **PARTIAL — the big miss (see §2)** |
| **`Candor/`** | `candor.py` — the anti-patronization / honesty auditor | **MISSING — never bridged** |
| **`Ontological & Philosophical Books/`** | Calculus series Books I–V + Compendium (PDFs) | **REFERENCE — never wired into literature** |
| **`Individual Programs/`** | PIH (Projection–Innovation Hierarchy) theory; `transcribe_final.py` | **REFERENCE** (PIH) + **STANDALONE** (transcribe) |
| Root docs | `README`, `LICENSE.md`, `NOTICE.md`, `CONTRIBUTING.md`, `FRAMING.md`, `*_EXPLORATION.md`, `PORTFOLIO_INCORPORATION_PLAN.md` | DONE (repo meta + prior exploration) |

---

## 2. What the last pass missed (the honest gap)

Last pass concluded "JDICert is *more* incorporated than expected" because the
SoCPM rule, the Daubert/FRE-702 analyzer, the LexGuard four-gate, the emotive
aggregation, the Maxwell-Cattaneo physics, and HMAC attestation **are** in
`chiron.py`. That was true — and it hid the real shape:

`cert_engine.py` is a **second ~13k-line monolith** (peer in scale to `chiron.py`,
280 tests passing) that contains the **entire HCT operator-calculus layer** — and
**none of it is bridged**. The fragments in `chiron.py` are the floor of JDICert,
not its building. The missing layer is exactly the "different layers you highlighted":

| Appended-doc / HCT construct | Lives in `cert_engine.py` as | In Chiron? |
|---|---|---|
| Six epistemic operators (Measure·Reframe·Invent·Model·Dialogue·Explore) | `MeasureOperator…ExploreOperator`, `EpistemicOperatorAlgebra` | **MISSING** |
| Mystery Vector (ξ over ignorance/paradox/transcendence/emergence/subjectivity/infinity) | `MysteryVector`, `KUOmegaPartition` | **MISSING** |
| Projection stack **P→C→E→S** (physical→contextual→emotive→semantic) | `EmotiveSubstrateProjectionStack`, `ProjectionStackProvenance` | **MISSING** |
| Significance = `tanh(α·κ)` (Ollivier-Ricci curvature) | `SignificanceGeometry`, `SignificanceField`, `CurvatureDrivenFlow` | **MISSING** |
| Emotion as Lindblad CPTP density evolution | `DensityEmotion`, `DensitySignificanceField`, `SuperpositionContext` | **MISSING** |
| Holographic distributed redundancy / recovery threshold | `HolographicQECAgent`, `LinearHolographicEncoder`, `MengerSponge`, `IsometricProjection` | **MISSING** |
| Provenance conservation (T3) | `ProvenanceDAG`, `ProvenanceCommit`, `Capsule` | **MISSING** |
| Active inference / free-energy agency | `FreeEnergyAgent`, `ActiveInferenceAgent` | **MISSING** |
| Jurisprudence: adversarial / precedent / jurisdiction | `RedTeamAttack`, `DoctrineLedger`, `SoCPMProgram`, `analyze_legal_admissibility`, `generate_judicial_brief` | **PARTIAL** (Daubert + SoCPM in chiron; no Chiron-facing suite) |
| **Aesthetics** (elegance · symmetry · resonance) | — *nothing, anywhere* | **MISSING (genuine)** |
| Candor / anti-patronization | `Candor/candor.py` (standalone) | **MISSING** |

**Architectural call:** `cert_engine.py` should be **bridged, not reimplemented**.
It already passes 280 tests and already carries numpy/scipy — exactly the situation
`uma_bridge.py` is in. Re-porting 13k lines into the single-file core would bloat it
and risk the green engine for zero benefit. The bridges import `cert_engine` and map
a Chiron finding one-way into its constructs, identical to the Infectatrum/UMA pattern.

---

## 3. The gameplan — bridges organized by the Tripartite Machine

Every module: additive, behind the membrane, mirrored to both folders, dual-framed
(civilian + contractor titles added to `FRAMING.md`), shipped only when the
subsystem suite still passes **and** `chiron.py selftest` is GREEN **and** a one-line
live demo runs. No phase ships red.

### Pillar I — EPISTEMIC (extraction + the operator calculus)
- **E-1 `operator_calculus.py`** — bridge `EpistemicOperatorAlgebra` + the six
  reduction operators + `MysteryVector` onto a Chiron finding's residual/unknowns.
  Demonstrates the non-commutativity (Measure∘Reframe ≠ Reframe∘Measure).
- **E-2 `projection_stack.py`** — bridge `EmotiveSubstrateProjectionStack`: run a
  surface up/down the **P→C→E→S** substrate chain with provenance; expose `recover()`.
  This *is* the contextual / emotive / semantic layering you asked for.
- **E-3 `OPERATOR_CALCULUS.md`** — formalize the arrows-as-operators (`→ ⇒ ⇐ ↔ ~ * |·| (·)`)
  as first-class objects per the appended dialogue: a notation spec, not a claim of new math.

### Pillar II — ONTOLOGICAL (physics / simulation + the substrate geometry)
- **O-1 `significance.py`** — bridge `SignificanceGeometry` (Ollivier-Ricci curvature →
  significance; high curvature = ambiguity/instability, low = coherent/recoverable).
- **O-2 `density_emotion.py`** — bridge `DensityEmotion` (Lindblad) + `SuperpositionContext`:
  emotional/semantic instability as CPTP density-matrix evolution — the **emotional + semantic** layer.
- **O-3 `holographic.py`** — bridge `HolographicQECAgent` + `MengerSponge`: does a
  recovered structure survive erasure of a boundary subset above threshold? The HCT
  continuity test, complementary to `uma_bridge.py`'s RSLS robustness axis.

### Pillar III — AXIOLOGICAL (value · law · beauty)
- **A-1 `aesthetics.py`** *(new build — the genuine gap)* — Elegance (compression/MDL
  saturation), Symmetry (Menger map), Resonance (Lyapunov stability) → an Aesthetic
  Score, built entirely on metrics Chiron + UMA already produce. Headline new capability.
- **A-2 Jurisprudence suite** (the "whole legal suite"):
  - `cross_examine.py` — adversarial: search the residual for an alternative generator
    ("reasonable doubt") via `RedTeamAttack` / `HallucinationDefeat`; survival raises certainty.
  - `stare_decisis.py` — precedent: hash each `govern()` decision into a Merkle
    `DoctrineLedger`; acting against precedent demands a higher confidence threshold.
  - `jurisdiction.py` — boundary conditions: per-domain SoCPM threshold T + variable
    weights (medical ≠ financial ≠ military ≠ creative) via `SoCPMProgram` / `CertifyConfig`.
- **A-3 `ontological.py`** — V-Units + Harmony — **already built** last pass; suite member.

### Pillar IV — DISCERNMENT (the through-line you affirmed)
- **D-1 `candor_bridge.py`** — bridge `Candor` to audit any `human_report` / explanation
  for condescension, unearned confidence, evasion, opacity. "Explanation before assertion."
- **D-2 `discernment.py`** *(capstone, last)* — the "independent witnesses": run a finding
  through Epistemic (collapse), Ontological (UMA robustness + holographic recovery),
  Axiological (govern + aesthetics + ontological), and Candor; **confidence = convergence,
  not authority.** Realizes the discernment-engine philosophy as one callable.

### Reference / lineage (no code — wire into the literature)
- **HCT theory** (`JDICert/HOLOGRAPHIC_CONTINUITY_THEORY.md`) → cite as the substrate theory.
- **PIH** (Projection–Innovation Hierarchy) → the rigorous variational backbone of the
  §7 action principle (MSR doubling); cite as the math lineage, don't bridge.
- **Calculus series I–V + Compendium** → the epistemological/ontological/axiological
  prose foundation (HCT is the sixth); cite in a `LITERATURE.md`.
- **Governance PDFs**, **`transcribe_final.py`** → source / intentionally standalone; leave.

---

## 4. Guardrails (unchanged, restated)

- `chiron.py` stays **byte-unchanged**; `cert_engine.py` is **bridged, never merged**.
- Every bridge mirrored to `Chiron/` **and** `Chiron-Refined/`; `ARCHITECTURE.md` rows added.
- **Do not** edit Merkle-sealed memory JSON. `AUTHOR_SIGNATURE` untouched.
- All shell commands delivered **comment-free** (your zsh has `interactive_comments` off).
- Dual civilian/contractor framing for every new capability (extend `FRAMING.md`).
- Per-phase verification; a **subagent** verification for the D-2 capstone.

---

## 5. Suggested order (if you say "all")

1. **A-1 `aesthetics.py`** — closes the one true axiological gap; cheap, high-signal, pure additive.
2. **E-1 + E-2** — the operator calculus + projection stack (the heart of what you said was un-added).
3. **O-1 + O-2 + O-3** — significance geometry, density-emotion, holographic recovery.
4. **A-2 jurisprudence suite** — cross-examine, stare decisis, jurisdiction.
5. **D-1 candor bridge**, then **E-3 / literature docs**.
6. **D-2 `discernment.py`** capstone + full verification (subagent).

Reviewable, reversible, and green at every step. Tell me to take all of it in this
order, a subset, or adjust the plan — and I'll start at the top and bring you each one
verified.
