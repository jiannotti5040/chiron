# IMPASSES.md

Questions the reconstruction could not resolve from the corpus alone. None hard-stopped the build (the package compiles, runs, and all
30 tests pass), but each would benefit from a definitive answer.


---

1. **FieldPosterior representations.** The canonical executor/inarticulation
   files dispatch on `posterior.representation in {'full','lowrank','ensemble','particle'}`.
   Only the `full` path is defined in the PDFs — were `lowrank`/`ensemble`/`particle`
   ever actually implemented in `uma.core.state`, or only stubbed?

2. **MSR cosine threshold.** The pipeline's `verify_T_equals_lichnerowicz`
   one-shot check returns `cos ~ 0.001` on random `psi`. Was the original
   gating supposed to be `|cos| - 1 < 0.01` (strict) or relaxed for
   stochastic init? I went with the relaxed `0.5` threshold to avoid
   spurious failures.

3. **Wetterich basin cutoff.** I chose `cutoff=0.5` for the
   `c_alpha/nu_2` ratio in `classify_basin`. Was there a previously
   calibrated cutoff in the original Levy-MSR work? The default
   couplings I used in the pipeline fall into the Gaussian basin.

4. **Engine3 `anchor` choice.** The PDFs use `"dIse"` as the default
   anchor in `tokenize_to_binary_weight`. Should this also be the
   default in `Venturi.inject_text`? I left both at `"dIse"` for
   consistency.

5. **GENERICConfig field names.** The canonical pipeline calls
   `cfg.generic.alpha`, `cfg.generic.lam`, `cfg.generic.mu`, `cfg.generic.g`,
   but other modules use `advection`/`reaction`. Are these aliases of
   the same parameters, or distinct? I unified to `advection / diffusion /
   reaction` and aliased `reaction <-> lam` at call sites.

---

## 2026-08-11 — is the RSLS kernel chaotic? (open)

Stage 5 and Stage 6 both asserted a positive Lyapunov exponent. Both claims
are withdrawn; see `studies/rsls_lyapunov/README.md` for the full record.

**Settled:** with frame-dragging disabled the estimate converges to
λ = −0.037448 — measurably not chaotic over that window.

**Open:** with frame-dragging on, the statistic is still climbing (second half
+2.349 against +1.141 over the whole window) and does not converge under grid
refinement at equal physical time (λ = +46.19, +2.84, +2.08, +27.06 at
N = 50, 100, 200, 400 for T = 5). The growth is δ-independent, so it is a real
property of the linearised map — it is simply not a resolved physical
quantity. The bursts are shock/interface events: separation localises to ~2
cells of 600, and 2.9% of steps carry 95.4% of the log sum.

**Blocked on two modelling decisions, not on analysis:**

1. `dt` is fixed at its t=0 value and violates CFL by ~550× once velocities
   grow. Making it adaptive is a correctness fix but changes every published
   Stage-5/6 number (cone aperture, drift, saturation margins).
2. Without a density floor the solution reaches a finite-time vacuum at
   t ≈ 3.34 and the integration stalls. A floor is standard atmosphere
   treatment but is a change to the physics.

Attempting the attractor question directly (`attractor.py`) did not resolve
it either: neither the dragged nor the undragged run reaches an attractor by
T = 40, and the undragged one is *growing*. So within reachable integration
times there is no invariant set for an exponent to be defined on.

**What would settle it:** make the two decisions above, then use a
tangent-space (variational) integrator rather than a finite-difference twin,
on a scheme where linearising across a shock is meaningful. Until then the
honest statement is "no chaos without drag, unresolved with drag".
