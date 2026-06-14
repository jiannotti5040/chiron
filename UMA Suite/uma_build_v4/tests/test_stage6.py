"""tests/test_stage6.py -- self-consistent Stage 6 closure tests."""
from __future__ import annotations
import numpy as np
import pytest

from uma.rsls.stage6 import (
    Stage6Config, run_stage6, equilibrium_beta_phi,
    beta_phi_causal_step, off_diagonal_stress,
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


@pytest.mark.slow
class TestStage6Lyapunov:
    """Full coupled Lyapunov computation (slow)."""

    def test_positive_lyapunov(self):
        cfg = Stage6Config(N=100, n_steps=2000, Omega_0=1.5,
                            enable_self_consistency=True)
        res = run_stage6(cfg, compute_lyapunov=True, verbose=False)
        # Strong positive: under coupling, chaos amplifies (perturbations
        # propagate through metric AND matter)
        assert res.lyapunov_max > 0.5
