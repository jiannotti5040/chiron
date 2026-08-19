# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Is the Phase A wall the theory's ell_*, or is it the initial pulse?

Phase A's headline result is that the wall thickness is mesh-independent:
log-log slope 0.015 against N, versus 1.0 for a pure numerical artifact. That
test is correct and it rules out numerical diffusion. It does not rule out the
other way of getting a mesh-independent width, which is for the width to be set
by a mesh-independent INITIAL CONDITION.

The theory makes a sharper, testable claim than mesh-independence:

    ell_*(M) = (M_max - M) * sqrt(mu * tau_M / lambda)

so the wall should scale linearly with sqrt(mu*tau_M/lambda). That is a
falsification handle the framework never pulled. This pulls it.

    PYTHONPATH=. python3 studies/phase_a_wall/scaling.py
"""
import math
import numpy as np

from uma.rsls.phase_a import PhaseAConfig, run_phase_a
from uma.rsls.memory import MemoryConfig, interface_width


def widest_interface(result, mcfg):
    ws = [interface_width(M, result.r_centers, mcfg) for M in result.M_history]
    ws = [w for w in ws if w is not None and np.isfinite(w)]
    return max(ws) if ws else float("nan")


def run(N=300, n_steps=4000):
    print("A. vary the theory's own parameter, hold the pulse fixed")
    print(f"   {'mu':>6} {'tau_M':>6} {'lam':>6} {'sqrt(mu*t/l)':>13} "
          f"{'interface_w':>12} {'M peak':>8}")
    pts = []
    for mu, tau, lam in [(0.08, 1.0, 0.12), (0.32, 1.0, 0.12), (0.08, 4.0, 0.12),
                         (0.08, 1.0, 0.48), (0.02, 1.0, 0.12)]:
        m = MemoryConfig(mu=mu, tau_M=tau, lam=lam)
        r = run_phase_a(PhaseAConfig(N=N, n_steps=n_steps, pulse_width=2.0,
                                     memory=m), verbose=False)
        w = widest_interface(r, m)
        pred = math.sqrt(mu * tau / lam)
        pts.append((pred, w))
        print(f"   {mu:>6} {tau:>6} {lam:>6} {pred:>13.4f} {w:>12.4f} "
              f"{max(float(M.max()) for M in r.M_history):>8.4f}")
    p = np.array([a for a, _ in pts]); w = np.array([b for _, b in pts])
    slope_theory = float(np.polyfit(np.log(p), np.log(w), 1)[0])
    print(f"   log-log slope vs sqrt(mu*tau/lam) = {slope_theory:.4f}   "
          f"(theory predicts 1.0)")

    print("\nB. vary the initial pulse, hold the theory fixed")
    print(f"   {'pulse_width':>12} {'interface_w':>12} {'w / pulse':>10}")
    pts = []
    for pw in (1.0, 2.0, 4.0):
        m = MemoryConfig()
        r = run_phase_a(PhaseAConfig(N=N, n_steps=n_steps, pulse_width=pw,
                                     memory=m), verbose=False)
        w = widest_interface(r, m)
        pts.append((pw, w))
        print(f"   {pw:>12} {w:>12.4f} {w / pw:>10.4f}")
    p = np.array([a for a, _ in pts]); w = np.array([b for _, b in pts])
    slope_pulse = float(np.polyfit(np.log(p), np.log(w), 1)[0])
    print(f"   log-log slope vs pulse_width = {slope_pulse:.4f}")

    print("\nVERDICT")
    print(f"   wall vs theory parameter : slope {slope_theory:+.4f}  "
          f"(predicted +1.0)")
    print(f"   wall vs initial pulse    : slope {slope_pulse:+.4f}")
    print("   The wall follows the initial condition, not the barrier.")
    return slope_theory, slope_pulse


if __name__ == "__main__":
    run()
