"""
calibrate.py -- derive closure thresholds from actual GENERIC trajectory
statistics.

Run once to calibrate SemanticFrictionConfig for a given UMA Config.

Usage:
    from calibrate import calibrate_closure
    thresholds = calibrate_closure(cfg, n_traj=50, n_steps=3000, burnin=1000)
    print(thresholds)

Returns a dict you paste directly into SemanticFrictionConfig.
"""
from __future__ import annotations
import math

import numpy as np

from uma import Config, UMAClient
from uma.core.state import FieldPosterior
from uma.dynamics.generic import hamiltonian


def calibrate_closure(
    cfg=None,
    n_traj: int = 50,
    n_steps: int = 3000,
    burnin: int = 1000,
    dt: float = 0.04,
    seed_start: int = 0,
    verbose: bool = True,
) -> dict:
    """
    Run n_traj independent GENERIC trajectories and derive:
        E_target    -- mean DC mode energy at equilibrium
        E_tol       -- std of DC mode energy (natural fluctuation amplitude)
        dz_dt_floor -- mean |dE/dt| at equilibrium (thermal noise rate)
        field_scale -- 2 * sqrt(2 * E_target) (natural |z| scale)
        H_target    -- mean H[psi] at equilibrium
        H_std       -- std of H[psi]
        dH_dt_floor -- mean |dH/dt| at equilibrium

    These replace any hand-chosen or guessed constants.
    """
    if cfg is None:
        cfg = Config()
    N = cfg.grid.N
    kT = cfg.generic.kT

    all_E: list[float] = []
    all_dz_dt: list[float] = []
    all_H: list[float] = []
    all_dH_dt: list[float] = []

    for seed in range(seed_start, seed_start + n_traj):
        rng = np.random.default_rng(seed)
        client = UMAClient(cfg)
        psi0 = 0.3 * (
            rng.standard_normal((N, N)) + 1j * rng.standard_normal((N, N))
        )
        client.initialize(psi0, sigma0=0.05, dt=dt)

        E_prev = None
        H_prev = None
        for step in range(n_steps):
            client.evolve(dt)
            z = client.filter.posterior.mean
            psi = client.psi

            if step >= burnin:
                E = float(np.real(z @ z) / 2.0)
                H = float(hamiltonian(psi, lam=cfg.generic.reaction))
                if E_prev is not None:
                    all_dz_dt.append(abs(E - E_prev) / dt)
                if H_prev is not None:
                    all_dH_dt.append(abs(H - H_prev) / dt)
                all_E.append(E)
                all_H.append(H)
                E_prev = E
                H_prev = H

        if verbose and (seed - seed_start) % 10 == 9:
            print(f"    ... {seed - seed_start + 1}/{n_traj} trajectories done")

    arr_E = np.array(all_E)
    arr_dz_dt = np.array(all_dz_dt)
    arr_H = np.array(all_H)
    arr_dH_dt = np.array(all_dH_dt)

    E_target = float(arr_E.mean())
    E_tol = float(arr_E.std())
    dz_dt_floor = float(arr_dz_dt.mean())
    dz_dt_p25 = float(np.percentile(arr_dz_dt, 25))
    field_scale = float(2.0 * math.sqrt(2.0 * abs(E_target) + 1e-15))
    H_target = float(arr_H.mean())
    H_std = float(arr_H.std())
    dH_dt_floor = float(arr_dH_dt.mean())
    dH_dt_p25 = float(np.percentile(arr_dH_dt, 25))

    thresholds = {
        # Paste these into SemanticFrictionConfig
        "E_target": E_target,
        "E_tol": E_tol,
        "dz_dt_floor": dz_dt_floor,
        "dz_dt_floor_tight": dz_dt_p25,
        "field_scale": field_scale,
        # H-tracking thresholds (preferred -- track real Hamiltonian)
        "H_target": H_target,
        "H_std": H_std,
        "dH_dt_floor": dH_dt_floor,
        "dH_dt_p25": dH_dt_p25,
        # Diagnostics
        "E_target_over_kT": E_target / kT,
        "E_tol_over_kT": E_tol / kT,
        "n_samples_E": len(arr_E),
        "n_samples_dz_dt": len(arr_dz_dt),
        "n_traj": n_traj,
        "kT": kT,
        "N": N,
        "dt": dt,
    }

    if verbose:
        print()
        print("=== Calibrated GENERIC closure thresholds ===")
        print(f"    E_target    = {E_target:.4e}   ({E_target/kT:.3f} kT)")
        print(f"    E_tol       = {E_tol:.4e}   ({E_tol/kT:.3f} kT)")
        print(f"    dz_floor    = {dz_dt_floor:.4e}   (mean thermal rate, E proxy)")
        print(f"    dz_floor25  = {dz_dt_p25:.4e}   (lower quartile)")
        print(f"    field_scale = {field_scale:.4e}")
        print(f"    H_target    = {H_target:.4e}")
        print(f"    H_std       = {H_std:.4e}")
        print(f"    dH_dt_floor = {dH_dt_floor:.4e}   (mean thermal rate, H)")
        print(f"    dH_dt_p25   = {dH_dt_p25:.4e}")
        print()
        print("Paste into SemanticFrictionConfig:")
        print(f"    convergence_dz_dt = {dH_dt_floor:.4e}")
        print(f"    closure_state_tol = {field_scale:.4e}")

    return thresholds


if __name__ == "__main__":
    print("Running calibration on default Config (50 trajectories x 3000 steps)...")
    print("This will take some time. Use n_traj/n_steps kwargs to shorten.")
    thresholds = calibrate_closure(Config(), n_traj=50, n_steps=3000, burnin=1000)
    print()
    print("Final thresholds:", thresholds)
