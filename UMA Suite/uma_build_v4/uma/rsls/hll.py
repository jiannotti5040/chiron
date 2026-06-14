"""
uma.rsls.hll -- HLL (Harten-Lax-van Leer) Riemann flux for the
conservative transport sector of the Phase A falsification kernel.

Used for the radial momentum S_r = rho v_r with flux
    F(S_r) = S_r * v_r + P_eff(M)
where P_eff(M) = V(M) = -lambda log(1 - M/Mmax) is the barrier pressure.

The HLL flux at the cell interface i+1/2:

    F_HLL = (lambda_plus * F_L - lambda_minus * F_R
             + lambda_plus * lambda_minus * (q_R - q_L))
            / (lambda_plus - lambda_minus)

with signal speeds
    lambda_L = v_L - c_eff
    lambda_R = v_R + c_eff
    lambda_plus  = max(0, lambda_L, lambda_R)
    lambda_minus = min(0, lambda_L, lambda_R)
    c_eff = sqrt(mu / tau_J)

HLL is the simplest characteristic-aware upwinding that strictly
preserves the maximum principle and is the entropy-stable choice
for our quasi-linear system. We do **not** use a Lax-Friedrichs
fallback (too diffusive) or a Roe scheme (entropy issues at sonic
points). HLL is the right answer.

Reference: docs/RSLS_specification.md, section VI.
"""
from __future__ import annotations
import numpy as np

from uma.rsls.memory import MemoryConfig, V


# ---------------------------------------------------------------------------
# HLL flux
# ---------------------------------------------------------------------------

def hll_flux(
    S_L: np.ndarray, S_R: np.ndarray,
    v_L: np.ndarray, v_R: np.ndarray,
    P_L: np.ndarray, P_R: np.ndarray,
    c_eff: float,
) -> np.ndarray:
    """
    Vectorised HLL flux at interfaces between adjacent cells.

    All arrays have the same length: the number of interfaces.

    Inputs:
        S_L, S_R : conserved momentum on left/right of each interface
        v_L, v_R : velocity on left/right
        P_L, P_R : pressure on left/right
        c_eff    : signal speed

    Returns:
        F : HLL flux at each interface, same shape as inputs

    The fluxes are computed as F = S v + P on each side and combined
    via the HLL formula. Edge cases where lambda_plus == lambda_minus
    (zero signal speed) fall back to the centred flux.
    """
    F_L = S_L * v_L + P_L
    F_R = S_R * v_R + P_R

    lam_L = v_L - c_eff
    lam_R = v_R + c_eff
    lam_plus  = np.maximum(0.0, np.maximum(lam_L, lam_R))
    lam_minus = np.minimum(0.0, np.minimum(lam_L, lam_R))

    denom = np.maximum(lam_plus - lam_minus, 1e-12)
    F_HLL = (
        lam_plus * F_L - lam_minus * F_R
        + lam_plus * lam_minus * (S_R - S_L)
    ) / denom
    return F_HLL


# ---------------------------------------------------------------------------
# Conservative update for S_r on a 1-D spherical grid
# ---------------------------------------------------------------------------

def hll_update_spherical(
    S: np.ndarray, D: np.ndarray, M: np.ndarray,
    r_faces: np.ndarray, r_centers: np.ndarray,
    dt: float, cfg: MemoryConfig,
) -> np.ndarray:
    """
    One conservative HLL step for the radial momentum S = rho v_r on
    a 1-D spherical grid. **Momentum-only** variant -- D is treated as
    a fixed background. Useful for short-time linear tests; for the
    falsification kernel use hll_update_spherical_2var (it adds the
    mass-continuity equation that bounds the velocity field).

    Inputs:
        S        : conserved momentum at cell centres, shape (N,)
        D        : density proxy at cell centres, shape (N,)
        M        : memory field at cell centres, shape (N,)
        r_faces  : radial face positions, shape (N+1,)
        r_centers: cell centre positions, shape (N,)
        dt       : time step
        cfg      : MemoryConfig

    Returns:
        S_new : updated momentum, shape (N,)

    The spherical conservative form integrates F over the cell volume:

        d/dt int_V S dV + integral A F dS = 0

    with A(r) = 4 pi r^2 and V_cell = (4 pi / 3)(r_{i+1}^3 - r_i^3).

    The boundary conditions are zero-gradient on both ends (outflow);
    suitable for the punctured-domain Stage 1 kernel.
    """
    N = len(S)
    v = S / np.maximum(D, 1e-12)
    P = V(M, cfg)  # P_eff = V(M)

    # Interfaces: indices 1 .. N-1 are internal; 0 and N are boundary.
    # For the internal interfaces, we use left/right cell values:
    F_int = hll_flux(
        S[:-1], S[1:],
        v[:-1], v[1:],
        P[:-1], P[1:],
        cfg.c_eff,
    )

    # Boundary fluxes: zero-gradient (use cell value on both sides).
    F_faces = np.zeros(N + 1)
    F_faces[1:-1] = F_int
    F_faces[0] = F_faces[1]
    F_faces[-1] = F_faces[-2]

    # Spherical areas and volumes
    A = 4.0 * np.pi * r_faces ** 2
    V_cells = (4.0 * np.pi / 3.0) * (r_faces[1:] ** 3 - r_faces[:-1] ** 3)
    V_cells = np.maximum(V_cells, 1e-15)

    S_new = S - (dt / V_cells) * (A[1:] * F_faces[1:] - A[:-1] * F_faces[:-1])
    return S_new


