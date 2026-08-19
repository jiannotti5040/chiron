# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""tests/test_ligo_lisa.py -- ringdown waveform injection-recovery."""
from __future__ import annotations
import numpy as np
import pytest

from uma.rsls.ligo_lisa import (
    RingdownParams, generate_kerr_ringdown, generate_rsls_echo_train,
    generate_synthetic_strain, autocorrelation, analyze_ringdown,
    synthetic_injection_recovery,
)


class TestWaveformGeneration:
    def test_kerr_ringdown_decays(self):
        t = np.linspace(0, 0.1, 1000)
        h = generate_kerr_ringdown(t, RingdownParams(tau_qnm=0.01))
        # Initial amplitude max ~= 1; later amplitude << 1
        assert abs(h[0]) > 0.9
        assert abs(h[-1]) < 0.001

    def test_echo_train_differs_from_bare_ringdown(self):
        """With echo amplitude > 0, the waveform must differ from the
        pure Kerr ringdown."""
        t = np.linspace(0, 0.5, 4096)
        p = RingdownParams(n_echoes=5, echo_amplitude_decay=0.5)
        bare = generate_kerr_ringdown(t, p)
        with_echo = generate_rsls_echo_train(t, p)
        # The two waveforms should differ measurably
        rms_diff = np.sqrt(np.mean((with_echo - bare) ** 2))
        assert rms_diff > 1e-3

    def test_generate_strain_shape(self):
        times, h = generate_synthetic_strain(duration=0.5, sample_rate=2048.0,
                                              add_noise=False, rng_seed=0)
        assert len(times) == len(h)
        assert len(times) == 1024


class TestAutocorrelation:
    def test_zero_lag_is_one(self):
        x = np.random.randn(100)
        ac = autocorrelation(x)
        assert abs(ac[0] - 1.0) < 1e-10

    def test_sinusoid_has_periodic_peaks(self):
        t = np.linspace(0, 10, 1000)
        x = np.sin(2 * np.pi * 1.0 * t)   # 1 Hz
        ac = autocorrelation(x)
        # Should peak at lag ~= 1 second
        sample_rate = 100  # 1000 samples over 10 s
        lag_index = int(1.0 * sample_rate)
        # Window around expected lag
        window = ac[lag_index - 5: lag_index + 6]
        assert window.max() > 0.85


class TestAnalysis:
    def test_pure_kerr_has_weak_secondary_peak(self):
        p = RingdownParams(n_echoes=0)
        times, h = generate_synthetic_strain(p, duration=1.0, sample_rate=4096.0,
                                              add_noise=False)
        result = analyze_ringdown(times, h, M_adm=p.M_adm)
        # Without echoes, autocorrelation peak should be modest
        assert result.autocorr_peak_height < 0.6

    def test_strong_echoes_increase_peak_height(self):
        p = RingdownParams(n_echoes=5, echo_amplitude_decay=0.6)
        times, h = generate_synthetic_strain(p, duration=1.0, sample_rate=4096.0,
                                              add_noise=False)
        result = analyze_ringdown(times, h, M_adm=p.M_adm)
        # Echoes should produce a clear autocorrelation peak
        assert result.autocorr_peak_height > 0.1
        assert result.rsls_vs_gr_loglikelihood > 1.0

    def test_injection_recovery_returns_finite_estimates(self):
        p, result = synthetic_injection_recovery(rng_seed=0)
        assert np.isfinite(result.detected_echo_spacing_s)
        assert result.detected_echo_spacing_s > 0
        assert np.isfinite(result.rsls_vs_gr_loglikelihood)


