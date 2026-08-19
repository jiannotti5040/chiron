# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""The Phase A wall does not scale with the theory's own length parameter.

Phase A's published result is mesh-independence (log-log slope 0.015 vs N,
against 1.0 for a numerical artifact). That correctly rules out numerical
diffusion. It does not rule out the other route to a mesh-independent width:
one set by a mesh-independent INITIAL CONDITION.

The theory predicts ell_*(M) = (M_max - M) * sqrt(mu * tau_M / lambda), so the
wall should scale linearly with sqrt(mu*tau_M/lambda). It does not scale with
it at all -- it tracks the initial pulse width instead. These gates pin that
so the finding cannot silently reverse, in either direction: if the wall ever
DOES start tracking the theory parameter, the last assertion fails and the
result is worth revisiting.

Full record: studies/phase_a_wall/README.md
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from uma.rsls.phase_a import PhaseAConfig, run_phase_a
from uma.rsls.memory import MemoryConfig, interface_width


def _widest(result, mcfg):
    ws = [interface_width(M, result.r_centers, mcfg) for M in result.M_history]
    ws = [w for w in ws if w is not None and np.isfinite(w)]
    assert ws, "no interface measured at all"
    return max(ws)


def _wall(mu=0.08, tau=1.0, lam=0.12, pulse=2.0, N=200, n_steps=3000):
    m = MemoryConfig(mu=mu, tau_M=tau, lam=lam)
    r = run_phase_a(PhaseAConfig(N=N, n_steps=n_steps, pulse_width=pulse,
                                 memory=m), verbose=False)
    return _widest(r, m), max(float(M.max()) for M in r.M_history)


class TestPhaseAWallScaling:
    def test_saturation_is_actually_reached(self):
        """Otherwise the parameter test would be measuring an unsaturated run."""
        _, peak = _wall()
        assert peak > 0.99, "M did not saturate (peak %.4f)" % peak

    def test_wall_does_not_track_the_theory_parameter(self):
        """lambda x4 changes sqrt(mu*tau/lam) by 2x and the wall not at all."""
        a, _ = _wall(lam=0.12)
        b, _ = _wall(lam=0.48)
        assert abs(a - b) / a < 0.02, (
            "the wall now moves with lambda (%0.4f -> %0.4f). If that is real, "
            "the singular-barrier mechanism may be operating after all -- "
            "re-run studies/phase_a_wall/scaling.py before trusting it."
            % (a, b))

    def test_wall_tracks_the_initial_pulse(self):
        """Doubling the pulse doubles the wall: slope ~1 in log-log.

        Needs N = 300 rather than the 200 the other gates use. At N = 200 the
        narrow pulse=1.0 wall spans only ~7 cells and measures 0.5091 against a
        converged 0.4372, which drags the slope down to 0.77 -- an under-
        resolution artifact in the control, not a change in the result.
        """
        w1, _ = _wall(pulse=1.0, N=300, n_steps=4000)
        w2, _ = _wall(pulse=2.0, N=300, n_steps=4000)
        slope = math.log(w2 / w1) / math.log(2.0)
        assert slope > 0.9, (
            "expected the wall to follow the initial pulse (slope ~1), got %.3f"
            % slope)

    def test_the_two_observables_agree(self):
        """Not an artifact of which width measurement is used."""
        m = MemoryConfig()
        r = run_phase_a(PhaseAConfig(N=200, n_steps=3000, pulse_width=2.0,
                                     memory=m), verbose=False)
        canonical = _widest(r, m)
        threshold = r.wall_thickness_max
        assert threshold is not None
        assert abs(canonical - threshold) / canonical < 0.05, (
            "canonical %0.4f vs threshold %0.4f" % (canonical, threshold))
