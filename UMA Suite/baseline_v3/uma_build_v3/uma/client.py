"""
uma.client -- UMAClient: kernel orchestrating projection + dynamics + filter.

Architecture:
    UMAClient owns:
      - the spatial field psi(N, N)
      - a FieldProjection that maps psi <-> z
      - a Kalman filter over z
      - a GENERICDynamics evolver that steps psi

The semantic layer (engine, executor, IR) talks to the client through:
      client.evolve(dt)
      client.observe(obs, y)
      client.psi             -- current spatial state
      client.filter.posterior -- current Gaussian posterior over z
"""
from __future__ import annotations
import numpy as np
from typing import Optional
from uma.config import Config
from uma.core.projection import FieldProjection
from uma.core.state import FieldPosterior
from uma.core.filter import KalmanFilter
from uma.dynamics.generic import GENERICDynamics, hamiltonian, entropy_S, msr_response
from uma.observations.base import Observation


class UMAClient:
    """The deterministic kernel. Knows nothing of semantic intent."""

    def __init__(self, config: Optional[Config] = None):
        self.config = config if config is not None else Config()
        self.projection = FieldProjection(N=self.config.grid.N, n_modes=self.config.grid.n_modes)
        d = self.projection.real_dim
        post = FieldPosterior.initial(d=d, init_cov=self.config.filter.init_cov)
        self.filter = KalmanFilter(post, process_noise=self.config.filter.process_noise)
        self.dynamics = GENERICDynamics(self.config.generic)
        self.dynamics.seed(self.config.seed)
        self.psi: np.ndarray = np.zeros((self.config.grid.N, self.config.grid.N), dtype=complex)
        self.t = 0.0
        self._step_count = 0

    # ------------------------------------------------------------------
    # initialisation
    # ------------------------------------------------------------------
    def initialize(
        self,
        psi0: np.ndarray,
        sigma0: Optional[float] = None,
        dt: Optional[float] = None,
    ) -> None:
        psi0 = np.asarray(psi0, dtype=complex)
        if psi0.shape != self.psi.shape:
            raise ValueError(f"psi0 shape {psi0.shape} != grid shape {self.psi.shape}")
        self.psi = psi0
        z0 = self.projection.project(psi0)
        self.filter.posterior.mean = z0
        if sigma0 is not None:
            d = self.projection.real_dim
            self.filter.posterior.cov = float(sigma0) * np.eye(d)
        if dt is not None:
            self.dynamics.cfg.dt = float(dt)
        self.t = 0.0
        self._step_count = 0

    # Compat alias used by canonical executor / engine
    @property
    def posterior_state(self) -> FieldPosterior:
        return self.filter.posterior

    @posterior_state.setter
    def posterior_state(self, p: FieldPosterior) -> None:
        self.filter.posterior = p

    # ------------------------------------------------------------------
    # evolution
    # ------------------------------------------------------------------
    def evolve(self, dt: Optional[float] = None) -> None:
        """Forward GENERIC step. Updates psi, syncs posterior mean."""
        if dt is not None:
            old_dt = self.dynamics.cfg.dt
            self.dynamics.cfg.dt = dt
            self.psi = self.dynamics.step(self.psi)
            self.dynamics.cfg.dt = old_dt
            self.t += dt
        else:
            self.psi = self.dynamics.step(self.psi)
            self.t += self.dynamics.cfg.dt
        # gentle covariance inflation (process noise on z)
        d = self.projection.real_dim
        F = np.eye(d)
        Q = self.config.filter.process_noise * np.eye(d)
        # update mean from psi via projection (deterministic-only sync)
        z_new = self.projection.project(self.psi)
        self.filter.posterior.mean = z_new
        self.filter.posterior.cov = F @ self.filter.posterior.cov @ F.T + Q
        self.filter.posterior.cov = 0.5 * (self.filter.posterior.cov + self.filter.posterior.cov.T)
        self._step_count += 1

    def observe(self, obs: Observation, y: np.ndarray) -> None:
        """Apply a Gaussian observation update."""
        self.filter.update(np.asarray(y, dtype=float), obs.H, obs.R)
        # lift the updated z back into psi (band-limited)
        z = self.filter.posterior.mean
        self.psi = self.projection.lift(z)

    # ------------------------------------------------------------------
    # diagnostics
    # ------------------------------------------------------------------
    def hamiltonian(self) -> float:
        return hamiltonian(self.psi, lam=self.config.generic.reaction)

    def entropy(self) -> float:
        return entropy_S(self.psi)

    def msr_response(self) -> np.ndarray:
        return msr_response(self.psi, lam=self.config.generic.reaction)

    @property
    def z(self) -> np.ndarray:
        """Current projected state."""
        return self.filter.posterior.mean

    @property
    def cov(self) -> np.ndarray:
        return self.filter.posterior.cov
