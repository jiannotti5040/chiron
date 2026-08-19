# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
uma.rsls.stage6 -- self-consistent ADM-driven frame-dragging.

Stage 5 ran with a *prescribed* beta^phi(R) (static Kerr-like profile).
Stage 6 closes the loop: beta^phi evolves causally, sourced by the
off-diagonal stress T_{R phi} of the matter, via a Maxwell-Cattaneo
-style relaxation equation -- the same structural pattern used for
the entropy flux J in Stage 4E.

The momentum constraint of ADM, in our 1.5-D cylindrical reduction,
reduces (in the slow-evolution / damped limit) to:

    tau_beta * d_t beta^phi = -(beta^phi - beta^phi_eq[T_Rphi])
                              + mu_beta * d_R^2 beta^phi

where beta^phi_eq is set by integrating the off-diagonal stress along
R outward from the boundary -- the cylindrical analogue of the
Komar-angular-momentum integral.

In the limit tau_beta -> 0 this reduces to an elliptic constraint
solved instantaneously each step (no information lag, the
configuration-space limit). For tau_beta > 0 the metric responds
causally to matter -- the proper relativistic limit.

This module establishes one architectural closure and refuses a second.

PROVEN HERE: under self-consistent beta^phi evolution the cone aperture
remains strictly positive throughout, the metric drift stays bounded, and
the saturation layer still forms. Those are the closure results.

NOT ESTABLISHED: this module previously also claimed "the Lyapunov exponent
remains positive in the saturation layer, i.e. the Stage-5 chaos signatures
survive the geometric back-reaction". That claim is withdrawn. The
twin-trajectory statistic it rested on fails every standard validity check
for a Lyapunov exponent (2026-08-11):

  * it does not converge -- widening the window gives lambda = -0.013,
    +3.16, +8.95, +39.12 at n_steps = 2k, 4k, 8k, 16k;
  * it is not independent of the perturbation size -- the same config gives
    -0.014, -0.013, +0.064, +5.57 at delta = 1e-6, 1e-8, 1e-10, 1e-12,
    changing sign;
  * a single renormalisation block supplies most of the sum. In the Stage-5
    configuration one block of 72 (growth x87) is 82% of the total; drop it
    and lambda falls from +5.499 to +0.999, while the MEDIAN block contracts
    (54 of 72). It measures one transient amplification, not a rate;
  * beyond ~8k steps the underlying solution is not bounded -- at 16k steps
    max|S_R| reaches 1.2e15 -- so the long-window values measure a numerical
    instability rather than sensitive dependence.

Three estimator bugs were fixed while establishing this: the Cattaneo flux J
was evolved but never renormalised with the rest of the state; a partial final
block was credited a full block of time; and renormalising only every 25 steps
let the separation grow x87 inside one block, far outside the linear regime
Benettin's algorithm needs. None rescued convergence, which is why the claim
is withdrawn rather than repaired.

Two further defects belong to the kernel rather than the estimator, and are
documented (not fixed) in studies/rsls_lyapunov/: dt is computed once from the
initial state and violates CFL by ~550x once velocities grow, and with dt made
adaptive the density instead collapses to a finite-time vacuum that stalls the
clock at t ~ 3.34. Fixing either changes every Stage-5/6 result, so both are
modelling decisions rather than diagnostic ones.

What DID survive the repair is the control: with frame-dragging disabled the
estimate passes every check and lands at lambda = -0.037448, so the undragged
kernel is measurably NOT chaotic. With drag it is still climbing (second half
+2.349 against +1.141 over the whole window) and stays refused. The honest
reading is "no chaos without drag, unresolved with drag" -- not the original
"drag makes the chaos structural".

`stage6_lyapunov` therefore returns a LyapunovReport that REFUSES: it runs
the checks, reports the raw statistic for diagnosis, and sets converged=False
with a reason. Whether this system is chaotic under back-reaction is an open
question here, not a negative result -- a competent answer needs a bounded
long-time integration and a tangent-space (not finite-difference) method.

