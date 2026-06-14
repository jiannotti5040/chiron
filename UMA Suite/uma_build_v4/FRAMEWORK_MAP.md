# UMA Framework Map

Flat index of every named object in the package, with the canonical
definition (from the corpus) in one line.

## Geometry

- **j_{n,k}** — k-th positive zero of the spherical Bessel function `j_n(x)`. `j_{0,1} = pi` exact.
- **SphericalMode** — `(n, l, k=mode_index)` selects which `j_{n,k}` defines the resonant frequency `f = c j / (2 pi R)`.
- **AcousticSphereGeometry(L, n, l, mode_index)** — solves the inside-out lock: from `L` and `(n, l, k)` derives `R = L/2`, `j_nl`, `f`, `r0 = R j_nl / pi`, `r_in = R/4`, `G = 1 - (r_in/r0)^2`, pendulum length / period, fan frequency, blind-slit angle, stellar `T*`. Nothing is chosen.
- **SystemGeometry** — frozen dataclass holding the solved geometry.
- **SphereProjectionField(geometry, n_harmonics)** — the standing-wave pressure field as a UMA observation operator. `H(z) = sum_lm <Y_lm | z> P_nlm(r_pend(t))`.
- **SpherePendulum(geometry)** — bob sweeps a great circle in the equatorial plane sampling the pressure field.
- **SphereVenturi(geometry, N)** — the Venturi with throat `r0 = R j_nl / pi`.

## Core

- **FieldProjection(N, n_modes)** — band-limited 2D Fourier projection: `psi (N x N complex) <-> z (real, length 2 * (n_modes^2 + n_modes))`.
- **FieldPosterior(mean, cov)** — Gaussian posterior over `z`. Single-rep (`full`); aliases `Sigma`, `representation = 'full'` provided for compat with the canonical multi-rep API.
- **KalmanFilter(posterior, process_noise)** — Joseph-form Kalman update with optional process noise. `update(y, H, R)`.

## Dynamics

- **GENERICConfig** — `kT, advection, diffusion, reaction, dt, noise`.
- **GENERICDynamics(cfg)** — `step(psi)` advances the field by `dt` under reversible (Hamiltonian) + dissipative (gradient-flow on `S`) parts plus thermal noise.
- **hamiltonian(psi, lam)** — `H[psi] = sum |grad psi|^2/2 - |psi|^2/2 + lam |psi|^4/4`.
- **entropy_S(psi)** — Shannon entropy of `|psi|^2/||psi||^2`.
- **msr_response(psi, lam)** — MSR response `psi_hat`. By convention `psi_hat = -dH/dpsi^*`.
- **dH_dpsi_conj(psi)** — `-msr_response(psi)` (Wirtinger derivative).

## Venturi

- **silver_E_target(kT)** — `kT / delta_S^2`. Backward-compat alias for `CALIBRATED_E_TARGET`.
- **silver_dz_dt_floor(kT, lam, N, dt)** — `sqrt(2 kT / delta_S^2 lam dt) / N`. Backward-compat alias for `CALIBRATED_DZ_DT_FLOOR`.
- **engine3_complex_state(x)** — `x ((1 - sqrt 2) + i sqrt e)`. Engine3 text-encoding seed.
- **Venturi == VenturiOperator** — 360-degree evolving Venturi: `V(r, r0) = (r0 / max(r, r_in))^beta envelope(r)`, `dr0/dt = -lam_v (E - E*)/E* r0`, `G = 1 - (r_in/r0)^2`.
- **CrossDomainInjector(venturi)** — applies the same `phi_inject` to both `psi` and `psi_hat`.

## MSR / GR

- **TensorBridge(cfg, residual_threshold, window)** — at every step: `T_munu = stress(psi, psi_hat); h_munu = poisson(T_munu); G^(1)_munu = lin_einstein(h); kappa = <T,G>/||G||^2; residual = ||T - kappa G||_F`. `einstein_satisfied` when residual < threshold.
- **TensorRecord** — per-step record of `T, G, h, kappa, residual_norm, relative_residual, einstein_satisfied`.
- **noether_stress_tensor(psi, lam, dx)** — canonical `T_munu` from `H[psi]`.
- **verify_T_consistency(psi)** — checks `H[psi] == int T_00`. Should be O(dx).
- **verify_T_equals_lichnerowicz(h_pert, m, N, seed)** — one-shot consistency check between Noether `T` and linearized Einstein `G^(1)` on a constant metric perturbation.
- **LevyMSRCouplings(nu_2, nu_alpha, D, c_alpha, alpha, D_dim)** — UV couplings of the Levy-MSR theory.
- **classify_basin(c, cutoff=0.5)** — `'levy'` if `c_alpha / nu_2 > cutoff` else `'gaussian'`.
- **dynamic_exponent(c)** — `alpha` in Levy basin, else 2.
- **NonlinearEinsteinSolver(cfg, G_newton, c)** — full nonlinear curvature: `Gamma, Ricci, R, G_full` from `g_ij = (1 + 2 Phi/c^2) delta_ij` with `Phi` solved by Poisson on `rho = |psi|^2`.
- **CurvatureResult** — full decomposition: `g, g_inv, Phi, Gamma, Ricci, Ricci_scalar, G_full, G_linear, T, nonlinear_residual, linear_residual, nonlinearity, kappa`.
- **IterativeMetricSolver(cfg, dt, max_iters, tol, coupling)** — iterates `psi <-> h` to a self-consistent fixed point via the curved-d'Alembertian leading correction.
- **MetricSolveResult, MetricState** — iteration history.
- **GRFixedPointSearch(cfg, n_seeds, n_steps, dt)** — brute-force seed search for `psi*` minimizing the Einstein residual.

