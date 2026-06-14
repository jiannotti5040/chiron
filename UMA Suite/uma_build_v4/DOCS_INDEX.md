# DOCS_INDEX.md — canonical document map

The complete UMA/RSLS theory and code base, with one home for every claim.
This file replaces the scattered PDF corpus.

## What was retired

The following sources are **superseded** by this build. Their content
has been reconciled into the canonical markdown files listed below.

| Retired source | Replaced by |
|----------------|-------------|
| `Files/RSLD.md` | `docs/RSLS_specification.md` |
| `Files/UMA_RSLS_Master_Specification.pdf` | `docs/RSLS_specification.md` |
| `Files/Blank 13.pdf` | `docs/RSLS_specification.md` |
| `Files/Forget function but important.pdf` | `docs/RSLS_specification.md` |
| `Files/Unified Master Architecture (UMA) and the Recursiv....pdf` | `docs/THEORY_unified_synthesis.md` |
| `Files/Variable list.pdf` | `docs/THEORY_variable_list.md` |
| `Files/operator.pdf` | `uma/venturi/operator.py` (already absorbed) |
| `Files/venturi injector.pdf` | `uma/venturi/injector.py` (already absorbed) |
| `Files/friction.pdf` | `uma/semantic/friction.py` (already absorbed) |
| `Files/constants.pdf` | `uma/semantic/constants.py` (already absorbed) |
| `Uma/*.pdf` (22 module exports) | `uma/...` (all already absorbed into v3) |

The retired PDFs are kept in the source corpus archive for provenance
but should not be read for current operation. **This file lists where
every claim now lives.**

## Canonical read order

For a new reader picking up the project, read in this order:

### 1. Orientation

- **`README.md`** — what's in the package, how to run it, key invariants.
- **`FRAMEWORK_MAP.md`** — every named object with its one-line role.
- **`BUILD_STATE.md`** — passing/failing tests, build history.

### 2. Theory (read in this order)

- **`docs/THEORY_sphere_derivation.md`** — why the geometry is locked
  to Bessel zeros. Nothing tuned.
- **`docs/THEORY_variable_list.md`** — every symbol used across UMA
  and RSLS, with definitions. (One unified list, no separate PDF.)
- **`docs/THEORY_unified_synthesis.md`** — full UMA + RSLS narrative
  synthesis. Read after the variable list; it assumes the notation.
- **`docs/THEORY_biggest_advance.md`** — the sharpest single result
  (friction → 0 and Einstein residual → 0 are the same event).
- **`docs/RSLS_specification.md`** — the canonical RSLS field-theoretic
  spec. One document. Replaces the four PDF restatements.
- **`docs/RSLS_menger_substrate.md`** — the Menger-sponge argument:
  why a fractal lattice is the predicted geometry of the saturated
  information attractor, with the two falsifiable observational
  predictions (log-periodic echo comb, photon-sphere multipole).

### 3. Code (read in this order)

- **`uma/config.py`** — `GridConfig`, `GENERICConfig`, `FilterConfig`.
- **`uma/core/`** — `FieldProjection`, `FieldPosterior`, `KalmanFilter`.
- **`uma/observations/`** — `Observation`, `GaussianObservation`.
- **`uma/dynamics/generic.py`** — `H[ψ]`, MSR response, GENERIC step.
- **`uma/sphere/`** — `AcousticSphereGeometry`, `SystemGeometry`,
  `SphereProjectionField`, `SpherePendulum`, `SphereVenturi`.
- **`uma/venturi/`** — `Venturi`/`VenturiOperator`,
  `CrossDomainInjector`.
- **`uma/msr/`** — `TensorBridge`, stress-energy, Wetterich flow,
  nonlinear Einstein solver, metric solver, GR fixed-point search.
- **`uma/semantic/`** — `SemanticEngine`, `UMA_IR`, `UMAExecutor`,
  `SemanticFriction`, `ConstraintSet`, `Inarticulator`.
- **`uma/rsls/`** — **NEW.** The RSLS subpackage: `memory.py` (M field
  + V(M) barrier), `cattaneo.py` (Maxwell–Cattaneo entropy flux),
  `hll.py` (HLL Riemann solver), `phase_a.py` (Stage 1 falsification
  kernel, 1-D spherical), `menger.py` (Menger sponge lattice + graph
  Laplacian), `coupling.py` (T_{μν}^{(∇M)} contribution to the
  TensorBridge).
- **`uma/pipeline.py`** — the 15-module integrator.
- **`uma/client.py`** — the deterministic kernel.

### 4. Runnable examples

- **`examples/run_pipeline.py`** — the original 15-module UMA run.
- **`examples/sphere_uma_execution.py`** — sphere-grounded run.
- **`examples/rsls_phase_a.py`** — **NEW.** Stage 1 falsification
  kernel: 1-D spherical solver with HLL + Cattaneo + V(M).
  Demonstrates ℓ_* grid convergence as dx → 0.
- **`examples/rsls_menger_substrate.py`** — **NEW.** Menger sponge
  lattice + M field demo. Shows automatic refinement triggered by
  |∇M| > threshold, and that V(M_n) grows linearly in level n.
- **`examples/rsls_uma_integrated.py`** — **NEW.** Full v3 pipeline
  + RSLS coupling. The T_{μν}^{(∇M)} term is visible in the
  TensorBridge; the Menger AMR is visible as a new closure condition.

### 5. Tests

- **`tests/test_sanity.py`** — 11 sanity checks for the original v3
  build.
- **`tests/test_semantic.py`** — 19 semantic-engine tests.
- **`tests/test_rsls.py`** — **NEW.** Phase A kernel correctness:
  HLL on Riemann problems, Cattaneo subluminal speed, V(M) convexity,
  ℓ_* grid-independence, NEC compliance of T_{μν}^{(∇M)}.
- **`tests/test_menger.py`** — **NEW.** Sponge construction at
  levels 0–3, volume/surface scaling, Hausdorff-dimension match,
  graph Laplacian symmetry, refinement/coarsen idempotence.

## Build markers (provenance)

- **`CORPUS_INDEX.md`** — original PDF→module mapping from v3 build.
- **`IMPASSES.md`** — open questions parked in v3.
- **`YOUR_NOTES.md`** — technical reservations from the v3 rebuild.
- **`YOUR_CONTRIBUTIONS.md`** — what Claude wrote in v3 vs. what came
  from the corpus.
- **`NEXT_SESSION.md`** — pickup notes from the v3 build.

These are kept for traceability but are not part of the canonical
theory. The v4 build's own markers are stamped in this `BUILD_STATE.md`.

## Rule

Every theory claim has exactly one home. If a claim appears in two
places they must reference each other or one must be wrong.
The default is: code is the source of truth for behaviour, markdown
in `docs/` is the source of truth for theory, and this file points
the reader to whichever is canonical for the question at hand.
