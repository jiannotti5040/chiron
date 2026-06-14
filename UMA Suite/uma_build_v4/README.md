# UMA — Universal Manifold Architecture

UMA is a stochastic metriplectic field engine. The package implements
a unified-systems theory in which a sphere-grounded acoustic geometry,
a GENERIC field-theoretic dynamics, an MSR–GR bridge, and a semantic
production engine compile into a single closed substrate.

This is a **v4 build** of the package: v3's verified pipeline plus the
RSLS (Recursive Symbiotic Logic System) subpackage — a field-theoretic
memory sector with a singular convex barrier, Maxwell-Cattaneo causal
flux, HLL Riemann transport, and a Menger-sponge AMR substrate.

## What changed in v4

v3 (the canonical pipeline) is untouched. v4 adds:

- `uma/rsls/` — six new modules: `memory.py`, `cattaneo.py`, `hll.py`,
  `phase_a.py`, `menger.py`, `coupling.py` (and `__init__.py`).
- `docs/RSLS_specification.md` — single consolidated RSLS specification
  (replaces four equivalent restatements that had accumulated).
- `docs/RSLS_menger_substrate.md` — structural argument for the
  Menger sponge as the AMR lattice for saturated information attractors.
- `examples/rsls_phase_a.py` — falsification-kernel demonstration
  (HLL + Cattaneo + V(M) on a punctured spherical grid; convergence
  study at N = 50..800).
- `examples/rsls_menger_substrate.py` — sponge construction, graph
  Laplacian, and |grad M|-triggered AMR.
- `examples/rsls_uma_integrated.py` — canonical pipeline + additive
  RSLS T^{(grad M)} coupling demo.
- `tests/test_rsls.py` (19 tests) and `tests/test_menger.py` (21 tests).

All 30 existing v3 tests still pass; the total is now **70/70 green**.

The canonical pipeline (`examples/run_pipeline.py`) closes at the same
deterministic step as in v3 (step 34 with seed=42).

## What changed in v4-extended (Stage 5)

After v4 shipped, an audit of the source materials surfaced the
**frame-dragging architectural pivot** from the most recent state of
the RSLS specification (the `*current*.pages` file dated 2026-05-07).
That content was folded in, plus the perturbative spectral analysis
and the statistical-reduction machinery to support it:

- `docs/RSLS_specification.md` — extended with **Section XIV: Stage 5 —
  Frame-Dragging Closure** (cone aperture, off-diagonal stress, Anosov-
  GKLS bridge, success and falsification criteria).
- `uma/rsls/stage3.py` — algebraic Stage-3 perturbative analysis:
  Whitham subcharacteristic, dispersion poles, pseudospectral envelope,
  complex impedance, Wigner time delay, echo spacing, detectability
  bound.
- `uma/rsls/srb.py` — statistical reduction machinery (Lorenz attractor
  as anchor, Benettin Lyapunov, SRB histograms, Koopman/Frobenius-
  Perron operator, GKLS / Lindblad amplitude damping).
- `uma/rsls/frame_dragging.py` — **the 1.5-D cylindrical frame-
  dragging kernel** with Kerr-like β^φ profile, conservative HLL on
  cylindrical shells, Coriolis coupling (the off-diagonal stress
  T_{Rφ}), cone-aperture diagnostic, twin-trajectory Lyapunov.
- `examples/rsls_stage3_perturbation.py`, `examples/rsls_srb_lyapunov.py`,
  `examples/rsls_frame_dragging.py`.
- `tests/test_stage3.py` (16), `tests/test_srb.py` (9), and
  `tests/test_frame_dragging.py` (10). All pass; total now
  **104/104 green** (2 slow ergodic-convergence tests deselected by
  default).

### The Stage-5 numerical verdict

The frame-dragging kernel runs twice (with and without β^φ) and reports
the side-by-side dichotomy. With default parameters
(`Omega_0=1.5, p=2, N=150, n_steps=3000`):

| Quantity                  | β^φ enabled  | β^φ = 0 (control) |
| ------------------------- | ------------ | ----------------- |
| M_max reached             | 1.0 (sat.)   | 0.7 (plateau)     |
| Cone sat-layer margin     | **+0.077**   | 0.0               |
| Cone strictly positive    | **True**     | False             |
| λ_max (Lyapunov)          | **+1.127**   | −0.044            |