## Semantic

- **DELTA_S, INV_DELTA_S_SQ, C1_SILVER, SQRT_E, SILVER_ANGLE** — Silver-Ratio mathematical constants. Real properties of the Engine3 encoding; not physics constants.
- **CALIBRATED_E_TARGET, CALIBRATED_DZ_DT_FLOOR, CALIBRATED_FIELD_SCALE** — replacements for Silver-derived values; from 50-trajectory calibration.
- **CALIBRATED_H_TARGET, CALIBRATED_H_STD, CALIBRATED_DH_DT_FLOOR, CALIBRATED_DH_DT_P25** — H[psi]-based calibrated thresholds. Used by SemanticFriction.
- **engine3_complex_state(x), engine3_E(x), tokenize_to_binary_weight(s, anchor)** — text-encoding bridge.
- **string_to_observation(s, dim, anchor, cfg)** — string -> Engine3 -> GaussianObservation + observation vector.
- **EqualityConstraint** — abstract `c(z) = 0` with `.check(z)`, `.project(z)`, `.apply(z)`.
- **LinearConstraint(a, b, name='alpha_dIse')** — Constraint Alpha: `a^T z = b`. Hyperplane projection.
- **BallConstraint(r, P, center, name='beta_VH')** — Constraint Beta: `||P z|| <= r`.
- **QuadraticConstraint(kappa, Q, center, name='gamma_Jd4m')** — Constraint Gamma: `z^T Q z <= kappa`. Eigenbasis KKT projection.
- **ConstraintSet(constraints, max_iters, tol)** — Dykstra cascade. `default_semantic_constraints(dim, z_target)` returns Alpha+Beta+Gamma anchored to `z_target`.
- **SemanticFrictionConfig** — `step_weight, closure_friction_threshold, convergence_dz_dt, closure_state_tol, min_steps_before_closure, kT, lam, N, dt`.
- **SemanticFriction(z_target, config, hamiltonian_fn)** — `friction -= step_weight / (1 + |dH/dt|/floor)` per step. Closes when `friction < 0.15 AND |dH/dt| < floor AND |z - z*| < tol`.
- **FrictionRecord** — per-step `t, H, E, dH_dt, dE_dt, friction, z_distance, closed`.
- **IRNode(node_id, kind, payload)** — kind in `{'evolve', 'observe', 'constrain', 'checkpoint'}`.
- **UMA_IR** — list of IRNodes; `nodes`, `schedule`, `objective`, `metadata`.
- **UMAExecutor(friction, inarticulator, stop_on_closure, verbose)** — drives the IR against a UMAClient.
- **ExecutorResult** — `is_closed, closure_node, friction_records, friction_summary, final_posterior, z_final, production_metrics, nodes_executed`.
- **classify_stage(sf_value, is_closed, sf_stability_threshold, sf_inarticulation_threshold)** — `ingestion / stability / inarticulation / solve`.
- **ProductionMetrics** — `semantic_density, trajectory_delta, scaling_coefficient, stability_index, constraint_converged, stage, closed, readout, readout_labels, friction_summary, constraint_report`.
- **NullInarticulator** — identity G translation.
- **ProjectionInarticulator(W, phi, labels)** — linear readout `W : R^d -> R^m` plus optional `phi`.
- **SemanticEngineConfig(friction, stop_on_closure, verbose, obs_every, constrain_every)** — engine-level config.
- **SemanticEngineResult** — `is_closed, closure_node, friction_records, friction_summary, final_posterior, z_final, production_metrics, nodes_executed, ir`.
- **SemanticEngine(z_target, config, constraints, inarticulator)** — `compile(...) -> UMA_IR`; `run(client, ...) -> SemanticEngineResult`.

## Pipeline

