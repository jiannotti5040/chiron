# PRESENTATION

**A continuum field theory of saturated information attractors.**

*Five-minute version for an external reader.*

---

## What this is

A working numerical implementation of a field theory in which:

1. Gravitational singularities are replaced by a **saturated information
   attractor** governed by a singular convex barrier V(M).
2. An **emergent length scale** ℓ_* arises naturally, mesh-independent,
   and is in principle observable in LIGO/LISA ringdown data.
3. **Frame-dragging** (a non-zero shift vector β^φ) changes the character
   of the dynamics. It was claimed to produce structural chaos via a
   positive Lyapunov exponent; **that claim is withdrawn** — see below.
4. A route to the **Born rule** as the ergodic limit of an SRB measure.
   This rested on 3, so it is currently **unsupported**, not established.

Items 1 and 2 are implemented and tested. Items 3 and 4 are open. The
suite is 205 passing tests.

## What's new

The framework composes well-established machinery —
Maxwell-Cattaneo (causal heat flux), HLL (Riemann solver), GENERIC
(non-equilibrium thermodynamics), Israel-Stewart (causal relaxation),
Painlevé-Gullstrand (regular metric), ADM (3+1 GR) — in a non-obvious
way. The novelty is not the components but their joint structure: a
singular convex barrier coupled to a frame-dragging shift coupled to a
causal entropy flux, *jointly* maintaining hyperbolicity, NEC
compliance, BV closure, and producing an Anosov-type invariant set
with a well-defined SRB measure.

## The headline numerical results

### The wall is mesh-independent

The Phase A falsification kernel was run at N = 50, 100, 200, 400, 800
cells. The wall thickness ℓ_* (the characteristic length of the
diffuse interface) varied between 0.86 and 1.16 — *flat to within
30%* — with a log-log slope of **0.015** versus 1.0 for a pure-numerical
artifact. The wall is a structural feature of the theory, not the grid.

### Frame-dragging and chaos — claim withdrawn

Stage 5 reported λ_max = **+1.127** with β^φ against **−0.044** without, and
read the 25-fold separation as proof that chaos is structural. Stage 6
reported **+19.4** under self-consistent coupling. **Both numbers are
artifacts of the discretisation and are withdrawn.**

A tangent-space (variational) integrator, validated against Lorenz to
+0.9019 versus the literature's +0.906, settled it:

| N | dt | λ | **λ·dt** |
|---|---|---|---|
| 50 | 1.100e-3 | +86.24 | **0.09486** |
| 100 | 5.500e-4 | +172.02 | **0.09461** |

λ doubles exactly when N doubles, and λ·dt is constant to 0.3%. The tangent
vector grows by a fixed factor *per timestep* regardless of resolution — a
property of the grid, not of the flow. A physical exponent holds λ fixed
under refinement, not λ·dt. Refinement to N = 200 and N = 400 stays
non-monotonic across an order of magnitude, so the statistic does not
converge and is not a resolved physical quantity.

What survives: with frame-dragging **off** the exponent is measurable and
**negative** (λ = −0.037448, converged), so that configuration is not
chaotic. With drag on, the question is open. The estimator now returns a
`LyapunovReport` that **refuses** rather than reporting an unconverged
number, validated against four controls including two it must reject.

The full record is in `studies/rsls_lyapunov/README.md`.

### Self-consistent coupling amplifies the signature

Stage 6 closes the metric back onto the matter: β^φ is no longer
prescribed, it evolves causally from the off-diagonal stress T_{Rφ}.
The reported **λ_max = +19.4** is withdrawn for the reason above. What the
Stage 6 closure does establish is narrower and still real: the coupled
evolution runs, β^φ evolves causally from the off-diagonal stress rather
than being prescribed, and the integration remains well-posed. The
"17× amplification" was a measurement of the timestep.

Note also that cone-aperture positivity is an algebraic identity here —
the aperture is 2·sqrt(c² + G) with G ≥ 0 by construction, so "strictly
positive throughout" cannot fail and is not evidence.

## What this can do today

