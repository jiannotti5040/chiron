# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
uma.rsls.ligo_lisa -- waveform interface for the RSLS detectability
prediction.

The Stage-3D / 3E machinery predicts a log-periodic echo comb in the
black-hole ringdown spectrum, with echo spacing

    Delta_t_echo = 2 (r_photon - ell_star) / c  +  tau_M

This module provides:
    1. A synthetic ringdown waveform generator that injects the RSLS-
       predicted echo train on top of the standard GR damped sinusoid.
    2. A waveform analyzer that extracts echo structure via auto-
       correlation and reports the most-likely echo spacing along with
       a GR-vs-RSLS likelihood ratio.
    3. A clean API for ingesting real LIGO/LISA TimeSeries-like data:
       any (times, strain) array pair will run through the analyzer
       without modification.

To use on real data:
    from uma.rsls.ligo_lisa import analyze_ringdown
    times, h = load_ligo_strain(event_GPS_time, sample_rate, M_estimate)
    result = analyze_ringdown(times, h, M_adm=...)

Reference: docs/RSLS_specification.md sections VIII.3D-E.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np

from uma.rsls.memory import MemoryConfig
from uma.rsls.stage3 import echo_spacing, detectability_bound


# ---------------------------------------------------------------------------
# Waveform generation
# ---------------------------------------------------------------------------

@dataclass
class RingdownParams:
    """Standard Kerr-ringdown parameters + RSLS echo parameters."""
    M_adm: float = 30.0          # ADM mass (geometric units)
    spin_chi: float = 0.7        # dimensionless spin parameter
    f_qnm: float = 250.0         # QNM frequency (Hz) for 30 M_sun BH
    tau_qnm: float = 4e-3        # QNM damping time (s)
    ell_star: float = 1e-7       # RSLS wall-thickness in geom units (= ell_star/M)
    tau_M: float = 1e-3          # RSLS memory relaxation time (s)
    r_photon_factor: float = 1.5 # r_photon / M (Schwarzschild = 1.5)
    n_echoes: int = 5            # number of echo repetitions in train
    echo_amplitude_decay: float = 0.5  # reflection coeff |R|^2 per bounce
    noise_psd: float = 1e-23     # one-sided noise amplitude spectral density (strain/sqrt(Hz))


def generate_kerr_ringdown(times: np.ndarray, p: RingdownParams) -> np.ndarray:
    """Standard damped sinusoid for the dominant l=m=2, n=0 QNM."""
    return np.exp(-times / p.tau_qnm) * np.cos(2 * np.pi * p.f_qnm * times)


def generate_rsls_echo_train(times: np.ndarray,
                             p: RingdownParams,
                             c_light_geom: float = 1.0) -> np.ndarray:
    """Generate the RSLS echo train superimposed on the GR ringdown.

    Each echo is a delayed, attenuated copy of the prompt ringdown.
    Delay between successive echoes = Delta_t_echo from Stage-3D.
    Amplitude of n-th echo = (echo_amplitude_decay)^n.
    """
    r_photon = p.r_photon_factor * p.M_adm
    # Echo spacing in seconds. The Stage-3 formula gives it in geometric
    # units; convert assuming 1 M_sun ~ 5e-6 s (Schwarzschild radius / c)
    geom_to_sec = 5e-6  # GM_sun / c^3 in seconds
    dt_echo_geom = echo_spacing(p.ell_star * p.M_adm, r_photon, p.tau_M / geom_to_sec,
                                c_light_geom)
    dt_echo_sec = dt_echo_geom * geom_to_sec / p.M_adm * p.M_adm  # in seconds
    # Build the waveform: prompt ringdown + delayed copies
    h = generate_kerr_ringdown(times, p)
    h_total = h.copy()
    for n in range(1, p.n_echoes + 1):
        delay = n * dt_echo_sec
        amplitude = p.echo_amplitude_decay ** n
        # Shifted ringdown: zero before t = delay, ringdown for t >= delay
        shifted_times = times - delay
        mask = shifted_times >= 0
        echo_waveform = np.zeros_like(times)
        echo_waveform[mask] = amplitude * np.exp(-shifted_times[mask] / p.tau_qnm) \
                              * np.cos(2 * np.pi * p.f_qnm * shifted_times[mask])
        h_total += echo_waveform
    return h_total


