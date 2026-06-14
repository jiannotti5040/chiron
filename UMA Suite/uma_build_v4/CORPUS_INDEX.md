# CORPUS_INDEX.md

Discovery date: 2026-05-10. Outside any project. Sweep covered uploaded
bundle (`Uma_2.zip`, 22 PDFs + Venturi.txt) and conversation_search across
prior build sessions.

## Uploaded canonical PDFs (Uma_2.zip)

These are the user's canonical UMA package sources, exported as PDFs.
Each PDF maps to one module of the package. Where pdftotext-extracted
indentation was damaged at page breaks, the module was reconstructed
faithfully against the PDF structure; reconstructions are noted in
YOUR_NOTES.md.

| PDF                       | Module path                        | Notes |
|---------------------------|------------------------------------|-------|
| sphere_geometry.pdf       | uma/sphere/geometry.py             | Bessel-zero derivation, AcousticSphereGeometry, SystemGeometry |
| sphere_field.pdf          | uma/sphere/field.py                | SphereProjectionField, SpherePendulum, SphereVenturi |
| sphere__init.pdf          | uma/sphere/__init__.py             | Sphere subpackage exports |
| sphere_derivation.pdf     | docs/THEORY_sphere_derivation.md   | "Inside Out" derivation theory |
| sphere_uma_execution.pdf  | examples/sphere_uma_execution.py   | Example runner |
| Venturi.pdf               | uma/venturi/operator.py            | VenturiOperator (360-degree evolving) |
| venturi_init.pdf          | uma/venturi/__init__.py            | Venturi subpackage exports |
| ir.pdf                    | uma/semantic/ir.py                 | UMA_IR + IRNode |
| executor.pdf              | uma/semantic/executor.py           | UMAExecutor + ExecutorResult |
| engine.pdf                | uma/semantic/engine.py             | SemanticEngine + tokenize_to_binary_weight |
| friction.pdf              | uma/semantic/friction.py           | SemanticFriction with H-tracking |
| constraints.pdf           | uma/semantic/constraints.py        | ConstraintSet + Alpha/Beta/Gamma + Dykstra |
| inarticulation.pdf        | uma/semantic/inarticulation.py     | Inarticulator + ProductionMetrics |
| constants.pdf             | uma/semantic/constants.py          | Calibrated H-target, dH_dt_floor, field_scale |
| init.pdf                  | uma/semantic/__init__.py           | Semantic subpackage exports |
| calibrate.pdf             | calibrate.py                       | 50-trajectory calibration script |
| tensor_bridge.pdf         | uma/msr/tensor_bridge.py           | <T_µν> ↔ G_µν^(1) live tracker |
| nonlinear_gr.pdf          | uma/msr/nonlinear_gr.py            | Full Christoffel/Ricci/Einstein |
| metric_solver.pdf         | uma/msr/metric_solver.py           | Self-consistent metric iteration |
| gr_fixed_point.pdf        | uma/msr/gr_fixed_point.py          | ψ* minimizing Einstein residual |
| pipeline.pdf              | uma/pipeline.py                    | UMAPipeline + UMAPipelineResult — the 15-module integrator |
| test_semantic.pdf         | tests/test_semantic.py             | Engine3-correct architecture tests |

## Synthesis documents (uploaded)

- `Unified_Master_Architecture__UMA__and_the_Recursiv___.pdf` — comprehensive
  field-theoretic synthesis. Stored as `docs/THEORY_unified_synthesis.md`.
- `Variable_list.pdf` — variable definitions across all domains. Stored as
  `docs/THEORY_variable_list.md`.
- `Left_to_do_as_is.pdf` — singularity avoidance as thermodynamic stiffness
  transition. Stored as `docs/THEORY_biggest_advance.md`.

## Past chat sessions surfaced via conversation_search

| Session | Date | URL fragment | Content |
|---|---|---|---|
| Assembling project components into runnable package | 2026-05-10 | 9ee3abda-aa18-4df9-9b61-89fe141e9064 | Most recent build. Architecture, calibrated thresholds, 12-test suite. |
| Integrating semantic engine into UMA system | 2026-05-06 | 3899d836-4760-4dd3-b858-98ffc27cf703 | SemanticEngine compile/run, noether_stress_tensor, three-layer split: physics / observer / controller. |
| System review and development framework | 2026-04-23 | 96a1035d-9928-454b-ac69-83bc8d8e2ff9 | UMA v1 (72 files), UMA v2 (24 files), full module map, GENERIC degeneracy, Lyapunov regime control. |
| File handling request | 2026-04-08 | 15cb3d0f-2192-43f6-b5a5-7b09303f3c86 | URF White Paper review, H_URF = -F bridge, signature flip as harmony/disharmony. |
| Clarifying intent for dropped code | 2026-04-07 | b9b903fc-994d-4081-8bf1-284c576621ce | TopologicalEngine v2.1.0, winding-number invariant b, RG-feedback, ΔT closure test, GR conformal back-reaction. |