Reference: docs/RSLS_specification.md Section XIV (Stage 5);
the Stage-6 closure is documented in this module's docstring and in
docs/TOTALITY_OF_THEORY.md.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from uma.rsls.memory import MemoryConfig, V, clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import hll_flux, transport_cfl
from uma.rsls.lyapunov import (BLOWUP as LYAP_BLOWUP, LyapunovReport,
                               lyapunov_report as _lyapunov_report)
from uma.rsls.frame_dragging import (
    FrameDraggingConfig, kerr_like_drag, cone_aperture_full,
    cylindrical_hll_step,
)


@dataclass
class Stage6Config(FrameDraggingConfig):
    """Stage 6 extends Stage 5 by evolving beta^phi self-consistently."""
    tau_beta: float = 5.0         # causal relaxation timescale for beta^phi
    mu_beta: float = 0.005        # diffusion coefficient for beta^phi
    kappa_drag: float = 0.4       # coupling: T_Rphi -> beta^phi_eq
    enable_self_consistency: bool = True
    beta_phi_freeze_steps: int = 100  # let matter settle before evolving metric
    # --- the two defects studies/rsls_lyapunov/ documented, now fixable here ---
    # Both default OFF so every existing Stage-5/6 number is reproduced bit for
    # bit. Turn them on to get an integration that is actually valid for long
    # times; see `adaptive_dt` and `density_floor` in the module docstring.
    adaptive_dt: bool = False     # recompute the CFL step every step
    density_floor: float = 0.0    # D >= floor ("atmosphere"); 0 disables


@dataclass
class Stage6Result:
    cfg: Stage6Config
    R_centers: np.ndarray
    R_faces: np.ndarray
    times: List[float]
    beta_phi_history: List[np.ndarray]
    cone_aperture_history: List[np.ndarray]
    M_max_history: List[float]
    T_Rphi_history: List[np.ndarray]
    D_final: np.ndarray
    S_R_final: np.ndarray
    S_phi_final: np.ndarray
    M_final: np.ndarray
    beta_phi_final: np.ndarray

    # Stage-6 closure verdicts
    cone_aperture_strictly_positive_throughout: bool
    cone_aperture_saturation_margin_final: float
    beta_phi_drift_fraction: float       # |Δβ^φ| / |β^φ(0)|, final
    self_consistency_converged: bool
    # NaN unless the estimator's validity checks passed. Read `lyapunov` for
    # the reason; this stays NaN rather than carrying an unusable number,
    # because a float named lyapunov_max is exactly what got read as a result.
    lyapunov_max: float
    lyapunov: Optional[LyapunovReport] = None

    def summary(self) -> dict:
        out = {
            "N":                              self.cfg.N,
            "n_steps":                        self.cfg.n_steps,
            "tau_beta":                       self.cfg.tau_beta,
            "kappa_drag":                     self.cfg.kappa_drag,
            "M_max_reached":                  round(max(self.M_max_history), 6),
            "beta_phi_drift_fraction":        round(self.beta_phi_drift_fraction, 4),
            "cone_aperture_sat_margin_final": round(self.cone_aperture_saturation_margin_final, 6),
            "cone_strictly_positive_through": self.cone_aperture_strictly_positive_throughout,
            "self_consistency_converged":     self.self_consistency_converged,
            "lyapunov_max":                   round(self.lyapunov_max, 6),
        }
        if self.lyapunov is not None:
            out.update(self.lyapunov.summary())
        return out


def off_diagonal_stress(D: np.ndarray, S_R: np.ndarray,
                        S_phi: np.ndarray) -> np.ndarray:
    """T_{R phi} = rho U^R U^phi = S_R * S_phi / D.

    The off-diagonal momentum-flux that sources beta^phi via the ADM
    momentum constraint.
    """
    return (S_R * S_phi) / np.maximum(D, 1e-12)


