<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Jacob Iannotti -->

# Is the RSLS kernel chaotic? — the Lyapunov investigation

Stage 5 asserted `lambda_max > 0.3` with frame-dragging and `< 0.1` without,
and read the difference as proof that chaos is *structural*. Stage 6 asserted
`lambda_max > 0.5` and read it as that chaos surviving geometric
back-reaction. This directory is the attempt to actually measure the thing.

**Short answer.** Without frame-dragging the exponent is real and negative:
`lambda = -0.0375`, fully converged. With frame-dragging it is still
unresolved, and the original numbers were artifacts. Two independent defects
in the kernel were found on the way.

## What was wrong with the original estimators

| Check | Stage 5 | Stage 6 |
|---|---|---|
| converges as the window grows | no: −0.017, +5.50, +6.42, +9.44, +5.61 | no: −0.013, +3.16, +8.95, +39.12 |
| independent of perturbation size | no: +0.34, +5.50, −0.024, −0.021 (sign flips) | no: −0.014, −0.013, +0.064, +5.57 |
| no single event dominates | no: 1 block of 72 (growth ×87) is **82%** of the sum; median block *contracts* (54/72) | no: same shape |

Drop that one block and Stage 5 falls from +5.499 to +0.999. The `> 0.3`
threshold was cleared by a single transient amplification.

Three estimator bugs were fixed (`converge.py`, `real_lyap.py`):

1. **J was never renormalised.** The Cattaneo flux is evolved and feeds back
   into M, but only `[D, S_R, S_phi, M, beta]` were rescaled, so the flux
   separation was left wherever it drifted — not a consistent tangent vector.
2. **Partial final blocks were credited a whole block of time.**
3. **Renormalisation every 25 steps** let the separation grow ×87 inside one
   block, far outside the linear regime where Benettin's algorithm is valid.

None of them rescued convergence.

## Two real defects in the kernel itself

These are separate from the estimator and affect any long run.

**Fixed timestep violates CFL** (`adaptive.py`). `dt` is computed once from
the initial state and never updated. `max|v|` grows 0.30 → 8.7 → 4.4e4, and by
step ~8000 the fixed `dt` exceeds the CFL limit by **548×**; by step 12951 the
solution is non-finite. Every "growth" measured after step ~8000 is that
instability. At 16k steps `max|S_R|` reaches 1.2e15.

**Finite-time vacuum** (`vacuum.py`). With adaptive `dt` the blow-up stops but
the integration *stalls*: `min(D)` collapses to ~1e-6, so `v = S/D` reaches
4e5, `dt` collapses to 1e-7, and 100 000 steps advance the clock only from
t = 3.337 to t = 3.348. The trajectory reaches a coordinate singularity in
finite time; there is no long-time attractor to measure an exponent on.

A density floor (the standard "atmosphere" treatment) fixes this cleanly:

| floor | reach in 20 000 steps |
|---|---|
| none | t = 3.34 (stalled, `max\|v\|` = 4e5) |
| D ≥ 0.001 | t = 4.42 |
| D ≥ 0.01 | t = 6.88 |
| D ≥ 0.1 | **t = 11.00**, `dt` never leaves 5.5e-4 |

## What the bursts are

Not clipping — `jumps.py` finds **zero** cases where the twins disagree about
an `M`-clip or a `D`-floor on a burst step. The separation during a burst
lives in ~2 cells out of 600 components (participation ratio 2.28 vs 4.23 on
quiet steps), and the field carries cell-scale jumps (max neighbour difference
/ max|S| ≈ 0.88). These are **shock/interface events**. 586 steps out of
20 000 (2.9%) carry 95.4% of the log sum.

Shrinking the pulse amplitude does not reach a smooth regime (`shocks.py`) —
the saturation layer and the near-singular barrier pressure
`V(M) = -lambda log(1 - M/M_max)` keep the structure sharp at every amplitude
tried, and `lambda` stays large and erratic (+60, +82, +179, +213, +69).

Notably the statistic *is* perturbation-size independent under per-step
renormalisation (+69.20, +69.25, +68.92 at δ = 1e-7, 1e-9, 1e-11), so the
growth is a genuine property of the linearised map — it simply does not
converge in time, which is what disqualifies it as an exponent.

## Grid convergence — the decisive test (`gridconv.py`)

A physical exponent converges as `dR → 0`. Compared at **equal physical time**
(not equal step count — `dt` scales with `dR`, and λ drifts with time, which
confounded a first attempt):

| N | λ at T=5 | burst fraction | λ at T=10 |
|---|---|---|---|
| 50 | +46.19 | 0.038 | +77.27 |
| 100 | +2.84 | 0.00055 | +81.80 |
| 200 | +2.08 | 0.00022 | +3.86 |
| 400 | +27.06 | 0.00264 | — |

Non-monotonic and spanning an order of magnitude at both times. **The dragged
statistic does not converge under refinement**, so it is not a resolved
physical quantity — which settles it: the refusal is correct, and no
reasonable amount of estimator care will turn this configuration into a
measured exponent.

