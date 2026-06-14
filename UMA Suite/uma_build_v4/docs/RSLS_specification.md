# RSLS — Recursive Symbiotic Logic System

**Canonical formal specification, single source.**

This document supersedes the following four redundant restatements that
were previously circulating as PDFs:

- `RSLD.md` (the early markdown draft)
- `UMA_RSLS_Master_Specification.pdf` (Stage 4 finalized)
- `Blank 13.pdf` (compact master spec)
- `Forget function but important.pdf` (full Stages 1–4)

Their content is reconciled here. Where they disagreed (mostly in
labelling: e.g. "Stage 1 / Phase A" vs "Stage 1A"; "Memory field M" vs
"Information density M") this document picks the labels used in
`UMA_RSLS_Master_Specification.pdf` because that is the most recently
edited file in the corpus.

---

## Classification

The RSLS is a **symmetric-hyperbolic Einstein–relaxation system with a
singular convex state-space boundary.** The framework couples the
Einstein field equations to a Maxwell–Cattaneo causal-relaxation
sector, regularised by an Israel–Stewart bounded scalar (the
"Holographic Wall"). Net effect: the Cauchy problem for gravitational
collapse is globally well-posed, with geometric singularities replaced
by a finite-thickness phase-transition boundary.

The RSLS is the field-theoretic engine that the UMA computational
pipeline implements. UMA is the software; RSLS is the physics it
solves.

---

## I. State Space

The RSLS is defined on a 4-dimensional pseudo-Riemannian manifold
(*M*, g_{μν}) with signature (+, −, −, −). The local state vector is

> **Ψ** = (g_{μν}, U^μ, M)

with three components:

1. **Gravitational metric** g_{μν} — the dynamic Lorentzian geometry.
2. **Information flow** U^μ — a timelike vector congruence,
   normalized as U^μ U_μ = 1, carrying the causal propagation of
   state-information.
3. **Thermodynamic memory** M ∈ [0, M_max) — an Israel–Stewart causal
   scalar relaxation field tracking local informational entropy
   density.

The bound M ∈ [0, M_max) is invariant: it is preserved dynamically by
the singular convex barrier V(M) (next section).

---

## II. Action and the Singular Convex Barrier

The action is partitioned so that interactions occur **only at the
first-derivative level**. This ensures strong hyperbolicity and
excludes Ostrogradsky ghost modes.

- Geometry: 𝓛_EH = (c⁴ / 16πG) R
- Kinematics: 𝓛_U = − ¼ F_{μν} F^{μν} + ½ κ (U_μ U^μ − 1)
  with F_{μν} = ∇_μ U_ν − ∇_ν U_μ and κ the Lagrange multiplier
- Memory: 𝓛_M = ½ ∇_μ M ∇^μ M − V(M)
- Coupling: 𝓛_int = − β M ∇_μ U^μ

The **singular convex barrier** is

> V(M) = − λ log(1 − M / M_max)

with the properties

- V is C^∞ on M ∈ [0, M_max)
- V''(M) > 0 strictly (strict convexity)
- V'(M) → ∞ as M → M_max⁻ (the divergent gradient)

V'(M) → ∞ at saturation is the entire stability mechanism: it acts as
an infinite repulsive potential in state space, ensuring the invariant
domain M < M_max and the coercivity of the mathematical entropy.

---

## III. Equations of Motion

Three coupled quasi-linear PDEs.

### 1. Einstein sector (geometric reaction)

> G_{μν} + Λ g_{μν} = 8πG T^{eff}_{μν}(Ψ)

T^{eff}_{μν} contains the flow stress, the memory stress, and the
dissipative exchange (sections IV.3 and IV.4 below). Geometry reacts
to information density; the lapse α freezes at a finite minimum during
core saturation rather than collapsing to zero.

### 2. Relaxation sector (thermodynamic memory)

> τ_M (U^α ∇_α M) + M = − κ_M ∇_μ U^μ

