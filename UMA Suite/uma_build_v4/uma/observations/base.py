"""
uma.observations.base -- Observation operators feeding the Kalman filter.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


class Observation:
    """Abstract observation operator y = H z + noise."""

    @property
    def H(self) -> np.ndarray:
        raise NotImplementedError

    @property
    def R(self) -> np.ndarray:
        raise NotImplementedError

    @property
    def dim_y(self) -> int:
        return self.H.shape[0]


@dataclass
class GaussianObservation(Observation):
    """Linear-Gaussian observation: y = H z + N(0, R)."""
    _H: np.ndarray
    _R: np.ndarray

    def __init__(self, H: np.ndarray, R: np.ndarray | float):
        self._H = np.asarray(H, dtype=float)
        if np.ndim(R) == 0:
            R = float(R) * np.eye(self._H.shape[0])
        self._R = np.asarray(R, dtype=float)

    @property
    def H(self) -> np.ndarray:
        return self._H

    @property
    def R(self) -> np.ndarray:
        return self._R
