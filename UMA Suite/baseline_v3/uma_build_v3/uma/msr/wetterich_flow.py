# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.msr.wetterich_flow -- Wetterich-style RG flow with Levy MSR couplings.

Classifies the universality class of the GENERIC field theory by the
ratio of Gaussian (nu_2) to fractional (c_alpha) couplings:

    Levy basin    -> non-local fractional Laplacian dominates,
                     dynamic exponent z = alpha (here alpha = 1.5)
    Gaussian      -> standard local diffusion dominates, z = 2

The cutoff is set heuristically; for a serious flow analysis run
calibrate.py with the relevant trajectory ensemble.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class LevyMSRCouplings:
    """Couplings of a Levy-MSR field theory at the UV cutoff."""
    nu_2: float       # Gaussian (k^2) diffusion coefficient
    nu_alpha: float   # fractional coefficient -- relative scale
    D: float          # noise strength (MSR D coupling)
    c_alpha: float    # fractional MSR coupling
    alpha: float      # fractional exponent (1 < alpha <= 2)
    D_dim: int = 2    # spatial dimension


def classify_basin(c: LevyMSRCouplings, cutoff: float = 0.5) -> str:
    """
    'levy' if c_alpha / (nu_2 + 1e-15) > cutoff (fractional sector wins),
    else 'gaussian'.
    """
    ratio = c.c_alpha / (c.nu_2 + 1e-15)
    return "levy" if ratio > cutoff else "gaussian"


def dynamic_exponent(c: LevyMSRCouplings) -> float:
    """
    z = alpha when Levy basin (fractional exponent), z = 2 in Gaussian.
    """
    if classify_basin(c) == "levy":
        return float(c.alpha)
    return 2.0