## The one result that stands

At N=150, n_steps=3000 (the Stage-5 test configuration):

| run | converged? | lambda | evidence |
|---|---|---|---|
| **drag OFF** | **yes** | **−0.037448** | 112 blocks, largest 3.7% of variation, second half within 0.021 of the whole |
| drag ON | no | (+1.141 raw) | second half +2.349 vs +1.141 — still climbing |

So: **the undragged kernel is measurably not chaotic.** With drag, the
question is open. The old ">0.3 differential" is unavailable, because half of
the comparison is not a measurement.

## A different attack: what is the attractor? (`attractor.py`)

Measuring the exponent kept failing, so this asks the prior question, which
shocks do not contaminate: **what does the trajectory settle onto?** A fixed
point cannot be chaotic (λ ≤ 0 with no estimate needed); a limit cycle gives
λ = 0. No twin, no perturbation — just `‖dx/dt‖` and recurrence on the
reference trajectory, with the density floor and adaptive `dt` so the run is
neither blowing up nor stalled.

| run | T | ‖dx/dt‖ early → late | std of ‖state‖, late half | verdict |
|---|---|---|---|---|
| drag ON | 11 | 29.7 → 10.2 | 0.32 | still transient |
| drag ON | 40 | 19.6 → 1.80 | 1.52 | still transient |
| drag OFF | 40 | 0.61 → **3.28** (growing) | 14.96 | still transient |

Neither reaches an attractor by T = 40, and the undragged run is *growing*
rather than settling. So within reachable integration times **there is no
attractor for an exponent to be defined on** — which is an independent reason
the refusal is right, arrived at without measuring an exponent at all.

It also puts a caveat on the one converged number below: the drag-OFF
λ = −0.037448 is a finite-time estimate over a transient, not a property of a
limiting invariant measure. It is honest as "this trajectory is not separating
over this window", not as "the system is provably non-chaotic forever".

## The tangent-space method — and what it finally settles (`tangent_lyapunov.py`)

Every attempt above used two finite-difference twins, which compound error
over the renormalisation interval and leave the linear regime. A tangent
method removes that failure mode: it propagates the linearisation
`v -> DF(x).v` directly, renormalising **every step**, so the perturbation is
never anything but infinitesimal. `DF` is applied matrix-free at the
roundoff-optimal step, evaluated fresh at the base point each time.

Validated first: with Lorenz's **analytic** Jacobian the same accumulation
gives **λ = +0.9019** against the literature's +0.906.

Three things it establishes that the twin method could not:

**1. The map IS differentiable along the dragged trajectory.** The integrator
audits this — it compares the active-constraint set (density floor, `clip_M`
bounds) and the HLL wave-speed sign pattern between the base and displaced
points at every step. For drag ON: **1 non-differentiable step in 36,364
(0.0%)**. My earlier "the bursts are shock non-smoothness" explanation was
**wrong**. (Drag OFF is a different story: 39.1% non-differentiable, so the
converged λ = −0.037448 reported below is on shakier ground than it looked.)

**2. The derivative is being computed correctly.** λ is independent of the
displacement size: +113.5, +110.8, +110.6, +111.2 at ε = 1e-6, 1e-8, 1e-10,
auto.

**3. It is still not a Lyapunov exponent — and now we know exactly why.**
Grid convergence at equal physical time, with the validated method:

| N | dR | dt | λ | **λ·dt** |
|---|---|---|---|---|
| 50 | 0.220 | 1.100e-3 | +86.24 | **0.09486** |
| 100 | 0.110 | 5.500e-4 | +172.02 | **0.09461** |
| 200 | 0.055 | 2.750e-4 | +9.23 | 0.00254 |

*(Window: `T_target = 20.0`, `T_burn = 2.0`. Re-derived 2026-08-19 — every
entry reproduces to three decimals, and λ·dt to five. An earlier revision of
this section described the window as T = 5, which is wrong: at T = 5 the same
code gives +62.76, +16.10, +4.13. See "How much the window matters" below,
which is why the distinction is not pedantic.)*

λ **doubles exactly** when N doubles (ratio 1.99), and `λ·dt` is identical to
0.3%. That is the signature of **grid-scale numerical amplification**: the
tangent vector grows by a fixed factor *per timestep* irrespective of
resolution, which is a property of the discretisation, not of the flow. A
physical exponent would hold λ fixed under refinement, not λ·dt. At N=200 the
amplification collapses by a factor of 19, consistent with the artifact being
resolved away.

So the answer to "is the RSLS kernel chaotic?" is not "we could not measure
it". It is: **the positive exponent reported by Stage 5 and Stage 6 is an
artifact of the discretisation.** The instantaneous rate does plateau (~290 at
N=100 after t≈18), which is why it looks like a real measurement — but the
plateau value is proportional to 1/dt, so it describes the grid, not the
physics.

## Why the refusal is not vacuous

`tests/test_stage6.py::TestLyapunovReportControls` runs the same
`uma.rsls.lyapunov.lyapunov_report` logic against systems with known answers:

