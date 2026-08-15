"""What are the x1000 single-step separation jumps?

Suspicion: the map is piecewise-smooth, not smooth. clip_M pins M at M_max and
the density floor pins D, and both are applied with np.maximum/np.clip. When a
cell is clipped for one twin but not the other, the difference gets a finite
kink -- the derivative does not exist there, and Benettin's algorithm silently
measures the kink instead of a tangent growth rate.

Test: correlate the big growth steps with clipping activity, and count how
much of the domain is sitting on a constraint.
"""
import numpy as np
from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step

D_FLOOR = 0.1
cfg = Stage6Config(N=100, n_steps=1, Omega_0=1.5, enable_self_consistency=False)
m = cfg.memory
N = cfg.N
Rf = np.linspace(cfg.R_in, cfg.R_out, N + 1)
Rc = 0.5 * (Rf[:-1] + Rf[1:])
dR = (cfg.R_out - cfg.R_in) / N
bp = kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
print(f"M_max = {m.M_max}   D_floor = {D_FLOOR}")


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


def clip_counts(st):
    D, S, P, M, J, b = st
    return int((M >= m.M_max - 1e-15).sum()), int((D <= D_FLOOR + 1e-15).sum())


a = init()
for k in range(2000):
    a = step(a, dt_of(a))
b = [x.copy() for x in a]
d0 = 1e-9
b[1][cfg.perturb_cell] += d0
flat = lambda s: np.concatenate(s)


def unflat(v):
    return [np.maximum(v[:N], D_FLOOR), v[N:2*N], v[2*N:3*N],
            clip_M(v[3*N:4*N], m), v[4*N:5*N], v[5*N:6*N]]


sep = flat(b) - flat(a)
b = unflat(flat(a) + sep / np.linalg.norm(sep) * d0)

rows = []
for k in range(20000):
    dt = dt_of(a)
    mA, dA = clip_counts(a)
    mB, dB = clip_counts(b)
    a = step(a, dt)
    b = step(b, dt)
    sep = flat(b) - flat(a)
    sn = np.linalg.norm(sep)
    g = sn / d0
    # cells where the two twins disagree about being clipped
    disagree_M = int(((a[3] >= m.M_max - 1e-15) != (b[3] >= m.M_max - 1e-15)).sum())
    disagree_D = int(((a[0] <= D_FLOOR + 1e-15) != (b[0] <= D_FLOOR + 1e-15)).sum())
    rows.append((k, g, mA, dA, disagree_M, disagree_D))
    b = unflat(flat(a) + sep / sn * d0)

rows = np.array(rows, dtype=float)
g = rows[:, 1]
print(f"\nsteps={len(g)}  median growth={np.median(g):.6f}  max={g.max():.1f}")
print(f"M pinned at M_max: median {np.median(rows[:,2]):.0f}/{N} cells")
print(f"D pinned at floor: median {np.median(rows[:,3]):.0f}/{N} cells")

big = g > 2.0
print(f"\nsteps with growth > 2      : {int(big.sum())} of {len(g)}")
print(f"  of those, twins DISAGREE about an M-clip in: "
      f"{int((rows[big,4] > 0).sum())}")
print(f"  of those, twins DISAGREE about a  D-clip in: "
      f"{int((rows[big,5] > 0).sum())}")
quiet = ~big
print(f"steps with growth <= 2     : {int(quiet.sum())}")
print(f"  twins disagree about an M-clip in: {int((rows[quiet,4] > 0).sum())}")

print(f"\ncontribution of the growth>2 steps to sum(log g): "
      f"{np.log(g[big]).sum():.2f} of {np.log(g).sum():.2f} "
      f"({100*np.log(g[big]).sum()/np.log(g).sum():.1f}%)")
print(f"lambda from the quiet steps only would be far smaller.")
print("\nTop 5 growth steps and their clip disagreements:")
idx = np.argsort(-g)[:5]
print(f"  {'step':>7} {'growth':>12} {'M-disagree':>11} {'D-disagree':>11}")
for i in idx:
    print(f"  {int(rows[i,0]):>7} {g[i]:>12.2f} {int(rows[i,4]):>11} {int(rows[i,5]):>11}")
