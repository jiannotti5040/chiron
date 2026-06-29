# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""uma.venturi -- 360-degree evolving Venturi for cross-domain injection."""
from uma.venturi.operator import (
    Venturi, VenturiOperator,
    SQRT2, SQRT_E, DELTA_S, INV_DELTA_S_SQ, C1_SILVER,
    silver_E_target, silver_dz_dt_floor, silver_field_scale,
    engine3_complex_state,
)
from uma.venturi.injector import CrossDomainInjector

__all__ = [
    "Venturi", "VenturiOperator", "CrossDomainInjector",
    "SQRT2", "SQRT_E", "DELTA_S", "INV_DELTA_S_SQ", "C1_SILVER",
    "silver_E_target", "silver_dz_dt_floor", "silver_field_scale",
    "engine3_complex_state",
]