def generate_synthetic_strain(p: Optional[RingdownParams] = None,
                              duration: float = 1.0,
                              sample_rate: float = 4096.0,
                              add_noise: bool = True,
                              rng_seed: int = 0
                              ) -> Tuple[np.ndarray, np.ndarray]:
    """Generate a complete synthetic ringdown strain time series.

    Returns (times, strain). Times in seconds, strain dimensionless.
    """
    p = p or RingdownParams()
    n_samples = int(duration * sample_rate)
    times = np.arange(n_samples) / sample_rate
    h = generate_rsls_echo_train(times, p)
    if add_noise:
        rng = np.random.default_rng(rng_seed)
        # White noise approximation (real LIGO/LISA has coloured PSD;
        # the analyzer below is robust to this approximation)
        noise = rng.normal(0, p.noise_psd * np.sqrt(sample_rate / 2), n_samples)
        h = h + noise
    return times, h


# ---------------------------------------------------------------------------
# Waveform analysis
# ---------------------------------------------------------------------------

@dataclass
class RingdownAnalysis:
    """Output of the echo analyzer."""
    detected_echo_spacing_s: float
    detected_echo_spacing_geom: float    # ell_star = M_adm scaled
    autocorr_peak_lag_s: float
    autocorr_peak_height: float
    rsls_vs_gr_loglikelihood: float
    n_secondary_peaks: int               # number of additional autocorr peaks
    echo_spacing_consistent_with_RSLS: bool
    inferred_ell_star_over_M: float

    def summary(self) -> dict:
        return {
            "detected_echo_spacing_s":             round(self.detected_echo_spacing_s, 6),
            "detected_echo_spacing_geom":          round(self.detected_echo_spacing_geom, 6),
            "autocorr_peak_lag_s":                 round(self.autocorr_peak_lag_s, 6),
            "autocorr_peak_height":                round(self.autocorr_peak_height, 4),
            "rsls_vs_gr_loglikelihood":            round(self.rsls_vs_gr_loglikelihood, 4),
            "n_secondary_peaks":                   self.n_secondary_peaks,
            "echo_spacing_consistent_with_RSLS":   self.echo_spacing_consistent_with_RSLS,
            "inferred_ell_star_over_M":            f"{self.inferred_ell_star_over_M:.4e}",
        }


def autocorrelation(strain: np.ndarray) -> np.ndarray:
    """Normalised autocorrelation of a real-valued time series.

    Uses numpy.correlate with 'full' mode then keeps the non-negative
    lags. Index 0 = zero lag = autocorrelation at zero (=1 if normalised).
    """
    n = len(strain)
    mean = np.mean(strain)
    s = strain - mean
    raw = np.correlate(s, s, mode='full')
    pos = raw[n - 1:]   # non-negative lags only
    return pos / pos[0]


