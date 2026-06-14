# NEXT_SESSION.md

How to pick this build up cleanly in a future session.

---

## Where things stand right now

- The package compiles end-to-end. `python3 examples/run_pipeline.py`
  runs to completion. `python3 -m pytest tests/` shows **30/30 passing**.
- The full 15-module pipeline closes (Omega) deterministically at
  seed=42 around step ~54.
- All marker files are written: README, FRAMEWORK_MAP, BUILD_STATE,
  YOUR_NOTES, YOUR_CONTRIBUTIONS, IMPASSES, NEXT_SESSION.
- Theory docs are extracted into `docs/THEORY_*.md`.

The shipped artifact is `uma_build_v3.zip` in `/mnt/user-data/outputs/`.

## Likely follow-up work, in priority order

1. **Multi-rep FieldPosterior.** If the canonical `lowrank` / `ensemble`
   / `particle` representations exist somewhere I didn't see, drop them
   into `uma/core/state.py`. The `representation` dispatch in
   `inarticulation.py::_scaling_coefficient` will need to be reactivated
   (it's currently single-branch). Nothing else in the package depends
   on the multi-rep machinery.

2. **wetterich_flow.py — full RG flow.** The shipped version is a
   compact basin classifier. If the corpus contains a fuller RG-flow
   derivation, it slots in here. Functions to expose: a full
   `wetterich_step(couplings, log_k)` that integrates couplings down
   from UV to IR, and a fixed-point finder for the IR basin.

3. **NonlinearEinsteinSolver convergence study.** The current
   implementation is exact at every step but `IterativeMetricSolver`
   reuses only the leading curved-d'Alembertian correction. Adding
   the full `h^munu d_mu d_nu psi + Gamma corrections` term to
   `_curved_step` would give a tighter self-consistent fixed point.

4. **GR fixed-point refinement.** `GRFixedPointSearch` finds the
   best-seeded trajectory; it doesn't gradient-refine. Adding a JAX
   or finite-difference gradient on the Einstein residual w.r.t. `psi`
   would let it do real refinement after seed-search.

5. **calibrate.py re-run.** The values in `uma/semantic/constants.py`
   (`CALIBRATED_H_TARGET = 1.092794`, etc.) are from the previous
   50-trajectory run. Re-running on the rebuilt kernel will produce
   slightly different numbers; pasting them back into `constants.py`
   refreshes the closure thresholds.

## Sanity-check ritual

After any non-trivial change:

```bash
cd uma_build_v3
python3 -m pytest tests/ -v             # all 30 should pass
python3 examples/run_pipeline.py         # closure (Omega) should appear
```

If those two commands both succeed, the build is intact.

## Things deliberately left untouched

- `THRUPUT` is not in this build. UMA is a different package; THRUPUT's
  semantic intelligence platform layers on top of UMA but is its own
  codebase.
- LexGuard / SoCPM are not in this build either; they're separate AI
  safety frameworks, not part of UMA.
- The Iannotti v. Galaxy Gas matter is unrelated to anything in this
  repo. Mentioned only here so the boundary is unambiguous.

## Open questions parked in IMPASSES.md

Five clarifications that did not hard-stop the build. Each is one
sentence. None require action to use the package as shipped; they're
points where definitive answers would improve fidelity to the original
corpus.
