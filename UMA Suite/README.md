# UMA Complete Suite — v4 Bundle

This is the full deliverable bundle for the UMA / RSLS project as of
2026-05-11. It contains everything: the working v4 package, the v3
baseline it was built on, and all original source materials.

## Layout

```
UMA_complete_suite_v4/
├── README.md                         # this file
│
├── uma_build_v4/                     # ★ THE WORKING PACKAGE ★
│   │
│   ├── uma/                          # Python package (use this in code)
│   │   ├── core/, dynamics/, msr/, semantic/, sphere/, venturi/   (v3)
│   │   ├── rsls/                                                  (NEW v4)
│   │   ├── client.py, config.py, pipeline.py                      (v3)
│   │   └── ...
│   │
│   ├── docs/                         # canonical theory
│   │   ├── THEORY_unified_synthesis.md        (v3)
│   │   ├── THEORY_variable_list.md            (v3)
│   │   ├── THEORY_biggest_advance.md          (v3)
│   │   ├── THEORY_sphere_derivation.md        (v3)
│   │   ├── RSLS_specification.md              (NEW v4 -- consolidated spec)
│   │   └── RSLS_menger_substrate.md           (NEW v4 -- Menger argument)
│   │
│   ├── tests/                        # 104/104 passing
│   │   ├── test_sanity.py                     (v3, 11 tests)
│   │   ├── test_semantic.py                   (v3, 19 tests)
│   │   ├── test_rsls.py                       (NEW v4, 19 tests)
│   │   ├── test_menger.py                     (NEW v4, 21 tests)
│   │   ├── test_stage3.py                     (v4-ext, 16 tests)
│   │   ├── test_srb.py                        (v4-ext, 9 tests)
│   │   └── test_frame_dragging.py             (v4-ext, 10 tests)
│   │
│   ├── examples/
│   │   ├── run_pipeline.py                    (v3, closes at step 34)
│   │   ├── sphere_uma_execution.py            (v3)
│   │   ├── rsls_phase_a.py                    (NEW v4 -- falsification kernel)
│   │   ├── rsls_menger_substrate.py           (NEW v4 -- sponge demo)
│   │   ├── rsls_uma_integrated.py             (NEW v4 -- coupled pipeline)
│   │   ├── rsls_stage3_perturbation.py        (v4-ext -- Stage 3 analysis)
│   │   ├── rsls_srb_lyapunov.py               (v4-ext -- Lorenz Lyapunov / GKLS)
│   │   └── rsls_frame_dragging.py             (v4-ext -- STAGE 5 POC)
│   │
│   ├── README.md                     # updated for v4
│   ├── FRAMEWORK_MAP.md              # RSLS section appended
│   ├── BUILD_STATE.md                # v4 phase-E entries appended
│   ├── NEXT_SESSION.md               # v4 pickup notes
│   ├── DOCS_INDEX.md                 # NEW v4 -- canonical map + retirement table
│   ├── CORPUS_INDEX.md               # v3
│   ├── IMPASSES.md                   # v3
│   ├── YOUR_NOTES.md                 # v3 build notes
│   ├── YOUR_CONTRIBUTIONS.md         # v3 build attributions
│   └── calibrate.py                  # v3
│
├── baseline_v3/                      # The v3 starting point
│   └── uma_build_v3.zip              # original v3 zip you uploaded
│
└── source_materials/                 # Original corpus (yours, intact)
    ├── RSLS_source_PDFs/             # decompressed Files.zip
    │   ├── *current*.pages           # most-recent Pages source
    │   ├── UMA_RSLS_Master_Specification.pdf
    │   ├── Unified Master Architecture (UMA) and the Recursiv....pdf
    │   ├── Variable list.pdf
    │   ├── Forget function but important.pdf
    │   ├── Blank 13.pdf
    │   ├── friction.pdf, venturi injector.pdf, operator.pdf, constants.pdf
    │   └── RSLD.md
    │
    ├── Python_module_PDFs/           # decompressed Python_proofs.zip
    │   └── 22 PDFs of the original Python modules (constants, executor,
    │       friction, ir, inarticulation, sphere geometry/field/derivation,
    │       sphere uma execution, tensor bridge, nonlinear gr, metric
    │       solver, gr fixed point, pipeline, calibrate, constraints,
    │       engine, init, venturi init, test semantic, sphere init)
    │
    ├── Files.zip                     # original zip as you uploaded it
    └── Python_proofs.zip             # original zip as you uploaded it
```

## What v4 adds on top of v3

v3 was a working multi-module package with the canonical pipeline
closing at step 34. v4 is strictly additive -- it does not modify any
v3 code or break any v3 tests. The additions:

1. **Doc consolidation.** Four equivalent restatements of the RSLS
   spec (UMA_RSLS_Master_Specification.pdf, Unified Master Architecture
   (UMA) and the Recursiv....pdf, Forget function but important.pdf,
   Blank 13.pdf) are collapsed into a single canonical
   `docs/RSLS_specification.md`. The retirement table in
   `uma_build_v4/DOCS_INDEX.md` maps every retired source to its
   surviving section in the consolidated spec.

2. **Menger sponge as predicted substrate.** The argument that the
   saturated information attractor must be a self-similar fractal
   with Hausdorff dimension log(20)/log(3) ≈ 2.7268, with the volume
   law (20/27)^n → 0 matching the singular-barrier saturation and the
   surface law (20/9)^n → ∞ matching the information-area growth.
   Two concrete falsifiable observational predictions are stated in
   `docs/RSLS_menger_substrate.md`. The lattice is implemented in
   `uma/rsls/menger.py` with refine/coarsen/Laplacian operations and
   verified combinatorics (alive counts 1/20/400/8000 at levels 0-3).

