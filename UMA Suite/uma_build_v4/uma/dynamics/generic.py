# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.dynamics.generic -- GENERIC dynamics for the complex field psi.

H[psi] = sum [ |grad psi|^2 / 2 + V(psi) ]   on a unit-spacing grid
V(psi) = -|psi|^2 / 2 + lambda |psi|^4 / 4   (double-well in |psi|)

dH/dpsi^* (Wirtinger derivative):
    dH/dpsi^* = -laplacian(psi) + dV/dpsi^*
    dV/dpsi^* = -psi/2 + lambda |psi|^2 psi

GENERIC step:
    psi <- psi + dt * (J grad H + M grad H)   with the convention that
    J is the skew (Hamiltonian) part and M is the symmetric (dissipative)
    part. Both act through the gradient grad_H = dH/dpsi^*.

    Skew part:   1j * grad_H            (rotational, Schroedinger-like)
    Symmetric:  -diffusion * grad_H     (gradient flow on H)

The MSR response field is the exact derivative:
    psi_hat = -dH/dpsi^*

This is the field that drives the canonical stress-energy tensor in
msr.tensor_bridge.
"""
from __future__ import annotations
import numpy as np
from uma.config import GENERICConfig


def laplacian_periodic(psi: np.ndarray) -> np.ndarray:
    """5-point Laplacian with periodic boundary conditions, dx = 1."""
    return (np.roll(psi, 1, axis=0) + np.roll(psi, -1, axis=0)
            + np.roll(psi, 1, axis=1) + np.roll(psi, -1, axis=1)
            - 4.0 * psi)


def hamiltonian(psi: np.ndarray, lam: float = 0.5) -> float:
    """
    H[psi] = sum [ |grad psi|^2 / 2 - |psi|^2 / 2 + lam/4 * |psi|^4 ]
    on a unit-spacing periodic grid.
    """
    dpx = np.roll(psi, -1, axis=0) - psi
    dpy = np.roll(psi, -1, axis=1) - psi
    grad_sq = (np.abs(dpx) ** 2 + np.abs(dpy) ** 2)
    V = -0.5 * np.abs(psi) ** 2 + 0.25 * lam * np.abs(psi) ** 4
    return float(np.sum(0.5 * grad_sq + V))


def msr_response(psi: np.ndarray, lam: float = 0.5) -> np.ndarray:
    """
    psi_hat = -dH/dpsi^* = laplacian(psi) - dV/dpsi^*
            = laplacian(psi) - ( -psi/2 + lam |psi|^2 psi )
            = laplacian(psi) + psi/2 - lam |psi|^2 psi

    This is the response field that drives the Noether stress-energy
    tensor T_mu_nu in msr.tensor_bridge. It is the exact (Wirtinger)
    derivative, not a finite-difference approximation.
    """
    return laplacian_periodic(psi) + 0.5 * psi - lam * np.abs(psi) ** 2 * psi


def entropy_S(psi: np.ndarray) -> float:
    """
    Shannon-like entropy of |psi|^2 normalized as a probability density.
    Used for tracking entropy production in the GENERIC step.
    """
    p = np.abs(psi) ** 2
    Z = float(p.sum())
    if Z <= 0:
        return 0.0
    p = p / Z
    p = np.clip(p, 1e-18, None)
    return float(-(p * np.log(p)).sum())


class GENERICDynamics:
    """
    GENERIC step:
        psi <- psi + dt [ 1j * advection * grad_H  -  diffusion * grad_H ]
              + sqrt(2 * diffusion * kT * dt) * eta   (bounded Wiener)

    with grad_H = dH/dpsi^* = -laplacian + dV/dpsi^* (sign-corrected so
    that gradient flow descends H).
    """

    def __init__(self, cfg: GENERICConfig | None = None):
        self.cfg = cfg if cfg is not None else GENERICConfig()
        self._rng: np.random.Generator | None = None

    def seed(self, seed: int) -> None:
        self._rng = np.random.default_rng(seed)

    def step(self, psi: np.ndarray) -> np.ndarray:
        cfg = self.cfg
        # grad_H = -psi_hat (since psi_hat = -dH/dpsi^*)
        psi_hat = msr_response(psi, lam=cfg.reaction)
        grad_H = -psi_hat
        # skew (J): 1j * grad_H ;  diss (M): -grad_H
        rhs = 1j * cfg.advection * grad_H - cfg.diffusion * grad_H
        psi_new = psi + cfg.dt * rhs
        if cfg.noise > 0:
            if self._rng is None:
                self._rng = np.random.default_rng(0)
            sigma = (2.0 * cfg.diffusion * cfg.kT * cfg.dt) ** 0.5
            eta = self._rng.standard_normal(psi.shape) + 1j * self._rng.standard_normal(psi.shape)
            psi_new = psi_new + cfg.noise * sigma * eta
        return psi_new

    def hamiltonian(self, psi: np.ndarray) -> float:
        return hamiltonian(psi, lam=self.cfg.reaction)

    def entropy(self, psi: np.ndarray) -> float:
        return entropy_S(psi)

    def dH_dpsi_conj(self, psi: np.ndarray) -> np.ndarray:
        """
        dH/d psi^* = -psi_hat. The pipeline uses this to compute
        psi_hat = -dH/d psi^*. Both forms are exact.
        """
        return -msr_response(psi, lam=self.cfg.reaction)
