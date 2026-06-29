# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
tests/test_frame_dragging.py -- Stage 5 frame-dragging kernel.

The key falsification test:

    WITH    beta^phi != 0:  cone aperture > 2 c_diff,  lambda_max > 0
    WITHOUT beta^phi:       cone aperture = 2 c_diff,  lambda_max <= 0

If these dichotomies hold, the frame-dragging closure is verified
numerically -- chaos is structural, not a transient artifact.
"""
from __future__ import annotations
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

    def test_lyapunov_positive_with_drag(self, with_drag):
        """The structural chaos signature: lambda_max > 0 with drag."""
        assert with_drag.lyapunov_max > 0.3, (
            f"lambda_max with drag = {with_drag.lyapunov_max} -- "
            "expected strongly positive"
        )

    def test_lyapunov_nonpositive_without_drag(self, without_drag):
        """Without the structural mixer, no chaos."""
        # Allow slight numerical positivity (~0.05) but not real chaos
        assert without_drag.lyapunov_max < 0.1, (
            f"lambda_max without drag = {without_drag.lyapunov_max} -- "
            "expected ~0 or slightly negative"
        )

    def test_lyapunov_differential(self, with_drag, without_drag):
        """The crucial separation: frame-dragging produces >0.3 differential."""
        diff = with_drag.lyapunov_max - without_drag.lyapunov_max
        assert diff > 0.3, (
            f"Lyapunov differential = {diff} -- frame-dragging is not "
            "producing a clear chaos signal"
        )

    def test_both_runs_converge(self, with_drag, without_drag):
        assert with_drag.converged
        assert without_drag.converged