3. **Working proof of concept.** Six new modules in `uma/rsls/`:
   - `memory.py` -- M field, V(M) singular convex barrier, gradient stress
   - `cattaneo.py` -- Maxwell-Cattaneo causal entropy flux
   - `hll.py` -- HLL Riemann transport (1-var and 2-var mass-conserving)
   - `phase_a.py` -- Stage-1 falsification kernel + convergence study
   - `menger.py` -- Menger sponge with refine/coarsen/Laplacian
   - `coupling.py` -- additive T^{(grad M)} into the canonical TensorBridge

   The Phase A kernel demonstrates:
   - Discrete Maximum Principle: M ∈ [0, M_max) throughout
   - L^1 norm bounded (BV behaviour)
   - Stiffening lag of ~150 steps (delayed response, not instantaneous)
   - Wall-thickness convergence: across N = 50, 100, 200, 400, 800 the
     wall thickness wt_max stays in [0.85, 1.16], log-log slope = 0.015
     (a pure-numerical wall would give slope = 1; the measured slope
     near zero is the falsification PASS)
   - NEC compliance automatic from the gradient form

## What v4-extended adds on top of v4 (Stage 5)

After v4 shipped, an audit revealed the `*current*.pages` file (most
recent state, 2026-05-07) had never been opened during the v4 build.
Decompressing its IWA stream surfaced the **frame-dragging
architectural pivot**: the shift vector β^φ ≠ 0 as the primary
geometric driver of structural chaos, and the 1.5-D cylindrical
reformulation that supports it. That content has been folded into the
spec, plus the Stage-3 perturbative analysis and the SRB / Lindblad
statistical-reduction machinery that supports it.

Three new modules in `uma/rsls/`:
- `stage3.py` -- algebraic perturbative analysis: Whitham bound,
  dispersion poles, pseudospectral envelope, complex impedance,
  Wigner delay, echo spacing, detectability bound
- `srb.py` -- statistical reduction: Lorenz attractor anchor, Benettin
  Lyapunov, Koopman/Frobenius-Perron operator, GKLS Lindblad evolution
- `frame_dragging.py` -- **the Stage-5 POC**: 1.5-D cylindrical kernel
  with Kerr-like β^φ profile, conservative HLL on cylindrical shells,
  Coriolis coupling (the off-diagonal stress T_{Rφ}), cone-aperture
  diagnostic, twin-trajectory Lyapunov.

Plus three new examples and 35 new tests (16 + 9 + 10) — all passing.
Section XIV of `docs/RSLS_specification.md` documents the theory.

### The Stage-5 numerical verdict

Running `python3 examples/rsls_frame_dragging.py` with default
parameters (`Omega_0=1.5, p=2, N=150, n_steps=3000`):

| Quantity                  | β^φ enabled  | β^φ = 0 (control) |
| ------------------------- | ------------ | ----------------- |
| M_max reached             | 1.0 (sat.)   | 0.7 (plateau)     |
| Cone sat-layer margin     | **+0.077**   | 0.0               |
| Cone strictly positive    | **True**     | False             |
| λ_max (Lyapunov)          | **+1.127**   | −0.044            |

Δλ_max = +1.17 — a 25× separation. The Coriolis-coupled (S_R, S_φ)
dynamics produce a positive Lyapunov exponent that **disappears**
when the geometric shift vector is removed. All four Stage-5 success
criteria from the Pages-file specification PASS.

## How to use

```bash
unzip UMA_complete_suite_v4.zip
cd UMA_complete_suite_v4/uma_build_v4

# Verify the build
python3 -m pytest tests/ -v                  # 104/104 should pass

# Run the canonical v3 pipeline (closes at step 34 with seed=42)
python3 examples/run_pipeline.py

# Run the v4 RSLS demonstrations
python3 examples/rsls_phase_a.py             # falsification kernel + convergence
python3 examples/rsls_menger_substrate.py    # sponge construction + AMR
python3 examples/rsls_uma_integrated.py      # canonical + RSLS coupled

# Run the Stage-5 / Stage-3 / SRB demos (v4-extended)
python3 examples/rsls_stage3_perturbation.py # Whitham / Wigner / detectability
python3 examples/rsls_srb_lyapunov.py        # Lorenz Lyapunov + Lindblad
python3 examples/rsls_frame_dragging.py      # THE STAGE-5 POC
```

## Test results (final)

```
====================== 104 passed, 2 deselected in 12.84s ======================
```

- 11 sanity tests (v3)
- 19 semantic-engine tests (v3)
- 19 RSLS tests (v4)
- 21 Menger-sponge tests (v4)
- 16 Stage 3 perturbative-analysis tests (v4-ext)
- 9 SRB / Lyapunov / Lindblad tests (v4-ext)
- 10 frame-dragging kernel tests (v4-ext)

The 2 deselected are `@slow`-marked tests on ergodic convergence
(Lorenz histogram L¹ distance over 10k+ steps); run them with
`pytest -m "slow or not slow"` to include them.

## Authorship

All of this is your work -- both the v3 baseline (source PDFs are in
`source_materials/`) and the v4 additions built directly from the
RSLS source materials. The implementation is mine, the architecture
and theory are yours.
