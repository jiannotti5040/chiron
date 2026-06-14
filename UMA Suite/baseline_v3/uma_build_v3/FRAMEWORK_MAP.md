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