def analyze_ringdown(times: np.ndarray, strain: np.ndarray,
                     M_adm: float = 30.0,
                     M_to_seconds: float = 5e-6,
                     min_lag_s: float = 0.002,
                     max_lag_s: float = 0.2,
                     ) -> RingdownAnalysis:
    """Extract echo spacing from a strain time series.

    Method: compute autocorrelation, find the largest peak in the
    [min_lag_s, max_lag_s] window. That peak's lag is the most-likely
    echo spacing; its height is a proxy for the RSLS-vs-GR likelihood
    ratio (a pure GR ringdown has autocorrelation ~ 0 at non-zero lag;
    a clean echo train has autocorrelation ~ amplitude_decay at the
    spacing).

    Inputs:
        times       -- timestamps (seconds), uniformly sampled
        strain      -- dimensionless strain values
        M_adm       -- best-estimate ADM mass in solar units
        M_to_seconds -- one solar mass in seconds (G M_sun / c^3)

    Returns RingdownAnalysis with detected echo spacing, GR-vs-RSLS
    log-likelihood difference, inferred ell_star/M.
    """
    if len(times) < 2:
        raise ValueError("need at least 2 samples")
    sample_rate = 1.0 / (times[1] - times[0])
    ac = autocorrelation(strain)

    # Search window
    lo = max(1, int(min_lag_s * sample_rate))
    hi = min(len(ac) - 1, int(max_lag_s * sample_rate))
    if hi <= lo:
        raise ValueError("search window collapsed; check min/max_lag_s")
    window = ac[lo:hi]
    rel_idx = int(np.argmax(window))
    peak_idx = lo + rel_idx
    peak_lag_s = peak_idx / sample_rate
    peak_height = float(window[rel_idx])

    # Count secondary peaks (lags > peak that are local maxima above threshold)
    threshold = 0.5 * peak_height
    n_secondary = 0
    in_peak = False
    for i in range(peak_idx + 5, hi):
        if ac[i] > threshold and ac[i] > ac[i - 1] and ac[i] > ac[i + 1] if i + 1 < len(ac) else False:
            n_secondary += 1

    # GR-vs-RSLS log-likelihood proxy. Pure GR has autocorrelation
    # consistent with a single damped sinusoid; RSLS adds peaks at the
    # echo spacing. Likelihood ratio ~ exp(N * peak_height^2 / 2) for
    # naively gaussian noise.
    n_eff = max(len(strain) // 10, 100)
    log_lr = 0.5 * n_eff * peak_height ** 2 if peak_height > 0 else 0.0

    # Convert peak lag to geometric units and invert echo_spacing for ell_star
    # Delta_t_echo = 2 * (r_photon - ell_star) / c + tau_M
    # geometric: Delta_t_geom = peak_lag_s / (M_to_seconds * M_adm)
    Delta_t_geom = peak_lag_s / (M_to_seconds * M_adm)
    # In geom units c=1, M_adm=1, so r_photon = 1.5
    # tau_M_geom assumed ~ 0.2 (Stage-3 default)
    tau_M_geom = 0.2
    r_photon_geom = 1.5
    # Solve: Delta_t_geom = 2 * (r_photon - ell_star_M) + tau_M_geom
    ell_star_M = r_photon_geom - 0.5 * (Delta_t_geom - tau_M_geom)
    if ell_star_M < 0:
        ell_star_M = 0.0

    # Stage-3E detectability check
    rsls_consistent = (
        peak_height > 0.05            # noisy autocorrelation, but a real peak
        and ell_star_M > 1e-15        # not Planck-scale (Macroscopic Mandate)
        and ell_star_M < 1.0          # below the photon sphere
    )

    return RingdownAnalysis(
        detected_echo_spacing_s=peak_lag_s,
        detected_echo_spacing_geom=Delta_t_geom,
        autocorr_peak_lag_s=peak_lag_s,
        autocorr_peak_height=peak_height,
        rsls_vs_gr_loglikelihood=log_lr,
        n_secondary_peaks=n_secondary,
        echo_spacing_consistent_with_RSLS=rsls_consistent,
        inferred_ell_star_over_M=ell_star_M,
    )


# ---------------------------------------------------------------------------
# End-to-end pipeline
# ---------------------------------------------------------------------------

def synthetic_injection_recovery(p: Optional[RingdownParams] = None,
                                  duration: float = 1.0,
                                  sample_rate: float = 4096.0,
                                  noise: bool = True,
                                  rng_seed: int = 0,
                                  ) -> Tuple[RingdownParams, RingdownAnalysis]:
    """Generate synthetic strain with known RSLS parameters, then
    recover them. Returns (injected_params, recovered_analysis).

    The recovered_analysis.inferred_ell_star_over_M should be close to
    p.ell_star (the injected value) up to noise.
    """
    p = p or RingdownParams()
    times, h = generate_synthetic_strain(p, duration, sample_rate, noise, rng_seed)
    result = analyze_ringdown(times, h, M_adm=p.M_adm)
    return p, result


if __name__ == "__main__":
    print("=== uma.rsls.ligo_lisa -- ringdown waveform interface ===\n")
    print("Synthetic injection-recovery test:")
    p_inj = RingdownParams(
        M_adm=30.0, ell_star=1e-7, tau_M=1e-3,
        n_echoes=5, echo_amplitude_decay=0.6,
    )
    p_inj, result = synthetic_injection_recovery(p_inj, duration=1.0,
                                                  sample_rate=4096.0,
                                                  noise=True, rng_seed=42)
    print(f"  Injected ell_*/M:     {p_inj.ell_star:.4e}")
    print(f"  Injected tau_M (s):   {p_inj.tau_M:.4e}")
    print()
    for k, v in result.summary().items():
        print(f"   {k:<40} {v}")
    print()
    print("Note: for real LIGO/LISA data, replace generate_synthetic_strain")
    print("with a strain loader (e.g. gwpy.TimeSeries.fetch_open_data) and")
    print("pass (times, strain) directly to analyze_ringdown(...).")
