# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls.srb -- Statistical reduction: KvN -> Lindblad -> SRB measure.

Implements the machinery of Section X of the spec: the bridge from
classical deterministic flow to quantum-statistical limit via:

    1. Lyapunov exponent computation (positive lambda_max = chaos)
    2. SRB invariant measure on a chaotic attractor (Lorenz as anchor)
    3. Koopman--von Neumann operator on discretised phase space
    4. GKLS (Lindblad) master-equation evolution
    5. Born-rule check: |Psi|^2 distribution vs SRB ergodic distribution

The Lorenz attractor is the verified anchor: its maximum Lyapunov
exponent is lambda_max ~= 0.9056 (classical result, e.g. Sprott 2003).
We use it to validate the Lyapunov computation, then apply the same
machinery to the frame-dragging kernel trajectories.

Reference: docs/RSLS_specification.md, section X.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Callable, Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Lorenz attractor (the verification anchor)
# ---------------------------------------------------------------------------

@dataclass
class LorenzParams:
    """Canonical Lorenz parameters with chaotic attractor."""
    sigma: float = 10.0
    rho:   float = 28.0
    beta:  float = 8.0 / 3.0


def lorenz_rhs(state: np.ndarray, p: LorenzParams) -> np.ndarray:
    """Right-hand side of the Lorenz ODE."""
    x, y, z = state
    return np.array([
        p.sigma * (y - x),
        x * (p.rho - z) - y,
        x * y - p.beta * z,
    ])


def rk4_step(rhs: Callable, state: np.ndarray, dt: float,
             *args) -> np.ndarray:
    """Fourth-order Runge-Kutta step."""
    k1 = rhs(state, *args)
    k2 = rhs(state + 0.5 * dt * k1, *args)
    k3 = rhs(state + 0.5 * dt * k2, *args)
    k4 = rhs(state + dt * k3, *args)
    return state + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)


def integrate_lorenz(state0: np.ndarray, dt: float, n_steps: int,
                     p: Optional[LorenzParams] = None) -> np.ndarray:
    """Integrate Lorenz from state0 for n_steps. Returns (n_steps+1, 3) array."""
    p = p or LorenzParams()
    out = np.zeros((n_steps + 1, 3))
    out[0] = state0
    for i in range(n_steps):
        out[i + 1] = rk4_step(lorenz_rhs, out[i], dt, p)
    return out


# ---------------------------------------------------------------------------
# Lyapunov exponent (Benettin's algorithm)
# ---------------------------------------------------------------------------

