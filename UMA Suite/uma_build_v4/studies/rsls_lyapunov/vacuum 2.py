"""Is the integration stalling because the density collapses to vacuum?

If min(D) -> 0 then v = S/D diverges by construction, the CFL timestep goes to
zero, and the trajectory reaches a coordinate singularity in finite time. A
Lyapunov exponent needs a trajectory that lives on a bounded attractor for a
long time; a finite-time vacuum means no such trajectory exists and no amount
of estimator care produces an exponent.

Also tests whether a physical density floor lets the run continue.
"""
import numpy as np
from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step


def run(cfg, n_steps, floor=None, report=None):
    m = cfg.memory
    Rf = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
    Rc = 0.5 * (Rf[:-1] + Rf[1:])
    dR = (cfg.R_out - cfg.R_in) / cfg.N
    bp = kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
    D = np.ones(cfg.N) * cfg.D_background
    S = cfg.pulse_amp * np.exp(-((Rc - cfg.pulse_center) / cfg.pulse_width) ** 2)
    P = np.zeros(cfg.N)
    M = clip_M(cfg.M_saturation_layer_amp * np.exp(
        -((Rc - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2), m)
    J = np.zeros(cfg.N)
    t = 0.0
    report = report or (n_steps // 5)
    print(f"  {'step':>7} {'t':>9} {'dt':>10} {'min D':>12} {'max|v|':>11} {'max M':>7}")
    for k in range(n_steps + 1):
        if floor is not None:
            D = np.maximum(D, floor)
        if k % report == 0:
            v = S / np.maximum(D, 1e-12)
            print(f"  {k:>7} {t:>9.3f} {0.0 if k==0 else dt:>10.3e} {D.min():>12.4e} "
                  f"{np.abs(v).max():>11.3e} {M.max():>7.4f}")
        v = S / np.maximum(D, 1e-12)
        dt = min(transport_cfl(v, dR, m, safety=cfg.cfl_safety),
                 cattaneo_cfl(dR, m, safety=cfg.cfl_safety), 0.005 * dR)
        M = clip_M(M, m)
        D, S, P = cylindrical_hll_step(D, S, P, M, bp, Rf, Rc, dt, m)
        v = S / np.maximum(D, 1e-12)
        M = clip_M(M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v, dR)), m)
        J = cattaneo_step(J, M, dR, dt, m)
        t += dt
        if not np.all(np.isfinite(S)):
            print(f"  NON-FINITE at step {k}")
            return t
    return t


cfg = Stage6Config(N=100, n_steps=1, Omega_0=1.5, enable_self_consistency=False)
print("=" * 72)
print("A. adaptive dt, no floor -- watch min(D)")
t = run(cfg, 20000)
print(f"  reached t = {t:.4f}")

for fl in (1e-3, 1e-2, 1e-1):
    print()
    print("=" * 72)
    print(f"B. adaptive dt WITH density floor D >= {fl}")
    t = run(cfg, 20000, floor=fl)
    print(f"  reached t = {t:.4f}")
