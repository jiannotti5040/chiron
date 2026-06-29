# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls.cattaneo -- Maxwell-Cattaneo entropy flux J_mu.

Implements the dynamical flux that converts the parabolic gradient
penalty -mu * Delta M into a causal telegrapher's equation:

    tau_J * d_t J_mu + J_mu = -mu * d_mu M

The implicit update (unconditionally stable in dt):

    J^{n+1} = (J^n - (dt mu / tau_J) grad M) / (1 + dt / tau_J)

This preserves the causal delay tau_J without introducing stiffness
instability. Characteristic velocity:

    c_diff = sqrt(mu / (tau_J tau_M))    -- bound by 1 for causality

Reference: docs/RSLS_specification.md, sections III.4 and IV.4E.
"""
from __future__ import annotations
from typing import Tuple

import numpy as np

from uma.rsls.memory import MemoryConfig


# ---------------------------------------------------------------------------
# Implicit update
# ---------------------------------------------------------------------------

def cattaneo_step(
    J: np.ndarray, M: np.ndarray, dx: float, dt: float, cfg: MemoryConfig,
) -> np.ndarray:
    """
    One implicit Cattaneo step for the radial entropy flux J_r.

    Inputs:
        J  : current J_r array, shape (N,)
        M  : current M field, shape (N,)
        dx : grid spacing
        dt : time step
        cfg: memory configuration

    Returns:
        J_new : updated flux, shape (N,)

    The update is implicit in the relaxation term:
        (1 + dt/tau_J) J^{n+1} = J^n - (dt mu / tau_J) grad M
    so the right side is fully explicit and stability is set only by
    the transport CFL (handled in the HLL step, not here).
    """
    grad_M = np.gradient(M, dx)
    J_new = (J - (dt * cfg.mu / cfg.tau_J) * grad_M) / (1.0 + dt / cfg.tau_J)
    return J_new


def cattaneo_step_2d(
    Jx: np.ndarray, Jy: np.ndarray, M: np.ndarray,
    dx: float, dt: float, cfg: MemoryConfig,
) -> Tuple[np.ndarray, np.ndarray]:
    """Two-dimensional Cartesian Cattaneo update."""
    dMdx = np.gradient(M, dx, axis=0)
    dMdy = np.gradient(M, dx, axis=1)
    Jx_new = (Jx - (dt * cfg.mu / cfg.tau_J) * dMdx) / (1.0 + dt / cfg.tau_J)
    Jy_new = (Jy - (dt * cfg.mu / cfg.tau_J) * dMdy) / (1.0 + dt / cfg.tau_J)
    return Jx_new, Jy_new


# ---------------------------------------------------------------------------
# CFL bound
# ---------------------------------------------------------------------------

def cattaneo_cfl(dx: float, cfg: MemoryConfig, safety: float = 0.5) -> float:
    """
    CFL bound on dt from the Cattaneo characteristic speed.

        dt <= safety * dx / c_diff

    The transport (HLL) step has its own CFL; the overall step must
    satisfy both.
    """
    return safety * dx / max(cfg.c_diff, 1e-12)


# ---------------------------------------------------------------------------
# Subluminal check
# ---------------------------------------------------------------------------

def subluminal(cfg: MemoryConfig, c_geom: float = 1.0) -> bool:
    """
    Whitham subcharacteristic condition: the entropy-flux speed must not
    exceed the geometric/fluid characteristic speed. Default c_geom = 1
    (relativistic case); for the Phase A flat-space prototype we relax
    this to c_geom = sqrt(mu/tau_J) (the local HLL speed).
    """
    return cfg.c_diff <= c_geom


if __name__ == "__main__":
    cfg = MemoryConfig()
    print("Cattaneo entropy flux")
    print(f"   c_diff = {cfg.c_diff:.6f}    c_eff (HLL) = {cfg.c_eff:.6f}")
    print(f"   Subluminal (<=1): {subluminal(cfg)}")
    print(f"   Whitham sub vs HLL: {subluminal(cfg, c_geom=cfg.c_eff)}")
    print()
    print("Demo: one step on a Gaussian M pulse")
    N, dx = 200, 0.05
    x = np.arange(N) * dx
    M = 0.5 * np.exp(-((x - 5.0) / 0.5) ** 2)
    J = np.zeros(N)
    dt = cattaneo_cfl(dx, cfg, safety=0.2)
    print(f"   dt (CFL) = {dt:.4e}")
    for _ in range(20):
        J = cattaneo_step(J, M, dx, dt, cfg)
    print(f"   After 20 steps:  |J|_max = {abs(J).max():.4e}")
    print(f"   (Should remain finite; signal propagates at c_diff)")