M integrates kinematic compression −∇_μ U^μ over time. The
Israel–Stewart structure inserts a causal relaxation lag τ_M between
geometric forcing and informational response.

### 3. Damped flow sector (kinematics)

> ∇_μ F^{μν} − κ U^ν + β ∇^ν M − γ_C C_U U^ν = 0

with C_U ≡ U^μ U_μ − 1. The −γ_C C_U U^ν term is the **constraint
damping current**, ensuring the timelike foliation U^μ U_μ = 1 remains
a dynamical attractor through nonlinear focusing.

### 4. Maxwell–Cattaneo entropy flux (causal transport)

> τ_J ∂_t J_r + J_r = − μ ∇M

The entropy flux is promoted to a dynamical field with its own
relaxation time τ_J. This eliminates infinite-speed diffusion: the
flux propagates subluminally, with characteristic velocity

> c_diff² = μ / (τ_J τ_M)

The structural causality bound is

> μ / (τ_J τ_M) ≤ c² = 1

---

## IV. Principal Symbol and Hyperbolicity

Let the state vector under linear perturbations in harmonic gauge be

> Ψ = ( h̄_{μν}, v^μ, φ )

where h̄_{μν} is the trace-reversed metric perturbation. Replacing
each second-order derivative by the characteristic covector ξ_μ gives
the principal symbol matrix P(ξ).

Because the interaction term β M ∇_μ U^μ is purely first-order,
P(ξ) is **block-diagonal**, and

> det P(ξ) = 0 ⟺ ξ² = 0

Characteristic surfaces are strictly Lorentzian: the system is
strongly hyperbolic, causal, and well-posed.

---

## V. Thermodynamic Structure

The stress-energy decomposes as

> T_{μν} = T^{(U)}_{μν} + T^{(M)}_{μν} + T^{(int)}_{μν}

The interaction enforces an energy-exchange current Q_ν between the
kinematic and memory sectors. Defining the Israel–Stewart entropy
current

> s^μ = s_0 U^μ − ½ (τ_M / κ_M) M² U^μ

the system satisfies the Second Law strictly:

> ∇_μ s^μ ≥ 0

Dissipative regularisation is thermodynamically monotonic.

---

## VI. Stage 1 — Phase A Falsification Kernel

The minimal numerical verification of the architecture is a 1-D
spherical solver with three components:

1. **Punctured radial domain** r ∈ (ε, R] — exclude r = 0 to avoid the
   coordinate singularity without artificial smoothing.
2. **HLL Riemann flux** for compressive transport. Signal speeds:
   λ_L = v_r − c_eff, λ_R = v_r + c_eff with c_eff = √(μ / τ_J).
3. **Implicit Cattaneo update** for J_r — preserves the causal delay
   τ_J without introducing stiffness instability:

   J_r ← (J_r − (dt μ / τ_J) ∇M) / (1 + dt / τ_J)

The falsification check, run as a vanishing-viscosity convergence
study (dx → 0):

- **L¹-contraction**: ‖Ψ_h(t) − Ψ_h'(t)‖₁ ≤ ‖Ψ_h(0) − Ψ_h'(0)‖₁
- **Grid independence**: ℓ_* → const, not → 0 and not → ∞
- **Delayed stiffening**: phase lag between peak compression and peak M
  consistent with hyperbolic relaxation (not instantaneous)

The reference kernel is `uma/rsls/phase_a.py`; the convergence study
runs in `examples/rsls_phase_a.py`.

---

## VII. Stage 2 — Covariant Geometric Saturation

Promotes the kernel to a spherically symmetric **dynamic** geometry.

Metric ansatz (Painlevé–Gullstrand, regular at the horizon):

> ds² = − α²(t,r) dt² + (dr + β^r(t,r) dt)² + r² dΩ²

- α(t,r) — dynamic lapse; collapses toward a finite minimum at core
  saturation (does **not** vanish).
- β^r(t,r) — radial shift; coupled to memory energy-momentum.

Evolved on a punctured domain r ∈ (ε, R]. State vector

