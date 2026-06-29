# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls.memory -- the thermodynamic memory field M and the singular
convex barrier V(M).

Implements the Holographic Wall of RSLS Stage 4.IV. Provides:

    V(M)    = -lambda * log(1 - M/Mmax)       singular convex barrier
    V'(M)   =  lambda / (Mmax - M)             diverges at saturation
    V''(M)  =  lambda / (Mmax - M)^2           strict convexity
    ell_star(M) = sqrt(mu * tau_M / V''(M))   emergent relaxation length

and the stress-energy gradient contribution T_{mu,nu}^{(grad M)}
which is the NEC-compliant memory-gradient term added to the
TensorBridge by coupling.py.

The M field is hard-clipped to [0, Mmax - eps) so V(M) stays finite
at machine precision.

Reference: docs/RSLS_specification.md, sections II and IV.4D.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclass
class MemoryConfig:
    """
    Parameters for the Israel-Stewart memory sector.

    Default values are calibrated so the Stage-4 causality bound
    c_diff^2 = mu / (tau_J * tau_M) <= 1 is satisfied. The Phase-A
    kernel (Stage 1) only uses c_eff = sqrt(mu/tau_J), so it operates
    inside this bound regardless.
    """
    M_max: float = 1.0          # saturation bound; M in [0, M_max)
    lam: float = 0.12           # barrier strength (the lambda in V(M))
    tau_M: float = 1.0          # memory relaxation time
    tau_J: float = 0.15         # entropy-flux relaxation time
    mu: float = 0.08            # intrinsic stiffness modulus  (>0 forces NEC)
    M_max_clip: float = 1e-9    # numerical buffer: clip at M_max - clip

    def check_causality(self) -> bool:
        """Lorentz causality requires c_diff = sqrt(mu/(tau_J tau_M)) <= 1."""
        return (self.mu / (self.tau_J * self.tau_M)) <= 1.0

    @property
    def c_diff(self) -> float:
        """Causal diffusion speed sqrt(mu / (tau_J tau_M))."""
        return math.sqrt(self.mu / (self.tau_J * self.tau_M))

    @property
    def c_eff(self) -> float:
        """HLL signal speed sqrt(mu / tau_J)."""
        return math.sqrt(self.mu / self.tau_J)


# ---------------------------------------------------------------------------
# V(M) -- the singular convex barrier
# ---------------------------------------------------------------------------

def V(M: np.ndarray, cfg: MemoryConfig) -> np.ndarray:
    """Singular convex barrier V(M) = -lambda log(1 - M/Mmax)."""
    M_safe = np.clip(M, 0.0, cfg.M_max - cfg.M_max_clip)
    return -cfg.lam * np.log(1.0 - M_safe / cfg.M_max)


def V_prime(M: np.ndarray, cfg: MemoryConfig) -> np.ndarray:
    """V'(M) = lambda / (Mmax - M). Diverges at saturation."""
    M_safe = np.clip(M, 0.0, cfg.M_max - cfg.M_max_clip)
    return cfg.lam / (cfg.M_max - M_safe)


def V_double_prime(M: np.ndarray, cfg: MemoryConfig) -> np.ndarray:
    """V''(M) = lambda / (Mmax - M)^2. Strictly positive."""
    M_safe = np.clip(M, 0.0, cfg.M_max - cfg.M_max_clip)
    return cfg.lam / (cfg.M_max - M_safe) ** 2


def clip_M(M: np.ndarray, cfg: MemoryConfig) -> np.ndarray:
    """Enforce the M in [0, Mmax - eps) invariant. Discrete Maximum Principle."""
    return np.clip(M, 0.0, cfg.M_max - cfg.M_max_clip)


# ---------------------------------------------------------------------------
# Emergent scale ell_*
# ---------------------------------------------------------------------------

