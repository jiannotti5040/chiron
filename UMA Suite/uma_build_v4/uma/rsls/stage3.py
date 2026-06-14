"""
uma.rsls.stage3 -- Perturbative Transport, Spectral Stability,
                   and Observability.

Implements the analytical machinery of Stage 3:

    3A. Whitham subcharacteristic condition on the linearised operator
    3B. Pseudospectral envelope inequality
    3C. Complex impedance Z(omega) and reflection coefficient R(omega)
    3D. Wigner time delay and the spectral comb of echoes
    3E/F. Detectability theorem (LIGO/LISA admissibility bound)

These are algebraic / inequality checks, not PDE solvers -- the heavy
lifting is in phase_a.py and frame_dragging.py. Stage 3 is the
*spectral* side of the analysis: given a saturated background, do the
linear perturbations behave?

Reference: docs/RSLS_specification.md, section VIII.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from uma.rsls.memory import MemoryConfig


# ---------------------------------------------------------------------------
# 3A. Whitham subcharacteristic condition
# ---------------------------------------------------------------------------

def whitham_subcharacteristic(cfg: MemoryConfig, c_geom: float = 1.0) -> bool:
    """
    The Whitham subcharacteristic condition for hyperbolic relaxation:
    the entropy-flux causal speed must not exceed the geometric/light
    cone:

        c_diff^2 = mu / (tau_J tau_M)  <=  c_geom^2

    Default c_geom = 1 (geometric units). Returns True if the bound
    holds (strict hyperbolicity preserved).
    """
    return cfg.c_diff <= c_geom


def whitham_margin(cfg: MemoryConfig, c_geom: float = 1.0) -> float:
    """Returns c_geom - c_diff. Positive => subcharacteristic; the
    larger, the safer."""
    return c_geom - cfg.c_diff


# ---------------------------------------------------------------------------
# 3A. Dispersion relation poles for the linearised system
# ---------------------------------------------------------------------------

def dispersion_polynomial(k: float, cfg: MemoryConfig) -> np.ndarray:
    """
    Returns the coefficients of the dispersion polynomial L(omega, k)
    for the Cattaneo-relaxation sector, as a numpy polynomial.

    The Cattaneo telegrapher's equation in 1-D:

        tau_J d_tt M + d_t M = mu d_xx M

    For perturbations M ~ exp(i(kx - omega t)) this gives

        -tau_J omega^2 - i omega + mu k^2 = 0
        tau_J omega^2 + i omega - mu k^2 = 0      (poly in omega)

    Coefficients are returned in numpy's leading-coefficient-first order.
    """
    return np.array([cfg.tau_J, 1j, -cfg.mu * k ** 2], dtype=complex)


def find_poles(k: float, cfg: MemoryConfig) -> np.ndarray:
    """Roots of L(omega, k) = 0 for a given wavenumber k."""
    coeffs = dispersion_polynomial(k, cfg)
    roots = np.roots(coeffs)
    return roots


def all_poles_stable(k_range: np.ndarray, cfg: MemoryConfig,
                     tol: float = 1e-12) -> bool:
    """
    Stage-3A stability requirement: all poles have Im(omega) <= 0 for
    all k in the range. Returns True if stable, False if any pole
    has Im(omega) > tol.
    """
    for k in k_range:
        omegas = find_poles(float(k), cfg)
        if np.any(omegas.imag > tol):
            return False
    return True


# ---------------------------------------------------------------------------
# 3B. Pseudospectral envelope (isotropisation vs shear competition)
# ---------------------------------------------------------------------------

@dataclass
class IsotropisationParams:
    """
    Parameters for the Stage-3B pseudospectral envelope.

    sigma_D    -- geometric shear-production rate (driven by 1/r focusing)
    Gamma_iso  -- relaxation isotropisation rate (driven by V''(M))
    """
    sigma_D: float
    Gamma_iso: float

    @property
    def chi(self) -> float:
        """The Stage-3C impedance bifurcation parameter."""
        return self.sigma_D / max(self.Gamma_iso, 1e-15)


def pseudospectral_envelope_satisfied(p: IsotropisationParams) -> bool:
    """
    Stage-3B verdict: the wall is stable iff isotropisation beats shear
    production -- equivalently, chi = sigma_D / Gamma_iso < 1.
    """
    return p.chi < 1.0


# ---------------------------------------------------------------------------
# 3C. Scattering matrix and complex impedance
# ---------------------------------------------------------------------------

def reflection_coefficient(omega: float, p: IsotropisationParams,
                           tau_J: float) -> complex:
    """
    Frequency-dependent reflection coefficient at the entropy wall.

    The impedance Z(omega) is built from the bifurcation parameter
    chi and the relaxation lag tau_J. The minimal model:

        Z(omega) = 1 + chi / (1 - i omega tau_J)

    gives R(omega) = (Z - 1) / (Z + 1).

    Limits:
        chi -> 0:    Z -> 1,         R -> 0  (perfect absorber)
        chi ~ 1:     |R| > 0 with peak at omega tau_J ~ 1 (resonance)
    """
    Z = 1.0 + p.chi / (1.0 - 1j * omega * tau_J)
    R = (Z - 1.0) / (Z + 1.0)
    return R


def reflection_spectrum(omegas: np.ndarray, p: IsotropisationParams,
                        tau_J: float) -> np.ndarray:
    """Vectorised reflection coefficient over a frequency grid."""
    Z = 1.0 + p.chi / (1.0 - 1j * omegas * tau_J)
    return (Z - 1.0) / (Z + 1.0)


# ---------------------------------------------------------------------------
# 3D. Wigner time delay and echo spacing
# ---------------------------------------------------------------------------

def wigner_delay(omegas: np.ndarray, p: IsotropisationParams,
                 tau_J: float) -> np.ndarray:
    """
    Wigner time delay tau_W(omega) = d phi / d omega, where phi is the
    phase of R(omega). Returns delay (same length as omegas).
    """
    R = reflection_spectrum(omegas, p, tau_J)
    phi = np.angle(R)
    # Unwrap to avoid 2 pi jumps
    phi_unwrapped = np.unwrap(phi)
    tau_W = np.gradient(phi_unwrapped, omegas)
    return tau_W


def echo_spacing(ell_star: float, r_photon: float, tau_M: float,
                 c_light: float = 1.0) -> float:
    """
    Stage-3D macroscopic echo spacing in the cavity between the photon
    sphere (r_photon) and the entropy wall (radius ell_star inside the
    Stage-2 saturation core):

        Delta_t_echo = 2 (r_photon - ell_star) / c_light  +  tau_M

    The geometric round-trip plus the relaxation lag. Observable as a
    spectral comb in the ringdown power spectrum.
    """
    geometric = 2.0 * (r_photon - ell_star) / c_light
    return geometric + tau_M


# ---------------------------------------------------------------------------
# 3E/F. Detectability theorem
# ---------------------------------------------------------------------------

def detectability_bound(M_adm: float, ell_star: float,
                        Gamma_kerr: float, N_floor: float = 1e-21) -> bool:
    """
    Stage-3E admissibility constraint. The reflected echo amplitude
    is attenuated by exp[-2 M_adm Gamma_kerr ln(M_adm / ell_star)].
    For the signal to exceed the detector noise floor N_floor:

        exp[-2 M_adm Gamma_kerr ln(M_adm / ell_star)]  >  N_floor

    Setting ell_star to the Planck length makes the argument of the
    log ~80, attenuating by ~ exp(-160 M Gamma_kerr) -- hundreds of
    orders of magnitude below any detector floor.

    The Macroscopic Mandate: for echoes to remain observationally
    distinct from classical GR ringdown, ell_star must satisfy roughly

        ell_star / M_adm  ≳  10^{-11}

    (the canonical estimate for LIGO/LISA sensitivity).
    """
    if ell_star <= 0 or M_adm <= 0:
        return False
    ratio = M_adm / ell_star
    if ratio <= 1:
        # ell_star >= M_adm: trivially detectable
        return True
    log_ratio = math.log(ratio)
    attenuation = math.exp(-2.0 * M_adm * Gamma_kerr * log_ratio)
    return attenuation > N_floor


def macroscopic_ell_star_lower_bound(M_adm: float, Gamma_kerr: float,
                                     N_floor: float = 1e-21) -> float:
    """
    Solves for the minimum ell_star that satisfies the detectability
    bound. Returns ell_star such that the attenuation just equals
    N_floor.

        attenuation = exp[-2 M_adm Gamma_kerr ln(M_adm / ell_star)] = N_floor
        2 M_adm Gamma_kerr ln(M_adm / ell_star) = -ln(N_floor)
        ln(M_adm / ell_star) = -ln(N_floor) / (2 M_adm Gamma_kerr)
        ell_star = M_adm * exp[ln(N_floor) / (2 M_adm Gamma_kerr)]
    """
    return M_adm * math.exp(math.log(N_floor) / (2.0 * M_adm * Gamma_kerr))


# ---------------------------------------------------------------------------
# Demonstration
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = MemoryConfig()
    print("=== Stage 3: Perturbative Analysis ===\n")
    print("3A. Whitham subcharacteristic check")
    print(f"    c_diff = {cfg.c_diff:.6f}")
    print(f"    c_geom = 1.0")
    print(f"    margin = {whitham_margin(cfg):.6f}")
    print(f"    VERDICT: {'PASS' if whitham_subcharacteristic(cfg) else 'FAIL'}")
    print()

    print("3A. Pole locations for k = 1..10")
    ks = np.array([1.0, 5.0, 10.0])
    for k in ks:
        roots = find_poles(float(k), cfg)
        max_im = max(r.imag for r in roots)
        print(f"    k = {k:5.1f}  roots = {roots}")
        print(f"              max(Im omega) = {max_im:+.6e}  "
              f"{'stable' if max_im <= 1e-12 else 'UNSTABLE'}")
    print()

    print("3B. Pseudospectral envelope (chi sweep)")
    for chi in [0.1, 0.5, 1.0, 2.0]:
        p = IsotropisationParams(sigma_D=chi, Gamma_iso=1.0)
        stable = pseudospectral_envelope_satisfied(p)
        print(f"    chi = {chi:.2f}  -> {'stable' if stable else 'UNSTABLE'}")
    print()

    print("3C/3D. Reflection coefficient and Wigner delay")
    p = IsotropisationParams(sigma_D=0.8, Gamma_iso=1.0)
    omegas = np.linspace(0.1, 5.0, 200)
    R = reflection_spectrum(omegas, p, tau_J=cfg.tau_J)
    tau_W = wigner_delay(omegas, p, tau_J=cfg.tau_J)
    print(f"    chi = {p.chi:.4f}")
    print(f"    |R|_max  = {abs(R).max():.4f} at omega = "
          f"{omegas[abs(R).argmax()]:.3f}")
    print(f"    tau_W_max = {tau_W.max():.4f}")
    print()

    print("3E. Echo spacing")
    dt = echo_spacing(ell_star=1e-11, r_photon=3.0, tau_M=cfg.tau_M)
    print(f"    Delta_t_echo = {dt:.6e} (geom = {2*3.0:.2f}, lag = {cfg.tau_M})")
    print()

    print("3F. Detectability")
    M_adm = 30.0   # 30 solar-mass equivalent in geometric units
    Gamma = 0.05   # Kerr-decay coefficient
    for ell in [1e-30, 1e-11, 1e-5, 1.0]:
        ok = detectability_bound(M_adm, ell, Gamma)
        print(f"    ell_* / M = {ell/M_adm:.2e}  "
              f"=> {'detectable' if ok else 'BELOW noise floor'}")
    bound = macroscopic_ell_star_lower_bound(M_adm, Gamma)
    print(f"    bound: ell_* / M >= {bound/M_adm:.4e}")
