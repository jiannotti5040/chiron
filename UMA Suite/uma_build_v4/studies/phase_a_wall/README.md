<!-- SPDX-License-Identifier: Apache-2.0 -->
<!-- Copyright 2026 Jacob Iannotti -->

# Is the Phase A wall the theory's ℓ\*? — the parameter-scaling test

**Short answer: no.** The measured wall thickness is set by the **initial pulse
width**, not by the singular barrier. It does not depend on μ, τ_M or λ at all.

This does not show the theory is wrong. It shows that Phase A, as configured,
does not demonstrate the mechanism it is presented as demonstrating.

## What was already established, and why it does not settle it

Phase A's headline result is mesh-independence: the wall thickness varies
between 0.86 and 1.16 across N = 50…800, a log-log slope of **0.015** against
1.0 for a pure numerical artifact. That test is correct and it rules out
numerical diffusion — a width set by the grid would scale with `dx`.

But there is a second way to get a mesh-independent width, and the test does
not exclude it: **the width can be set by a mesh-independent initial
condition.** Ruling out the grid is not the same as ruling in the barrier.

## The sharper claim the theory actually makes

`uma/rsls/memory.py:98`:

    ell_*(M) = (M_max - M) * sqrt(mu * tau_M / lambda)

This is a closed form, not an emergent quantity — it is algebraic in `M` and
three configuration constants. It predicts something specific and checkable:
**the wall should scale linearly with `sqrt(mu * tau_M / lambda)`.** Nothing in
the suite had ever varied those three parameters.

## Result

Measured with `interface_width` — the canonical Cahn-Hilliard / Allen-Cahn
diffuse-interface width at the steepest gradient, whose own docstring says it
"converges to a finite limit as dx → 0 if and only if the wall thickness is a
*physical* length". N = 300, 4000 steps, full saturation (`M` peak = 1.0000)
reached in every run.

**A. Vary the theory's parameter, hold the pulse fixed:**

| μ | τ_M | λ | sqrt(μτ/λ) | interface width |
|---|---|---|---|---|
| 0.08 | 1.0 | 0.12 | 0.8165 | **0.8630** |
| 0.32 | 1.0 | 0.12 | 1.6330 | **0.8630** |
| 0.08 | 4.0 | 0.12 | 1.6330 | **0.8630** |
| 0.08 | 1.0 | 0.48 | 0.4082 | **0.8630** |
| 0.02 | 1.0 | 0.12 | 0.4082 | **0.8630** |

Identical to four decimals across a 4× range of the predicted length.
**log-log slope = +0.0000, where the theory predicts +1.0.**

**B. Vary the initial pulse, hold the theory fixed:**

| pulse_width | interface width | ratio |
|---|---|---|
| 1.0 | 0.4372 | 0.4372 |
| 2.0 | 0.8630 | 0.4315 |
| 4.0 | 1.7192 | 0.4298 |

**log-log slope = +0.9878.** The wall is ≈ 0.43 × the initial pulse width.

So the wall is neither a grid artifact (slope 0.015 against N) nor the
predicted ℓ\* (slope 0.000 against sqrt(μτ/λ)). It is the initial condition,
propagated (slope 0.988 against pulse width).

## Ruled out: too short a run

The obvious benign explanation is that the wall had not yet relaxed to ℓ\*.
It had not, and it does not — at the full default `n_steps = 15000`, with
`M` saturated at 1.0000, the width is still **0.8630** for both λ = 0.12 and
λ = 0.48. Longer integration does not move it toward the prediction.

The threshold-based `wall_thickness` agrees with the canonical measurement
(0.8679 vs 0.8630), so this is not an artifact of which observable is used.

## What this does and does not mean

It does **not** mean ℓ\* is wrong as a piece of theory, or that a
barrier-set wall cannot exist. It means:

1. The Phase A kernel does not currently exhibit a barrier-set wall. Whatever
   sets the interface in this configuration, it is not `sqrt(mu tau_M/lambda)`.
2. The mesh-independence result should not be quoted as evidence for the
   singular-barrier mechanism. It is evidence against *numerical diffusion*,
   which is a weaker and different statement.
3. The framework's own falsification checkpoint — "if on careful re-run the
   wall-thickness slope is ≥ 0.5, the singular-barrier mechanism is wrong" —
   tests the grid. The parameter slope is the one that discriminates, and it
   was never tested.

## Root cause: ℓ\* is derived from an equation the code does not solve

`ell_star` is the length at which diffusion balances the barrier's curvature:

    ell_*(M) = sqrt(mu * tau_M / V''(M))

That balance is the steady state of an M-equation of the form

    d_t M = mu grad^2 M - V'(M)

The M-equation the kernel actually integrates (`phase_a.py`, `stage6.py`) is

    d_t M = -div J - 0.5 div v ,        tau_J d_t J + J = -mu grad M

so with the flux relaxed, `d_t M ≈ mu grad^2 M - 0.5 div v`. **There is no
`-V'(M)` restoring term.** `V_prime` is defined at `memory.py:77`, imported by
`phase_a.py:35` and `frame_dragging.py:45`, and never called anywhere in
`uma/rsls/`. What holds M below M_max is `clip_M`, a hard `np.clip`, not a
barrier force.

