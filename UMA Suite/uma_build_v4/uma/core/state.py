# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.core.state -- FieldPosterior: Gaussian posterior over projected state z.
"""
from __future__ import annotations
import numpy as np
from dataclasses import dataclass


@dataclass
class FieldPosterior:
    """
    Gaussian posterior over the real-valued projected state z.

    mean : (d,) real array
    cov  : (d, d) symmetric positive-definite array
    """
    mean: np.ndarray
    cov: np.ndarray

    @classmethod
    def initial(cls, d: int, init_cov: float = 1.0):
        return cls(mean=np.zeros(d), cov=init_cov * np.eye(d))

    @classmethod
    def full(cls, mean: np.ndarray, Sigma: np.ndarray) -> "FieldPosterior":
        """Single-rep convenience: build a full-cov posterior."""
        return cls(mean=np.asarray(mean, dtype=float),
                   cov=np.asarray(Sigma, dtype=float))

    # Aliases for the canonical multi-rep API (single-rep here).
    @property
    def Sigma(self) -> np.ndarray:
        return self.cov

    @property
    def representation(self) -> str:
        return "full"

    @property
    def dim(self) -> int:
        return self.mean.shape[0]

    def copy(self) -> "FieldPosterior":
        return FieldPosterior(mean=self.mean.copy(), cov=self.cov.copy())

    def total_variance(self) -> float:
        return float(np.trace(self.cov))

    def log_det(self) -> float:
        sign, ld = np.linalg.slogdet(self.cov)
        if sign <= 0:
            return -np.inf
        return float(ld)