Δλ = +1.17, ≈ 25× separation. The Coriolis-coupled (S_R, S_φ)
dynamics produce a positive Lyapunov exponent that **disappears**
when the geometric shift vector is removed — exactly what the Pages-
file Stage-5 success criteria predicted.

To run it yourself:

```
python examples/rsls_frame_dragging.py
```

The Stage-5 kernel uses a *prescribed* β^φ (static Kerr-like profile).
A fully self-consistent coupling — letting β^φ evolve from the ADM
momentum constraint — is the next architectural step ("Stage 6").

## What's in here

```
uma/
  config.py              -- GridConfig, GENERICConfig, FilterConfig, Config
  client.py              -- UMAClient (deterministic kernel)
  pipeline.py            -- UMAPipeline (15-module integrator)

  core/
    projection.py        -- FieldProjection (band-limited mode projection)
    state.py             -- FieldPosterior (Gaussian on z)
    filter.py            -- KalmanFilter (Joseph form)

  observations/
    base.py              -- Observation, GaussianObservation

  dynamics/
    generic.py           -- GENERICDynamics, hamiltonian, entropy_S,
                            msr_response, dH_dpsi_conj

  sphere/
    geometry.py          -- AcousticSphereGeometry, SphericalMode,
                            spherical Bessel zeros (j_{0,1} = pi exact)
    field.py             -- SphereProjectionField, SpherePendulum,
                            SphereVenturi  (sphere is the projection medium)

  venturi/
    operator.py          -- Venturi / VenturiOperator (Silver-grounded
                            360-degree azimuthal injection)
    injector.py          -- CrossDomainInjector (psi + psi_hat in lockstep)

  msr/
    tensor_bridge.py     -- TensorBridge: live <T> <-> G^(1) tracker
    stress_energy.py     -- Noether T_munu + Lichnerowicz consistency
    wetterich_flow.py    -- Levy-vs-Gaussian basin classifier
    nonlinear_gr.py      -- NonlinearEinsteinSolver (full curvature)
    metric_solver.py     -- IterativeMetricSolver (self-consistent g)
    gr_fixed_point.py    -- GRFixedPointSearch (psi*)

  semantic/
    constants.py         -- Silver Ratio constants + calibrated thresholds
    ir.py                -- UMA_IR + IRNode
    friction.py          -- SemanticFriction (dH/dt accumulator)
    constraints.py       -- Alpha (dIse) / Beta (V:[H) / Gamma (Jd$m4)
    inarticulation.py    -- ProductionMetrics + classify_stage
    executor.py          -- UMAExecutor (drives UMAClient)
    engine.py            -- SemanticEngine + Engine3 string bridge

  rsls/                  -- v4 RSLS subpackage (new)
    memory.py            -- M field, V(M) singular convex barrier,
                            gradient stress T^{(grad M)}, NEC check
    cattaneo.py          -- Maxwell-Cattaneo entropy flux J_mu (causal)
    hll.py               -- HLL Riemann solver (1- and 2-variable)
    phase_a.py           -- Stage 1 falsification kernel + convergence study
    menger.py            -- MengerSponge lattice (refine/coarsen/Laplacian)
    coupling.py          -- RSLSCoupling: additive T^{(grad M)} into TensorBridge
    stage3.py            -- Stage 3 perturbative analysis (v4-ext)
                            Whitham bound, dispersion poles,
                            pseudospectral envelope, reflection
                            coefficient, Wigner delay, detectability
    srb.py               -- statistical reduction (v4-ext)
                            Lorenz Lyapunov, Koopman/transfer matrix,
                            GKLS / Lindblad, Born-rule match
    frame_dragging.py    -- Stage 5 / 1.5-D cylindrical kernel (v4-ext)
                            Kerr-like beta^phi, conservative HLL on
                            cylindrical shells, Coriolis coupling,
                            cone aperture, twin-trajectory Lyapunov

calibrate.py             -- 50-trajectory closure-threshold calibrator
examples/run_pipeline.py
examples/sphere_uma_execution.py
examples/rsls_phase_a.py            -- v4
examples/rsls_menger_substrate.py   -- v4
examples/rsls_uma_integrated.py     -- v4
examples/rsls_stage3_perturbation.py    -- v4-ext
examples/rsls_srb_lyapunov.py           -- v4-ext
examples/rsls_frame_dragging.py         -- v4-ext  (THE STAGE-5 POC)
tests/test_sanity.py     -- 11 sanity tests
tests/test_semantic.py   -- 19 semantic-engine tests
tests/test_rsls.py       -- 19 RSLS tests (v4)
tests/test_menger.py     -- 21 Menger-sponge tests (v4)
tests/test_stage3.py     -- 16 Stage 3 tests (v4-ext)
tests/test_srb.py        -- 9 SRB tests (v4-ext; 2 marked @slow)
tests/test_frame_dragging.py -- 10 frame-dragging tests (v4-ext)

docs/
  THEORY_unified_synthesis.md
  THEORY_variable_list.md
  THEORY_biggest_advance.md
  THEORY_sphere_derivation.md
  RSLS_specification.md             -- v4
  RSLS_menger_substrate.md          -- v4

DOCS_INDEX.md                       -- v4 canonical map + retirement table
FRAMEWORK_MAP.md
BUILD_STATE.md
YOUR_NOTES.md
YOUR_CONTRIBUTIONS.md
NEXT_SESSION.md
IMPASSES.md
```