So the length ℓ\* describes a balance that never occurs in the M dynamics.
That is why varying λ does not move the wall: λ reaches the M field only
indirectly.

**A correction to a first reading of this.** It is tempting to conclude from
the above that "the barrier is not in the model". That is wrong, and the code
says so: `hll.py:121,170` and `frame_dragging.py:226` compute `P = V(M, cfg)`
and use it as the effective pressure in the **momentum** flux —
`d_t(R S_R) + d_R(R [S_R v_R + V(M)]) = 0`. The barrier is real and it acts;
it acts on the momentum, not on M directly. Varying λ does perturb the
solution (max|ΔM| ≈ 8e-2 for λ: 0.12 → 0.48) through that pressure and the
advection it drives. It simply does not set the interface width, because the
term that would set it is not in the M equation.

For completeness, `tau_M` enters the kernel only through
`c_diff = sqrt(mu/(tau_J tau_M))`, which sets the Cattaneo CFL timestep. The
flux relaxes on `tau_J`, not `tau_M`. So of the three quantities in ℓ\*, one
(`mu`) acts on M, one (`lambda`) acts on momentum, and one (`tau_M`) acts only
on the timestep.

## The relaxed interface sits at the grid scale

The published mesh-independence measured `wall_thickness_max`, the widest
interface across all snapshots — which is the *initial* one. The interface
does not stay there. It collapses within one snapshot interval and then holds
at a fixed number of CELLS, not a fixed length:

| N | dR | wall_max | wall_final | final / dR |
|---|---|---|---|---|
| 100 | 0.1400 | 0.8919 | 0.2800 | 2.00 cells |
| 200 | 0.0700 | 0.8679 | 0.1919 | 2.74 cells |
| 400 | 0.0350 | 0.8611 | 0.1297 | 3.71 cells |
| 800 | 0.0175 | 1.1186 | 0.0681 | 3.89 cells |

log-log slope against dR: **wall_max −0.097** (mesh-independent, reproducing
the published 0.015), **wall_final +0.669** (1.0 would be pure numerical
diffusion).

So the quantity the mesh-independence test was designed to protect — a
physical interface width that survives dx → 0 — is grid-dependent. The test
missed it by measuring a transient that could not exhibit it.

## What would settle it

Find the regime, if there is one, where the barrier rather than the initial
condition sets the interface: the pulse must be wide compared to ℓ\* so the
wall has something to relax *from*, and the run long enough to relax. If the
width then tracks sqrt(μ τ_M / λ), the mechanism is real and Phase A simply
had the wrong initial data. If it never does, the claim needs withdrawing.

## Reproduce

    PYTHONPATH=. python3 studies/phase_a_wall/scaling.py

Gated in `tests/test_phase_a_wall.py`, which asserts the measured slopes so
the finding cannot silently reverse.

## The constructive test: supplying the missing term does NOT rescue it

`PhaseAConfig.barrier_force` (default **off**, so every published number is
unchanged) adds the absent `-V'(M)` to the M equation, making the prediction
testable rather than assumed. It is a clean negative result.

**Transient wall** (`wall_thickness_max`), log-log slope against λ:

| | slope | theory |
|---|---|---|
| barrier force OFF | **+0.000** | −0.5 |
| barrier force ON | **−0.075** | −0.5 |

So the term does couple λ to the interface — the response goes from exactly
flat to slightly negative — but it recovers about 15% of the predicted
exponent.

**Relaxed wall** (final snapshot), where the diffusion/barrier balance would
actually live, at N = 300 (dR = 0.0467):

| μ | λ | ℓ\* | wall (force ON) | cells |
|---|---|---|---|---|
| 0.08 | 0.03 | 1.6330 | 0.0941 | 2.02 |
| 0.08 | 0.12 | 0.8165 | 0.0933 | 2.00 |
| 0.08 | 0.48 | 0.4082 | 0.0933 | 2.00 |
| 0.14 | 0.03 | 2.1602 | 0.1058 | 2.27 |
| 0.14 | 0.12 | 1.0801 | 0.0933 | 2.00 |
| 0.14 | 0.48 | 0.5401 | 0.1004 | 2.15 |

The relaxed interface is **2.0–2.3 cells in every configuration tested**, while
ℓ\* ranges over 0.41–2.16 — that is 9 to 46 cells, comfortably resolvable. The
wall does not track it, with or without the barrier force, at any μ tested
inside the causality bound.

### What this means

The interface is not diffusion-controlled at these parameters; it is
compression-controlled and mesh-limited. The barrier can only push M away from
M_max — it does not by itself set a profile width — and the width that would
come from μ is overwhelmed by the `-0.5 div v` compression, which sharpens the
front until the grid stops it.

So the repair is **not** "add the missing term". The missing term is real and
should be there, but the emergent-length claim needs the M equation's
advection/compression balance addressed as well. That is a structural question
about the model, not a bug, and it is now a measured one rather than an
assumed one.