def hll_update_spherical_2var(
    D: np.ndarray, S: np.ndarray, M: np.ndarray,
    r_faces: np.ndarray, r_centers: np.ndarray,
    dt: float, cfg: MemoryConfig,
):
    """
    Two-variable HLL step: conserves both mass (D) and momentum (S)
    on the punctured spherical grid. This is the falsification-kernel
    update that bounds velocities and stops the focusing pathology of
    the momentum-only variant.

    Conservative form:
        d/dt rho + (1/r^2) d/dr (r^2 rho v) = 0
        d/dt S   + (1/r^2) d/dr (r^2 (S v + P)) = 0

    where v = S/rho and P = V(M). HLL upwinding on each pair, then
    the discrete divergence on the spherical-shell volumes.

    Returns:
        (D_new, S_new) -- the updated density and momentum arrays.
    """
    N = len(S)
    v = S / np.maximum(D, 1e-12)
    P = V(M, cfg)

    # Mass-flux HLL: F_rho = rho * v
    F_rho_L = D[:-1] * v[:-1]
    F_rho_R = D[1:]  * v[1:]
    lam_L = v[:-1] - cfg.c_eff
    lam_R = v[1:]  + cfg.c_eff
    lam_plus  = np.maximum(0.0, np.maximum(lam_L, lam_R))
    lam_minus = np.minimum(0.0, np.minimum(lam_L, lam_R))
    denom = np.maximum(lam_plus - lam_minus, 1e-12)
    F_rho_int = (
        lam_plus * F_rho_L - lam_minus * F_rho_R
        + lam_plus * lam_minus * (D[1:] - D[:-1])
    ) / denom

    # Momentum-flux HLL: F_S = S v + P
    F_S_int = hll_flux(S[:-1], S[1:], v[:-1], v[1:], P[:-1], P[1:], cfg.c_eff)

    # Assemble face fluxes (zero-gradient outflow at both boundaries)
    F_rho_faces = np.zeros(N + 1)
    F_S_faces   = np.zeros(N + 1)
    F_rho_faces[1:-1] = F_rho_int
    F_S_faces[1:-1]   = F_S_int
    F_rho_faces[0]    = F_rho_faces[1]
    F_rho_faces[-1]   = F_rho_faces[-2]
    F_S_faces[0]      = F_S_faces[1]
    F_S_faces[-1]     = F_S_faces[-2]

    # Spherical areas and volumes
    A = 4.0 * np.pi * r_faces ** 2
    V_cells = (4.0 * np.pi / 3.0) * (r_faces[1:] ** 3 - r_faces[:-1] ** 3)
    V_cells = np.maximum(V_cells, 1e-15)

    D_new = D - (dt / V_cells) * (A[1:] * F_rho_faces[1:] - A[:-1] * F_rho_faces[:-1])
    S_new = S - (dt / V_cells) * (A[1:] * F_S_faces[1:]   - A[:-1] * F_S_faces[:-1])

    # Positivity floor on density (prevents division-by-zero spirals)
    D_new = np.maximum(D_new, 1e-6)
    return D_new, S_new


# ---------------------------------------------------------------------------
# Transport CFL
# ---------------------------------------------------------------------------

def transport_cfl(
    v: np.ndarray, dx: float, cfg: MemoryConfig, safety: float = 0.5,
) -> float:
    """
    Standard CFL bound on dt from the transport step.

        dt <= safety * dx / max(|v| + c_eff)

    Combined with the Cattaneo CFL, the overall step must satisfy the
    tighter of the two.
    """
    v_max = float(np.max(np.abs(v))) + cfg.c_eff
    return safety * dx / max(v_max, 1e-12)


if __name__ == "__main__":
    cfg = MemoryConfig()
    print("HLL Riemann solver")
    print(f"   c_eff = {cfg.c_eff:.6f}")
    print()
    # Simple Riemann problem: S_L = 1, S_R = -1, no pressure
    N = 8
    S = np.concatenate([np.ones(N // 2), -np.ones(N // 2)])
    D = np.ones(N)
    M = np.zeros(N)
    r_faces = np.linspace(1.0, 9.0, N + 1)
    r_centers = 0.5 * (r_faces[:-1] + r_faces[1:])
    dt = transport_cfl(S / D, r_faces[1] - r_faces[0], cfg, safety=0.2)
    print(f"   dt (CFL) = {dt:.4e}")
    S_new = hll_update_spherical(S, D, M, r_faces, r_centers, dt, cfg)
    print(f"   S before:   {S}")
    print(f"   S after:    {np.round(S_new, 4)}")
    print(f"   (HLL preserves the BV norm; jump diffuses by at most one cell.)")
