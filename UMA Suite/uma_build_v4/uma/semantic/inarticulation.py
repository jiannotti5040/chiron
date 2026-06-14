"""
Inarticulation Function -- G Translation.

The Inarticulation Function G is the final stage of the Semantic Engine:
it takes the **solved** State-Space Closure (Omega) and translates it
back into tangible production metrics.

In the UMA framework:
    G: (z_Omega, posterior_Omega, friction_summary, constraint_report)
       -> ProductionMetrics

This is the inverse of the initial ingestion step: the engine
"inarticulates" (makes concrete) the abstract solved trajectory.

Built-in translators:
    NullInarticulator        -- identity pass.
    ProjectionInarticulator  -- linear readout W : R^d -> R^m + phi.
    LLMInarticulator         -- (placeholder for LLM observation readout).

Stages (mirrors the SE spec table):
    Ingestion       -> Initial differential, friction at t = 0
    Stability       -> Equalities Filter, friction descending
    Inarticulation  -> G Translation, friction below threshold
    Solve           -> State-Space Closure, closed = True
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# ProductionMetrics
# ---------------------------------------------------------------------------

@dataclass
class ProductionMetrics:
    """
    Tangible production output from the Inarticulation stage.
    All quantities are scalar or low-dimensional.
    """
    semantic_density: float       # 1 - SF_total in [0, 1]
    trajectory_delta: float       # ||z_Omega - z_target||
    scaling_coefficient: float    # det(Sigma)^{-1/d}
    stability_index: float        # 1 - final_constraint_violation
    constraint_converged: bool
    stage: str                    # 'ingestion' | 'stability' | 'inarticulation' | 'solve'
    closed: bool
    readout: Optional[np.ndarray] = None
    readout_labels: Optional[List[str]] = None
    friction_summary: Optional[Dict[str, Any]] = None
    constraint_report: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        d = {
            "semantic_density": round(self.semantic_density, 6),
            "trajectory_delta": round(self.trajectory_delta, 6),
            "scaling_coefficient": round(self.scaling_coefficient, 6),
            "stability_index": round(self.stability_index, 6),
            "constraint_converged": self.constraint_converged,
            "stage": self.stage,
            "closed": self.closed,
        }
        if self.readout is not None:
            d["readout"] = self.readout.tolist()
        if self.readout_labels is not None:
            d["readout_labels"] = self.readout_labels
        if self.friction_summary is not None:
            d["friction_summary"] = self.friction_summary
        if self.constraint_report is not None:
            d["constraint_report"] = self.constraint_report
        return d

    def __repr__(self) -> str:
        return (
            f"ProductionMetrics(stage={self.stage!r}, closed={self.closed}, "
            f"density={self.semantic_density:.4f}, "
            f"delta={self.trajectory_delta:.4f}, "
            f"stability={self.stability_index:.4f})"
        )


# ---------------------------------------------------------------------------
# Stage classifier
# ---------------------------------------------------------------------------

def classify_stage(
    sf_value: float,
    is_closed: bool,
    sf_stability_threshold: float = 0.50,
    sf_inarticulation_threshold: float = 0.20,
) -> str:
    """
    sf_value = 1.0          -> ingestion
    sf_value in (0.5, 1.0)  -> stability
    sf_value in (0.2, 0.5)  -> stability or inarticulation depending on sub-thresholds
    closed = True           -> solve
    """
    if is_closed:
        return "solve"
    if sf_value > sf_stability_threshold:
        return "ingestion"
    if sf_value > sf_inarticulation_threshold:
        return "stability"
    return "inarticulation"


# ---------------------------------------------------------------------------
# Scaling coefficient (single-representation FieldPosterior)
# ---------------------------------------------------------------------------

def _scaling_coefficient(posterior) -> float:
    """det(Sigma)^{-1/d}. High = concentrated. Low = diffuse."""
    d = posterior.dim
    Sigma = posterior.cov
    sign, logdet = np.linalg.slogdet(Sigma)
    if sign <= 0:
        return 0.0
    return float(np.exp(-logdet / d))


# ---------------------------------------------------------------------------
# Abstract Inarticulator
# ---------------------------------------------------------------------------

class Inarticulator(ABC):
    """Abstract base for G Translation functions."""

    @abstractmethod
    def translate(
        self,
        z_omega: np.ndarray,
        posterior,
        z_target: np.ndarray,
        friction_summary: Dict[str, Any],
        constraint_report: Dict[str, Any],
    ) -> ProductionMetrics:
        ...


# ---------------------------------------------------------------------------
# NullInarticulator
# ---------------------------------------------------------------------------

class NullInarticulator(Inarticulator):
    """Identity pass."""

    def translate(self, z_omega, posterior, z_target, friction_summary, constraint_report):
        sf_total = friction_summary.get("sf_total", 1.0)
        is_closed = friction_summary.get("is_closed", False)
        stage = classify_stage(sf_total, is_closed)
        delta = float(np.linalg.norm(z_omega - z_target))
        scl = _scaling_coefficient(posterior)
        final_viol = constraint_report.get("final_total_violation", 0.0)
        converged = constraint_report.get("converged", True)
        stability = float(np.clip(1.0 - final_viol, 0.0, 1.0))

        return ProductionMetrics(
            semantic_density=1.0 - sf_total,
            trajectory_delta=delta,
            scaling_coefficient=scl,
            stability_index=stability,
            constraint_converged=converged,
            stage=stage,
            closed=is_closed,
            readout=z_omega.copy(),
            readout_labels=[f"z_{i}" for i in range(len(z_omega))],
            friction_summary=friction_summary,
            constraint_report=constraint_report,
        )


# ---------------------------------------------------------------------------
# ProjectionInarticulator
# ---------------------------------------------------------------------------

class ProjectionInarticulator(Inarticulator):
    """Linear readout W : R^d -> R^m applied to z_Omega, then phi nonlinearity."""

    def __init__(
        self,
        W: np.ndarray,
        phi: Optional[Callable[[np.ndarray], np.ndarray]] = None,
        labels: Optional[List[str]] = None,
    ):
        self._W = np.asarray(W, dtype=float)
        self._phi = phi if phi is not None else (lambda x: x)
        self._labels = labels

    def translate(self, z_omega, posterior, z_target, friction_summary, constraint_report):
        sf_total = friction_summary.get("sf_total", 1.0)
        is_closed = friction_summary.get("is_closed", False)
        stage = classify_stage(sf_total, is_closed)

        readout_raw = self._phi(self._W @ z_omega)
        delta = float(np.linalg.norm(z_omega - z_target))
        scl = _scaling_coefficient(posterior)
        final_viol = constraint_report.get("final_total_violation", 0.0)
        converged = constraint_report.get("converged", True)
        stability = float(np.clip(1.0 - final_viol, 0.0, 1.0))

        return ProductionMetrics(
            semantic_density=1.0 - sf_total,
            trajectory_delta=delta,
            scaling_coefficient=scl,
            stability_index=stability,
            constraint_converged=converged,
            stage=stage,
            closed=is_closed,
            readout=readout_raw,
            readout_labels=self._labels,
            friction_summary=friction_summary,
            constraint_report=constraint_report,
        )

    @classmethod
    def principal_components(
        cls, dim: int, m: int = 4, labels: Optional[List[str]] = None,
    ) -> "ProjectionInarticulator":
        """Random orthonormal readout basis of rank m. Replace with calibrated W in production."""
        rng = np.random.default_rng(0)
        A = rng.standard_normal((dim, m))
        Q, _ = np.linalg.qr(A)
        return cls(W=Q.T[:m, :].copy(), labels=labels)
