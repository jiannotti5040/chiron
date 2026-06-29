# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
nonlinear_gr.py -- Full nonlinear curvature computation.

Beyond linearized theory. Computes:
    Gamma^k_ij    -- Christoffel symbols from g_ij = eta_ij + h_ij
    R^l_kij       -- Riemann curvature tensor
    R_ij          -- Ricci tensor
    R             -- Ricci scalar
    G_ij          -- Full Einstein tensor G_ij = R_ij - (1/2) g_ij R
    Residual: ||G_ij - 8 pi G T_ij||_F

The metric g_ij at each spatial point (x, y) is derived from the local
field energy density rho(x, y) = |psi(x, y)|^2:

    h_ij(x, y) = Phi(x, y) * delta_ij
    nabla^2 Phi = -4 pi G rho        (Poisson)
    g_ij = (1 + 2 Phi / c^2) delta_ij  (isotropic weak field metric)

Newtonian limit of GR but computed nonlinearly: Phi is solved exactly
for the given rho; Christoffel symbols are computed without assuming
|h| << 1. Strong fields (|Phi| ~ 1) depart from the linearized Einstein
tensor; this is captured by `nonlinearity`.
"""
from __future__ import annotations
import math
from dataclasses import dataclass

import numpy as np

from uma.msr.tensor_bridge import (
    _stress_tensor_spatial, _einstein_tensor_from_h, _spatial_mean,
)


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

@dataclass
class CurvatureResult:
    """Full curvature decomposition at one field state."""
    g: np.ndarray              # (2, 2, N, N)
    g_inv: np.ndarray          # (2, 2, N, N)
    Phi: np.ndarray            # (N, N)
    Gamma: np.ndarray          # (2, 2, 2, N, N)
    Ricci: np.ndarray          # (2, 2, N, N)
    Ricci_scalar: np.ndarray   # (N, N)
    G_full: np.ndarray         # (2, 2, N, N) full nonlinear G_ij
    G_linear: np.ndarray       # (2, 2, N, N) linearized for comparison
    T: np.ndarray              # (2, 2, N, N) MSR stress
    nonlinear_residual: float
    linear_residual: float
    nonlinearity: float
    G_mean: np.ndarray
    T_mean: np.ndarray
    kappa: float


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class NonlinearEinsteinSolver:
    """Computes the full nonlinear Einstein tensor from the field psi."""

    def __init__(self, cfg, G_newton: float = 1.0, c: float = 1.0):
        self.N = cfg.grid.N
        self.dx = 1.0 / cfg.grid.N
        self.G = G_newton
        self.c = c
        kx = 2 * math.pi * np.fft.fftfreq(self.N, d=self.dx)
        KX, KY = np.meshgrid(kx, kx)
        self.k2 = KX ** 2 + KY ** 2
        self.k2[0, 0] = 1.0

    def _grad(self, f: np.ndarray, axis: int) -> np.ndarray:
        return np.gradient(f, self.dx, axis=axis)

    def _poisson(self, rho: np.ndarray) -> np.ndarray:
        """nabla^2 Phi = -4 pi G rho via FFT."""
        rho_k = np.fft.fft2(rho)
        Phi_k = 4 * math.pi * self.G * rho_k / self.k2
        Phi_k[0, 0] = 0.0
        return np.fft.ifft2(Phi_k).real

    def _build_metric(self, Phi: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """g_ij = (1 + 2 Phi / c^2) delta_ij; g^ij = 1/factor * delta_ij."""
        N = self.N
        factor = 1.0 + 2 * Phi / self.c ** 2
        # avoid division by zero; physically Phi must be > -c^2/2
        factor = np.where(np.abs(factor) < 1e-12, 1e-12, factor)
        g = np.zeros((2, 2, N, N))
        g_inv = np.zeros((2, 2, N, N))
        g[0, 0] = factor; g[1, 1] = factor
        g_inv[0, 0] = 1.0 / factor; g_inv[1, 1] = 1.0 / factor
        return g, g_inv

    def _christoffel(self, g: np.ndarray, g_inv: np.ndarray) -> np.ndarray:
        """Gamma^k_ij = (1/2) g^kl (d_i g_lj + d_j g_li - d_l g_ij)."""
        N = self.N
        Gamma = np.zeros((2, 2, 2, N, N))
        # dg[m, i, j] = d_m g_ij
        dg = np.zeros((2, 2, 2, N, N))
        for mm in range(2):
            for ii in range(2):
                for jj in range(2):
                    dg[mm, ii, jj] = self._grad(g[ii, jj], mm)
        for k in range(2):
            for i in range(2):
                for j in range(2):
                    s = np.zeros((N, N))
                    for l in range(2):
                        s += g_inv[k, l] * (
                            dg[i, l, j] + dg[j, l, i] - dg[l, i, j]
                        )
                    Gamma[k, i, j] = 0.5 * s
        return Gamma

    def _ricci(self, Gamma: np.ndarray) -> np.ndarray:
        """R_ij = d_k G^k_ij - d_j G^k_ik + G^k_kl G^l_ij - G^k_jl G^l_ik."""
        N = self.N
        R = np.zeros((2, 2, N, N))
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    R[i, j] += self._grad(Gamma[k, i, j], k)
                    R[i, j] -= self._grad(Gamma[k, i, k], j)
                    for l in range(2):
                        R[i, j] += Gamma[k, k, l] * Gamma[l, i, j]
                        R[i, j] -= Gamma[k, j, l] * Gamma[l, i, k]
        return R

    def _einstein_full(
        self, Ricci: np.ndarray, R_scalar: np.ndarray, g: np.ndarray
    ) -> np.ndarray:
        """G_ij = R_ij - 1/2 g_ij R."""
        return Ricci - 0.5 * g * R_scalar[None, None, :, :]

    def _linear_einstein(self, h: np.ndarray) -> np.ndarray:
        """Linearized G^(1)[h] for comparison via the bridge primitive."""
        return _einstein_tensor_from_h(h, dx=self.dx)

    def compute(self, psi: np.ndarray, psi_hat: np.ndarray) -> CurvatureResult:
        rho = np.abs(psi) ** 2
        Phi = self._poisson(rho)
        g, g_inv = self._build_metric(Phi)
        Gamma = self._christoffel(g, g_inv)
        Ricci = self._ricci(Gamma)
        # R = g^ij R_ij
        R_scalar = sum(g_inv[i, j] * Ricci[i, j] for i in range(2) for j in range(2))
        G_full = self._einstein_full(Ricci, R_scalar, g)

        # Linearised comparison: h_ij = (g - eta) at this Phi
        eta = np.zeros_like(g); eta[0, 0] = 1.0; eta[1, 1] = 1.0
        h = g - eta
        G_linear = self._linear_einstein(h)

        # Stress tensor
        T = _stress_tensor_spatial(psi, psi_hat, dx=self.dx)
        T_8piG = 8 * math.pi * self.G * T

        nonlinear_residual = float(
            np.linalg.norm(G_full - T_8piG)
            / (np.linalg.norm(G_full) + 1e-15)
        )
        linear_residual = float(
            np.linalg.norm(G_linear - T_8piG)
            / (np.linalg.norm(G_linear) + 1e-15)
        )
        nonlinearity = float(
            np.linalg.norm(G_full - G_linear)
            / (np.linalg.norm(G_full) + 1e-15)
        )

        G_mean = _spatial_mean(G_full)
        T_mean = _spatial_mean(T)
        T_norm = float(np.linalg.norm(T_mean))
        G_norm = float(np.linalg.norm(G_mean))
        kappa = float(np.sum(T_mean * G_mean) / (G_norm ** 2 + 1e-15))

        return CurvatureResult(
            g=g, g_inv=g_inv, Phi=Phi,
            Gamma=Gamma, Ricci=Ricci, Ricci_scalar=R_scalar,
            G_full=G_full, G_linear=G_linear, T=T,
            nonlinear_residual=nonlinear_residual,
            linear_residual=linear_residual,
            nonlinearity=nonlinearity,
            G_mean=G_mean, T_mean=T_mean, kappa=kappa,
        )