> **Q** = [r²ρ, r²U^r, r²M]^T

Parity & flux conditions at r → 0:

- U^r odd, M and α even (mod parity)
- lim_{r→0} r² F^r < ∞ (finite-flux condition)

Stage 2 success criteria (the Non-Negotiables):

1. **r_c → ℓ_***  : the saturation radius converges to a non-zero
   constant independent of dx.
2. **Lapse freezing**: α_min → α_core > 0.
3. **Phase-boundary migration**: under continued mass injection, r_c
   expands while interior homogeneity is preserved.
4. **Multipole shadow**: exterior metric carries an
   O(ℓ_*² / r³) correction → measurably larger photon sphere than
   Schwarzschild for the same ADM mass.

---

## VIII. Stage 3 — Perturbative Transport, Spectral Stability,
Observability

### 3A. Linearised operator and spectral stability

Linearise around the saturated Stage-2 background Ψ^(0) and Fourier
transform: δΨ ∼ exp i(kr − ωt). The dispersion relation

> 𝓛(ω, k) δΨ = 0

must satisfy the **Whitham subcharacteristic condition**:

> Im ω_n ≤ 0 for all roots

The high-frequency "frozen" waves governed by V''(M) must bound the
causal characteristics of the geometric envelope, otherwise the
relaxation lag τ_M triggers a delayed-feedback resonance.

### 3B. Pseudospectral envelope (isotropisation)

Spectral stability is necessary but not sufficient: non-normal
transients can grow. The stability constraint reduces to a direct
competition between geometric shear production σ_D and thermodynamic
isotropisation Γ_iso:

> The Entropy Wall is stable iff V''(M) isotropises infalling shear
> faster than 1/r geometric focusing amplifies it.

### 3C. Scattering matrix and impedance

Defining the impedance bifurcation parameter χ = σ_D / Γ_iso:

- **χ ≪ 1** (perfect absorber): R(ω) → 0; ringdown matches GR.
- **χ ∼ 1** (anisotropic crust): R(ω) > 0; impedance spikes at
  resonance, producing partial reflection.

### 3D. Resonance manifold — the spectral comb

When χ ∼ 1, dispersive reflection produces a **Wigner time delay**:

> Δt_echo = Δt_geom + τ_M

Echoes are quantised in the cavity between the photon sphere and the
entropy wall. The comb spacing is the **direct observable** of the
universe's informational relaxation rate.

(This is where the Menger sponge substrate becomes predictive: see
`RSLS_menger_substrate.md` for the log-periodic comb structure that
follows from discrete scale invariance.)

### 3E–F. Detectability and inverse constraint

To beat the exponential decay of standard GR ringdown above the noise
floor:

> The fundamental length ℓ_* must satisfy
> ℓ_* ≳ 10⁻¹¹ M (in geometric units)

i.e., not Planckian. Setting ℓ_* = L_Planck attenuates the signal by
hundreds of orders of magnitude — it would be unobservable. A
macroscopic ℓ_* is therefore not an aesthetic preference but a
falsifiability requirement.

---

## IX. Stage 4 — Global Well-Posedness

### 4A. Entropy variables and renormalised symmetrisation

To admit a uniform symmetriser S(U) = ∇²_U η(U) with η strictly
convex, the coupling κ must scale not with the barrier stiffness
V''(M) but with the relaxation lag:

> κ ∝ τ_M

This quarantines the divergent V''(M) into the algebraic source block
and keeps the principal symbol non-singular.

### 4B. Uniform hyperbolicity and characteristic decoupling

Applying a diagonal weight W, the renormalised symmetriser
S̃ = W S W absorbs the 1/ε divergence (ε = τ_M / V''(M)) without
touching the transport fluxes A^r. The characteristic polynomial

> det(Ã^r − c S̃) = 0

factors into two sectors:

1. Geometric/fluid transport: bounded speeds c_± ∼ ±c_s ± U^r.
2. Memory transport: c_M = 0 exactly.

