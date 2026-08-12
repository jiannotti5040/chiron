# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""tests/test_stage6.py -- self-consistent Stage 6 closure tests."""
from __future__ import annotations
import math

import numpy as np
import pytest

from uma.rsls.stage6 import (
    Stage6Config, run_stage6, equilibrium_beta_phi,
    beta_phi_causal_step, off_diagonal_stress,
    stage6_lyapunov, _lyapunov_report,
)


class TestOffDiagonalStress:
    def test_zero_when_either_velocity_zero(self):
        D = np.ones(10); S_R = np.zeros(10); S_phi = np.ones(10)
        assert np.allclose(off_diagonal_stress(D, S_R, S_phi), 0)
        S_R = np.ones(10); S_phi = np.zeros(10)
        assert np.allclose(off_diagonal_stress(D, S_R, S_phi), 0)

    def test_correct_formula(self):
        D = np.array([2.0, 4.0]); S_R = np.array([6.0, 8.0]); S_phi = np.array([1.0, 2.0])
        # T_Rphi = S_R * S_phi / D
        expected = np.array([3.0, 4.0])
        assert np.allclose(off_diagonal_stress(D, S_R, S_phi), expected)


class TestEquilibriumBetaPhi:
    def test_zero_T_gives_zero_beta(self):
        R = np.linspace(1.0, 10.0, 50); T = np.zeros_like(R)
        beq = equilibrium_beta_phi(T, R, 0.4)
        assert np.allclose(beq, 0)

    def test_positive_T_gives_negative_beta(self):
        """T_Rphi > 0 induces negative beta^phi (the matter is dragging
        the metric, which appears as negative shift in our sign convention)."""
        R = np.linspace(1.0, 10.0, 50); T = 0.5 * np.exp(-((R - 3) / 1.0) ** 2)
        beq = equilibrium_beta_phi(T, R, 0.4)
        # All values should be <= 0 (we integrate -T outward)
        assert (beq <= 1e-10).all()


class TestCausalRelaxation:
    def test_relaxes_toward_target(self):
        """In the limit dt > 0 small, beta_phi should move toward target."""
        beta = np.ones(20) * 1.0
        target = np.ones(20) * 0.5
        beta_new = beta_phi_causal_step(beta, target, dR=0.1, dt=0.01,
                                         tau_beta=1.0, mu_beta=0.0)
        # Each cell should move toward target
        assert np.all(beta_new < beta)
        assert np.all(beta_new > target)

    def test_stable_at_target(self):
        beta = np.ones(20) * 0.5
        target = np.ones(20) * 0.5
        beta_new = beta_phi_causal_step(beta, target, dR=0.1, dt=0.01,
                                         tau_beta=1.0, mu_beta=0.0)
        assert np.allclose(beta_new, beta)


class TestStage6Closure:
    """The key closure tests for Stage 6."""

    @pytest.fixture(scope="class")
    def coupled(self):
        cfg = Stage6Config(N=100, n_steps=2000, Omega_0=1.5,
                            enable_self_consistency=True)
        return run_stage6(cfg, compute_lyapunov=False, verbose=False)

    @pytest.fixture(scope="class")
    def uncoupled(self):
        """With self-consistency off, beta^phi is frozen -- should reduce
        to Stage 5 behaviour."""
        cfg = Stage6Config(N=100, n_steps=2000, Omega_0=1.5,
                            enable_self_consistency=False)
        return run_stage6(cfg, compute_lyapunov=False, verbose=False)

    def test_coupled_converges(self, coupled):
        assert coupled.self_consistency_converged

    def test_cone_strictly_positive_throughout(self, coupled):
        """The Stage-6 closure: cone stays open under self-consistency."""
        assert coupled.cone_aperture_strictly_positive_throughout

    def test_cone_margin_remains_substantial(self, coupled):
        """Final saturation-layer margin should still be meaningful."""
        assert coupled.cone_aperture_saturation_margin_final > 0.01

    def test_uncoupled_has_zero_drift(self, uncoupled):
        """Without self-consistency, beta^phi must not change."""
        assert uncoupled.beta_phi_drift_fraction < 1e-10

    def test_coupled_has_nonzero_drift(self, coupled):
        """With self-consistency, beta^phi should move coherently in response to matter."""
        # 5%-200% range expected; outside this is suspect
        assert 0.01 < coupled.beta_phi_drift_fraction < 2.0

    def test_M_reaches_saturation(self, coupled):
        """Self-consistency should not prevent the saturation layer from forming."""
        assert max(coupled.M_max_history) > 0.9 * coupled.cfg.memory.M_max


