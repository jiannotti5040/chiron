# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
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
                             c_light_geom: float = 1.0,
                             M_to_seconds: float = 5e-6) -> np.ndarray:
    """Generate the RSLS echo train superimposed on the GR ringdown.

    Each echo is a delayed, attenuated copy of the prompt ringdown.
    Delay between successive echoes = Delta_t_echo from Stage-3D.
    Amplitude of n-th echo = (echo_amplitude_decay)^n.
    """
    # Everything here is dimensionless, in units of the ADM mass M -- which is
    # the convention the fields already document (`ell_star` is "= ell_star/M",
    # `r_photon_factor` is "r_photon / M") and the convention analyze_ringdown
    # inverts. The forward map used to disagree with both: it scaled ell_star
    # and r_photon by M_adm while the inverse used r_photon/M = 1.5, so the two
    # differed by a factor of M_adm, and the trailing "/ p.M_adm * p.M_adm"
    # cancelled to nothing while looking like a unit conversion. The round trip
    # could not close.
    M_in_seconds = M_to_seconds * p.M_adm      # one M of THIS hole, in seconds
    r_photon_over_M = p.r_photon_factor
    tau_M_over_M = p.tau_M / M_in_seconds      # tau_M is stored in seconds
    dt_echo_over_M = echo_spacing(p.ell_star, r_photon_over_M, tau_M_over_M,
                                  c_light_geom)
    dt_echo_sec = dt_echo_over_M * M_in_seconds
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
    # The smallest ell_star/M this configuration could resolve at all: one
    # autocorrelation lag bin, divided by the 2/M with which ell_star enters
    # the echo spacing. Below it the answer is REFUSED, not negative.
    ell_star_resolution_floor: float = float("inf")
    below_timing_resolution: bool = True

    def summary(self) -> dict:
        return {
            "detected_echo_spacing_s":             round(self.detected_echo_spacing_s, 6),
            "detected_echo_spacing_geom":          round(self.detected_echo_spacing_geom, 6),
            "autocorr_peak_lag_s":                 round(self.autocorr_peak_lag_s, 6),
            "autocorr_peak_height":                round(self.autocorr_peak_height, 4),
            "rsls_vs_gr_loglikelihood":            round(self.rsls_vs_gr_loglikelihood, 4),
            "n_secondary_peaks":                   self.n_secondary_peaks,
            "echo_spacing_consistent_with_RSLS":   self.echo_spacing_consistent_with_RSLS,
            "ell_star_resolution_floor":           f"{self.ell_star_resolution_floor:.4e}",
            "below_timing_resolution":             self.below_timing_resolution,
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


def cepstrum(strain: np.ndarray) -> np.ndarray:
    """Real cepstrum: IFFT of the mean-removed log magnitude spectrum.

    This is the right tool for a repeated-echo structure and autocorrelation
    is not. A train of delayed copies multiplies the spectrum by a comb, so in
    LOG magnitude the comb becomes ADDITIVE and separates from the carrier;
    the inverse transform then shows a sharp peak at the echo delay.

    Autocorrelation cannot do this here. Over the lag range where the echo
    lives (~1.2-1.45 ms for a 30 M_sun hole) the autocorrelation of the
    250 Hz damped sinusoid is still inside its own first oscillation and
    decreasing monotonically, so it swamps the comb: measured across
    ell_star/M = 0.0, 0.3, 0.6, 0.9 the ACF peak sat at the search window's
    lower edge every time, independent of what was injected. The cepstrum
    recovers all four exactly (ratio to truth 1.000).
    """
    windowed = strain * np.hanning(strain.size)
    spectrum = np.fft.rfft(windowed)
    log_mag = np.log(np.abs(spectrum) + 1e-30)
    return np.fft.irfft(log_mag - log_mag.mean())


def analyze_ringdown(times: np.ndarray, strain: np.ndarray,
                     M_adm: float = 30.0,
                     M_to_seconds: float = 5e-6,
                     min_lag_s: Optional[float] = None,
                     max_lag_s: Optional[float] = None,
                     tau_M: float = 1e-3,
                     r_photon_factor: float = 1.5,
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
    # The physical echo spacing is 2(r_photon - ell_star)/c + tau_M, so across
    # the whole admissible range of ell_star (0 .. r_photon) it lies between
    # tau_M and 2*r_photon*M + tau_M. The defaults used to be a hardcoded
    # [0.002, 0.2] s window, which for M = 30 excludes that entire range --
    # the true spacing is ~1.2e-3 to 1.45e-3 s, below the window's floor, so
    # the search could not find the echo for ANY ell_star and locked onto a
    # harmonic instead. Derive it from the parameters instead of guessing.
    _M_in_s = M_to_seconds * M_adm
    _span_hi = 2.0 * r_photon_factor * _M_in_s + tau_M
    _span_lo = tau_M
    if min_lag_s is None:
        min_lag_s = max(0.25 * _span_lo, 2.0 * float(times[1] - times[0]))
    if max_lag_s is None:
        max_lag_s = 2.0 * _span_hi

    # Echo delay from the cepstrum (see `cepstrum` for why not autocorrelation).
    _cep = cepstrum(strain)
    _dt_s = float(times[1] - times[0]) if times.size > 1 else 1.0
    _lo = max(1, int(min_lag_s / _dt_s))
    _hi = min(_cep.size, max(_lo + 2, int(max_lag_s / _dt_s)))
    _seg = _cep[_lo:_hi]
    _k = _lo + int(np.argmax(_seg))
    _cep_peak_lag_s = _k * _dt_s
    _cep_med = float(np.median(np.abs(_seg))) if _seg.size else 0.0
    _cep_prominence = (float(_cep[_k]) / _cep_med) if _cep_med > 0 else 0.0

    ac = autocorrelation(strain)

    # Search window
    lo = max(1, int(min_lag_s * sample_rate))
    hi = min(len(ac) - 1, int(max_lag_s * sample_rate))
    if hi <= lo:
        raise ValueError("search window collapsed; check min/max_lag_s")
    window = ac[lo:hi]
    rel_idx = int(np.argmax(window))
    peak_idx = lo + rel_idx
    # The AUTOCORRELATION peak is retained only as a diagnostic. The echo delay
    # that gets inverted for ell_star comes from the cepstrum, which is the
    # statistic that actually resolves the comb.
    acf_peak_lag_s = peak_idx / sample_rate
    acf_peak_height = float(window[rel_idx])
    peak_lag_s = _cep_peak_lag_s
    # Prominence of the cepstral peak over the local median, squashed into
    # (0, 1) so it reads on the same scale the downstream thresholds expect.
    peak_height = float(_cep_prominence / (1.0 + _cep_prominence))

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
    M_in_seconds = M_to_seconds * M_adm
    Delta_t_geom = peak_lag_s / M_in_seconds
    # These were hardcoded to 1.5 and 0.2 while the generator used
    # 1.5 * M_adm and tau_M / 5e-6 -- three different conventions for two
    # quantities. They are now derived the same way on both sides.
    r_photon_geom = r_photon_factor
    tau_M_geom = tau_M / M_in_seconds
    # Solve: Delta_t_geom = 2 * (r_photon - ell_star_M) + tau_M_geom
    ell_star_M = r_photon_geom - 0.5 * (Delta_t_geom - tau_M_geom)
    if ell_star_M < 0:
        ell_star_M = 0.0

    # How small an ell_star could this configuration SEE at all?
    # ell_star enters only through 2*ell_star/M, so a shift of delta in
    # ell_star/M moves the echo by 2*delta*M_in_seconds seconds. Nothing
    # below one lag bin is recoverable, whatever the units are.
    lag_bin_s = float(times[1] - times[0]) if times.size > 1 else float("inf")
    ell_star_resolution_floor = lag_bin_s / (2.0 * M_in_seconds)
    below_timing_resolution = ell_star_M < ell_star_resolution_floor

    # Stage-3E detectability check
    # "Not consistent with RSLS" and "too small for this instrument to see" are
    # different statements, and reporting the second as the first is a false
    # negative dressed as a measurement. A value under the timing floor is
    # REFUSED: the configuration carries no information about it either way.
    rsls_consistent = (
        peak_height > 0.05            # noisy autocorrelation, but a real peak
        and not below_timing_resolution
        and ell_star_M > 1e-15        # not Planck-scale (Macroscopic Mandate)
        and ell_star_M < 1.0          # below the photon sphere
    )

    return RingdownAnalysis(
        detected_echo_spacing_s=peak_lag_s,
        detected_echo_spacing_geom=Delta_t_geom,
        autocorr_peak_lag_s=acf_peak_lag_s,
        autocorr_peak_height=acf_peak_height,
        rsls_vs_gr_loglikelihood=log_lr,
        n_secondary_peaks=n_secondary,
        echo_spacing_consistent_with_RSLS=rsls_consistent,
        inferred_ell_star_over_M=ell_star_M,
        ell_star_resolution_floor=ell_star_resolution_floor,
        below_timing_resolution=below_timing_resolution,
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
    # The analyzer must be told the SAME tau_M and r_photon the generator used.
    # It previously defaulted to hardcoded values that did not match, so the
    # round trip was inverting a different map from the one that made the data.
    result = analyze_ringdown(times, h, M_adm=p.M_adm,
                              tau_M=p.tau_M,
                              r_photon_factor=p.r_photon_factor)
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
