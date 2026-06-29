# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
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
