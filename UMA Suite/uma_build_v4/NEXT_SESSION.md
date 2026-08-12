# NEXT_SESSION.md

How to pick this build up cleanly in a future session.

---

## CURRENT STATUS — 2026-08-11 (read this first)

`PYTHONPATH=. python3.12 -m pytest tests -q` → **197 passed, 1 skipped, 0 failed.**
(The "70/70" further down is from v4's first session and is long stale.)
Use Python 3.12: `/opt/homebrew/opt/python@3.12/bin/python3.12`. The default
`python3` on this machine is 3.14 without pytest.

**Three claims were withdrawn and one capability was added.**

Withdrawn — each was asserted by a passing test that measured an artifact:

1. **Stage 6 positive Lyapunov** ("chaos survives geometric back-reaction").
2. **Stage 5 positive Lyapunov** and the ">0.3 drag/no-drag differential".
   Both statistics fail convergence, perturbation-size independence, and
   single-event dominance; one block of 72 carried 82% of the Stage-5 sum
   while the median block contracted. Three estimator bugs were fixed and
   none rescued it. `uma/rsls/lyapunov.py` now REFUSES, and the refusal is
   validated against Lorenz (+0.9032 vs literature +0.906) and a pure decay
   (−0.5000 exactly) so it is discriminating, not blanket.
   The one surviving measurement: **drag OFF converges to λ = −0.037448**,
   i.e. measurably not chaotic. With drag it is unresolved.
3. **`docs/BSD_REPORT.md`'s originality claims** — "every published Sha_an is
   a rounded float quotient" and "first procedure capable of returning no".
   Refuted by demonstration, not citation: `studies/exact_rank0_sha/` computes
   the report's own rank-0 battery in exact rationals from modular symbols
   (11.a2→1, 15.a1→1, 37.b1→1, 571.b1→4), no float anywhere. Corrections are
   inline in the report with dated notes.

Added — `studies/rank2_389a1/`, the rank-2 vertical slice the audit called for:
analytic rank proved exactly 2, **Mordell–Weil saturation proved per curve**
(Silverman C → exhaustive enumeration → μ → Hermite index bound →
`ellisdivisible` sieve), then a falsification sweep. The radius-14 box ran to
completion overnight: 10,092 candidates examined, **103 curves certified
end-to-end, conductors 389-11467, ZERO refutations**. See `RESULTS.md`; re-run
`summarize_results.py` after any further sweep to regenerate it.

Caveat stated in RESULTS.md and repeated here because it matters: every one of
the 103 answers is 1, so the sweep does not exercise the non-trivial-Sha path.
A bug forcing the quotient to 1 would produce exactly that table. Certifying a
rank-2 curve with Sha > 1 is the strongest missing test.
It caught a real unsaturated basis in the wild: PARI's descent points for
389.a1 span an index-3 sublattice (Reg 9× too big, quotient 1/9) and the
certificate refused rather than reporting it.

**Two kernel defects found and deliberately NOT fixed** (they change every
Stage-5/6 number, so they are your call, not a diagnostic's) —
`studies/rsls_lyapunov/`:

- `dt` is computed once from the initial state and violates CFL by ~550× once
  velocities grow; the solution is non-finite by step ~12951.
- With `dt` adaptive the density instead collapses to a finite-time vacuum
  (min D → 1e-6, v → 4e5) and the clock stalls at t ≈ 3.34. A density floor
  D ≥ 0.1 reaches t = 11 cleanly.

**Nothing is committed.** All of the above is in the working tree.

---

## Where things stand right now (v4)

- The package compiles end-to-end. Two top-level demonstrations work:
  - `python3 examples/run_pipeline.py` — canonical v3 pipeline, closure
    at step 34 with seed=42.
  - `python3 examples/rsls_phase_a.py` — Phase A falsification kernel,
    wall thickness convergence study, NEC verification.
- `python3 -m pytest tests/` shows **70/70 passing** (30 v3 + 40 v4).
- Marker files: README, FRAMEWORK_MAP, BUILD_STATE, NEXT_SESSION,
  YOUR_NOTES, YOUR_CONTRIBUTIONS, IMPASSES, DOCS_INDEX.
- Theory docs: `docs/THEORY_*.md` (v3) and `docs/RSLS_*.md` (v4).

The shipped artifact is `uma_build_v4.zip` in `/mnt/user-data/outputs/`.

## v4 deliverables (this session)

1. **Doc consolidation**: four equivalent PDFs collapsed into the single
   canonical spec `docs/RSLS_specification.md`. Retired sources listed
   in `DOCS_INDEX.md`.
2. **Menger sponge substrate**: `uma/rsls/menger.py` plus the structural
   argument in `docs/RSLS_menger_substrate.md`. Two falsifiable
   observational predictions: log-periodic factor-of-3 modulation in
   Stage 3D ringdowns and a fractal multipole correction to the photon
   sphere.
3. **Phase A POC**: HLL + Cattaneo + V(M) on a punctured spherical grid.
   Demonstrates DMP, BV behaviour, delayed stiffening (~150-step lag),
   wall-thickness convergence (slope ~0.015 across N=50..800; wt
   essentially flat at ~0.9), automatic NEC compliance.

## Likely follow-up work, in priority order

### From v3 (still open)

1. Multi-rep FieldPosterior (lowrank / ensemble / particle).
2. `wetterich_flow.py` — full RG flow (currently a basin classifier).
3. NonlinearEinsteinSolver: integrate the full curved d'Alembertian
   into `_curved_step` rather than just the leading correction.
4. `GRFixedPointSearch`: add gradient refinement on Einstein residual.
5. Re-run `calibrate.py` on the rebuilt kernel.

### From v4 (new)

6. **Convergence study at N>=2000.** The current Phase A log-log slope
   is 0.015 across N=50..800; the wall thickness has visually flattened
   in the wt_max measurement. Running at N=1600, 3200 would push the
   slope even closer to zero and provide tighter Richardson-extrapolation
   bounds on the dr -> 0 limit.

7. **Phase B kernel.** The spec sketches a Stage-2 / Phase B kernel that
   couples Phase A's M-field to the Einstein evolution (rather than
   the linearised TensorBridge). Build that as `uma/rsls/phase_b.py`,
   following the same numerical structure (HLL + Cattaneo + V(M)) but
   on a 2-D axisymmetric (r, theta) grid with the metric solved via
   `uma/msr/metric_solver.py::IterativeMetricSolver`.

8. **Menger AMR coupled to Cattaneo-V(M).** The current Menger demo is
   geometric only -- shows the lattice, the graph Laplacian, and AMR.
   The next step is to evolve M on the sponge with the Cattaneo flux,
   using the graph Laplacian for the smoothing term and refining
   wherever |grad M| > threshold.

9. **Stage-4 closure.** Combine 7 + 8: full GENERIC dynamics on a
   Menger-AMR substrate with the canonical pipeline running on top.
   This is the "Stage 4" the spec promises; v4 has the kernel but not
   the full assembly.

10. **Observational pipeline.** The two falsifiable predictions in
    `docs/RSLS_menger_substrate.md` (log-periodic ringdown comb;
    fractal photon-sphere multipole correction) need a data-analysis
    front-end. Suggested approach: build a `uma/rsls/observation.py`
    that takes a time-series and tests for the log-periodic modulation
    via wavelet spectrum on `log t`.

## Sanity-check ritual

After any non-trivial change:

```bash
cd uma_build_v4
python3 -m pytest tests/ -v                          # 70/70 should pass
python3 examples/run_pipeline.py                     # closure at step 34
python3 examples/rsls_phase_a.py                     # slope < 0.9; NEC OK
python3 examples/rsls_menger_substrate.py            # counts 1/20/400/8000
python3 examples/rsls_uma_integrated.py              # canonical + RSLS T
```

If all five commands succeed, the build is intact.

## Things deliberately left untouched

- `THRUPUT` is not in this build. UMA is a different package; THRUPUT's
  semantic intelligence platform layers on top of UMA but is its own
  codebase.
- LexGuard / SoCPM are not in this build either; they're separate AI
  safety frameworks, not part of UMA.
- The Iannotti v. Galaxy Gas matter is unrelated to anything in this
  repo. Mentioned only here so the boundary is unambiguous.

## Open questions

The original v3 IMPASSES.md is still valid -- none of those five
clarifications were unblocked by v4. New v4 items:

- The Phase A wall-thickness measurement (`interface_width` =
  M_range / max|dM/dr|) is a standard diffuse-interface metric. The
  spec wording ("wall thickness ell_*") could also be read as the
  *characteristic* length `sqrt(mu tau_M / V''(M))` evaluated at the
  peak M. The two agree in the diffuse-interface limit but can differ
  by a constant prefactor in the strict-saturation regime. For the
  current build I use `interface_width` because it's directly
  measurable from the field; closing the prefactor is a future task.

- The Stage-4 causality bound `c_diff^2 = mu/(tau_J tau_M) <= 1`
  forces `tau_M >= mu/tau_J = 0.533` for the published parameters.
  The default is `tau_M = 1.0` (giving `c_diff = 0.73`). Phase A
  itself uses only `c_eff = sqrt(mu/tau_J) = 0.73` so it's always
  causal; the choice of `tau_M` only enters when the full Stage-4
  back-reaction is run (not in this build).

---

## v4-extended (Stage 5 / frame-dragging) -- 2026-05-11

### What just happened

After the v4 build, an audit revealed the `*current*.pages` file (your
most recent state, 2026-05-07) had never been opened. Decompressing
the IWA stream surfaced:

1. The frame-dragging architectural pivot: `beta^phi != 0` as the
   primary geometric driver, not just an initial condition.
2. 1.5-D cylindrical reformulation (not 1-D spherical).
3. The cone aperture / Anosov-splitting numerical tracker.
4. The closing question: *"are you ready to initialize the first
   shift-vector-driven collapse on the PG background?"*

This session built the answer:

- `docs/RSLS_specification.md` extended with Section XIV (Stage 5).
- `uma/rsls/stage3.py` -- algebraic Stage-3 perturbative checks.
- `uma/rsls/srb.py` -- Lorenz Lyapunov + GKLS Lindblad + Koopman.
- `uma/rsls/frame_dragging.py` -- the 1.5-D cylindrical kernel.
- 35 new tests (Stage 3: 16, SRB: 9, Frame-Dragging: 10). 104/104 pass.

### The headline number to remember

`lambda_max = +1.127` with frame-dragging, `-0.044` without. The
Coriolis-coupled (S_R, S_phi) dynamics produce structural chaos
exactly when the geometric shift `beta^phi` is non-zero. The cone
stays open in the saturation layer iff `beta^phi != 0`.

### What's still architectural-pending

Stage 5 here uses a **prescribed** `beta^phi(R)` (Kerr-like, static).
A full self-consistent treatment would couple `beta^phi` to the
Einstein constraint and let the metric evolve dynamically with the
matter. That's the genuine next step:

- Replace the static `beta^phi` with an evolved field driven by the
  momentum constraint (`d_t beta^phi` from the ADM equations).
- Verify that the cone-aperture invariance survives the geometric
  back-reaction (the Stage-2 "phase-boundary migration" criterion).
- Generate the **Bifurcation Phase Map**: a 2D scan in
  (Omega_0, mass-injection-rate) showing the boundary between
  deterministic bounce and quantum-stochastic decoherence.

That's not implemented yet -- it requires the full ADM-Cattaneo
coupled solver. The Stage-5 kernel here demonstrates the kinematic
content of the architectural pivot; closing the metric loop is the
real Stage-6 work.

### Things to keep in mind

- `lyapunov_kernel(cfg)` is expensive (~30s with default params); test
  fixtures use class-scope to share runs between assertions.
- The `cone_aperture_min_margin` is dominated by outer R where
  `beta^phi -> 0`; use `cone_aperture_saturation_margin` (restricted
  to M-saturated cells) as the meaningful diagnostic.
- The Coriolis term `+/- 2 D beta^phi v` is what makes the system
  actually chaotic. Without it the kernel is dissipative even with
  `beta^phi != 0` (verified: differential collapsed to numerical noise
  in the initial kernel before the Coriolis terms were added).