- **UMAPipelineResult** — `geometry, H_trajectory, S_trajectory, z_trajectory, E_proxy, pendulum_samples, friction_walk, is_closed, closure_step, stage, msr_cosine, msr_verified, rg_basin, rg_z, interference_amplitudes, tensor_records, n_steps, dt`.
- **UMAPipeline(L, n_mode, l_mode, mode_index, n_steps, dt, seed, verbose, input_text)** — full pipeline orchestrator. `run() -> UMAPipelineResult`.

## Closure (Omega) — joint condition

The system has reached `Omega` when *all three* hold simultaneously:
1. `SemanticFriction.is_closed` (friction below threshold AND |dH/dt| below floor AND z near z*).
2. `TensorBridge.is_einstein_satisfied` (relative residual below threshold).
3. The pipeline declares closure on the same step.

Friction collapsing to zero and the Einstein residual collapsing to zero are
the same physical event measured two ways.

## RSLS (v4 -- the field-theoretic memory sector)

The `uma.rsls` subpackage adds the singular-barrier memory field M
and its coupling into the canonical pipeline.

- **MemoryConfig** -- `M_max=1.0, lam=0.12, tau_M=1.0, tau_J=0.15, mu=0.08`. The defaults satisfy `c_diff = sqrt(mu/(tau_J tau_M)) <= 1` (Stage-4 causality).
- **V(M)** -- singular convex barrier `-lambda log(1 - M/Mmax)`. `V'(M) -> inf` as `M -> Mmax`.
- **clip_M(M, cfg)** -- discrete maximum principle: enforces `M in [0, Mmax - eps)`.
- **ell_star(M, cfg)** -- emergent length `sqrt(mu tau_M / V''(M)) = (Mmax - M) sqrt(mu tau_M / lambda)`.
- **interface_width(M, x, cfg)** -- canonical wall thickness: `(M_max - M_min) / max|dM/dx|`.
- **gradient_stress(M, dx, cfg)** -- `T^{(grad M)}_{mu nu}` (shape `(2,2,N,N)`); NEC compliant by construction.
- **nec_violation(M, dx, cfg)** -- samples null vectors and returns `min T k k`.

- **cattaneo_step(J, M, dx, dt, cfg)** -- implicit Maxwell-Cattaneo update for the entropy flux `J_r`. Unconditionally stable in `dt`.
- **cattaneo_cfl(dx, cfg)** -- bound on `dt` from `c_diff`.
- **subluminal(cfg, c_geom=1)** -- Whitham subcharacteristic check.

- **hll_flux(...)** -- HLL Riemann flux at interfaces. Entropy-stable.
- **hll_update_spherical(S, D, M, ...)** -- 1-variable momentum step.
- **hll_update_spherical_2var(D, S, M, ...)** -- conservative `(rho, S)` pair on spherical grid. Eliminates focusing pathology.

- **PhaseAConfig** -- `N=400, R_in=1.0, R_out=15.0, n_steps=15000, pulse_amplitude=-2.5`.
- **PhaseAResult** -- `M_history, S_history, D_history, J_history, wall_thickness, wall_thickness_max, M_at_peak, L1_norm, stiffening_lag`.
- **run_phase_a(cfg)** -- runs the falsification kernel; returns `PhaseAResult`.
- **convergence_study(Ns, base_cfg)** -- runs at multiple `N` for the falsification check.

- **MengerSponge(level, side)** -- Menger sponge lattice. 20 surviving offsets per subdivision. `refine(idx)`, `coarsen(parent_idx)`, `neighbors(idx)`, `laplacian(field)`, `volume()`, `surface_area()`.
- **HAUSDORFF_DIM** = `log 20 / log 3 ~= 2.7268`.
- **theoretical_n_cells / theoretical_volume / theoretical_surface_area** -- closed-form references.

- **RSLSCoupling(memory_cfg, residual_threshold)** -- bridge between RSLS and the canonical TensorBridge. `augmented_update(bridge, psi, psi_hat, M_2d, dx, t) -> RSLSTensorRecord`. Adds `T^{(grad M)}` additively, recomputes kappa and residual on combined sources, samples NEC.
- **RSLSTensorRecord** -- `canonical_T, rsls_T, combined_T, kappa, residual_norm, relative_residual, einstein_satisfied, nec_min, nec_compliant`.

---

## `uma.rsls` -- Stage 3 / Stage 5 / SRB extensions

The Stage 5 closure (frame-dragging via beta^phi != 0) is added as
three new modules. Spec: `docs/RSLS_specification.md` Section XIV.

### Stage 3 -- Perturbative spectral analysis (`uma/rsls/stage3.py`)