The entropy wall is a **critically damped impedance converter**: the
infinite stiffness halts geometric collapse, but because c_M = 0 it
cannot propagate outward as a shock.

### 4C. Diffuse regularisation and BV closure

The degenerate limit τ_M → 0 risks a Gradient Catastrophe. Elevate
the entropy to H¹-coercivity with an intrinsic stiffness modulus
μ > 0:

> 𝓛_M → 𝓛_M − μ |∇M|²

This adds a parabolic gradient penalty −μ ΔM to the relaxation
operator. The wall thickness emerges as

> ℓ_*² ≈ μ / V''(M)

The "Entropy Wall" is now a finite, continuous **diffuse-interface
phase boundary** in BV space.

### 4D. NEC compliance

The gradient penalty backreacts through

> T^{(∇M)}_{μν} = ∂_μ M ∂_ν M − ½ g_{μν} ∂_α M ∂^α M

Contracting with any null vector k^μ:

> T^{(∇M)}_{μν} k^μ k^ν = (k^μ ∂_μ M)² ≥ 0

So long as μ > 0 the Null Energy Condition is strictly satisfied.
Collapse is halted by **incompressible jamming** — radial pressure
diverges while tangential pressure stays soft, locking the geometry
into an effectively rigid radial equation of state. No exotic
negative energy is invoked.

### 4E. Maxwell–Cattaneo causal transport

The parabolic −μ ΔM has infinite signal speed: violates causality. We
promote the gradient to a dynamical flux J_μ:

> τ_J ∂_t J_μ + J_μ = − μ ∇_μ M

A causal telegrapher's equation. Characteristic velocity:

> c_diff² = μ / (τ_J τ_M)

For relativistic causality (c_diff ≤ 1):

> μ ≤ τ_J τ_M

### 4F. Self-quenching failsafe

The fully coupled Einstein–Cattaneo manifold has three characteristic
families: geometric, fluid, and entropy-flux. The threat is
**compound-mode collapse** (relaxation caustics) if c_geom ≈ c_J.

RSLS forbids this via a nonlinear negative-feedback loop:

1. Geometric focusing drives M → M_max.
2. V''(M) → ∞ ⇒ effective bulk modulus diverges
   ⇒ expansion scalar θ = ∇_μ U^μ → 0.
3. Geometric driver shuts off dynamically, severing mode coupling
   before resonance forms.
4. Causal telegrapher damping 1/τ_J regains dominance.

Continuation criterion:

> 𝒢_focus < Γ_iso × (V''(M)·τ_M)

where 𝒢_focus is the nonlinear compression gain and Γ_iso the
anisotropic isotropisation rate.

---

## X. Statistical Reduction (KvN → Lindblad → Born)

As M → M_max the continuum stiffens infinitely. The classical flow
on (*M*, g_{μν}) lifts to a Hilbert space via Koopman–von Neumann:

> 𝓗_QM = L²(*M*, √(−g) d⁴x)

The Liouvillian L̂ = − i U^μ ∇_μ generates unitary evolution. As
the local environmental correlation rate

> γ(M) = γ_0 exp[Δ / (M_max − M)]

outpaces every curvature invariant, unitary flow breaks down into a
Lindblad dissipator:

> ∂_t ρ = − i [Ĥ, ρ] + Σ_k ( L̂_k ρ L̂_k† − ½ {L̂_k† L̂_k, ρ} )

The system settles on the Sinai–Ruelle–Bowen invariant measure of the
chaotic scattering, and

> P_i = ∫_{Γ_i} |Ψ|² dΓ

The **Born rule emerges** as the ergodic limit of informational
saturation — not postulated.

---

## XI. Computational Stratification

Numerical implementation in three layers:

1. **Positivity-preserving transport** (explicit):
   HLL Riemann fluxes + entropy-stable flux limiter (MinMod). Discrete
   Maximum Principle forbids M ≥ M_max.

2. **Stiff source containment** (implicit):
   V(M) and the dissipative coupling solved via bounded Newton–Krylov;
   constraint projection prevents overshoots.

