# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
tests/test_frame_dragging.py -- Stage 5 frame-dragging kernel.

The key falsification test:

    WITH    beta^phi != 0:  cone aperture > 2 c_diff
    WITHOUT beta^phi:       cone aperture = 2 c_diff

The cone-aperture dichotomy is the surviving Stage-5 result.

The Lyapunov half of this file previously asserted `lambda_max > 0` with drag
and `<= 0` without, and read the difference as proof that chaos is structural
rather than transient. That comparison is withdrawn (2026-08-11): both sides
were unconverged, perturbation-size-dependent statistics dominated by single
transient events, so their difference measured nothing. See
uma/rsls/lyapunov.py for the numbers and studies/rsls_lyapunov/ for the
investigation, which also turned up two separate defects in the kernel
itself -- a fixed timestep that violates CFL by ~550x once velocities grow,
and a finite-time vacuum that stalls the integration at t ~ 3.34.
"""
from __future__ import annotations
import math

import numpy as np
import pytest

from uma.rsls import MemoryConfig
from uma.rsls.frame_dragging import (
    FrameDraggingConfig, run_frame_dragging,
    kerr_like_drag, cone_aperture_full,
)


class TestBetaPhiProfile:
    def test_kerr_like_drag_decays_outward(self):
        R = np.linspace(1.0, 10.0, 100)
        beta = kerr_like_drag(R, R_in=1.0, Omega_0=1.0, exponent=2.0)
        # At R = R_in = 1, beta = Omega_0 = 1; at large R, beta -> 0
        assert abs(beta[0] - 1.0) < 1e-10
        assert beta[-1] < beta[0]
        assert np.all(np.diff(beta) < 0)   # strictly monotone decreasing

    def test_zero_omega_gives_zero_drag(self):
        R = np.linspace(1.0, 10.0, 50)
        beta = kerr_like_drag(R, R_in=1.0, Omega_0=0.0, exponent=2.0)
        assert np.all(beta == 0)


class TestConeAperture:
    def test_aperture_floor_with_zero_drag(self):
        """With beta^phi = 0, Delta_Lambda = 2 c_diff (the floor)."""
        cfg = MemoryConfig()
        R = np.linspace(1.0, 10.0, 50)
        beta = np.zeros_like(R)
        ap = cone_aperture_full(R, beta, cfg)
        # Cone aperture should equal 2 c_diff everywhere
        assert np.allclose(ap, 2.0 * cfg.c_diff, atol=1e-10)

    def test_aperture_strictly_above_floor_with_drag(self):
        """With beta^phi != 0 (and non-zero gradient), cone is strictly open."""
        cfg = MemoryConfig()
        R = np.linspace(1.0, 10.0, 50)
        beta = kerr_like_drag(R, R_in=1.0, Omega_0=1.0, exponent=2.0)
        ap = cone_aperture_full(R, beta, cfg)
        floor = 2.0 * cfg.c_diff
        # At inner cells where grad is largest, aperture > floor by a clear margin
        assert ap[0] > floor + 0.5
        # Everywhere: aperture >= floor (sqrt of c_diff^2 + non-negative)
        assert np.all(ap >= floor - 1e-12)


class TestKernelDichotomy:
    """The headline test: frame-dragging produces chaos; absence does not."""

    @pytest.fixture(scope="class")
    def with_drag(self):
        cfg = FrameDraggingConfig(N=150, n_steps=3000, Omega_0=1.5,
                                  enable_drag=True)
        return run_frame_dragging(cfg, verbose=False)

    @pytest.fixture(scope="class")
    def without_drag(self):
        cfg = FrameDraggingConfig(N=150, n_steps=3000, Omega_0=1.5,
                                  enable_drag=False)
        return run_frame_dragging(cfg, verbose=False)

    def test_cone_aperture_open_with_drag(self, with_drag):
        # In the saturation layer (where M is saturated), cone is strictly open
        assert with_drag.cone_aperture_saturation_margin > 0.01

    def test_cone_aperture_closed_without_drag(self, without_drag):
        # No frame-dragging => cone closes to the c_diff floor
        assert abs(without_drag.cone_aperture_saturation_margin) < 1e-8

    def test_lyapunov_is_refused_not_reported(self, with_drag):
        """This asserted `lyapunov_max > 0.3` as the structural chaos
        signature until 2026-08-11. The statistic is not an exponent: it does
        not converge, it changes sign with the perturbation size (+0.34,
        +5.50, -0.024, -0.021 at delta = 1e-6 ... 1e-12), and ONE block of 72
        -- a single growth of x87 -- carries 82% of the sum while the median
        block contracts. The 0.3 threshold was cleared by that one event.

        Two real estimator bugs were fixed (J was never renormalised with the
        rest of the state; partial blocks were credited a full block of time)
        and neither rescued convergence, so the claim is withdrawn rather than
        repaired. The controls in test_stage6.py prove the refusal
        discriminates -- it accepts Lorenz at +0.9032 against +0.906.
        """
        assert with_drag.lyapunov is not None
        assert not with_drag.lyapunov.converged, (
            "the estimator now claims convergence -- if that is real the "
            "withdrawn chaos claim can be revisited; check the controls first")
        assert math.isnan(with_drag.lyapunov_max), (
            "lyapunov_max must stay NaN while refused, so no caller can read "
            "an unconverged statistic as a result")

    def test_the_dragged_run_is_refused_for_not_plateauing(self, with_drag):
        """At this resolution the refusal is the convergence check, not the
        single-event one: the second half of the window gives roughly twice
        the whole-window rate, so the statistic is still climbing."""
        rep = with_drag.lyapunov
        assert not rep.converged
        assert "not plateaued" in rep.reason, rep.reason
        assert abs(rep.second_half_value - rep.value) > 0.10

    def test_undragged_control_converges_and_is_not_chaotic(self, without_drag):
        """The one Lyapunov statement here that survives.

        Without frame-dragging the estimate DOES pass every check -- 112
        blocks, largest carrying 3.7% of the variation, second half within
        0.021 of the whole window -- and lands at lambda ~ -0.037. So the
        undragged kernel is measurably NOT chaotic, and that is a real result
        rather than a refusal.

        Note what this does and does not license. The old pair of tests read
        a >0.3 differential between the two runs as proof that frame-dragging
        drives structural chaos. Half of that comparison (the dragged side)
        is still an unconverged statistic, so the differential remains
        unavailable: the honest reading is "no chaos without drag, unresolved
        with drag", not "drag causes chaos".
        """
        rep = without_drag.lyapunov
        assert rep is not None
        assert rep.converged, rep.reason
        assert rep.value < 0.0, rep.value
        assert without_drag.lyapunov_max == rep.value
        assert rep.top_block_share < 0.25
        assert rep.bounded

    def test_both_runs_converge(self, with_drag, without_drag):
        assert with_drag.converged
        assert without_drag.converged
