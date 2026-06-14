"""
metric_solver.py -- Self-consistent iterative metric solver.

Solves for g_munu self-consistently from the field psi.

CURRENT (one-way):
    psi -> T_munu -> h_munu (Poisson) -> G_munu^(1)[h]
    (metric has no feedback into the field evolution.)

THIS MODULE (self-consistent):
    psi^(n) -> T_munu^(n) -> h_munu^(n) -> modified dynamics -> psi^(n+1)
    The metric feeds back into the field through the curved d'Alembertian:
        box_g psi = box_eta psi + h^munu d_mu d_nu psi + ...

    Iteration continues until ||h^(n) - h^(n-1)|| / ||h^(n)|| < tol.

PHYSICAL MEANING:
    At convergence, psi* and h* are mutually consistent. The field
    produces the metric that curves the space in which it evolves.
    Genuine GR solution -- not a verification of a known result.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

import numpy as np

from uma.dynamics.generic import GENERICDynamics, msr_response
from uma.msr.tensor_bridge import _stress_tensor_spatial, _metric_from_T


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

@dataclass
class MetricState:
    """Current state of the self-consistent metric iteration."""
    iteration: int
    h: np.ndarray         # (2, 2, N, N) metric perturbation
    psi: np.ndarray       # (N, N) field at this iteration
    psi_hat: np.ndarray   # (N, N) MSR response
    T_avg: np.ndarray     # (2, 2) spatial-mean stress
    h_avg: np.ndarray     # (2, 2) spatial-mean perturbation
    delta_h_norm: float   # ||h - h_prev||
    rel_change: float     # delta_h_norm / ||h||
    converged: bool


@dataclass
class MetricSolveResult:
    history: List[MetricState] = field(default_factory=list)
    final: MetricState = None
    converged: bool = False
    n_iters: int = 0


# ---------------------------------------------------------------------------
# Solver
# ---------------------------------------------------------------------------

class IterativeMetricSolver:
    """
    Iterates psi <-> h until they stop changing (within tol).

    The dynamics are perturbed by h via a simple metric-coupling step:
        psi -> psi + dt * (eta_step + (h^00 + h^11) Lap psi)
    which is the leading curved-d'Alembertian correction in 2D.
    """

    def __init__(
        self,
        cfg,
        dt: float = 0.04,
        max_iters: int = 50,
        tol: float = 1e-3,
        coupling: float = 1.0,
    ):
        self.cfg = cfg
        self.dt = dt
        self.max_iters = max_iters
        self.tol = tol
        self.coupling = coupling
        self.dx = 1.0 / cfg.grid.N
        self.dynamics = GENERICDynamics(cfg.generic)

    def _laplacian(self, psi: np.ndarray) -> np.ndarray:
        return (
            np.roll(psi, 1, 0) + np.roll(psi, -1, 0)
            + np.roll(psi, 1, 1) + np.roll(psi, -1, 1) - 4 * psi
        ) / (self.dx ** 2)

    def _curved_step(self, psi: np.ndarray, h: np.ndarray) -> np.ndarray:
        """One step of psi evolution under the metric h (leading correction)."""
        eta_step = self.dynamics.step(psi)
        h_trace = h[0, 0] + h[1, 1]
        lap = self._laplacian(psi)
        return eta_step + self.dt * self.coupling * h_trace * lap

    def solve(
        self,
        psi_initial: np.ndarray,
        psi_hat_initial: np.ndarray = None,
        n_field_steps_per_iter: int = 5,
    ) -> MetricSolveResult:
        """Iterate to a self-consistent (psi*, h*) pair."""
        N = psi_initial.shape[0]
        psi = psi_initial.copy()
        psi_hat = (
            psi_hat_initial.copy() if psi_hat_initial is not None
            else msr_response(psi, lam=self.cfg.generic.reaction)
        )
        h = np.zeros((2, 2, N, N))
        history: List[MetricState] = []

        for it in range(self.max_iters):
            # 1. compute T from current (psi, psi_hat)
            T_spatial = _stress_tensor_spatial(psi, psi_hat, dx=self.dx)
            # 2. solve Poisson for h
            h_new = _metric_from_T(T_spatial, G_newton=1.0, dx=self.dx)
            # 3. norms
            denom = np.linalg.norm(h_new) + 1e-15
            delta = np.linalg.norm(h_new - h)
            rel = delta / denom
            converged = rel < self.tol and it > 0
            T_avg = T_spatial.mean(axis=(-2, -1))
            h_avg = h_new.mean(axis=(-2, -1))
            state = MetricState(
                iteration=it,
                h=h_new, psi=psi.copy(), psi_hat=psi_hat.copy(),
                T_avg=T_avg, h_avg=h_avg,
                delta_h_norm=float(delta), rel_change=float(rel),
                converged=converged,
            )
            history.append(state)
            if converged:
                break
            # 4. evolve psi under the new metric
            h = h_new
            for _ in range(n_field_steps_per_iter):
                psi = self._curved_step(psi, h)
            psi_hat = msr_response(psi, lam=self.cfg.generic.reaction)

        return MetricSolveResult(
            history=history,
            final=history[-1],
            converged=history[-1].converged,
            n_iters=len(history),
        )