class TestLyapunovReportControls:
    """The refusal has to discriminate, or it proves nothing.

    These are the positive controls for `_lyapunov_report`: systems whose
    exponent is known independently. If the checks cannot accept Lorenz and
    recover +0.906, then Stage 6's refusal below is just a broken gate saying
    no to everything.
    """

    DT = 0.005
    RENORM = 25
    D0 = 1e-8

    def _twin_blocks(self, f, s0, n_steps, burn=2000):
        def rk4(s):
            k1 = f(s); k2 = f(s + 0.5 * self.DT * k1)
            k3 = f(s + 0.5 * self.DT * k2); k4 = f(s + self.DT * k3)
            return s + self.DT / 6.0 * (k1 + 2 * k2 + 2 * k3 + k4)

        s1 = np.array(s0, dtype=float)
        for _ in range(burn):
            s1 = rk4(s1)
        s2 = s1.copy(); s2[0] += self.D0
        logs, times, done = [], [], 0
        while done < n_steps:
            k = min(self.RENORM, n_steps - done)
            for _ in range(k):
                s1 = rk4(s1); s2 = rk4(s2)
            done += k
            sep = s2 - s1; sn = np.linalg.norm(sep)
            if sn > 1e-30:
                logs.append(float(np.log(sn / self.D0)))
                times.append(k * self.DT)
                s2 = s1 + sep / sn * self.D0
        return np.array(logs), np.array(times)

    def test_accepts_lorenz_and_recovers_the_known_exponent(self):
        def lorenz(s):
            x, y, z = s
            return np.array([10.0 * (y - x), x * (28.0 - z) - y, x * y - (8.0 / 3.0) * z])

        logs, times = self._twin_blocks(lorenz, [1.0, 1.0, 1.0], 30000)
        rep = _lyapunov_report(logs, times, bounded=True)
        assert rep.converged, f"refused a known-chaotic system: {rep.reason}"
        assert abs(rep.value - 0.906) < 0.05, rep.value   # literature lambda_max

    def test_accepts_a_contracting_system_at_its_exact_rate(self):
        logs, times = self._twin_blocks(lambda s: -0.5 * s, [1.0, 1.0, 1.0], 30000)
        rep = _lyapunov_report(logs, times, bounded=True)
        assert rep.converged, rep.reason
        assert abs(rep.value - (-0.5)) < 1e-3, rep.value

    def test_refuses_a_single_transient_spike(self):
        spiky = np.full(72, 1e-4); spiky[40] = 4.47
        rep = _lyapunov_report(spiky, np.full(72, 0.125), bounded=True)
        assert not rep.converged
        assert "transient" in rep.reason

    def test_refuses_when_the_trajectory_left_the_physical_range(self):
        logs, times = self._twin_blocks(lambda s: -0.5 * s, [1.0, 1.0, 1.0], 30000)
        rep = _lyapunov_report(logs, times, bounded=False)
        assert not rep.converged
        assert "instability" in rep.reason


@pytest.mark.slow
class TestStage6Lyapunov:
    """Full coupled Lyapunov computation (slow).

    This asserted `lyapunov_max > 0.5` until 2026-08-11, on the claim that
    Stage-5 chaos survives geometric back-reaction. The statistic it read is
    not an exponent: it does not converge (-0.013, +3.16, +8.95, +39.12 at
    n_steps 2k/4k/8k/16k), it changes sign with the perturbation size, one
    block of 72 carries most of the sum while the median block contracts, and
    past ~8k steps the solution itself is unbounded. Two genuine estimator
    bugs were fixed (J was never renormalised; partial blocks were credited a
    full block of time) and neither rescued it.

    So the gate now asserts the honest outcome -- the estimator refuses --
    and the controls above prove the refusal is discriminating rather than
    blanket. Whether the coupled system is chaotic is open, not settled.
    """

    def test_lyapunov_is_refused_not_reported(self):
        cfg = Stage6Config(N=100, n_steps=2000, Omega_0=1.5,
                            enable_self_consistency=True)
        res = run_stage6(cfg, compute_lyapunov=True, verbose=False)
        assert res.lyapunov is not None
        assert not res.lyapunov.converged, (
            "the estimator now claims convergence -- if that is real, the "
            "withdrawn chaos claim can be revisited; check the controls first")
        assert math.isnan(res.lyapunov_max), (
            "lyapunov_max must stay NaN while the estimate is refused, so no "
            "caller can read an unconverged statistic as a result")
        assert res.lyapunov.reason

    def test_the_refusal_reason_is_the_documented_one(self):
        rep = stage6_lyapunov(Stage6Config(N=100, n_steps=2000, Omega_0=1.5,
                                            enable_self_consistency=True))
        assert rep.top_block_share > 0.25, rep.top_block_share
        assert "transient" in rep.reason
        # the median block contracts -- there is no sustained divergence here
        assert rep.contracting_fraction > 0.5, rep.contracting_fraction
