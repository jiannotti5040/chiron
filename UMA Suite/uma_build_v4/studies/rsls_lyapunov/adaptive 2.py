"""Does recomputing dt each step keep the RSLS solution bounded?

If yes, a long-time integration exists and a genuine Lyapunov measurement
becomes possible. If it still blows up, the growth is in the model, not the
timestep, and no amount of estimator care will produce an exponent.
"""
import numpy as np
from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step


def run(cfg, n_steps, adaptive, cap=None, report_every=4000):
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

    def dt_of(S, D):
        v = S / np.maximum(D, 1e-12)
        d = min(transport_cfl(v, dR, m, safety=cfg.cfl_safety),
                cattaneo_cfl(dR, m, safety=cfg.cfl_safety), 0.005 * dR)
        return d if cap is None else min(d, cap)

    dt0 = dt_of(S, D)
    t = 0.0
    print(f"  {'step':>7} {'t':>10} {'dt':>11} {'max|v|':>12} {'max|S|':>12}")
    for k in range(n_steps + 1):
        if k % report_every == 0:
            v = S / np.maximum(D, 1e-12)
            print(f"  {k:>7} {t:>10.3f} {(dt_of(S,D) if adaptive else dt0):>11.3e} "
                  f"{np.abs(v).max():>12.4e} {np.abs(S).max():>12.4e}")
        dt = dt_of(S, D) if adaptive else dt0
        M = clip_M(M, m)
        D, S, P = cylindrical_hll_step(D, S, P, M, bp, Rf, Rc, dt, m)
        v = S / np.maximum(D, 1e-12)
        M = clip_M(M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v, dR)), m)
        J = cattaneo_step(J, M, dR, dt, m)
        t += dt
        if not np.all(np.isfinite(S)) or np.abs(S).max() > 1e12:
            print(f"  DIVERGED at step {k}, t={t:.4f}")
            return False, t
    return True, t


cfg = Stage6Config(N=100, n_steps=1, Omega_0=1.5, enable_self_consistency=False)
print("=" * 70)
print("FIXED dt (as shipped), 20000 steps")
ok, t = run(cfg, 20000, adaptive=False)
print(f"  bounded: {ok}   final t={t:.3f}")

print()
print("=" * 70)
print("ADAPTIVE dt, 20000 steps")
ok, t = run(cfg, 20000, adaptive=True)
print(f"  bounded: {ok}   final t={t:.3f}")

print()
print("=" * 70)
print("ADAPTIVE dt, 100000 steps -- is it bounded for a long time?")
ok, t = run(cfg, 100000, adaptive=True, report_every=20000)
print(f"  bounded: {ok}   final t={t:.3f}")