## Named objects (verbatim from corpus)

### Geometry / Sphere
- `j_nl` — exact zero of spherical Bessel j_n. `j_{0,1} = π`, `j_{0,2} = 2π`.
- `R` — internal sphere radius = L/2.
- `k_nl = j_nl / R` — wavenumber.
- `f_nl = c_air · k_nl / (2π)` — resonant frequency.
- `L_pend = g / (4π² · f_nl²)` — pendulum length, locks period to 1/f.
- `r_0 = R · j_nl / π` — Venturi throat (exact Bessel resonance).
- `r_in = R · j_(n-1)l / π` — Venturi inner cutoff.
- `G = 1 - (r_in/r_0)²` — Bernoulli gain (derived, not tunable).
- `d = λ · √(r_0² + D²) / r_0` — blind-gate diffraction spacing.
- `c_air · j_nl / R = h·ν / kT` — interference convergence (locks fan modulation to stellar T).

### Field dynamics (GENERIC)
- `ψ` — primary continuous complex field state.
- `ψ̂` — exact MSR response = `-dH/dψ*`.
- `H[ψ]` — actual GENERIC Hamiltonian.
- `S[ψ]` — entropy production functional.
- `dt` — discrete time step.

### Semantic / projection
- `z` — projected lower-dimensional state vector (leading Fourier modes).
- `x` — discrete binary weight from text vs anchor "dIse".
- `z_c = x · ((1-√2) + i√e)` — Engine3 complex state seed (encoding design choice, not derived).
- `E^* = kT / Δ_S²` — historical Silver-Ratio target (retracted as derivation; preserved as encoding).
- `Δ_S = 1 + √2` — Silver Ratio (kept as encoding constant).

### Constraints (UMA Equalities, Dykstra projection)
- `Alpha` — `a · z = b` hyperplane (LinearConstraint, anchors structural compilation boundary).
- `Beta` — ball constraint (V:$).
- `Gamma` — quadratic ellipsoid constraint with Q (Fisher information).
- `tol = 1e-6` — Dykstra convergence tolerance.

### Calibrated thresholds (50-trajectory baseline)
- `H_target = 1.092794`
- `H_std = 0.255051`
- `dH_dt_floor = 1.292312`
- `dH_dt_p25 = 0.519153`
- `field_scale = 0.175200`

### Closure conditions (3 simultaneous)
1. friction < 0.15
2. |dH/dt| < dH_dt_floor
3. ||z - z*|| < 2 · field_scale

### Tensor Bridge / GR
- `T_µν` — MSR stress-energy from `ψ̂ · ∂_i ψ` real-part contractions.
- `h_µν` — metric perturbation from Poisson `∇²h = -16πG T`.
- `G^(1)_µν` — linearized Einstein tensor from h.
- `κ` — least-squares slope `<T> = κ · <G>`.
- `metric_tol = 0.01` — self-consistent solver convergence.

### Inarticulation outputs
- `ProductionMetrics`: semantic_density = 1 - friction, trajectory_delta = ||z_Ω - z_target||, scaling_coefficient = det(Σ)^(-1/d).
- Stages: Ingestion (>0.50) / Stability (0.20-0.50) / Inarticulation (<0.20, !closed) / Solve (closed).

### RSLS field theory (4-D pseudo-Riemannian, signature +---)
- `g_µν, U^µ, M, V(M), α, β^r, β^φ, ℓ_*, τ_M, τ_J, µ, J_µ, θ, κ`.

### Statistical reduction
- `Ψ` — KvN classical wavefunction in `H_QM = L²(M, √-g d⁴x)`.
- `L̂ = -i U^µ ∇_µ` — Liouvillian.
- `γ(M) = γ_0 · exp(Δ/(M_max - M))` — exponential decoherence rate at the wall.
- Lindblad master equation in saturation limit.
- SRB measure → Born rule emergence.

## Sensitive-review-needed flags

None at this layer. The user's prompt explicitly excluded personal /
litigation / poetry material. The corpus surfaced here is exclusively
technical.