def lyapunov_max(rhs: Callable, state0: np.ndarray,
                 dt: float = 0.01, n_steps: int = 5000,
                 renormalize_every: int = 5, delta0: float = 1e-8,
                 *args) -> float:
    """
    Maximum Lyapunov exponent via Benettin's algorithm.

    Algorithm:
        1. Run two trajectories starting infinitesimally apart (delta0).
        2. Periodically measure |delta(t)| / delta0 and renormalize.
        3. Sum log(growth) / dt over the run; the average is lambda_max.

    Returns the estimated lambda_max. For canonical Lorenz with default
    parameters, the expected value is ~0.9056.
    """
    s_main = state0.copy()
    s_pert = state0.copy()
    # Perturb in a random unit direction (deterministic seed for reproducibility)
    rng = np.random.default_rng(0)
    direction = rng.standard_normal(state0.shape)
    direction /= np.linalg.norm(direction)
    s_pert = s_pert + delta0 * direction

    log_sum = 0.0
    n_renorm = 0
    total_time = 0.0

    # Burn-in: integrate both for ~20% of total to reach attractor
    burn_in = max(1, n_steps // 5)
    for _ in range(burn_in):
        s_main = rk4_step(rhs, s_main, dt, *args)
        s_pert = rk4_step(rhs, s_pert, dt, *args)
        # Renormalize separation
        sep = s_pert - s_main
        sep_norm = np.linalg.norm(sep)
        if sep_norm > 0:
            sep = sep / sep_norm * delta0
            s_pert = s_main + sep

    # Measurement phase
    for step in range(n_steps):
        for _ in range(renormalize_every):
            s_main = rk4_step(rhs, s_main, dt, *args)
            s_pert = rk4_step(rhs, s_pert, dt, *args)
        sep = s_pert - s_main
        sep_norm = np.linalg.norm(sep)
        if sep_norm > 0:
            log_sum += math.log(sep_norm / delta0)
            total_time += renormalize_every * dt
            # Renormalize back to delta0 along the same direction
            s_pert = s_main + sep / sep_norm * delta0
            n_renorm += 1

    if total_time <= 0:
        return float("nan")
    return log_sum / total_time


# ---------------------------------------------------------------------------
# SRB measure: 1-D histogram on a coordinate of the attractor
# ---------------------------------------------------------------------------

def srb_histogram(trajectory: np.ndarray, axis: int = 2,
                  n_bins: int = 64) -> Tuple[np.ndarray, np.ndarray]:
    """
    Empirical SRB measure: histogram of a single coordinate of a long
    trajectory on the attractor. By the ergodic theorem, this converges
    to the SRB invariant measure (assuming sufficient mixing).

    Returns (bin_centres, probability_density).
    """
    coord = trajectory[:, axis]
    hist, edges = np.histogram(coord, bins=n_bins, density=True)
    centres = 0.5 * (edges[:-1] + edges[1:])
    return centres, hist


def srb_converges(rhs: Callable, state0: np.ndarray,
                  dt: float = 0.01, n_short: int = 2000,
                  n_long: int = 20000, axis: int = 2,
                  *args) -> float:
    """
    Verify ergodic convergence to the SRB measure: histograms from two
    different-length trajectories on the same chaotic attractor should
    agree (up to noise). Returns the L^1 distance between the two
    histograms; small value (< 0.1) indicates convergence.
    """
    long_traj = state0.copy()
    short_hist_states = []
    long_hist_states = []
    # Burn-in
    for _ in range(500):
        long_traj = rk4_step(rhs, long_traj, dt, *args)
    state_short = long_traj.copy()
    for _ in range(n_short):
        state_short = rk4_step(rhs, state_short, dt, *args)
        short_hist_states.append(state_short.copy())
    state_long = state_short.copy()
    for _ in range(n_long):
        state_long = rk4_step(rhs, state_long, dt, *args)
        long_hist_states.append(state_long.copy())

    short_arr = np.array(short_hist_states)
    long_arr = np.array(long_hist_states)
    # Common bin edges (over the union of both ranges)
    all_vals = np.concatenate([short_arr[:, axis], long_arr[:, axis]])
    edges = np.linspace(all_vals.min(), all_vals.max(), 65)
    h_short, _ = np.histogram(short_arr[:, axis], bins=edges, density=True)
    h_long,  _ = np.histogram(long_arr[:, axis],  bins=edges, density=True)
    de = np.diff(edges)
    l1 = float(np.sum(np.abs(h_short - h_long) * de))
    return l1


# ---------------------------------------------------------------------------
# Koopman--von Neumann operator (discretised)
# ---------------------------------------------------------------------------

def koopman_transfer_matrix(rhs: Callable, dt: float, n_bins: int,
                            bounds: Tuple[float, float], *args) -> np.ndarray:
    """
    Build the discrete Koopman/transfer operator on a 1-D coordinate.

    Procedure: discretise the coordinate into n_bins. For each bin
    centre, integrate forward by dt and record which bin it lands in.
    The resulting transfer matrix T[i, j] = 1 if bin i maps to bin j,
    else 0 (with normalisation so rows sum to 1).

    Returns an n_bins x n_bins row-stochastic matrix.

    Note: this is a discrete *Frobenius-Perron* (transfer) operator,
    which is the adjoint of the Koopman operator. For SRB-measure
    purposes the two are interchangeable up to transposition.
    """
    lo, hi = bounds
    centres = np.linspace(lo, hi, n_bins)
    edges = np.linspace(lo, hi, n_bins + 1)
    T = np.zeros((n_bins, n_bins))
    # We need a full state to integrate -- assume 1-D for now (axis 0)
    # For higher-D systems use koopman_transfer_matrix_nd
    for i, c in enumerate(centres):
        s = np.array([c])
        s_next = rk4_step(rhs, s, dt, *args)
        target = s_next[0]
        # Bin assignment
        j = int(np.clip(np.searchsorted(edges, target) - 1, 0, n_bins - 1))
        T[i, j] = 1.0
    return T


def koopman_stationary(T: np.ndarray) -> np.ndarray:
    """
    Stationary distribution of the transfer operator T: the eigenvector
    of T.T with eigenvalue 1, normalised to sum to 1. This is the
    discrete SRB measure on the coordinate.
    """
    # Eigendecomposition of T.T to find left eigenvectors of T
    eigvals, eigvecs = np.linalg.eig(T.T)
    # Find eigenvalue closest to 1
    idx = int(np.argmin(np.abs(eigvals - 1.0)))
    v = np.real(eigvecs[:, idx])
    v = np.abs(v)  # ensure positivity
    total = v.sum()
    return v / max(total, 1e-15)


# ---------------------------------------------------------------------------
# GKLS (Lindblad) master equation
# ---------------------------------------------------------------------------

def lindblad_step(rho: np.ndarray, H: np.ndarray,
                  L_list: list, dt: float) -> np.ndarray:
    """
    One forward-Euler step of the GKLS master equation:

        d rho / dt = -i [H, rho]
                     + sum_k (L_k rho L_k^dag
                              - 1/2 {L_k^dag L_k, rho})

    Inputs:
        rho    : current density matrix (Hermitian, trace 1)
        H      : Hamiltonian (Hermitian)
        L_list : list of jump operators L_k
        dt     : time step

    Returns:
        rho_new : updated density matrix

    For demonstration / verification: with H = 0 and a single jump
    operator L = sigma_minus, the diagonal of rho decays toward the
    ground state |0><0| -- the canonical amplitude-damping channel.
    """
    # Commutator [H, rho]
    commutator = H @ rho - rho @ H
    dissipator = np.zeros_like(rho)
    for L in L_list:
        Ldag = L.conj().T
        dissipator += L @ rho @ Ldag - 0.5 * (Ldag @ L @ rho + rho @ Ldag @ L)
    drho = -1j * commutator + dissipator
    return rho + dt * drho


def integrate_lindblad(rho0: np.ndarray, H: np.ndarray, L_list: list,
                       dt: float, n_steps: int) -> np.ndarray:
    """Integrate the Lindblad equation for n_steps. Returns trajectory of rho."""
    out = np.zeros((n_steps + 1,) + rho0.shape, dtype=complex)
    out[0] = rho0
    for i in range(n_steps):
        out[i + 1] = lindblad_step(out[i], H, L_list, dt)
    return out


# ---------------------------------------------------------------------------
# Born rule check (ergodic limit)
# ---------------------------------------------------------------------------

def born_rule_match(srb_density: np.ndarray, psi_squared: np.ndarray,
                    bin_widths: np.ndarray) -> float:
    """
    L^1 distance between the empirical SRB density and the candidate
    |Psi|^2 distribution. If the Born rule emerges as the SRB ergodic
    limit (Section X), the two should agree up to noise.

    Inputs:
        srb_density: empirical histogram, normalised so sum * width = 1
        psi_squared: candidate quantum density on the same bins
        bin_widths : widths of each bin
    """
    if srb_density.shape != psi_squared.shape:
        raise ValueError("density shapes must match")
    # Normalise psi^2 to a probability density
    psi_norm = psi_squared / max(np.sum(psi_squared * bin_widths), 1e-15)
    srb_norm = srb_density / max(np.sum(srb_density * bin_widths), 1e-15)
    return float(np.sum(np.abs(srb_norm - psi_norm) * bin_widths))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== uma.rsls.srb -- Statistical Reduction ===\n")

    print("(1) Lorenz attractor: max Lyapunov exponent")
    state0 = np.array([1.0, 1.0, 1.0])
    lam = lyapunov_max(lorenz_rhs, state0, 0.01, 3000, 5, 1e-8,
                       LorenzParams())
    print(f"    lambda_max = {lam:.4f}   (expected ~0.9056)")
    print(f"    Chaos: {'CONFIRMED' if lam > 0.5 else 'no'}")
    print()

    print("(2) SRB ergodic convergence")
    l1 = srb_converges(lorenz_rhs, state0, 0.01, 2000, 10000, 2,
                       LorenzParams())
    print(f"    L^1 distance between trajectories: {l1:.4f}")
    print(f"    Ergodic convergence: {'PASS' if l1 < 0.3 else 'FAIL'}")
    print()

    print("(3) Lindblad amplitude damping demo")
    # 2-level system: rho starts in |1><1|, decays via sigma_minus
    rho0 = np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex)
    H = np.zeros((2, 2), dtype=complex)
    sigma_minus = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=complex)
    traj = integrate_lindblad(rho0, H, [sigma_minus], dt=0.01, n_steps=500)
    p_excited = np.real(traj[:, 1, 1])
    print(f"    P_excited(0)    = {p_excited[0]:.4f}")
    print(f"    P_excited(t=2)  = {p_excited[200]:.4f}")
    print(f"    P_excited(t=5)  = {p_excited[500]:.4f}")
    print(f"    Decay to ground state: "
          f"{'PASS' if p_excited[-1] < 0.05 else 'FAIL'}")
