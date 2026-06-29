# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
tests/test_srb.py -- statistical-reduction correctness.
"""
from __future__ import annotations
import math
import numpy as np
import pytest

from uma.rsls.srb import (
    LorenzParams, lorenz_rhs, integrate_lorenz,
    lyapunov_max, srb_histogram, srb_converges,
    koopman_transfer_matrix, koopman_stationary,
    lindblad_step, integrate_lindblad,
    born_rule_match,
)


class TestLorenzIntegration:
    def test_integrate_runs(self):
        traj = integrate_lorenz(np.array([1.0, 1.0, 1.0]),
                                dt=0.01, n_steps=500)
        assert traj.shape == (501, 3)
        assert np.all(np.isfinite(traj))

    def test_attractor_bounded(self):
        """Lorenz trajectory stays in a bounded region."""
        traj = integrate_lorenz(np.array([1.0, 1.0, 1.0]),
                                dt=0.01, n_steps=5000)
        # Skip burn-in
        on_attractor = traj[1000:]
        # Standard attractor bounds (approximately)
        assert np.all(np.abs(on_attractor[:, 0]) < 30)
        assert np.all(np.abs(on_attractor[:, 1]) < 30)
        assert np.all(on_attractor[:, 2] > 0) and np.all(on_attractor[:, 2] < 60)


class TestLyapunov:
    def test_lorenz_lyapunov_positive(self):
        """Canonical Lorenz lambda_max ~= 0.9056."""
        state0 = np.array([1.0, 1.0, 1.0])
        lam = lyapunov_max(lorenz_rhs, state0, 0.01, 3000, 5, 1e-8,
                          LorenzParams())
        # Allow significant tolerance; 0.5 < lam < 1.3 is generous
        assert 0.5 < lam < 1.3, f"lambda_max = {lam}, expected ~0.9"

    def test_lyapunov_of_decaying_system_negative(self):
        """A pure exponential decay dx/dt = -x has Lyapunov = -1."""
        rhs = lambda s, *a: -s
        state0 = np.array([1.0])
        lam = lyapunov_max(rhs, state0, 0.01, 1000, 5, 1e-8)
        assert lam < 0, f"decay system gave lam={lam}, expected < 0"


class TestSRB:
    def test_histogram_normalised(self):
        state0 = np.array([1.0, 1.0, 1.0])
        traj = integrate_lorenz(state0, 0.01, 5000)
        centres, hist = srb_histogram(traj[1000:], axis=2, n_bins=32)
        assert centres.shape == hist.shape
        # Integral should be ~1 (density)
        bin_width = centres[1] - centres[0]
        total = hist.sum() * bin_width
        assert abs(total - 1.0) < 0.01

    @pytest.mark.slow
    def test_ergodic_convergence(self):
        """Two trajectories from same IC, different lengths, should
        give similar SRB histograms."""
        state0 = np.array([1.0, 1.0, 1.0])
        l1 = srb_converges(lorenz_rhs, state0, 0.01, 2000, 10000, 2,
                           LorenzParams())
        # L^1 distance < 0.5 is reasonable convergence
        assert l1 < 0.5


class TestLindblad:
    def test_amplitude_damping_to_ground(self):
        """A 2-level system in excited state should decay under
        sigma_minus jump operator to ground state."""
        rho0 = np.array([[0.0, 0.0], [0.0, 1.0]], dtype=complex)
        H = np.zeros((2, 2), dtype=complex)
        sigma_minus = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=complex)
        traj = integrate_lindblad(rho0, H, [sigma_minus], dt=0.01, n_steps=1000)
        # Excited state population should decay to ~0
        p_excited_final = float(np.real(traj[-1, 1, 1]))
        p_ground_final = float(np.real(traj[-1, 0, 0]))
        assert p_excited_final < 0.01
        assert abs(p_ground_final - 1.0) < 0.01

    def test_trace_preserving(self):
        """Lindblad evolution preserves trace = 1."""
        rho0 = np.array([[0.6, 0.1 + 0.1j], [0.1 - 0.1j, 0.4]], dtype=complex)
        H = np.array([[1.0, 0.5], [0.5, -1.0]], dtype=complex)
        sigma_z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
        traj = integrate_lindblad(rho0, H, [sigma_z], dt=0.001, n_steps=500)
        # Trace should stay ~1
        traces = [float(np.real(np.trace(rho))) for rho in traj]
        max_drift = max(abs(t - 1.0) for t in traces)
        assert max_drift < 0.01


class TestKoopman:
    def test_transfer_matrix_row_stochastic(self):
        """Each row of T should sum to 1."""
        rhs = lambda s, *a: -0.5 * s  # simple contracting flow
        T = koopman_transfer_matrix(rhs, dt=0.1, n_bins=20,
                                    bounds=(-1.0, 1.0))
        row_sums = T.sum(axis=1)
        # Each row that has nonzero entries should sum to 1
        nz_rows = row_sums > 0.5
        assert np.allclose(row_sums[nz_rows], 1.0)

    def test_stationary_normalised(self):
        """Stationary distribution should sum to 1."""
        rhs = lambda s, *a: -0.5 * s
        T = koopman_transfer_matrix(rhs, dt=0.1, n_bins=20,
                                    bounds=(-1.0, 1.0))
        pi = koopman_stationary(T)
        assert abs(pi.sum() - 1.0) < 1e-6
        assert np.all(pi >= 0)
