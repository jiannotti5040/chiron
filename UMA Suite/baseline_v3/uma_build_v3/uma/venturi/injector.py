# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.venturi.injector -- CrossDomainInjector.

Applies 360-degree azimuthal injection of synthetic amplitudes across
both the MSR (response) and semantic (field) domains. Sits on top of the
Venturi operator and routes injection through it for each domain.
"""
from __future__ import annotations
import numpy as np

from uma.venturi.operator import Venturi, engine3_complex_state


class CrossDomainInjector:
    """
    Couples Venturi injection into two channels simultaneously:

      psi       <- venturi.step(psi, phi_inject, z_dc)
      psi_hat   <- venturi.step(psi_hat, phi_inject, z_dc)   (MSR response)

    Both domains see the same 360-degree azimuthal phi_inject derived
    from the Engine3 complex state seed for the given text.
    """

    def __init__(self, venturi: Venturi):
        self.venturi = venturi

    def inject(
        self,
        text: str,
        psi: np.ndarray,
        psi_hat: np.ndarray,
        z_dc: np.ndarray,
        anchor: str = "dIse",
    ) -> tuple[np.ndarray, np.ndarray]:
        binary = ''.join(format(ord(c), '08b') for c in text)
        anc_binary = ''.join(format(ord(c), '08b') for c in anchor)
        x = len(binary) / max(len(anc_binary), 1)
        z_c = engine3_complex_state(x)
        phi_s = self.venturi._azimuthal_field(z_c, psi)
        psi_out = self.venturi.step(psi, phi_s, z_dc)
        psi_hat_out = self.venturi.step(psi_hat, phi_s, z_dc)
        return psi_out, psi_hat_out
