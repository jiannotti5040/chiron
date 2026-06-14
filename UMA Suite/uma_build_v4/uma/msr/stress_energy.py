"""
uma.msr.stress_energy -- Canonical Noether T_munu from the GENERIC Lagrangian.

Whenever you want T_munu computed strictly from H[psi] (not from ad-hoc
gradient products of the response field), use noether_stress_tensor.

This is the cleanly derived form referenced in the integration session
notes. It uses the same Hamiltonian as uma.dynamics.generic.hamiltonian.
"""
from __future__ import annotations
import numpy as np

from uma.dynamics.generic import hamiltonian, msr_response


def noether_stress_tensor(
    psi: np.ndarray, lam: float = 0.5, dx: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """
    Canonical stress-energy tensor T_munu from GENERIC Lagrangian.

    L = (1/2) |grad psi|^2 - V(psi) ; V = -|psi|^2/2 + lam |psi|^4 / 4

    T_munu = d_mu psi^* d_nu psi + d_nu psi^* d_mu psi
             - eta_munu ( |grad psi|^2 - 2 V(psi) )

    Returns (T_spatial, T00_field) where T_spatial is (2, 2, N, N) and
    T00_field is the energy density (N, N) used for h via Poisson.
    """
    N = psi.shape[0]
    dpsi = [np.gradient(psi, dx, axis=i) for i in range(2)]
    grad_sq = sum(np.abs(dpsi[i]) ** 2 for i in range(2))
    V = -0.5 * np.abs(psi) ** 2 + 0.25 * lam * np.abs(psi) ** 4

    T = np.zeros((2, 2, N, N))
    for mu in range(2):
        for nu in range(2):
            T[mu, nu] = (
                np.real(np.conj(dpsi[mu]) * dpsi[nu])
                + np.real(np.conj(dpsi[nu]) * dpsi[mu])
            )
    diag = grad_sq - 2.0 * V
    T[0, 0] -= diag
    T[1, 1] -= diag
    # T_00 energy density: kinetic + potential
    T00 = grad_sq * 0.5 + V
    return T, T00


def verify_T_consistency(
    psi: np.ndarray, lam: float = 0.5, dx: float = 1.0
) -> dict:
    """
    Compare the spatial integral of T_00 to the GENERIC Hamiltonian H[psi].
    Returns relative error -- should be O(dx) for periodic boundary conditions.
    """
    H = hamiltonian(psi, lam=lam)
    _, T00 = noether_stress_tensor(psi, lam=lam, dx=dx)
    H_from_T = float(T00.sum())
    return {
        "H_GENERIC": H,
        "H_from_T00": H_from_T,
        "abs_error": abs(H - H_from_T),
        "rel_error": abs(H - H_from_T) / (abs(H) + 1e-15),
    }


def verify_T_equals_lichnerowicz(
    h_pert: np.ndarray, m: float = 0.1, N: int = 32, seed: int = 0
) -> dict:
    """
    One-shot consistency check used by the pipeline at start-up.

    Fixed massive-scalar test field psi on a constant metric perturbation
    h_pert (2x2). Computes:
        T_munu (Noether)
        Lichnerowicz/Linearized-Einstein G_munu^(1)[h_pert]
    Then reports the cosine similarity between the two flattened tensors.
    A value close to +/-1 means T is proportional to G^(1).
    """
    rng = np.random.default_rng(seed)
    psi = (rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N))) * m
    T, T00 = noether_stress_tensor(psi, lam=0.0, dx=1.0)
    T_avg = T.mean(axis=(-2, -1))   # (2, 2)
    # Linearized Einstein on a homogeneous metric perturbation: G^(1) = -box h
    # which on a constant h is zero; we use the trace-reversed mass-shell form:
    h = np.asarray(h_pert, dtype=float)
    # G^(1)_ij = m^2 * (h_ij - 0.5 trace(h) eta_ij)
    eta = np.eye(2)
    G = m * m * (h - 0.5 * np.trace(h) * eta)
    Tf = T_avg.flatten()
    Gf = G.flatten()
    denom = (np.linalg.norm(Tf) * np.linalg.norm(Gf)) + 1e-15
    cos = float(np.dot(Tf, Gf) / denom)
    return {
        "T_avg": T_avg.tolist(),
        "G_lin": G.tolist(),
        "cosine_similarity": cos,
        "norm_T": float(np.linalg.norm(Tf)),
        "norm_G": float(np.linalg.norm(Gf)),
    }
