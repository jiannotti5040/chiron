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


class TestWhyTheWallDoesNotTrackTheory:
    """The mechanism behind the scaling result, pinned as behaviour.

    ell_* = sqrt(mu * tau_M / V''(M)) is the length where diffusion balances
    the barrier's curvature -- the steady state of d_t M = mu grad^2 M - V'(M).
    The kernel integrates d_t M = -div J - 0.5 div v with tau_J d_t J + J =
    -mu grad M, which has no -V'(M) term. V_prime is defined, imported, and
    never called; clip_M (a hard np.clip) is what holds M below M_max.

    The barrier is NOT absent from the model -- it is the effective pressure in
    the momentum flux, V(M) in d_t(R S_R) + d_R(R[S_R v_R + V(M)]) = 0. So
    lambda does perturb the solution. It just does not set the interface width.
    """

    def test_lambda_does_perturb_the_solution(self):
        """Via the momentum pressure -- so 'the barrier does nothing' is wrong."""
        import numpy as np
        outs = {}
        for lam in (0.12, 0.48):
            m = MemoryConfig(lam=lam)
            r = run_phase_a(PhaseAConfig(N=150, n_steps=2000, pulse_width=2.0,
                                         memory=m), verbose=False)
            outs[lam] = r.M_history[-1].copy()
        delta = float(np.max(np.abs(outs[0.48] - outs[0.12])))
        assert delta > 1e-3, (
            "lambda appears to have no effect at all (max|dM| = %.2e). It "
            "should act through the barrier pressure V(M) in the momentum "
            "flux." % delta)

    def test_the_relaxed_interface_is_grid_scale(self):
        """The published mesh-independence measured the widest (initial)
        interface. The relaxed one holds a fixed CELL count, not a length."""
        import numpy as np
        cells = []
        for N in (100, 200):
            m = MemoryConfig()
            cfg = PhaseAConfig(N=N, n_steps=4000, pulse_width=2.0, memory=m)
            r = run_phase_a(cfg, verbose=False)
            dR = (cfg.R_out - cfg.R_in) / N
            ws = [interface_width(M, r.r_centers, m) for M in r.M_history]
            ws = [w for w in ws if w is not None and np.isfinite(w)]
            cells.append(ws[-1] / dR)
        assert all(c < 8.0 for c in cells), (
            "the relaxed interface should sit within a few cells; got %r"
            % cells)
        assert abs(cells[1] - cells[0]) / cells[0] < 1.0, (
            "cell count should be roughly resolution-independent (that is the "
            "defect); got %r" % cells)


class TestBarrierForceDoesNotRescueTheScaling:
    """PhaseAConfig.barrier_force supplies the absent -V'(M). It is not enough.

    Measured: the transient wall's slope against lambda moves from +0.000 to
    -0.075 (theory -0.5), and the RELAXED wall stays at 2.0-2.3 cells for every
    (mu, lambda) tested while ell_* ranges over 9-46 cells. The interface is
    compression-controlled and mesh-limited, not diffusion-controlled.
    """

    def test_default_is_off_so_published_numbers_are_unchanged(self):
        assert PhaseAConfig().barrier_force is False

    def test_the_force_does_couple_lambda_to_the_wall(self):
        import numpy as np
        widths = []
        for lam in (0.03, 1.92):
            m = MemoryConfig(lam=lam)
            r = run_phase_a(PhaseAConfig(N=200, n_steps=3000, pulse_width=2.0,
                                         memory=m, barrier_force=True),
                            verbose=False)
            ws = [interface_width(M, r.r_centers, m) for M in r.M_history]
            ws = [w for w in ws if w is not None and np.isfinite(w)]
            widths.append(max(ws))
        assert widths[1] < widths[0], (
            "with the barrier force on, a larger lambda should give a thinner "
            "wall; got %r" % widths)

    def test_but_the_relaxed_wall_stays_at_the_grid_floor(self):
        """The negative result, pinned: ell_* is resolvable and still ignored."""
        import numpy as np
        N = 200
        dR = 14.0 / N
        cells = []
        for lam in (0.03, 0.48):
            m = MemoryConfig(lam=lam)
            r = run_phase_a(PhaseAConfig(N=N, n_steps=4000, pulse_width=2.0,
                                         memory=m, barrier_force=True),
                            verbose=False)
            ws = [interface_width(M, r.r_centers, m) for M in r.M_history]
            ws = [w for w in ws if w is not None and np.isfinite(w)]
            cells.append(ws[-1] / dR)
        assert all(c < 8.0 for c in cells), (
            "the relaxed wall is expected to sit at the grid floor even with "
            "the barrier force on; got %r cells. If this has become resolved, "
            "the emergent-length claim is worth re-testing." % cells)
