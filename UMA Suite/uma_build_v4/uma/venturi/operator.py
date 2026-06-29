# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
venturi.py -- 360-degree evolving Venturi for cross-domain injection.

Standalone. No dependencies except numpy and math.

The Venturi auto-regulates the throat radius r0 by the projected DC
energy E. When E < E* the throat expands (release more injected
amplitude); when E > E* the throat contracts (more suction). The Silver
Ratio constants are preserved as a deliberate text-encoding design
choice (see semantic/constants.py for the calibration retraction note).

Run:  python3 -m uma.venturi.operator
"""
from __future__ import annotations
import math
import numpy as np


# ---------------------------------------------------------------------
# Silver Ratio constants
# ---------------------------------------------------------------------

SQRT2          = math.sqrt(2)
SQRT_E         = math.sqrt(math.e)
DELTA_S        = 1.0 + SQRT2          # Silver Ratio
INV_DELTA_S_SQ = 1.0 / DELTA_S ** 2   # 3 - 2*sqrt(2) ~ 0.17157
C1_SILVER      = 1.0 - SQRT2          # ~ -0.41421


def silver_E_target(kT: float) -> float:
    return kT * INV_DELTA_S_SQ


def silver_dz_dt_floor(kT: float, lam: float, N: int, dt: float) -> float:
    return math.sqrt(2.0 * kT * INV_DELTA_S_SQ * lam * dt) / N


def silver_field_scale(kT: float) -> float:
    return math.sqrt(2.0 * silver_E_target(kT))


def engine3_complex_state(x: float) -> complex:
    """Engine3 seed: z_c = x * ((1 - sqrt 2) + i sqrt e). Encoding choice."""
    return complex(x * C1_SILVER, x * SQRT_E)


# ---------------------------------------------------------------------
# Venturi
# ---------------------------------------------------------------------

class Venturi:
    """
    360-degree evolving Venturi for cross-domain injection.

        V(r, r0) = (r0 / max(r, r_in))^beta * envelope(r)
        dr0/dt   = -lam_v * (E - E*)/E* * r0
        G        = 1 - (r_in/r0)^2

        d psi/dt|venturi = G * V(r, r0(t)) * phi_inject
    """

    def __init__(
        self,
        N: int = 32, kT: float = 0.005, lam: float = 0.4,
        r0: float = 0.15, r_in: float = 0.04, r_out: float = 0.42,
        beta: float = 1.0, lam_v: float = 0.1, coupling: float = 1.0, dt: float = 0.04,
    ):
        self.N = N
        self.kT = kT
        self.lam = lam
        self.r0 = r0
        self.r0_init = r0
        self.r_in = r_in
        self.r_out = r_out
        self.beta = beta
        self.lam_v = lam_v
        self.coupling = coupling
        self.dt = dt
        self.t = 0.0

        self.E_star      = silver_E_target(kT)
        self.dz_dt_floor = silver_dz_dt_floor(kT, lam, N, dt)
        self.field_scale = silver_field_scale(kT)

        self.history: list[dict] = []
        self._R = self._radial_grid(N)

    # -----------------------------------------------------------------

    def _radial_grid(self, N: int) -> np.ndarray:
        x = np.linspace(0, 1, N, endpoint=False)
        X, Y = np.meshgrid(x, x)
        dx = np.abs(X - 0.5); dx = np.minimum(dx, 1 - dx)
        dy = np.abs(Y - 0.5); dy = np.minimum(dy, 1 - dy)
        return np.sqrt(dx ** 2 + dy ** 2)

    def _V(self, r0: float) -> np.ndarray:
        r_eff = np.maximum(self._R, self.r_in)
        throat = (r0 / r_eff) ** self.beta
        envelope = np.clip((self.r_out - self._R) / (self.r_out - r0 + 1e-8), 0, 1)
        return throat * envelope

    def _G(self, r0: float) -> float:
        return max(0.0, 1.0 - (self.r_in / max(r0, self.r_in + 1e-8)) ** 2)

    def _evolve_r0(self, E: float) -> float:
        dr0 = -self.lam_v * (E - self.E_star) / (self.E_star + 1e-15) * self.r0
        self.r0 = float(np.clip(self.r0 + dr0 * self.dt, 0.03, 0.45))
        return float(dr0)

    # -----------------------------------------------------------------

    def step(self, psi: np.ndarray, phi_inject: np.ndarray, z_dc: np.ndarray) -> np.ndarray:
        """
        One Venturi step.

        psi        : current field (N x N complex)
        phi_inject : injection field (N x N complex)
        z_dc       : DC projected state (drives throat evolution)

        Returns psi_out (N x N complex)
        """
        z_dc = np.asarray(z_dc).ravel()
        E = float(np.real(z_dc @ z_dc) / 2.0)
        dr0 = self._evolve_r0(E)
        G = self._G(self.r0)
        V = self._V(self.r0)
        # broadcast V to psi grid if needed
        if V.shape != psi.shape:
            from scipy.ndimage import zoom
            V = zoom(V, (psi.shape[0] / V.shape[0], psi.shape[1] / V.shape[1]), order=1)
        self.t += self.dt
        psi_out = psi + self.dt * G * self.coupling * V * phi_inject
        self.history.append({
            "t": self.t, "r0": self.r0, "G": G,
            "E": E, "dr0_dt": dr0,
        })
        return psi_out

    def inject_text(
        self, text: str, psi: np.ndarray, z_dc: np.ndarray, anchor: str = "dIse",
    ) -> np.ndarray:
        """
        Inject a text string into the field via Venturi.

        text -> binary weight -> Engine3 complex state -> 360-degree field -> step.
        """
        binary = ''.join(format(ord(c), '08b') for c in text)
        anc_binary = ''.join(format(ord(c), '08b') for c in anchor)
        x = len(binary) / max(len(anc_binary), 1)
        z_c = engine3_complex_state(x)
        phi_s = self._azimuthal_field(z_c, psi)
        return self.step(psi, phi_s, z_dc)

    def _azimuthal_field(self, z_c: complex, psi: np.ndarray) -> np.ndarray:
        """360-degree injection: amplitude |z_c|, phase rotates around field center."""
        intensity = np.abs(psi) ** 2
        total = intensity.sum() + 1e-15
        coords = np.linspace(0, 1, psi.shape[0], endpoint=False)
        X, Y = np.meshgrid(coords, coords)
        cx = float((intensity * X).sum() / total)
        cy = float((intensity * Y).sum() / total)
        dx = X - cx; dx -= np.round(dx)
        dy = Y - cy; dy -= np.round(dy)
        theta = np.arctan2(dy, dx)
        return abs(z_c) * np.exp(1j * (np.angle(z_c) + theta))

    def reset(self) -> None:
        self.r0 = self.r0_init
        self.t = 0.0
        self.history.clear()

    def summary(self) -> str:
        if not self.history:
            return "No steps yet."
        h = self.history[-1]
        return (
            f"t={h['t']:.3f}  r0={h['r0']:.4f}  G={h['G']:.4f}  "
            f"E={h['E']:.4e}  E*={self.E_star:.4e}  dr0/dt={h['dr0_dt']:.4e}"
        )


# Alias the user uses interchangeably across the corpus
VenturiOperator = Venturi


# ---------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------

if __name__ == "__main__":
    print("=== 360-degree Venturi -- standalone demo ===\n")

    N, kT, lam, dt = 32, 0.005, 0.4, 0.04
    rng = np.random.default_rng(42)
    psi = 0.3 * (rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N)))

    def project(psi):
        m = psi.mean()
        return np.array([m.real, m.imag])

    venturi = Venturi(N=N, kT=kT, lam=lam, dt=dt)
    print("Silver constants:")
    print(f"  1/delta_S^2 = {INV_DELTA_S_SQ:.6f}  (= 3 - 2*sqrt(2))")
    print(f"  sqrt(e)     = {SQRT_E:.6f}  (exponential bridge)")
    print(f"  E_target    = {silver_E_target(kT):.6e}  (kT / delta_S^2)")
    print(f"  dz/dt floor = {silver_dz_dt_floor(kT, lam, N, dt):.6e}\n")
    print(f"{'step':>5}  {'r0':>7}  {'G':>7}  {'E_field':>12}  {'dr0/dt':>12}")
    print("-" * 55)
    for step in range(50):
        z_dc = project(psi)
        psi = venturi.inject_text("THRUPUT semantic field resolution", psi, z_dc)
        if step % 5 == 0:
            h = venturi.history[-1]
            print(f"{step:>5}  {h['r0']:>7.4f}  {h['G']:>7.4f}  "
                  f"{h['E']:>12.4e}  {h['dr0_dt']:>12.4e}")
    print()
    print("Final:", venturi.summary())
    print()
    print("Throat expands when E < E* (below Silver target -> release)")
    print("Throat contracts when E > E* (above Silver target -> more suction)")
