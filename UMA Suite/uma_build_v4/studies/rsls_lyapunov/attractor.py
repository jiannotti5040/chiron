# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""What does the RSLS kernel actually settle onto?

Measuring the Lyapunov exponent directly failed for a reason that is now
understood: the growth concentrates at moving shocks, so the statistic does
not converge in time and does not converge under grid refinement.

This asks the prior question instead, which is not contaminated by shocks:
what kind of attractor is this? A trajectory that settles to a FIXED POINT
cannot be chaotic at all -- lambda_max <= 0 follows with no exponent estimate
needed. A limit cycle gives lambda_max = 0. Only a trajectory that keeps
exploring can be chaotic.

Diagnostics, all on the reference trajectory alone (no twin, no perturbation):
  * ||d(state)/dt|| -- does the motion die out?
  * recurrence ||x(t) - x(t - tau)|| -- does it return to where it was?
  * the spread of a late-time observable

Requires the density floor and adaptive dt from the same directory, without
which the run either blows up (CFL) or stalls in a vacuum at t ~ 3.34.
"""
import numpy as np

from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step

D_FLOOR = 0.1


def evolve(cfg, T_target, drag=True, samples=40):
    m = cfg.memory
    N = cfg.N
    Rf = np.linspace(cfg.R_in, cfg.R_out, N + 1)
    Rc = 0.5 * (Rf[:-1] + Rf[1:])
    dR = (cfg.R_out - cfg.R_in) / N
    bp = (kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
          if drag else np.zeros(N))
    D = np.ones(N) * cfg.D_background
    S = cfg.pulse_amp * np.exp(-((Rc - cfg.pulse_center) / cfg.pulse_width) ** 2)
    P = np.zeros(N)
    M = clip_M(cfg.M_saturation_layer_amp * np.exp(
        -((Rc - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2), m)
    J = np.zeros(N)

    t = 0.0
    hist_t, hist_rate, snaps = [], [], []
    next_sample = 0.0
    prev = np.concatenate([D, S, P, M, J])
    while t < T_target:
        D = np.maximum(D, D_FLOOR)
        v = S / D
        dt = min(transport_cfl(v, dR, m, safety=cfg.cfl_safety),
                 cattaneo_cfl(dR, m, safety=cfg.cfl_safety), 0.005 * dR)
        M = clip_M(M, m)
        D, S, P = cylindrical_hll_step(D, S, P, M, bp, Rf, Rc, dt, m)
        D = np.maximum(D, D_FLOOR)
        v = S / D
        M = clip_M(M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v, dR)), m)
        J = cattaneo_step(J, M, dR, dt, m)
        t += dt
        cur = np.concatenate([D, S, P, M, J])
        rate = np.linalg.norm(cur - prev) / dt
        prev = cur
        if t >= next_sample:
            hist_t.append(t)
            hist_rate.append(rate)
            snaps.append(cur.copy())
            next_sample += T_target / samples
    return np.array(hist_t), np.array(hist_rate), np.array(snaps)


def report(label, cfg, T, drag):
    t, rate, snaps = evolve(cfg, T, drag=drag)
    print(f"\n=== {label}  (T={T})")
    print(f"  {'t':>8} {'||dx/dt||':>13}")
    for i in range(0, len(t), max(1, len(t) // 8)):
        print(f"  {t[i]:>8.2f} {rate[i]:>13.4e}")
    first, last = rate[len(rate) // 10], rate[-1]
    print(f"  motion early -> late : {first:.4e} -> {last:.4e}"
          f"   ratio {last / max(first, 1e-300):.3e}")
    # recurrence over the last half
    half = len(snaps) // 2
    late = snaps[half:]
    d = [np.linalg.norm(late[i] - late[-1]) for i in range(len(late))]
    print(f"  distance to final state over the late half: "
          f"{d[0]:.4e} -> {d[len(d)//2]:.4e} -> {d[-1]:.4e}")
    spread = np.std([np.linalg.norm(s) for s in late])
    print(f"  std of ||state|| over the late half        : {spread:.4e}")
    if last < 1e-8 * max(first, 1e-300) or last < 1e-10:
        print("  VERDICT: motion has died out -- this is a FIXED POINT.")
        print("           A fixed point cannot be chaotic: lambda_max <= 0,")
        print("           with no exponent estimate required.")
    elif spread < 1e-6:
        print("  VERDICT: ||state|| is constant to 1e-6 while motion persists")
        print("           -- consistent with a limit cycle (lambda_max = 0).")
    else:
        print("  VERDICT: still exploring; attractor type not settled here.")


if __name__ == "__main__":
    base = dict(N=100, n_steps=1, Omega_0=1.5, enable_self_consistency=False)
    for T in (11.0, 40.0):
        report(f"drag ON", Stage6Config(**base), T, True)
    report("drag OFF (control)", Stage6Config(**base), 40.0, False)
