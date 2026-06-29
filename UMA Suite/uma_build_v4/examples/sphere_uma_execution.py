# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
sphere_uma_execution.py -- runs the sphere projection system inside UMA.

The sphere defines the geometry. The UMA dynamics observe through
SphereProjectionField (acoustic standing wave) and SpherePendulum (great-
circle sweep). r0 of SphereVenturi is locked to R*j_nl/pi -- nothing is
free.
"""
from __future__ import annotations
import os
import sys
import math
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from uma import Config, UMAClient
from uma.sphere.geometry import AcousticSphereGeometry
from uma.sphere.field import SphereProjectionField, SpherePendulum, SphereVenturi


def main() -> None:
    print("=" * 60)
    print("Sphere geometry derived inside-out from Bessel zeros")
    print("=" * 60)
    geo = AcousticSphereGeometry(L=1.0, n=0, l=0, mode_index=1).solve()
    geo.summary()

    cfg = Config()
    rng = np.random.default_rng(0)
    client = UMAClient(cfg)
    N = cfg.grid.N
    psi0 = 0.3 * (rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N)))
    client.initialize(psi0)

    sphere_field = SphereProjectionField(geo, n_harmonics=2)
    pendulum = SpherePendulum(geo)
    sphere_v = SphereVenturi(geo, N=N)

    print()
    print("Sphere -> UMA execution (40 steps):")
    for step in range(40):
        # GENERIC step
        client.evolve(cfg.generic.dt)
        # MSR response
        psi_hat = -client.dynamics.dH_dpsi_conj(client.psi)
        # Sphere venturi inject MSR back into psi
        client.psi = sphere_v.apply(client.psi, psi_hat, cfg.generic.dt)
        # Pendulum sample
        if step % 8 == 0:
            sample = pendulum.sample_field(sphere_field, step * cfg.generic.dt)
            H = client.dynamics.hamiltonian(client.psi)
            print(
                f"  step={step:3d}  t={step*cfg.generic.dt:6.3f}  "
                f"H={H:+.4e}  P_real={sample['P_real']:+.4f}  "
                f"phi={math.degrees(sample['phi']):6.1f}deg"
            )


if __name__ == "__main__":
    main()