- **Lorenz** → accepted, `lambda = +0.9032` (literature +0.906)
- **pure decay** `ds/dt = -s/2` → accepted, `lambda = -0.5000` exactly
- single-spike record → refused
- blown-up trajectory → refused

A gate that says no to everything proves nothing, so those controls ship with
the suite.

## Scripts

| file | what it answers |
|---|---|
| `converge.py` | convergence, δ-independence, single-block dominance of the shipped estimators |
| `adaptive.py` | is the blow-up a CFL violation? |
| `vacuum.py` | is the stall a density collapse, and does a floor fix it? |
| `real_lyap.py` | proper Benettin: adaptive dt, density floor, per-step renormalisation |
| `jumps.py` | are the bursts clipping kinks? (no) |
| `shocks.py` | are they shocks, and is there a smooth regime? |
| `gridconv.py` | grid convergence at equal physical time |

Run from `uma_build_v4/` with `PYTHONPATH=. python3.12 studies/rsls_lyapunov/<script>`.

## Not done — resolved 2026-08-19

This section used to say the question needed two modelling decisions made and
then a tangent-space integrator. It contradicted the tangent-space section
directly above it, which had already done exactly that and settled the answer:
the positive exponent is an artifact of the discretisation.

The remaining half was true and is now also done. The fixed-`dt` and vacuum
defects were documented here and not fixed in the module, on the grounds that
changing the timestepping alters every Stage-5/6 result. That objection is
void — those results are the ones this study showed to be artifacts, so there
was nothing left to protect. `Stage6Config` now carries `adaptive_dt` and
`density_floor`, both defaulting OFF so every published number reproduces bit
for bit. Measured at N = 100 over 16000 steps:

| configuration | t reached | max\|S_R\| |
|---|---|---|
| baseline, as published | 8.801 | 1.181e+15 |
| adaptive dt only | 2.710 | 7.579e-01 |
| **adaptive dt + floor 0.1** | **8.801** | **2.482e-01** |

The published configuration reaches t = 8.8 only by integrating an unstable
scheme; the floored adaptive run reaches the same physical time with the
solution bounded. A valid long-time integration now exists in the module, not
only in this directory's private `Kernel`.

### How much the window matters — and a reproduction, 2026-08-19

A re-run at T = 5 gave +62.76, +16.10, +4.13 against the table's +86.24,
+172.02, +9.23, which looked at first like a failure to reproduce. It was not:
the harness is deterministic and the table is exact. The ε-independence figures
quoted above reproduce to four decimals (+113.4747, +110.8471, +110.6263,
+111.1995 against +113.5, +110.8, +110.6, +111.2), and every entry of the grid
table reproduces at **T = 20**, which is the window it was actually run at.

The reason the mislabel mattered so much is itself the sharpest evidence in
this directory. At fixed N = 100 and a fixed grid, the exponent moves by more
than an order of magnitude with the *window alone*:

| T_burn (T = 5) | λ |     | T_target (burn = 2) | λ |
|---|---|---|---|---|
| 0.0 | +5.54 | | 5.0 | +16.10 |
| 1.0 | +6.85 | | 8.0 | +82.77 |
| 2.0 | +16.10 | | 12.0 | +111.20 |
| 3.0 | +45.13 | | 20.0 | +172.02 |
| 5.0 | +129.31 | | | |

**A 23× swing from the burn-in and a 10× swing from the window length, with
nothing about the physics or the discretisation changed.** A Lyapunov exponent
is a limit; a quantity that depends this strongly on where you start looking
and how long you look has not reached one. This is an independent argument for
the refusal, and it does not depend on the grid-refinement argument at all.

Both the λ·dt-constant signature (N = 50 → 100, constant to 0.3%) and the
non-monotonicity under further refinement therefore stand as originally
written.

### Why the tangent table stops at N = 200

It is not an oversight. **N = 400 at T = 20 is not reachable**: the adaptive
step collapses. Measured by integrating each resolution for 8 wall-clock
seconds and reading `dt` at the end —

| N | dt initial | dt after 8 s | t reached |
|---|---|---|---|
| 100 | 5.500e-4 | 5.500e-4 | 47.70 |
| 200 | 2.750e-4 | 2.750e-4 | 21.96 |
| 400 | 1.375e-4 | **1.185e-5** | 8.94 |

At N = 100 and N = 200 the step never leaves its initial value. At N = 400 it
has fallen 12× and is still falling, so the projected step count to reach
T = 20 grows faster than the run completes it. A 33-minute run produced no
result.

This is the finite-time vacuum from `vacuum.py` reappearing at high
resolution *despite* the density floor: a finer grid resolves sharper velocity
gradients, `max|v|` rises, the transport CFL tightens, and the clock stalls.
So the refinement ladder has a practical ceiling here, and the honest reading
is that the dragged statistic is unresolved over the range that CAN be
computed — which is the conclusion this directory already reached by three
independent routes (grid non-monotonicity, λ·dt constancy, and window
sensitivity).
