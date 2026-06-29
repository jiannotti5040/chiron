# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.config -- Configuration dataclasses for the UMA pipeline.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GridConfig:
    """Spatial grid for psi(x,y) and projection."""
    N: int = 32           # grid points per axis
    L: float = 1.0        # box side length (m)
    n_modes: int = 4      # number of leading Fourier modes per axis (z dim = (2n+1)^2 - 1)


@dataclass
class GENERICConfig:
    """GENERIC dynamics parameters."""
    dt: float = 0.04
    diffusion: float = 0.05      # M scale (dissipative operator coefficient)
    advection: float = 0.10      # J scale (skew-symmetric Poisson part)
    reaction: float = 0.50       # double-well coefficient lambda
    noise: float = 0.0           # bounded Wiener amplitude (0 = deterministic)
    kT: float = 1.0              # thermal scale


@dataclass
class FilterConfig:
    """Linear-Gaussian Kalman filter on z."""
    process_noise: float = 0.05
    obs_noise: float = 0.10
    init_cov: float = 1.0


@dataclass
class Config:
    """Top-level UMA configuration."""
    grid: GridConfig = field(default_factory=GridConfig)
    generic: GENERICConfig = field(default_factory=GENERICConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    seed: int = 42

    def real_dim(self) -> int:
        """Dimension of the real-valued projected state z."""
        # leading Fourier modes (excluding DC), real and imag parts
        n = self.grid.n_modes
        # number of complex modes (excluding DC) in (2n+1)x(2n+1) low-pass box
        n_complex = (2 * n + 1) ** 2 - 1
        return 2 * n_complex
