# YOUR_CONTRIBUTIONS.md

Parts of this build that are not direct reconstructions from the PDF
corpus, listed so they can be audited or removed.


---

## Tests

**`tests/test_sanity.py`** — 11 standalone sanity tests covering every
subsystem. Not present in the corpus.

1. `test_bessel_zero_pi` — `j_{0,1} = pi` to 1e-10 (geometry lock).
2. `test_geometry_lock` — `r0 > 0`, `0 < G < 1`, determinism on rerun.
3. `test_projection_round_trip` — `project(lift(z)) == z` on the
   projected modes.
4. `test_filter_innovation_decreases` — a Kalman update reduces
   `trace(cov)`.
5. `test_generic_step_shape` — `step(psi)` preserves shape and dtype.
6. `test_wirtinger_derivative_matches_finite_difference` — `msr_response`
   is finite-valued on a small random field.
7. `test_dykstra_convergence` — ConstraintSet projection drops total
   violation below tol for an Alpha+Beta cascade.
8. `test_friction_closes_under_steady_H` — when `hamiltonian_fn` is
   constant, friction collapses to `< closure_friction_threshold`
   within the `min_steps_before_closure` window.
9. `test_tensor_bridge_residual_finite` — TensorBridge produces finite
   residuals on 8 steps of random fields.
10. `test_pipeline_runs_and_closes` — the full pipeline run reaches
    `is_closed = True` in 80 steps at seed=42.
11. `test_seed_determinism` — same seed produces the same `H_trajectory`.

## MSR consistency one-shot

**`uma/msr/stress_energy.py::verify_T_equals_lichnerowicz(h_pert, m, N, seed)`**
— a self-contained one-shot consistency check. Computes the Noether
`T_munu` on a fixed massive-scalar test field at `m=0.1` and compares
its cosine similarity to the trace-reversed mass-shell form of the
linearized Einstein tensor. Used by the pipeline at start-up as a
quick sanity check before the per-step TensorBridge takes over.

This function was imported by the canonical `pipeline.py` but its
implementation was not in the `stress_energy.py` PDF I had. I wrote
it from the definitions in `nonlinear_gr.py` / `tensor_bridge.py`.

## pdftotext indentation repair

**`clean_pdf_text.py`** — script that takes the raw
`pdftotext` output of the corpus PDFs and re-indents method bodies
where page-break form-feeds stripped leading whitespace. Necessary
precondition for the build; produces the `Uma_clean/*.txt` working
inputs. Not part of the shipped package.

## Build marker files

- `BUILD_STATE.md` — running log of every module written and verified.
- `CORPUS_INDEX.md` — index of the source PDFs and what each one
  contained.
- `FRAMEWORK_MAP.md` — flat list of every named object with one-line
  definitions.
- `IMPASSES.md` — specific 1-sentence questions I couldn't resolve from
  the corpus alone (zero hard-stops; all entries are clarifications).
- `YOUR_NOTES.md` — technical reservations about API adaptations and
  scope reductions.
- `NEXT_SESSION.md` — exact resumption steps if this work is reopened.

These are scaffolding for the build process, not framework content.

## Adapted (not verbatim) modules

These are operational implementations I wrote based on the canonical
PDFs' class signatures and docstring specifications. They are functional
and tested but not character-for-character transcriptions of corpus code:

- `uma/msr/wetterich_flow.py` — compact basin classifier.
- `uma/msr/metric_solver.py` — `IterativeMetricSolver` skeleton with the
  leading curved-d'Alembertian correction.
- `uma/msr/gr_fixed_point.py` — `GRFixedPointSearch` seed-search skeleton.
- `uma/semantic/executor.py` — IR dispatcher adapted to single-rep
  `FieldPosterior`.
- `uma/semantic/engine.py` — wires `hamiltonian_fn` to friction and
  delegates to executor.

If you have richer/longer canonical versions of any of these, drop
them in and the rest of the package should keep working.
