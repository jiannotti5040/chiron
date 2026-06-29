# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls.coupling -- bridge between the RSLS memory sector and the
existing UMA TensorBridge.

When a Phase A run (or a Menger-AMR run) produces an M field, the
gradient stress T_{mu,nu}^{(grad M)} from memory.gradient_stress() is
*added* to the canonical MSR stress tensor in TensorBridge. This makes
the new contribution visible to the existing Einstein-consistency
residual check without modifying the canonical bridge.

The intended use:

    bridge = TensorBridge(cfg, residual_threshold=0.15, window=30)
    rsls   = RSLSCoupling(memory_cfg=MemoryConfig())
    for step in range(N):
        ...
        # current GENERIC psi and MSR response
        psi_hat = client.dynamics.msr_response(psi)
        # current RSLS memory field projected to the 2D grid
        M_2d = ...   # shape (N, N)
        # combined stress: bridge.update is given the original psi, psi_hat,
        # plus the RSLS additive T^(grad M) which we compute separately
        rec = rsls.augmented_update(bridge, psi, psi_hat, M_2d, dx, t)

The augmented record carries the extra "rsls_residual" / "nec_min"
diagnostics alongside the canonical Einstein residual.

Reference: docs/RSLS_specification.md section IV.4D; coupling design
in docs/RSLS_menger_substrate.md section 3.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np

from uma.rsls.memory import MemoryConfig, gradient_stress, nec_violation


# ---------------------------------------------------------------------------
# Augmented record
# ---------------------------------------------------------------------------

@dataclass
class RSLSTensorRecord:
    """Augmented per-step record carrying RSLS-specific diagnostics."""
    t: float
    canonical_T: np.ndarray             # (2,2) MSR-only T
    rsls_T: np.ndarray                  # (2,2) T^(grad M)
    combined_T: np.ndarray              # (2,2) sum
    kappa: float                        # least-squares slope vs G_combined
    residual_norm: float
    relative_residual: float
    einstein_satisfied: bool
    nec_min: float                      # min of T^(grad M) k k over null vecs
    nec_compliant: bool


# ---------------------------------------------------------------------------
# Coupling
# ---------------------------------------------------------------------------

class RSLSCoupling:
    """
    Adds T^(grad M) to a TensorBridge update without modifying the bridge.

    The coupling is *additive*: T_total = T_MSR + T^(grad M).
    The bridge's internal Poisson and Einstein-tensor stages are then run
    on this total. The result is a single residual measuring "how well
    the *combined* matter sources satisfy the linearised Einstein equation."

    This is the operative meaning of the Stage 4D claim that "the gradient
    stress backreacts on the geometry": the geometry sees both sources.
    """

    def __init__(
        self,
        memory_cfg: Optional[MemoryConfig] = None,
        residual_threshold: float = 0.15,
        nec_tolerance: float = -1e-12,
    ):
        self.cfg = memory_cfg or MemoryConfig()
        self.residual_threshold = residual_threshold
        self.nec_tolerance = nec_tolerance
        self.records: list[RSLSTensorRecord] = []

    def augmented_update(
        self,
        bridge,                  # uma.msr.tensor_bridge.TensorBridge
        psi: np.ndarray,
        psi_hat: np.ndarray,
        M_2d: np.ndarray,
        dx: float,
        t: float,
    ) -> RSLSTensorRecord:
        """
        Run a TensorBridge update and add the RSLS gradient stress.

        Inputs:
            bridge   : existing TensorBridge instance
            psi      : current complex field (N, N)
            psi_hat  : MSR response (N, N)
            M_2d     : memory field on the same 2D grid (N, N)
            dx       : grid spacing
            t        : current time

        Returns:
            RSLSTensorRecord with the canonical-plus-RSLS diagnostics

        Side effect: appends a canonical record to bridge.records as well
        (so the existing pipeline reporting still works).
        """
        # (1) Get the canonical record from the unmodified bridge
        canonical = bridge.update(psi, psi_hat, t)

        # (2) Compute the additive RSLS stress and spatial-average
        T_rsls_spatial = gradient_stress(M_2d, dx, self.cfg)   # (2,2,N,N)
        T_rsls = T_rsls_spatial.mean(axis=(-2, -1))             # (2,2)

        # (3) Combined T = canonical + RSLS contribution
        T_combined = canonical.T + T_rsls

        # (4) Recompute kappa and residual against the canonical G
        G = canonical.G
        T_norm = float(np.linalg.norm(T_combined))
        G_norm = float(np.linalg.norm(G))
        if G_norm > 1e-15:
            kappa = float(np.sum(T_combined * G) / (G_norm ** 2))
        else:
            kappa = 0.0
        residual = float(np.linalg.norm(T_combined - kappa * G))
        rel_res = residual / (T_norm + 1e-15)
        satisfied = rel_res < self.residual_threshold

        # (5) NEC compliance check on the new stress
        nec = nec_violation(M_2d, dx, self.cfg)
        nec_ok = nec >= self.nec_tolerance

        rec = RSLSTensorRecord(
            t=t,
            canonical_T=canonical.T,
            rsls_T=T_rsls,
            combined_T=T_combined,
            kappa=kappa,
            residual_norm=residual,
            relative_residual=rel_res,
            einstein_satisfied=satisfied,
            nec_min=nec,
            nec_compliant=nec_ok,
        )
        self.records.append(rec)
        return rec

    # -----------------------------------------------------------------
    # Diagnostics
    # -----------------------------------------------------------------

    @property
    def is_einstein_satisfied(self) -> bool:
        return bool(self.records and self.records[-1].einstein_satisfied)

    @property
    def is_nec_compliant(self) -> bool:
        return bool(self.records and all(r.nec_compliant for r in self.records))

    @property
    def residual_history(self) -> np.ndarray:
        return np.array([r.relative_residual for r in self.records])

    @property
    def nec_history(self) -> np.ndarray:
        return np.array([r.nec_min for r in self.records])

    def summary(self) -> dict:
        if not self.records:
            return {"status": "no_data"}
        final = self.records[-1]
        return {
            "n_steps":                  len(self.records),
            "kappa_final":              round(final.kappa, 6),
            "rel_residual_final":       round(final.relative_residual, 6),
            "einstein_satisfied":       final.einstein_satisfied,
            "rel_residual_min":         round(float(self.residual_history.min()), 6),
            "nec_min_overall":          round(float(self.nec_history.min()), 8),
            "nec_compliant_all_steps":  self.is_nec_compliant,
        }