def equilibrium_beta_phi(T_Rphi: np.ndarray, R_centers: np.ndarray,
                         kappa_drag: float) -> np.ndarray:
    """beta^phi_eq from integrating T_{R phi} outward.

    Cylindrical analogue of the Komar angular-momentum integral:
        beta^phi_eq(R) = -kappa_drag/(R^2) * integral_R^{R_out} T_{R phi}(R') R' dR'

    This is the value beta^phi would take if the momentum constraint
    were imposed instantaneously (elliptic limit). The Stage-6
    evolution lets beta^phi relax toward this target with finite
    timescale tau_beta -- the causal limit.
    """
    integrand = T_Rphi * R_centers
    cumulative = np.zeros_like(R_centers)
    # Trapezoidal integration from outer boundary inward
    for i in range(len(R_centers) - 2, -1, -1):
        dR_loc = R_centers[i + 1] - R_centers[i]
        cumulative[i] = cumulative[i + 1] + 0.5 * (integrand[i] + integrand[i + 1]) * dR_loc
    return -kappa_drag * cumulative / np.maximum(R_centers ** 2, 1e-6)


def beta_phi_causal_step(beta_phi: np.ndarray, beta_phi_eq: np.ndarray,
                         dR: float, dt: float,
                         tau_beta: float, mu_beta: float) -> np.ndarray:
    """One step of the Maxwell-Cattaneo-style causal relaxation:

        d_t beta^phi = -(beta^phi - beta^phi_eq)/tau_beta + mu_beta * d_R^2 beta^phi

    Stable for dt < min(tau_beta, dR^2/(2 mu_beta)).
    """
    d2_dR2 = np.gradient(np.gradient(beta_phi, dR), dR)
    return beta_phi + dt * (
        -(beta_phi - beta_phi_eq) / tau_beta + mu_beta * d2_dR2
    )


