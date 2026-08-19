# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Gates for the tangent-space Lyapunov harness in studies/rsls_lyapunov/.

That harness is what settled the chaos question -- it is the reason the
Stage-5 and Stage-6 exponents are withdrawn as discretisation artifacts -- and
until now nothing in the suite exercised it. A conclusion that load-bearing
should not rest on a script no gate ever runs.

Two things are pinned here:

  1. The METHOD is valid: with Lorenz's analytic Jacobian the same accumulation
     recovers the literature exponent. A tangent integrator that cannot do this
     has no standing to refuse anything.

  2. The RSLS statistic is window-dependent to a degree that by itself denies
     it is an exponent. At fixed N and a fixed grid it moves ~10x with the
     integration window. A Lyapunov exponent is a limit; this has not reached
     one. This is independent of the grid-refinement argument.
"""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "studies", "rsls_lyapunov"))

from tangent_lyapunov import lorenz_tangent, tangent_lyapunov  # noqa: E402
from uma.rsls.stage6 import Stage6Config  # noqa: E402

BASE = dict(n_steps=1, Omega_0=1.5, enable_self_consistency=False)


class TestTangentMethodIsValid:
    def test_recovers_the_lorenz_exponent(self):
        """Literature lambda_max = +0.906. The full run gives +0.9019."""
        lam = lorenz_tangent(n=40000)
        assert abs(lam - 0.906) < 0.03, (
            "tangent accumulation does not recover Lorenz: %r" % lam)


class TestRSLSStatisticIsNotAnExponent:
    def test_window_length_moves_it_by_an_order_of_magnitude(self):
        """At fixed N and fixed dt, only the window changes.

        Measured at N = 100: +16.10, +82.77, +111.20, +172.02 at
        T = 5, 8, 12, 20. Nothing about the physics or the discretisation
        differs between those four numbers.
        """
        # Measured at N = 100: +16.10, +111.20 at T = 5, 12 -- a 6.9x spread.
        # The effect is grid-dependent and much milder at N = 50 (+62.76 to
        # +91.04, 1.45x), which is why this asserts at the resolution where it
        # was actually measured rather than the cheapest one.
        lams = [tangent_lyapunov(Stage6Config(N=100, **BASE), T_target=T)["lambda"]
                for T in (5.0, 12.0)]
        assert all(l > 0 for l in lams), lams
        spread = max(lams) / min(lams)
        assert spread > 3.0, (
            "the statistic is expected to be strongly window-dependent; "
            "got %r (spread %.2fx). If this has become stable, the withdrawn "
            "chaos claim is worth revisiting -- check the controls first."
            % (lams, spread))

    def test_burn_in_moves_it_too(self):
        """Discarding more transient changes the answer, which a converged
        exponent would not care about."""
        a = tangent_lyapunov(Stage6Config(N=50, **BASE),
                             T_target=5.0, T_burn=0.0)["lambda"]
        b = tangent_lyapunov(Stage6Config(N=50, **BASE),
                             T_target=5.0, T_burn=3.0)["lambda"]
        assert abs(b - a) / max(abs(a), 1e-12) > 0.5, (
            "burn-in should move this statistic substantially; got %r -> %r"
            % (a, b))


@pytest.mark.slow
class TestGridTableReproduces:
    """The published grid table, at the window it was actually run at (T=20).

    An earlier revision of the study README labelled this table T = 5. It is
    T = 20; at T = 5 the same code gives +62.76, +16.10, +4.13. Slow because
    each point is a full tangent integration.
    """

    @pytest.mark.parametrize("N,expected", [(50, 86.24), (100, 172.02)])
    def test_entry(self, N, expected):
        lam = tangent_lyapunov(Stage6Config(N=N, **BASE), T_target=20.0)["lambda"]
        assert abs(lam - expected) < 0.05 * expected, (
            "N=%d: expected ~%.2f at T=20, got %.3f" % (N, expected, lam))
