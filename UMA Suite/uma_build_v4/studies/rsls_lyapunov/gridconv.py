"""Grid convergence at EQUAL PHYSICAL TIME.

The previous sweep compared equal step counts, but dt scales with dR, so
finer grids covered less physical time -- and lambda drifts with time, so the
comparison was confounded. Integrate every resolution to the same T.
"""
import numpy as np
from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step

D_FLOOR = 0.1


def measure(N, T_target, d0=1e-9, T_burn=1.0, drag=True):
    cfg = Stage6Config(N=N, Omega_0=1.5, n_steps=1,
                       enable_self_consistency=False,
                       perturb_cell=max(1, min(20, N // 5)))
    m = cfg.memory
    Rf = np.linspace(cfg.R_in, cfg.R_out, N + 1)
    Rc = 0.5 * (Rf[:-1] + Rf[1:])
    dR = (cfg.R_out - cfg.R_in) / N
    bp = (kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
          if drag else np.zeros(N))

    def step(st, dt):
        D, S, P, M, J, b = st
        D = np.maximum(D, D_FLOOR)
        M = clip_M(M, m)
        D, S, P = cylindrical_hll_step(D, S, P, M, b, Rf, Rc, dt, m)
        D = np.maximum(D, D_FLOOR)
        v = S / D
        M = clip_M(M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v, dR)), m)
        J = cattaneo_step(J, M, dR, dt, m)
        return [D, S, P, M, J, b]

    def dt_of(st):
        return min(transport_cfl(st[1] / np.maximum(st[0], D_FLOOR), dR, m,
                                 safety=cfg.cfl_safety),
                   cattaneo_cfl(dR, m, safety=cfg.cfl_safety), 0.005 * dR)

    D = np.ones(N) * cfg.D_background
    S = cfg.pulse_amp * np.exp(-((Rc - cfg.pulse_center) / cfg.pulse_width) ** 2)
    M = clip_M(cfg.M_saturation_layer_amp * np.exp(
        -((Rc - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2), m)
    a = [D, S, np.zeros(N), M, np.zeros(N), bp.copy()]
    t = 0.0
    while t < T_burn:
        dt = dt_of(a); a = step(a, dt); t += dt
    b = [x.copy() for x in a]
    b[1][cfg.perturb_cell] += d0
    flat = lambda s: np.concatenate(s)

    def unflat(v):
        return [np.maximum(v[:N], D_FLOOR), v[N:2*N], v[2*N:3*N],
                clip_M(v[3*N:4*N], m), v[4*N:5*N], v[5*N:6*N]]

    sep = flat(b) - flat(a)
    b = unflat(flat(a) + sep / np.linalg.norm(sep) * d0)
    log_sum, T, nb, nstep = 0.0, 0.0, 0, 0
    while T < T_target:
        dt = dt_of(a)
        a = step(a, dt); b = step(b, dt); T += dt; nstep += 1
        sep = flat(b) - flat(a); sn = np.linalg.norm(sep)
        g = sn / d0
        if g > 2:
            nb += 1
        log_sum += np.log(g)
        b = unflat(flat(a) + sep / sn * d0)
    return log_sum / T, nstep, nb / nstep


for T_target in (5.0, 10.0):
    print("=" * 72)
    print(f"Equal physical time T = {T_target}")
    print(f"  {'N':>5} {'steps':>8} {'lambda':>12} {'burst frac':>11}")
    for N in (50, 100, 200, 400):
        lam, ns, bf = measure(N, T_target)
        print(f"  {N:>5} {ns:>8} {lam:>+12.4f} {bf:>11.5f}")
    print()

print("=" * 72)
print("drag OFF control, T = 10")
print(f"  {'N':>5} {'lambda':>12}")
for N in (100, 200):
    lam, ns, bf = measure(N, 10.0, drag=False)
    print(f"  {N:>5} {lam:>+12.4f}")