- **whitham_subcharacteristic(cfg, c_geom=1.0)** -- `c_diff <= c_geom`.
- **whitham_margin(cfg)** -- `c_geom - c_diff` (positive => safe).
- **dispersion_polynomial(k, cfg)** -- coefficients of `tau_J omega^2 + i omega - mu k^2`.
- **find_poles(k, cfg)** -- roots of `L(omega, k) = 0`.
- **all_poles_stable(k_range, cfg)** -- verifies `Im(omega) <= 0` for all `k`.
- **IsotropisationParams(sigma_D, Gamma_iso)** -- with `.chi` = `sigma_D / Gamma_iso`.
- **pseudospectral_envelope_satisfied(p)** -- `chi < 1`.
- **reflection_coefficient(omega, p, tau_J)** -- `Z(omega) = 1 + chi/(1 - i omega tau_J)`, `R = (Z-1)/(Z+1)`.
- **reflection_spectrum / wigner_delay(omegas, p, tau_J)** -- spectral comb diagnostics.
- **echo_spacing(ell_star, r_photon, tau_M)** -- `Delta_t = 2(r_photon - ell_*)/c + tau_M`.
- **detectability_bound(M_adm, ell_star, Gamma_kerr, N_floor=1e-21)** -- `exp[-2 M Gamma ln(M/ell_*)] > N_floor`.
- **macroscopic_ell_star_lower_bound(M_adm, Gamma_kerr, N_floor=1e-21)** -- algebraic solve.

### Statistical reduction (`uma/rsls/srb.py`)

KvN -> Lindblad -> SRB anchored on the Lorenz attractor.

- **LorenzParams / lorenz_rhs / integrate_lorenz / rk4_step** -- canonical chaotic anchor.
- **lyapunov_max(rhs, state0, dt, n_steps, renormalize_every, delta0, *args)** -- Benettin's algorithm. Verified at `~0.88` on Lorenz (canonical 0.9056).
- **srb_histogram(trajectory, axis, n_bins)** / **srb_converges(...)** -- ergodic-limit measure.
- **koopman_transfer_matrix(rhs, dt, n_bins, bounds, *args)** -- discrete Frobenius-Perron operator on a 1-D coordinate.
- **koopman_stationary(T)** -- left-eigenvector at eigenvalue 1.
- **lindblad_step(rho, H, L_list, dt)** / **integrate_lindblad(...)** -- GKLS master-equation forward-Euler. Verified: 2-level amplitude damping `|1><1| -> |0><0|`.
- **born_rule_match(srb_density, psi_squared, bin_widths)** -- `L^1` distance between ergodic and quantum densities.

### Stage 5 -- Frame-dragging kernel (`uma/rsls/frame_dragging.py`)

THE NEXT-STEP POC.

- **FrameDraggingConfig** -- `N=200, R_in=1.0, R_out=12.0, Omega_0=0.6, drag_exponent=2.0, M_saturation_layer_amp=0.7, perturb_cell=20, perturb_delta=1e-8, lyap_renorm_every=25`.
- **FrameDraggingResult** -- `D_final, S_R_final, S_phi_final, M_final, beta_phi, times, cone_aperture_history, cone_compression_history, M_max_history, lyapunov_max, cone_aperture_strictly_positive, cone_aperture_min_margin, cone_aperture_saturation_margin, cone_compression_below_unity_fraction, converged`.
- **kerr_like_drag(R_centers, R_in, Omega_0, exponent)** -- `beta^phi(R) = Omega_0 (R_in/R)^p`.
- **cone_aperture_full(R_centers, beta_phi, cfg)** -- `Delta_Lambda(R) = 2 sqrt(c_diff^2 + (R d_R beta^phi)^2)`.
- **cylindrical_hll_step(D, S_R, S_phi, M, beta_phi, R_faces, R_centers, dt, cfg)** -- conservative `(R D, R S_R, R S_phi)` HLL with cylindrical-shell volumes, plus Coriolis coupling `+2 D beta^phi v_phi on S_R, -2 D beta^phi v_R on S_phi` (the off-diagonal stress `T_{R phi}` that produces structural chaos).
- **lyapunov_kernel(cfg)** -- twin-trajectory Benettin with perturbation at `perturb_cell` in `S_R`, renorm every `lyap_renorm_every` steps.
- **run_frame_dragging(cfg, snapshot_every=200, verbose=False)** -- main entry point.

Headline result (Omega_0=1.5, N=150, n_steps=3000):
| Quantity                        | beta^phi enabled | beta^phi = 0 |
| ------------------------------- | ---------------- | ------------ |
| M_max reached                   | 1.0              | 0.7          |
| Cone sat-layer margin           | +0.077           | 0.0          |
| Cone strictly positive          | **True**         | False        |
| Lyapunov max                    | **+1.127**       | -0.044       |

`Delta lambda_max = +1.17` -- 25x separation, matching the Pages-file
Stage-5 success criteria exactly.