3. **Scale separation** (AMR):
   Refinement triggered strictly by |∇M| and |∇·U|. The
   Menger-sponge substrate (see `RSLS_menger_substrate.md`) realises
   this layer as a deterministic 1:3 fractal AMR.

---

## XII. Variable Index

(For the full reconciled variable list spanning RSLS field theory,
acoustic-sphere hardware geometry, and the semantic engine, see
`THEORY_variable_list.md`. The RSLS-specific subset is reproduced
below for convenience.)

| Symbol | Meaning |
|--------|---------|
| g_{μν} | Lorentzian metric |
| U^μ | Timelike information flow, U^μ U_μ = 1 |
| M | Thermodynamic memory, M ∈ [0, M_max) |
| M_max | Saturation bound |
| V(M) | Singular convex barrier (holographic wall) |
| α(t,r) | Dynamic lapse |
| β^r(t,r) | Radial shift |
| ℓ_* | Emergent relaxation length scale |
| τ_M | Memory relaxation time |
| τ_J | Entropy-flux relaxation time |
| μ | Intrinsic stiffness modulus |
| J_μ | Dynamical entropy-gradient flux |
| θ = ∇_μ U^μ | Expansion scalar |
| κ_M | Memory-compression coupling, κ_M ∝ τ_M |
| β | Memory–flow coupling (Lagrangian) |
| γ_C | Constraint damping rate |
| c_eff = √(μ/τ_J) | HLL signal speed |
| c_diff = √(μ/(τ_J τ_M)) | Causal diffusion speed |
| 𝒢_focus | Nonlinear compression gain |
| Γ_iso | Anisotropic isotropisation rate |
| T^{(∇M)}_{μν} | Gradient stress (NEC-compliant) |

---

## XIII. Status

The RSLS is closed as a Cauchy problem. The spacetime fabric is a
relativistic viscoelastic phase-transition medium, structurally
conservative (NEC compliant), strictly causal (Maxwell–Cattaneo
hyperbolised), and dynamically immune to relaxation caustics via the
Stage 4F self-quenching loop.

Outstanding falsifiability checkpoints (where the theory could fail):

- Phase A: ℓ_* grid-independence (numerical, in this build).
- Stage 2: lapse freezing α_min > 0 (numerical, future build).
- Stage 3D: log-periodic echo spacing in LIGO/LISA ringdown data
  (observational; the Menger substrate sharpens the prediction).
- Stage 3E: macroscopic ℓ_* ≳ 10⁻¹¹ M as a hard observability bound.

The Phase A falsification kernel is implemented in `uma/rsls/phase_a.py`
and the dx → 0 convergence study runs in `examples/rsls_phase_a.py`.

---

## XIV. Stage 5 — Frame-Dragging Closure (Cone Invariance)

Stages 1–4 establish global well-posedness on a spherically symmetric
background. The architectural pivot — encoded in the most recent state
of the specification — is that the **shift vector itself must carry the
non-equilibrium driver**. Spherical symmetry is too restrictive: it
permits only a *transient* chaos, dissipated as soon as numerical or
physical viscosity takes hold. The GKLS (Lindblad) limit requires the
mixing to be *structural*, encoded into the manifold connection.

The geometric ingredient is **azimuthal frame-dragging**: a non-zero
shift β^φ in the cylindrical reduction.

### 14.1 The 1.5-D cylindrical reduction

To make the Cauchy problem tractable while preserving the structural
shear, we reduce to cylindrical symmetry (∂_φ = ∂_z = 0):

> ds² = − α²(t,R) dt² + (dR + β^R dt)² + R² (dφ + β^φ dt)² + dz²

Coordinates R ∈ (ε, R_max], with R = 0 punctured to avoid the regular-
isation trap. State vector

> **Q** = [ R ρ, R S_R, R S_φ, R M ]ᵀ

where S_R = ρ U^R, S_φ = ρ U^φ.

### 14.2 Modified characteristic structure

