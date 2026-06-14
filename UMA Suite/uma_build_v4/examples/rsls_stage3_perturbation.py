"""
examples/rsls_stage3_perturbation.py -- Stage 3 perturbative analysis.

Demonstrates the analytic results of Stage 3:

  3A. Whitham subcharacteristic condition on the linearised operator
  3A. Dispersion-relation poles all in lower half plane
  3B. Pseudospectral envelope inequality (chi < 1 stable)
  3C. Complex impedance Z(omega) and reflection coefficient
  3D. Wigner time delay -- spectral comb structure
  3E. Detectability theorem and the macroscopic ell_* mandate

These are algebraic checks on the linearised operator, not a PDE
solver. They establish the *spectral* admissibility of the Stage-2
saturated background.
"""
from __future__ import annotations
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
ROOT = THIS.parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np

from uma.rsls import MemoryConfig
from uma.rsls.stage3 import (
    whitham_subcharacteristic, whitham_margin,
    find_poles, all_poles_stable,
    IsotropisationParams, pseudospectral_envelope_satisfied,
    reflection_coefficient, reflection_spectrum,
    wigner_delay, echo_spacing,
    detectability_bound, macroscopic_ell_star_lower_bound,
)


def main():
    print("=" * 70)
    print("Stage 3: Perturbative Transport, Spectral Stability, Observability")
    print("=" * 70)
    print()
    cfg = MemoryConfig()
    print(f"Memory configuration: mu = {cfg.mu}, tau_J = {cfg.tau_J}, "
          f"tau_M = {cfg.tau_M}")
    print(f"Intrinsic entropy-transport speed c_diff = sqrt(mu/tau_J/tau_M) "
          f"= {cfg.c_diff:.6f}")
    print()

    # -------------------------------------------------------------------
    # 3A. Whitham subcharacteristic condition
    # -------------------------------------------------------------------
    print(">>> 3A. Whitham subcharacteristic condition")
    pass_whitham = whitham_subcharacteristic(cfg)
    print(f"    c_diff <= c_geom (= 1): {pass_whitham}")
    print(f"    margin                 : {whitham_margin(cfg):.6f}")
    print(f"    verdict                : {'PASS' if pass_whitham else 'FAIL'}")
    print()

    # -------------------------------------------------------------------
    # 3A. Dispersion-relation poles
    # -------------------------------------------------------------------
    print(">>> 3A. Dispersion poles (must lie in lower half plane Im omega <= 0)")
    ks = np.array([0.1, 1.0, 10.0, 100.0])
    for k in ks:
        roots = find_poles(float(k), cfg)
        max_im = max(r.imag for r in roots)
        status = "STABLE" if max_im <= 1e-12 else "UNSTABLE"
        print(f"    k = {k:6.2f}: max(Im omega) = {max_im:+.3e}  [{status}]")
    overall = all_poles_stable(np.linspace(0.1, 100, 30), cfg)
    print(f"    overall stability over k in [0.1, 100]: {overall}")
    print()

    # -------------------------------------------------------------------
    # 3B. Pseudospectral envelope inequality
    # -------------------------------------------------------------------
    print(">>> 3B. Pseudospectral envelope (chi = sigma_D / Gamma_iso)")
    for chi in [0.1, 0.5, 0.9, 1.0, 1.5, 3.0]:
        p = IsotropisationParams(sigma_D=chi, Gamma_iso=1.0)
        stable = pseudospectral_envelope_satisfied(p)
        print(f"    chi = {chi:4.2f}: {'stable' if stable else 'UNSTABLE'}")
    print()

    # -------------------------------------------------------------------
    # 3C/3D. Reflection coefficient and Wigner time delay
    # -------------------------------------------------------------------
    print(">>> 3C/3D. Reflection coefficient R(omega) and Wigner delay")
    p = IsotropisationParams(sigma_D=0.8, Gamma_iso=1.0)
    omegas = np.linspace(0.1, 5.0, 200)
    R = reflection_spectrum(omegas, p, tau_J=cfg.tau_J)
    tau_W = wigner_delay(omegas, p, tau_J=cfg.tau_J)
    R_peak_idx = int(np.argmax(np.abs(R)))
    print(f"    chi             = {p.chi:.4f}")
    print(f"    |R|_max         = {abs(R).max():.4f} at omega = "
          f"{omegas[R_peak_idx]:.3f}")
    print(f"    tau_W_max       = {tau_W.max():.4f}")
    print(f"    tau_W at omega=1 = {tau_W[np.argmin(abs(omegas-1.0))]:.4f}")
    print()

    # -------------------------------------------------------------------
    # 3D. Echo spacing
    # -------------------------------------------------------------------
    print(">>> 3D. Echo spacing in cavity between photon sphere and entropy wall")
    M = 30.0   # 30 solar-mass equivalent in geometric units
    r_photon = 1.5 * M   # Schwarzschild photon sphere ~ 3M; but in non-stand units...
    for ell in [1e-11 * M, 1e-5 * M, 0.01 * M, 0.1 * M]:
        dt = echo_spacing(ell_star=ell, r_photon=r_photon, tau_M=cfg.tau_M)
        print(f"    ell_*/M = {ell/M:.2e} -> Delta_t_echo = {dt:.4f}")
    print()

    # -------------------------------------------------------------------
    # 3E. Detectability theorem
    # -------------------------------------------------------------------
    print(">>> 3E. Detectability theorem (LIGO/LISA admissibility)")
    Gamma = 0.05
    for ell_ratio in [1e-35, 1e-30, 1e-20, 1e-11, 1e-5, 1.0]:
        ell = ell_ratio * M
        ok = detectability_bound(M_adm=M, ell_star=ell, Gamma_kerr=Gamma)
        print(f"    ell_*/M = {ell_ratio:.0e}: "
              f"{'detectable' if ok else 'BELOW noise floor'}")
    ell_min = macroscopic_ell_star_lower_bound(M, Gamma)
    print(f"    lower-bound estimate: ell_*/M >= {ell_min/M:.4e}")
    print()
    print("The 'Macroscopic Mandate': for RSLS to be observationally distinct")
    print("from classical Kerr ringdown, ell_* must be macroscopic, not Planck-")
    print("scale -- the logarithmic delay penalty exp[-2 M Gamma ln(M/ell_*)]")
    print("attenuates Planck-scale signals by hundreds of orders of magnitude.")


if __name__ == "__main__":
    main()
