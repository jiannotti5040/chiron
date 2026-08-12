"""Are the bursts shock events, and is there a smooth regime where the
Lyapunov exponent is actually well defined?

Two probes:
  A. localisation -- after a burst, does the separation live in one or two
     cells (an interface event) or spread across the domain (real chaos)?
  B. amplitude sweep -- shrink the pulse until the flow stays smooth. In a
     smooth regime Benettin applies and lambda should converge cleanly. If it
     converges to ~0 there, the system is not chaotic and the bursts were
     shock artefacts; if it converges positive, that is genuine chaos.
"""
import numpy as np
from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step

D_FLOOR = 0.1


def build(cfg, drag=True):
    m = cfg.memory
    N = cfg.N
    Rf = np.linspace(cfg.R_in, cfg.R_out, N + 1)
    Rc = 0.5 * (Rf[:-1] + Rf[1:])
    dR = (cfg.R_out - cfg.R_in) / N
    bp = (kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
          if drag else np.zeros(N))

    def init():
        D = np.ones(N) * cfg.D_background
        S = cfg.pulse_amp * np.exp(-((Rc - cfg.pulse_center) / cfg.pulse_width) ** 2)
        M = clip_M(cfg.M_saturation_layer_amp * np.exp(
            -((Rc - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2), m)
        return [D, S, np.zeros(N), M, np.zeros(N), bp.copy()]

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
    return init, step, dt_of, N, dR


def run(cfg, n_steps=40000, d0=1e-9, burn=2000, drag=True, want_loc=False):
    init, step, dt_of, N, dR = build(cfg, drag)
    m = cfg.memory
    a = init()
    for _ in range(burn):
        a = step(a, dt_of(a))
    b = [x.copy() for x in a]
    b[1][cfg.perturb_cell] += d0
    flat = lambda s: np.concatenate(s)

    def unflat(v):
        return [np.maximum(v[:N], D_FLOOR), v[N:2*N], v[2*N:3*N],
                clip_M(v[3*N:4*N], m), v[4*N:5*N], v[5*N:6*N]]

    sep = flat(b) - flat(a)
    b = unflat(flat(a) + sep / np.linalg.norm(sep) * d0)
    logs, T, locs = [], 0.0, []
    smooth = []
    for k in range(n_steps):
        dt = dt_of(a)
        a = step(a, dt); b = step(b, dt); T += dt
        sep = flat(b) - flat(a); sn = np.linalg.norm(sep)
        g = sn / d0
        logs.append(np.log(g))
        if want_loc:
            # how concentrated is the separation? (participation ratio)
            w = (sep / sn) ** 2
            pr = 1.0 / np.sum(w ** 2)          # ~1 = one cell, ~6N = spread
            locs.append((g, pr))
            # smoothness proxy: largest |dS| between neighbouring cells
            smooth.append(np.abs(np.diff(a[1])).max() / max(np.abs(a[1]).max(), 1e-30))
        b = unflat(flat(a) + sep / sn * d0)
    return np.array(logs), T, np.array(locs), np.array(smooth)


BASE = dict(N=100, Omega_0=1.5, n_steps=1, enable_self_consistency=False)

print("=" * 76)
print("A. Where does the separation live during a burst?")
cfg = Stage6Config(**BASE)
logs, T, locs, smooth = run(cfg, n_steps=20000, want_loc=True)
g, pr = locs[:, 0], locs[:, 1]
big = g > 2
print(f"  participation ratio (1 = a single cell, 600 = fully spread)")
print(f"    burst steps (g>2, n={big.sum():>5}): median PR = {np.median(pr[big]):.2f}")
print(f"    quiet steps (g<=2, n={(~big).sum():>5}): median PR = {np.median(pr[~big]):.2f}")
print(f"  max |dS| between neighbours / max|S|: median {np.median(smooth):.4f}"
      f"  (a smooth field keeps this small; ~1 means a cell-scale jump = shock)")

print()
print("=" * 76)
print("B. Amplitude sweep -- shrink the pulse toward a smooth flow")
print(f"  {'pulse_amp':>10} {'lambda':>12} {'max nbr jump':>13} {'burst frac':>11}"
      f" {'top-step share':>15}")
for amp in (3e-1, 1e-1, 1e-2, 1e-3, 1e-4):
    c = Stage6Config(**BASE, pulse_amp=amp)
    logs, T, locs, smooth = run(c, n_steps=40000, want_loc=True)
    gg = locs[:, 0]
    lam = logs.sum() / T
    share = np.abs(logs).max() / np.abs(logs).sum()
    print(f"  {amp:>10.0e} {lam:>+12.6f} {np.median(smooth):>13.4f}"
          f" {np.mean(gg > 2):>11.4f} {share:>15.4f}")

print()
print("=" * 76)
print("C. In the smoothest regime, is lambda converged and delta-independent?")
c = Stage6Config(**BASE, pulse_amp=1e-4)
print(f"  {'n_steps':>9} {'lambda':>12}")
for ns in (10000, 20000, 40000, 80000):
    logs, T, _, _ = run(c, n_steps=ns)
    print(f"  {ns:>9} {logs.sum()/T:>+12.6f}")
print(f"  {'delta':>9} {'lambda':>12}")
for d in (1e-7, 1e-9, 1e-11):
    logs, T, _, _ = run(c, n_steps=40000, d0=d)
    print(f"  {d:>9.0e} {logs.sum()/T:>+12.6f}")
print()
print("  drag OFF control at the same amplitude:")
logs, T, _, _ = run(c, n_steps=40000, drag=False)
print(f"    lambda = {logs.sum()/T:+.6f}")