class TestEchoRoundTrip:
    """The falsification handle must recover what it injects.

    Until 2026-08-19 it could not, for three compounding reasons, all fixed:

      1. The forward map scaled ell_star and r_photon by M_adm while the
         inverse used the dimensionless r/M convention the fields document,
         so the two differed by a factor of M_adm, and a trailing
         "/ M_adm * M_adm" cancelled to nothing while looking like a unit
         conversion. tau_M had three different conventions across two call
         sites.
      2. The autocorrelation search window was hardcoded to [0.002, 0.2] s.
         For M = 30 the echo spacing is ~1.2-1.45 ms for EVERY admissible
         ell_star, i.e. entirely below the window, so the search could not
         find the echo at all and locked onto a harmonic.
      3. Autocorrelation is the wrong statistic. Over that lag range the
         250 Hz ringdown's own ACF is still inside its first oscillation and
         decreasing, and it swamps the comb. The cepstrum separates them
         because a delayed copy multiplies the spectrum, which is additive
         in log magnitude.
    """

    def test_injection_recovery_is_exact(self):
        for ell in (0.3, 0.6, 0.9):
            p = RingdownParams(M_adm=30.0, ell_star=ell, tau_M=1e-3,
                               n_echoes=5, echo_amplitude_decay=0.6)
            p, a = synthetic_injection_recovery(
                p, duration=0.06, sample_rate=400000.0, noise=True, rng_seed=42)
            assert abs(a.inferred_ell_star_over_M - ell) < 1e-3, (
                "injected ell*/M=%.3f recovered as %.6f"
                % (ell, a.inferred_ell_star_over_M))
            assert a.echo_spacing_consistent_with_RSLS
            assert not a.below_timing_resolution

    def test_below_resolution_is_refused_not_called_inconsistent(self):
        # ell*/M = 1e-7 shifts the echo by 3e-11 s while a 4096 Hz sample
        # period is 2.4e-4 s -- eight million times too coarse. That is a
        # measurement this configuration cannot make, not a refuted theory.
        p = RingdownParams(M_adm=30.0, ell_star=1e-7, tau_M=1e-3,
                           n_echoes=5, echo_amplitude_decay=0.6)
        p, a = synthetic_injection_recovery(
            p, duration=1.0, sample_rate=4096.0, noise=True, rng_seed=42)
        assert a.below_timing_resolution
        assert a.ell_star_resolution_floor > p.ell_star

    def test_resolution_floor_scales_with_sample_rate(self):
        floors = []
        for sr in (4096.0, 40960.0):
            p = RingdownParams(M_adm=30.0, ell_star=0.3, tau_M=1e-3)
            _, a = synthetic_injection_recovery(
                p, duration=0.06, sample_rate=sr, noise=False, rng_seed=1)
            floors.append(a.ell_star_resolution_floor)
        assert floors[1] < floors[0] / 5.0, (
            "a 10x finer sample rate must lower the floor ~10x, got %r" % floors)

    def test_cepstrum_beats_autocorrelation_on_the_comb(self):
        # The control that justifies the method change: across injected
        # values the cepstral estimate tracks truth and the ACF does not.
        import numpy as np
        from uma.rsls.ligo_lisa import cepstrum, autocorrelation, echo_spacing
        sr, M_in_s = 400000.0, 5e-6 * 30.0
        cep_ok = acf_ok = 0
        for ell in (0.0, 0.3, 0.6, 0.9):
            p = RingdownParams(M_adm=30.0, ell_star=ell, tau_M=1e-3,
                               n_echoes=5, echo_amplitude_decay=0.6)
            times, h = generate_synthetic_strain(p, 0.06, sr, True, 42)
            true_dt = echo_spacing(p.ell_star, p.r_photon_factor,
                                   p.tau_M / M_in_s, 1.0) * M_in_s
            lo, hi = int(0.5e-3 * sr), int(3e-3 * sr)
            for stat, hits in ((cepstrum(h), "cep"), (autocorrelation(h), "acf")):
                k = lo + int(np.argmax(stat[lo:hi]))
                if abs((k / sr) / true_dt - 1.0) < 0.02:
                    if hits == "cep":
                        cep_ok += 1
                    else:
                        acf_ok += 1
        assert cep_ok == 4, "cepstrum should recover all four, got %d" % cep_ok
        assert acf_ok == 0, "autocorrelation unexpectedly recovered %d" % acf_ok
