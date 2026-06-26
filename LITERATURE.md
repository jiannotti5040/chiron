# Literature — the theory behind the engines

*The conceptual lineage of this vault, and where each piece is realized in running code. All
are author-developed drafts, not peer-reviewed; the code is the part that is tested.*

---

## The theory line

| Work | What it is | Realized in code |
|---|---|---|
| **Holographic Continuity Theory (HCT)** (`JDICert/HOLOGRAPHIC_CONTINUITY_THEORY.md`) | The central proposition: identity persists under transformation via distributed-redundancy operators, with provenance conserved. 12 axioms, 8 theorems, the `Proc` base category. | `JDICert/cert_engine.py` (280 tests); bridged into Chiron via `projection_stack.py`, `significance.py`, `density_emotion.py`, `holographic.py`, `operator_calculus.py` |
| **The Projection Calculus** (HCT's formal apparatus) | The operator algebra: projection, recovery, curvature, conservation across substrates. | `OPERATOR_CALCULUS.md` (notation) + the bridges above |
| **The Projection–Innovation Hierarchy (PIH)** (`Individual Programs/PIH_*.md`) | A covariant, renormalized variational field theory (iterated Martin-Siggia-Rose doubling) — the rigorous backbone of HCT's action principle. | Reference/lineage; the variational principle behind the UMA dynamics in `chiron.py` |
| **The Calculus series, Books I–V + Compendium** (`Ontological & Philosophical Books/`) | Truth & Consciousness, Becoming, Transcendence, Creation, Value — the epistemological / ontological / axiological foundation. HCT is the sixth in the series. | The philosophical substrate; `ontological.py` (V-Units, Harmony) operationalizes Book V (Value) |
| **A Standard of Care for Persuasive Machines** + **LexGuard** (`Governance/`) | The duty-of-care / SoCPM decision rule and the four-gate governance frame. | `chiron.py` (SoCPM, LexGuard), `govern.py`, `jurisdiction.py`, `stare_decisis.py` |

## The Tripartite Machine

The engines organize as three pillars communicating through bridges, under one discipline
(abstain-or-prove). This is a **discernment engine**, not a new mathematics.

- **Epistemology** — extraction: `chiron.py` (collapse), `operator_calculus.py`, `language.py`.
- **Ontology** — physics / simulation: `uma_bridge.py`, `significance.py`, `density_emotion.py`, `holographic.py`.
- **Axiology** — value, law, beauty: `ontological.py` (value), `aesthetics.py` (beauty),
  `govern.py` / `cross_examine.py` / `stare_decisis.py` / `jurisdiction.py` (law).
- **Discernment** — the through-line: `candor_bridge.py` (honesty) and `discernment.py`
  (independent witnesses, confidence by convergence).

## Honest status

Every theory document here is a **self-developed draft, not peer-reviewed**. The reference
implementation (`cert_engine.py`) passes its own 280-test suite; the Chiron bridges are
proof-of-concept couplings, framed as such. Where a claim is physics-grade it is labeled a
*tested crucible*, not confirmed physics — see `UMA Suite/.../PROOF_AND_FALSIFICATION_CHECKPOINTS.md`.
The strongest, most defensible artifact remains the exact-recovery engine and its zero-false-
positive benchmark; the theory is the scaffolding around it.