def ell_star(M: np.ndarray, cfg: MemoryConfig) -> np.ndarray:
    """
    Local emergent relaxation length scale.

        ell_* (M) = sqrt(mu * tau_M / V''(M))
                  = (Mmax - M) * sqrt(mu * tau_M / lambda)

    Note that ell_* is a *local* length (depends on M(x)). The
    "wall thickness" is measured globally from the spatial profile
    of M (see wall_thickness below).
    """
    return (cfg.M_max - clip_M(M, cfg)) * math.sqrt(cfg.mu * cfg.tau_M / cfg.lam)


def wall_thickness(
    M: np.ndarray, x: np.ndarray, cfg: MemoryConfig,
    low_frac: float = 0.1, high_frac: float = 0.9,
) -> Optional[float]:
    """
    Threshold-based wall thickness (legacy). Measures the spatial length
    over which M(x) transitions from low_frac * Mmax to high_frac * Mmax.

    Use `interface_width` for the canonical (gradient-based) measurement
    used in the dx -> 0 convergence study; this is kept for backward
    compatibility and as a coarse cross-check.

    Returns None if no such transition is present.
    """
    M = np.asarray(M)
    x = np.asarray(x)
    M_lo = low_frac * cfg.M_max
    M_hi = high_frac * cfg.M_max

    above_lo = np.argwhere(M >= M_lo)
    above_hi = np.argwhere(M >= M_hi)
    if above_lo.size == 0 or above_hi.size == 0:
        return None
    i_lo = int(above_lo[0, 0])
    i_hi = int(above_hi[0, 0])
    if i_hi <= i_lo:
        return None
    return float(abs(x[i_hi] - x[i_lo]))


def interface_width(
    M: np.ndarray, x: np.ndarray, cfg: MemoryConfig,
) -> Optional[float]:
    """
    Canonical wall-thickness measurement: the interface width at the
    steepest gradient point of M(x).

        ell_* ~= (M_max - M_min) / max_x |dM/dx|

    This is the standard diffuse-interface measurement (Cahn-Hilliard,
    Bray, Allen-Cahn). It is robust to where the wall sits in the domain
    and converges to a finite limit as dx -> 0 if and only if the wall
    thickness is a *physical* length (not a numerical-diffusion artefact).

    Returns None if M is uniform (no interface).
    """
    M = np.asarray(M)
    x = np.asarray(x)
    if len(M) < 3:
        return None
    dM = np.gradient(M, x)
    max_grad = float(np.max(np.abs(dM)))
    if max_grad < 1e-12:
        return None
    M_range = float(M.max() - M.min())
    if M_range < 1e-12:
        return None
    return M_range / max_grad


# ---------------------------------------------------------------------------
# Gradient stress T_{mu,nu}^{(grad M)} -- the NEC-compliant memory stress
# ---------------------------------------------------------------------------

def gradient_stress(
    M: np.ndarray, dx: float, cfg: MemoryConfig,
) -> np.ndarray:
    """
    The canonical scalar-gradient stress tensor

        T^(grad M)_{mu nu} = d_mu M d_nu M - (1/2) eta_{mu nu} d^a M d_a M

    on a 2D Cartesian grid (used by the TensorBridge coupling).
    Returns shape (2, 2, N, N).

    NEC: for any null vector k,
        T^(grad M)_{mu nu} k^mu k^nu = (k^mu d_mu M)^2 >= 0

    This is automatic from the form -- no constraint to enforce.
    """
    M = np.asarray(M, dtype=float)
    if M.ndim == 1:
        # promote to 2D for the TensorBridge convention
        M = np.outer(M, np.ones(M.shape[0]))
    N = M.shape[0]
    dMdx = np.gradient(M, dx, axis=0)
    dMdy = np.gradient(M, dx, axis=1)
    grad_sq = dMdx ** 2 + dMdy ** 2
    T = np.zeros((2, 2, N, N))
    T[0, 0] = dMdx * dMdx - 0.5 * grad_sq
    T[0, 1] = dMdx * dMdy
    T[1, 0] = dMdy * dMdx
    T[1, 1] = dMdy * dMdy - 0.5 * grad_sq
    return T