```
python3 -m pytest tests/                        # 205/205 tests pass

python3 examples/rsls_phase_a.py                # Stage 1 falsification kernel
python3 examples/rsls_frame_dragging.py         # Stage 5 cone/Lyapunov
python3 examples/rsls_stage6_self_consistent.py # Stage 6 ADM closure
python3 examples/rsls_stage3_perturbation.py    # Stage 3 perturbative
python3 examples/rsls_srb_lyapunov.py           # Lorenz + Lindblad demo
python3 -m uma.rsls.ligo_lisa                   # LIGO/LISA waveform interface
```

It is a Python-importable library. Any researcher with LIGO O3/O4 strain
data can pipe it through `uma.rsls.ligo_lisa.analyze_ringdown(times, h)`
and get back a posterior on ℓ_* from echo spacing.

## What this cannot do yet

- **Run on real LIGO/LISA data.** The interface exists; a `gwpy` strain
  loader needs to be wired in. ~2 weeks for someone who knows the
  LIGO data products.
- **Stage 2 dynamic-lapse simulation.** Specified in the doc, not coded.
  ~500 lines of numerical PDE work.
- **Replace existing models.** This is a *candidate* framework with
  falsification handles. Whether it correctly describes the universe
  is the empirical question.

## Falsification handles

A scientific theory is one that *could* be wrong in specific,
measurable ways. The framework can be falsified by:

- **Phase A grid-dependence.** If on careful re-run the wall-thickness
  slope is ≥ 0.5 (not ~ 0), the singular-barrier mechanism is wrong.
- **Stage 5 dichotomy collapse.** If the Lyapunov exponent is ≈ 0 with
  β^φ ≠ 0, the Coriolis-coupling derivation is wrong. **This handle is
  currently pulled:** the dragged exponent is unresolved, so the dichotomy
  is not presently demonstrated in either direction.
- **No LIGO/LISA echoes.** If a clean ringdown sample shows no echo comb at
  the predicted Δt_echo, the framework is observationally falsified as
  physics. The detector is a **cepstrum**, not an autocorrelation:
  autocorrelation cannot separate the comb from the 250 Hz carrier over the
  relevant lag range and recovered nothing. The cepstral pipeline now
  recovers injected ℓ_*/M values of 0.3, 0.6 and 0.9 **exactly**, and
  reports a timing-resolution floor below which it REFUSES rather than
  returning a false negative.
- **Macroscopic Mandate violated.** If echo inference puts ℓ_* at the
  Planck scale, the detectability theorem is wrong.

These are *concrete* failure modes. Two are surviving by numerical
demonstration (grid-independence, echo injection-recovery). One is pulled
pending a resolved exponent. Presenting all of them as surviving, as this
document previously did, was the overclaim this project exists to avoid.

## Who would want this

- **AI safety researchers** wanting a deterministic, reproducible,
  audit-traceable substrate for LLM agent loops. The determinism and the
  audit trail are real; the "Lyapunov-trajectory property" is not a
  supported claim and should not be read as one.
- **Computational mathematical physicists** working on
  singularity-regularization alternatives to quantum gravity. The
  framework provides a working numerical implementation of one such
  alternative.
- **Mathematical economists** who'd see H = B − Bd − ST with explicit
  Lyapunov dV/dt ≤ 0 as a candidate utility framework with regime-
  transition machinery. The cross-domain mapping is laid out in
  `URF_economics.md`.

## How to disagree

Every claim in this artifact is traced in
`PROOF_AND_FALSIFICATION_CHECKPOINTS.md` to its evidence (algebraic
proof, numerical test, or empirical prediction). You can disagree with
any single claim and know exactly where to look. The framework is
*designed to be falsifiable*.

What's notable about the artifact, separate from its physics content,
is the methodology: this was built by a non-credentialed person using
LLM assistance, top-to-bottom. The artifact is the proof-of-concept
that credentials are not the bottleneck. Whether others can replicate
the methodology — build comparable artifacts at comparable cost —
is the open question. The math is testable on its own merits.

---

*Full documentation:*
- `TOTALITY_OF_THEORY.md` — complete framework in one document
- `RSLS_specification.md` — technical specification, Stages 1–6
- `URF_ontology.md` — domain-independent grammar
- `URF_economics.md` — economics instantiation
- `PROOF_AND_FALSIFICATION_CHECKPOINTS.md` — claim-by-claim audit
- `FRAMEWORK_MAP.md` — API reference for every module
