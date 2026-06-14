"""
uma.rsls.phase_a -- the Stage 1 / Phase A Falsification Kernel.

This is the pure numerical proof of the RSLS architecture. A 1-D
spherically symmetric solver that combines:

    1. HLL Riemann flux for compressive transport (hll.py)
    2. Implicit Cattaneo update for the entropy flux J_r (cattaneo.py)
    3. Singular convex barrier V(M) for the memory field (memory.py)

The kernel demonstrates the three claimed properties:

    A. **Delayed stiffening** -- phase lag between peak compression and
       peak M, consistent with hyperbolic relaxation (not instantaneous).

    B. **L^1-contraction** -- the vanishing-viscosity limit is strongly
       convergent.

    C. **Grid independence** -- the wall thickness ell_* converges to
       a finite, nonzero constant as dx -> 0. This is the falsification
       check: if ell_* -> 0 or diverges with refinement, the theory is
       wrong.

Reference: docs/RSLS_specification.md, section VI.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from uma.rsls.memory import (
    MemoryConfig, V, V_prime, clip_M, ell_star, wall_thickness, interface_width,
)
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import hll_update_spherical_2var, transport_cfl


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class PhaseAConfig:
    """Configuration for the Phase A falsification kernel."""
    N: int = 400                  # number of radial cells
    R_in: float = 1.0             # inner cutoff (puncture domain)
    R_out: float = 15.0           # outer boundary
    n_steps: int = 15000          # total integration steps
    cfl_safety: float = 0.5       # CFL safety factor
    pulse_center: float = 8.0     # initial pulse position
    pulse_width: float = 2.0      # initial pulse width sigma
    pulse_amplitude: float = -2.5 # initial inward radial momentum amplitude
    memory: MemoryConfig = field(default_factory=MemoryConfig)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class PhaseAResult:
    """Outputs of a Phase A run."""
    cfg: PhaseAConfig
    r_centers: np.ndarray         # cell centres, shape (N,)
    r_faces: np.ndarray           # cell faces, shape (N+1,)
    M_history: List[np.ndarray]   # snapshots of M(r) over time
    S_history: List[np.ndarray]   # snapshots of S_r(r) over time
    J_history: List[np.ndarray]   # snapshots of J_r(r) over time
    D_history: List[np.ndarray]   # snapshots of D(r) over time
    times: List[float]            # snapshot times
    wall_thickness: Optional[float]      # at the snapshot of peak M
    wall_thickness_final: Optional[float]
    wall_thickness_max: Optional[float]  # maximum across all snapshots
    M_at_peak: Optional[np.ndarray]
    M_max_reached: float
    L1_norm: List[float]          # total |M| (BV check)
    M_peak_step: int
    compression_peak_step: int
    converged: bool

    @property
    def stiffening_lag(self) -> int:
        """
        Steps between peak compression and peak M. Positive value
        indicates the predicted delayed stiffening (Stage 1 property A).
        """
        return self.M_peak_step - self.compression_peak_step

    def summary(self) -> dict:
        return {
            "N":                    self.cfg.N,
            "n_steps":              self.cfg.n_steps,
            "wall_thickness_peak":  self.wall_thickness,
            "wall_thickness_max":   self.wall_thickness_max,
            "wall_thickness_final": self.wall_thickness_final,
            "M_max_reached":        round(self.M_max_reached, 6),
            "M_max_allowed":        self.cfg.memory.M_max,
            "stiffening_lag":       self.stiffening_lag,
            "L1_initial":           round(self.L1_norm[0], 6),
            "L1_final":             round(self.L1_norm[-1], 6),
            "L1_growth":            round(self.L1_norm[-1] - self.L1_norm[0], 6),
            "converged":            self.converged,
        }


# ---------------------------------------------------------------------------
# Kernel
# ---------------------------------------------------------------------------

def run_phase_a(cfg: Optional[PhaseAConfig] = None, snapshot_every: int = 500,
                verbose: bool = False) -> PhaseAResult:
    """
    Run the Phase A falsification kernel.

    The setup is RSLS Stage 1 verbatim:
        - Punctured spherical grid r in (R_in, R_out]
        - Infalling Gaussian momentum pulse
        - HLL transport, implicit Cattaneo flux, strict V(M) clip
        - Zero-gradient outflow at both boundaries

    Returns a PhaseAResult.
    """
    cfg = cfg or PhaseAConfig()
    mcfg = cfg.memory

    # --- Grid (RSLS-VI: punctured domain, no r=0 cell) ---
    r_faces = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
    r_centers = 0.5 * (r_faces[:-1] + r_faces[1:])
    dr = (cfg.R_out - cfg.R_in) / cfg.N

    # --- Initial conditions ---
    D = np.ones(cfg.N) * 0.1                  # background density proxy
    S = cfg.pulse_amplitude * np.exp(
        -((r_centers - cfg.pulse_center) / cfg.pulse_width) ** 2
    )                                          # infalling radial momentum
    M = np.zeros(cfg.N)
    J = np.zeros(cfg.N)

    # --- Time step (most-restrictive CFL) ---
    dt_transport = transport_cfl(S / D, dr, mcfg, safety=cfg.cfl_safety)
    dt_cattaneo  = cattaneo_cfl(dr, mcfg, safety=cfg.cfl_safety)
    dt = min(dt_transport, dt_cattaneo, 0.005 * dr)  # extra safety

    if verbose:
        print(f"[Phase A] N={cfg.N}  dr={dr:.4e}  dt={dt:.4e}")
        print(f"[Phase A] c_eff={mcfg.c_eff:.4e}  c_diff={mcfg.c_diff:.4e}")

    # --- Histories ---
    M_history: List[np.ndarray] = []
    S_history: List[np.ndarray] = []
    J_history: List[np.ndarray] = []
    D_history: List[np.ndarray] = []
    times: List[float] = []
    L1_norm: List[float] = []

    M_max_reached = 0.0
    M_peak_step = 0
    M_peak_field: Optional[np.ndarray] = None
    compression_peak_step = 0
    max_compression = 0.0

    # --- Main loop ---
    for step in range(cfg.n_steps + 1):
        # (1) Strict M clip and reload (Discrete Maximum Principle)
        M = clip_M(M, mcfg)

        # (2) HLL transport step on (D, S) -- mass-conserving 2-variable form
        D, S = hll_update_spherical_2var(D, S, M, r_faces, r_centers, dt, mcfg)

        # (3) Memory accumulates kinematic compression: dM/dt = -div J - 0.5 div v
        v_r = S / np.maximum(D, 1e-12)
        grad_vR = np.gradient(v_r, dr)
        M = M + dt * (-np.gradient(J, dr) - 0.5 * grad_vR)
        M = clip_M(M, mcfg)

        # (4) Implicit Cattaneo update for J_r (causal, unconditionally stable)
        J = cattaneo_step(J, M, dr, dt, mcfg)

        # --- Diagnostics ---
        M_max_now = float(M.max())
        if M_max_now > M_max_reached:
            M_max_reached = M_max_now
            M_peak_step = step
            M_peak_field = M.copy()
        compression_now = float(-grad_vR.min())  # peak compression
        if compression_now > max_compression:
            max_compression = compression_now
            compression_peak_step = step

        # --- Snapshots ---
        if step % snapshot_every == 0 or step == cfg.n_steps:
            M_history.append(M.copy())
            S_history.append(S.copy())
            J_history.append(J.copy())
            D_history.append(D.copy())
            times.append(step * dt)
            L1_norm.append(float(np.sum(np.abs(M)) * dr))

        # --- Defensive: if the field becomes non-finite, halt
        if not np.all(np.isfinite(M)):
            if verbose:
                print(f"[Phase A] non-finite M at step {step}; halting")
            break

    # --- Wall thickness measurements ---
    wt_at_peak: Optional[float] = None
    if M_peak_field is not None:
        wt_at_peak = interface_width(M_peak_field, r_centers, mcfg)
    wt_final = interface_width(M, r_centers, mcfg)
    # Maximum wall thickness observed across all snapshots (the moment of
    # fattest wall -- the operative observable for the convergence study)
    wt_max: Optional[float] = None
    for M_snap in M_history:
        wt_snap = interface_width(M_snap, r_centers, mcfg)
        if wt_snap is not None:
            if wt_max is None or wt_snap > wt_max:
                wt_max = wt_snap

    converged = (
        M_max_reached > 0.5 * mcfg.M_max  # the wall actually formed
        and bool(np.all(np.isfinite(M)))
    )

    if verbose:
        print(f"[Phase A] done. M_max reached = {M_max_reached:.6f}")
        print(f"[Phase A] wall_thickness at peak = {wt_at_peak}")
        print(f"[Phase A] wall_thickness final   = {wt_final}")
        print(f"[Phase A] wall_thickness max     = {wt_max}")
        print(f"[Phase A] stiffening_lag = {M_peak_step - compression_peak_step} steps")

    return PhaseAResult(
        cfg=cfg,
        r_centers=r_centers, r_faces=r_faces,
        M_history=M_history, S_history=S_history,
        J_history=J_history, D_history=D_history,
        times=times,
        wall_thickness=wt_at_peak,
        wall_thickness_final=wt_final,
        wall_thickness_max=wt_max,
        M_at_peak=M_peak_field,
        M_max_reached=M_max_reached,
        L1_norm=L1_norm,
        M_peak_step=M_peak_step,
        compression_peak_step=compression_peak_step,
        converged=converged,
    )


# ---------------------------------------------------------------------------
# Convergence study (the actual falsification check)
# ---------------------------------------------------------------------------

def convergence_study(
    Ns: Optional[List[int]] = None,
    base_cfg: Optional[PhaseAConfig] = None,
    n_steps_scale: bool = True,
    verbose: bool = False,
) -> List[PhaseAResult]:
    """
    Run Phase A at multiple grid resolutions and return the list of
    results. The wall thickness must converge to a finite, nonzero
    constant as dx -> 0; the example script in examples/rsls_phase_a.py
    plots this.

    Inputs:
        Ns           : list of N values to run at; defaults to [100, 200, 400, 800]
        base_cfg     : PhaseAConfig template; N is overridden per run
        n_steps_scale: if True, scale n_steps inversely with dx so the
                       physical end-time matches across resolutions
        verbose      : per-run progress
    """
    Ns = Ns or [100, 200, 400, 800]
    base_cfg = base_cfg or PhaseAConfig()
    base_steps = base_cfg.n_steps
    base_N = base_cfg.N

    results: List[PhaseAResult] = []
    for N in Ns:
        cfg = PhaseAConfig(
            N=N,
            R_in=base_cfg.R_in, R_out=base_cfg.R_out,
            n_steps=int(base_steps * (N / base_N)) if n_steps_scale else base_steps,
            cfl_safety=base_cfg.cfl_safety,
            pulse_center=base_cfg.pulse_center,
            pulse_width=base_cfg.pulse_width,
            pulse_amplitude=base_cfg.pulse_amplitude,
            memory=base_cfg.memory,
        )
        if verbose:
            print(f"\n--- N = {N} ---")
        results.append(run_phase_a(cfg, verbose=verbose))
    return results


if __name__ == "__main__":
    cfg = PhaseAConfig(N=200, n_steps=3000)
    print("=== UMA / RSLS Phase A Falsification Kernel ===")
    print()
    res = run_phase_a(cfg, verbose=True)
    print()
    for k, v in res.summary().items():
        print(f"   {k:<24} {v}")