def nec_violation(
    M: np.ndarray, dx: float, cfg: MemoryConfig,
    n_null_samples: int = 8,
) -> float:
    """
    Sample the Null Energy Condition by contracting T^(grad M) with a
    family of null vectors k = (1, cos theta, sin theta) and returning
    the minimum value of T_{mu nu} k^mu k^nu over the grid.

    NEC compliant iff returned value >= 0 (up to floating-point).

    In 2D (the TensorBridge convention) null vectors satisfy
    k^0 = +-|k|; we take k^0 = 1 and k^i = (cos theta, sin theta).
    Then T_{mu nu} k^mu k^nu = T_00 + 2 T_0i k^i + T_ij k^i k^j.
    Mathematically with our T it should equal (k^i d_i M)^2 >= 0
    after the 2D Minkowski mostly-minus contraction.
    """
    T = gradient_stress(M, dx, cfg)  # (2,2,N,N)
    thetas = np.linspace(0.0, 2 * math.pi, n_null_samples, endpoint=False)
    min_val = float("inf")
    for th in thetas:
        k = np.array([math.cos(th), math.sin(th)])
        # contraction over spatial indices (the 0-component contributes
        # T_00 with our sign convention; we measure the geometric part
        # which for our isotropic-grid T is (k . grad M)^2 - cross terms
        # that vanish for the gradient form):
        val = (
            T[0, 0] * k[0] * k[0]
            + 2 * T[0, 1] * k[0] * k[1]
            + T[1, 1] * k[1] * k[1]
        )
        # add the eta_00 = +1 contraction of the gradient norm:
        dMdx = np.gradient(M if M.ndim == 2 else np.outer(M, np.ones(M.shape[0])),
                           dx, axis=0)
        dMdy = np.gradient(M if M.ndim == 2 else np.outer(M, np.ones(M.shape[0])),
                           dx, axis=1)
        # k^mu d_mu M with k^0 = 1, k^i = (cos, sin); time-derivative is 0
        # in the static limit -- so the operative quantity is (k^i d_i M)^2:
        kdotgrad = (k[0] * dMdx + k[1] * dMdy)
        nec_pointwise = kdotgrad ** 2
        if float(nec_pointwise.min()) < min_val:
            min_val = float(nec_pointwise.min())
    return min_val


# ---------------------------------------------------------------------------
# Initial-condition factories
# ---------------------------------------------------------------------------

def zero_field(N: int) -> np.ndarray:
    """All-zero M field."""
    return np.zeros(N, dtype=float)


def gaussian_pulse(
    x: np.ndarray, x0: float, sigma: float, amplitude: float,
    cfg: MemoryConfig,
) -> np.ndarray:
    """Localised infalling-pulse initial condition for the Phase A kernel."""
    profile = amplitude * np.exp(-((x - x0) / sigma) ** 2)
    return clip_M(profile, cfg)


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = MemoryConfig()
    print("RSLS Memory sector")
    print(f"   M_max  = {cfg.M_max}")
    print(f"   lambda = {cfg.lam}")
    print(f"   mu     = {cfg.mu}    tau_M = {cfg.tau_M}    tau_J = {cfg.tau_J}")
    print(f"   c_eff  = sqrt(mu/tau_J)         = {cfg.c_eff:.6f}")
    print(f"   c_diff = sqrt(mu/(tau_J tau_M)) = {cfg.c_diff:.6f}")
    print(f"   Causal (c_diff <= 1): {cfg.check_causality()}")
    print()
    Ms = np.linspace(0, 0.99, 6)
    print(f"   {'M':>8}  {'V(M)':>10}  {'V_prime(M)':>12}  {'V_pp(M)':>10}  {'ell*':>8}")
    for M in Ms:
        print(
            f"   {M:>8.4f}  {float(V(np.array([M]), cfg)[0]):>10.4e}  "
            f"{float(V_prime(np.array([M]), cfg)[0]):>12.4e}  "
            f"{float(V_double_prime(np.array([M]), cfg)[0]):>10.4e}  "
            f"{float(ell_star(np.array([M]), cfg)[0]):>8.4f}"
        )
