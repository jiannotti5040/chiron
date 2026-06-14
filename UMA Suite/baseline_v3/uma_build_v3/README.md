# UMA — Universal Manifold Architecture

UMA is a stochastic metriplectic field engine. The package implements
a unified-systems theory in which a sphere-grounded acoustic geometry,
a GENERIC field-theoretic dynamics, an MSR–GR bridge, and a semantic
production engine compile into a single closed substrate.

This is a v3 build of the package, merged and verified end-to-end.

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

calibrate.py             -- 50-trajectory closure-threshold calibrator
examples/run_pipeline.py
examples/sphere_uma_execution.py
tests/test_sanity.py     -- 11 sanity tests
tests/test_semantic.py   -- ~19 semantic-engine tests

docs/
  THEORY_unified_synthesis.md
  THEORY_variable_list.md
  THEORY_biggest_advance.md
  THEORY_sphere_derivation.md

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

30 tests pass (11 sanity + 19 semantic).

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
