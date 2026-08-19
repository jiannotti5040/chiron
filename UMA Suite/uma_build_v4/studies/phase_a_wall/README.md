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