The flux Jacobian A = ∂F/∂U evaluated on the saturation manifold yields
radial characteristic speeds shifted by the coordinate velocity. With
c_diff = √(μ / τ_J) the intrinsic entropy-transport speed and the
geometric shear production term

> 𝒢 = β^φ R ∂_R(β^φ)   +  (off-diagonal stress contribution)

the cone-aperture eigenvalues are

> Λ_± = β^R  ±  √( c_diff² + 𝒢 )

The **cone aperture**

> ΔΛ := Λ_+ − Λ_− = 2 √( c_diff² + 𝒢 )

must satisfy

> ΔΛ > 2 c_diff        ⇔        𝒢 > 0

i.e. the geometric shear must produce a strictly wider unstable cone
than the intrinsic causal damping. Equivalently:

> The unstable bundle E^u has a strictly positive minimum opening
> angle iff frame-dragging is active (β^φ ≠ 0 and ∂_R β^φ ≠ 0).

### 14.3 Off-diagonal stress

The off-diagonal stress component

> T_{Rφ} = ρ U^R U^φ + (Cattaneo cross-term)

is computed via *staggered flux correlation*: S_R lives at radial cell
centres, S_φ at radial cell faces, with the cross-product evaluated by
averaging without artificial damping. This preserves the structural
chaos that vanilla centred differencing would smear out.

### 14.4 Cone compression factor

At each timestep the solver computes

> η(R, t) := ΔΛ(R, t+dt) / ΔΛ(R, t)

If η < 1 uniformly across the saturation layer, tangent vectors are
being mapped *into* the expanding subspace E^u — the discrete signature
of an **Anosov splitting**. The cone is forward-invariant in the strict
sense.

### 14.5 The Anosov–GKLS bridge

A uniformly hyperbolic invariant set with the Anosov property satisfies
exponential decay of correlations. Coarse-graining over the unstable
bundle produces a Markovian master equation — exactly the GKLS
(Lindblad) form anticipated by Stage X. The frame-dragging closure
therefore *derives* (rather than postulates) the quantum-statistical
limit from the geometric structure of the manifold.

### 14.6 Success criteria for the Stage-5 kernel

A Stage-5 numerical run successfully demonstrates the frame-dragging
closure if and only if:

1. **Cone aperture positive**: min_R ΔΛ(R, t) − 2 c_diff > 0 for all t
   in the integration window.
2. **Cone compression η < 1**: across the saturation layer, all
   timesteps.
3. **Lyapunov exponent positive**: λ_max(R, t) > 0 in the saturation
   layer, indicating sensitive dependence on initial conditions.
4. **Correlation decay**: ⟨S_R(t) S_R(0)⟩ / ⟨S_R(0)²⟩ → 0 exponentially
   in t — the observable signature of Anosov mixing.

### 14.7 Implementation

- **Spec**: this section.
- **Code**: `uma/rsls/frame_dragging.py` (the kernel),
  `uma/rsls/stage3.py` (the perturbative analysis — Whitham bound,
  Wigner delay, reflection coefficient, detectability bound),
  `uma/rsls/srb.py` (Lyapunov + GKLS demonstration on the Lorenz
  attractor as a verified anchor).
- **Demo**: `examples/rsls_frame_dragging.py`.
- **Tests**: `tests/test_frame_dragging.py`, `tests/test_stage3.py`,
  `tests/test_srb.py`.

### 14.8 Falsifiability

The Stage-5 closure is falsified if any of the following hold for the
implemented kernel:

- ΔΛ(R, t) − 2 c_diff → 0 as resolution is refined (the cone closes —
  the frame-dragging does not produce structural shear).
- η ≥ 1 in a sustained interval (the discrete map is not contracting
  onto E^u — Anosov splitting fails).
- λ_max ≤ 0 on the saturation manifold (no positive Lyapunov exponent
  — no chaos to coarse-grain).

Each is a concrete, measurable failure mode. None is currently
expected from the theory, but each is the experimental signature that
would force a revision.