## Quickstart

```bash
pip install numpy scipy pytest
python3 examples/run_pipeline.py
```

Expected output: closure (Omega) on or before step ~80 with the default
seed=42, friction collapsing to 0, Einstein bridge satisfied via the
TensorBridge residual.

## Tests

```bash
python3 -m pytest tests/ -v
```

104 tests pass (2 marked `@slow` are deselected by default):
- 11 sanity tests (v3)
- 19 semantic-engine tests (v3)
- 19 RSLS tests (v4)
- 21 Menger-sponge tests (v4)
- 16 Stage-3 perturbative-analysis tests (v4-ext)
- 9 SRB / Lyapunov / Lindblad tests (v4-ext)
- 10 frame-dragging kernel tests (v4-ext)

To include the slow tests (ergodic convergence on Lorenz, ~3s extra):
```bash
python3 -m pytest tests/ -v -m "slow or not slow"
```

## The RSLS sector (v4)

The RSLS subpackage is a self-contained field engine. Run the Phase A
falsification demo:

```bash
python3 examples/rsls_phase_a.py
```

Expected behaviour:
- Discrete Maximum Principle: `0 <= M < M_max` throughout
- L^1(M) bounded (BV property)
- Stiffening lags compression by ~150 steps (delayed response)
- Wall thickness converges to a constant as `dr -> 0`:
  log-log slope of `wt(dr)` is essentially zero (~0.01)
- NEC compliance: `T^{(grad M)}_{mu nu} k^mu k^nu >= 0` automatic

Run the Menger substrate demo:

```bash
python3 examples/rsls_menger_substrate.py
```

Expected: correct cell counts (1, 20, 400, 8000), correct volume scaling
`(20/27)^n`, correct surface scaling `(20/9)^n`, Hausdorff dimension
`log(20)/log(3) ≈ 2.7268`, working refine/coarsen/Laplacian.

Run the integrated coupling demo:

```bash
python3 examples/rsls_uma_integrated.py
```

Expected: canonical pipeline closes at step 34 (unchanged from v3);
RSLS `T^{(grad M)}` adds additively; NEC compliance verified.

## Calibration

`calibrate.py` runs 50 GENERIC trajectories of 3000 steps each, dumps
H_target / dH_dt_floor / field_scale that you can paste into
`SemanticFrictionConfig`. The values currently in
`uma/semantic/constants.py` are the result of one such run.

## Theory pointers

The four `docs/THEORY_*.md` files are the canonical theoretical
documents. Read them in this order:

1. `THEORY_sphere_derivation.md` — why the geometry is locked to
   Bessel zeros and nothing is tuned.
2. `THEORY_variable_list.md` — definitions of every symbol used in
   the codebase.
3. `THEORY_unified_synthesis.md` — full synthesis: GENERIC + MSR + GR
   + semantic closure as one structure.
4. `THEORY_biggest_advance.md` — the sharpest result: friction == 0
   and Einstein residual -> 0 are the same physical event.

## Key invariants

- `j_{0,1} = pi` to 1e-10 (geometry self-locks).
- `1/delta_S^2 = 3 - 2 sqrt(2)` is preserved as a text-encoding
  *design choice*, not a physics constant. The retraction note is
  inline at the top of `uma/semantic/constants.py`.
- Closure (Omega) is declared when `friction < 0.15` AND
  `|dH/dt| < CALIBRATED_DH_DT_FLOOR` AND TensorBridge residual is
  satisfied — the same physical event measured three ways.