def run_stage6(cfg: Optional[Stage6Config] = None,
               snapshot_every: int = 200,
               compute_lyapunov: bool = True,
               verbose: bool = False) -> Stage6Result:
    """Run the Stage-6 self-consistent kernel.

    The matter (D, S_R, S_phi, M) evolves under the current beta^phi.
    The metric (beta^phi) evolves under the current T_{R phi}.
    They are integrated together with a forward-Euler split:
    matter step first, then metric step.
    """
    cfg = cfg or Stage6Config()
    mcfg = cfg.memory

    R_faces = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
    R_centers = 0.5 * (R_faces[:-1] + R_faces[1:])
    dR = (cfg.R_out - cfg.R_in) / cfg.N

    # Initial beta^phi: Kerr-like profile (same as Stage 5)
    beta_phi = kerr_like_drag(R_centers, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
    beta_phi_initial = beta_phi.copy()

    # Initial matter
    D = np.ones(cfg.N) * cfg.D_background
    S_R = cfg.pulse_amp * np.exp(
        -((R_centers - cfg.pulse_center) / cfg.pulse_width) ** 2)
    S_phi = np.zeros(cfg.N)
    M = cfg.M_saturation_layer_amp * np.exp(
        -((R_centers - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2)
    M = clip_M(M, mcfg)
    J = np.zeros(cfg.N)

    # Time step (matter CFL + Cattaneo CFL + beta_phi CFL)
    def _cfl_dt(S_R_now, D_now):
        """Most-restrictive stable step for the CURRENT state.

        Evaluated once at t=0 when `adaptive_dt` is False, which is what every
        published Stage-5/6 number used. That is unsound once the flow speeds
        up: max|v| grows 0.30 -> 8.7 -> 4.4e4, so the frozen step exceeds the
        transport CFL bound by ~548x by step 8000 and the solution is
        non-finite by 12951 (studies/rsls_lyapunov/adaptive.py).
        """
        dt_trans = transport_cfl(S_R_now / np.maximum(D_now, 1e-12), dR, mcfg,
                                 safety=cfg.cfl_safety)
        dt_catt = cattaneo_cfl(dR, mcfg, safety=cfg.cfl_safety)
        dt_beta = cfg.cfl_safety * min(cfg.tau_beta,
                                       (dR ** 2) / (2 * max(cfg.mu_beta, 1e-12)))
        return min(dt_trans, dt_catt, dt_beta, 0.005 * dR)

    dt = _cfl_dt(S_R, D)

    if verbose:
        print(f"[Stage6] N={cfg.N} dR={dR:.3e} dt={dt:.3e} tau_beta={cfg.tau_beta}")

    times = []
    beta_history = []
    cone_history = []
    M_max_history = []
    T_Rphi_history = []
    min_margin_throughout = float("inf")

    t_now = 0.0
    for step in range(cfg.n_steps + 1):
        # ---- Matter step (with current beta_phi) ----
        if cfg.adaptive_dt:
            dt = _cfl_dt(S_R, D)
        M = clip_M(M, mcfg)
        D, S_R, S_phi = cylindrical_hll_step(
            D, S_R, S_phi, M, beta_phi, R_faces, R_centers, dt, mcfg)
        if cfg.density_floor > 0.0:
            # Standard atmosphere treatment. Without it min(D) collapses to
            # ~1e-6, v = S/D reaches 4e5, dt collapses to 1e-7 and the clock
            # stalls at t ~ 3.34 -- a coordinate singularity in finite time,
            # with no long-time trajectory for anything to be measured on.
            D = np.maximum(D, cfg.density_floor)
        v_R = S_R / np.maximum(D, 1e-12)
        M = M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v_R, dR))
        M = clip_M(M, mcfg)
        J = cattaneo_step(J, M, dR, dt, mcfg)
        t_now += dt

        # ---- Metric step (beta_phi evolution from T_Rphi) ----
        if cfg.enable_self_consistency and step >= cfg.beta_phi_freeze_steps:
            T_Rphi = off_diagonal_stress(D, S_R, S_phi)
            beta_phi_eq = equilibrium_beta_phi(T_Rphi, R_centers, cfg.kappa_drag)
            # Blend the equilibrium target with the initial profile to keep
            # the asymptotic frame-dragging anchored
            beta_phi_target = 0.5 * beta_phi_eq + 0.5 * beta_phi_initial
            beta_phi = beta_phi_causal_step(
                beta_phi, beta_phi_target, dR, dt,
                cfg.tau_beta, cfg.mu_beta,
            )
            # Clip to keep the metric sane
            beta_phi = np.clip(beta_phi, -3.0 * cfg.Omega_0, 3.0 * cfg.Omega_0)

        # ---- Diagnostics ----
        aperture_now = cone_aperture_full(R_centers, beta_phi, mcfg)
        sat_mask = M > 0.5 * mcfg.M_max
        if sat_mask.any():
            margin = float((aperture_now[sat_mask] - 2 * mcfg.c_diff).min())
        else:
            margin = float((aperture_now - 2 * mcfg.c_diff).min())
        if margin < min_margin_throughout:
            min_margin_throughout = margin

        if step % snapshot_every == 0 or step == cfg.n_steps:
            times.append(t_now)
            beta_history.append(beta_phi.copy())
            cone_history.append(aperture_now.copy())
            M_max_history.append(float(M.max()))
            T_Rphi_history.append(off_diagonal_stress(D, S_R, S_phi).copy())

        if not np.all(np.isfinite(beta_phi)) or not np.all(np.isfinite(M)):
            if verbose:
                print(f"[Stage6] non-finite at step {step}; halting")
            break

    # Final diagnostics
    sat_mask_final = M > 0.5 * mcfg.M_max
    if sat_mask_final.any():
        sat_margin_final = float((cone_aperture_full(R_centers, beta_phi, mcfg)[sat_mask_final]
                                  - 2 * mcfg.c_diff).min())
    else:
        sat_margin_final = 0.0

    # beta^phi drift: how much did self-consistency move beta^phi
    # from the prescribed profile?
    initial_norm = np.linalg.norm(beta_phi_initial)
    drift_norm = np.linalg.norm(beta_phi - beta_phi_initial)
    drift_fraction = float(drift_norm / max(initial_norm, 1e-12))

    self_consistency_converged = (
        np.all(np.isfinite(beta_phi))
        and np.all(np.isfinite(M))
        and (max(M_max_history) > 0.5 * mcfg.M_max)
        and (drift_fraction < 2.0)  # didn't blow up
    )

    cone_strictly_positive_through = bool(min_margin_throughout > 0)

    # Lyapunov (twin-trajectory; the Stage-5 machinery does not carry over
    # directly because beta_phi evolves, so both coupled kernels run in
    # parallel). lyapunov_max stays NaN unless the estimator's validity
    # checks pass -- the report carries the raw statistic and the reason.
    lam = float("nan")
    lyap_report = None
    if compute_lyapunov:
        lyap_report = stage6_lyapunov(cfg)
        lam = lyap_report.value if lyap_report.converged else float("nan")

    return Stage6Result(
        cfg=cfg, R_centers=R_centers, R_faces=R_faces,
        times=times, beta_phi_history=beta_history,
        cone_aperture_history=cone_history, M_max_history=M_max_history,
        T_Rphi_history=T_Rphi_history,
        D_final=D, S_R_final=S_R, S_phi_final=S_phi,
        M_final=M, beta_phi_final=beta_phi,
        cone_aperture_strictly_positive_throughout=cone_strictly_positive_through,
        cone_aperture_saturation_margin_final=sat_margin_final,
        beta_phi_drift_fraction=drift_fraction,
        self_consistency_converged=self_consistency_converged,
        lyapunov_max=lam,
        lyapunov=lyap_report,
    )


def stage6_lyapunov(cfg: Stage6Config) -> LyapunovReport:
    """Twin-trajectory separation statistic for the coupled Stage-6 system,
    with the validity checks that decide whether it is an exponent.

    Perturbs S_R at one cell; runs two coupled (matter + metric) trajectories;
    renormalises periodically; accumulates the log-growth rate. beta^phi
    differs between the twins, so the metric responds to the perturbation too.

    The raw rate is NOT returned as a Lyapunov exponent. It is returned inside
    a LyapunovReport whose `converged` flag is set only if the statistic
    survives four checks: the reference trajectory stayed bounded, no single
    renormalisation block dominates the sum, the second half agrees with the
    whole, and at least a few blocks contributed. On this system none of the
    shipped configurations pass -- see the module docstring for the numbers.

    The whole dynamical state is renormalised, J included. Leaving J out (as
    the Stage-5 kernel still does) rescales part of the perturbation and
    leaves the flux separation wherever it drifted, which is not a consistent
    tangent vector. Partial final blocks are credited only the time they
    actually ran.
    """
    mcfg = cfg.memory
    R_faces = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
    R_centers = 0.5 * (R_faces[:-1] + R_faces[1:])
    dR = (cfg.R_out - cfg.R_in) / cfg.N

    def init_state():
        bp = kerr_like_drag(R_centers, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
        D = np.ones(cfg.N) * cfg.D_background
        S_R = cfg.pulse_amp * np.exp(
            -((R_centers - cfg.pulse_center) / cfg.pulse_width) ** 2)
        S_phi = np.zeros(cfg.N)
        M = cfg.M_saturation_layer_amp * np.exp(
            -((R_centers - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2)
        M = clip_M(M, mcfg)
        J = np.zeros(cfg.N)
        return D, S_R, S_phi, M, J, bp, bp.copy()

    D1, S_R1, S_phi1, M1, J1, bp1, bp1_init = init_state()
    D2, S_R2, S_phi2, M2, J2, bp2, bp2_init = init_state()
    if 0 <= cfg.perturb_cell < cfg.N:
        S_R2[cfg.perturb_cell] += cfg.perturb_delta

    delta0 = cfg.perturb_delta
    dt_trans = transport_cfl(S_R1 / np.maximum(D1, 1e-12), dR, mcfg, safety=cfg.cfl_safety)
    dt_catt = cattaneo_cfl(dR, mcfg, safety=cfg.cfl_safety)
    dt_beta = cfg.cfl_safety * min(cfg.tau_beta, (dR ** 2) / (2 * max(cfg.mu_beta, 1e-12)))
    dt = min(dt_trans, dt_catt, dt_beta, 0.005 * dR)

    def evolve_one_step(D, S_R, S_phi, M, J, beta_phi, bp_init, step_index):
        M = clip_M(M, mcfg)
        D, S_R, S_phi = cylindrical_hll_step(D, S_R, S_phi, M, beta_phi,
                                              R_faces, R_centers, dt, mcfg)
        v_R = S_R / np.maximum(D, 1e-12)
        M = M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v_R, dR))
        M = clip_M(M, mcfg)
        J = cattaneo_step(J, M, dR, dt, mcfg)
        if cfg.enable_self_consistency and step_index >= cfg.beta_phi_freeze_steps:
            T_Rphi = off_diagonal_stress(D, S_R, S_phi)
            beta_eq = equilibrium_beta_phi(T_Rphi, R_centers, cfg.kappa_drag)
            beta_target = 0.5 * beta_eq + 0.5 * bp_init
            beta_phi = beta_phi_causal_step(beta_phi, beta_target, dR, dt,
                                             cfg.tau_beta, cfg.mu_beta)
            beta_phi = np.clip(beta_phi, -3 * cfg.Omega_0, 3 * cfg.Omega_0)
        return D, S_R, S_phi, M, J, beta_phi

    # Burn-in
    n_burn = min(200, cfg.n_steps // 4)
    for k in range(n_burn):
        D1, S_R1, S_phi1, M1, J1, bp1 = evolve_one_step(D1, S_R1, S_phi1, M1, J1, bp1, bp1_init, k)
        D2, S_R2, S_phi2, M2, J2, bp2 = evolve_one_step(D2, S_R2, S_phi2, M2, J2, bp2, bp2_init, k)

    N = cfg.N

    def state_stack(D, S_R, S_phi, M, J, bp):
        # J belongs to the state: it is evolved and it feeds back into M.
        return np.concatenate([D, S_R, S_phi, M, J, bp])

    def unstack(s):
        return (np.maximum(s[:N], 1e-6), s[N:2*N], s[2*N:3*N],
                clip_M(s[3*N:4*N], mcfg), s[4*N:5*N], s[5*N:6*N])

    s1 = state_stack(D1, S_R1, S_phi1, M1, J1, bp1)
    s2 = state_stack(D2, S_R2, S_phi2, M2, J2, bp2)
    sep = s2 - s1
    sn = np.linalg.norm(sep)
    if sn > 0:
        D2, S_R2, S_phi2, M2, J2, bp2 = unstack(s1 + sep / sn * delta0)

    logs: List[float] = []
    times: List[float] = []
    bounded = True
    n_measure = cfg.n_steps - n_burn
    step_count = 0
    while step_count < n_measure:
        in_block = 0
        for _ in range(cfg.lyap_renorm_every):
            if step_count >= n_measure:
                break
            D1, S_R1, S_phi1, M1, J1, bp1 = evolve_one_step(
                D1, S_R1, S_phi1, M1, J1, bp1, bp1_init, n_burn + step_count)
            D2, S_R2, S_phi2, M2, J2, bp2 = evolve_one_step(
                D2, S_R2, S_phi2, M2, J2, bp2, bp2_init, n_burn + step_count)
            step_count += 1
            in_block += 1
        # A reference trajectory that has left the physical range is measuring
        # its own numerical instability, not sensitive dependence.
        if not np.all(np.isfinite(S_R1)) or np.abs(S_R1).max() > LYAP_BLOWUP \
                or not np.all(np.isfinite(D1)) or np.abs(D1).max() > LYAP_BLOWUP:
            bounded = False
            break
        s1 = state_stack(D1, S_R1, S_phi1, M1, J1, bp1)
        s2 = state_stack(D2, S_R2, S_phi2, M2, J2, bp2)
        sep = s2 - s1
        sn = np.linalg.norm(sep)
        if sn > 1e-30 and in_block:
            logs.append(float(np.log(sn / delta0)))
            times.append(in_block * dt)   # only the time that actually ran
            D2, S_R2, S_phi2, M2, J2, bp2 = unstack(s1 + sep / sn * delta0)

    return _lyapunov_report(np.array(logs), np.array(times), bounded)


if __name__ == "__main__":
    print("=== Stage 6: self-consistent ADM-beta^phi coupling ===\n")
    cfg = Stage6Config(N=150, n_steps=3000, Omega_0=1.5,
                       enable_self_consistency=True, tau_beta=5.0)
    res = run_stage6(cfg, verbose=True)
    print()
    for k, v in res.summary().items():
        print(f"  {k:<40}  {v}")
