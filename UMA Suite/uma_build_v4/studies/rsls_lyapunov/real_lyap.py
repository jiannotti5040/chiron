"""A genuine Benettin Lyapunov measurement for the RSLS kernel.

Three defects fixed relative to the shipped estimators:
  1. dt was computed once from the initial state. Velocities grow, CFL is
     violated by ~550x around step 8000, and the "growth" measured after that
     is the numerical instability. dt is now recomputed every step from the
     REFERENCE trajectory and applied to both twins.
  2. Without a density floor D collapses to ~1e-6, v = S/D reaches 4e5, dt
     collapses to 1e-7 and the integration stalls at t = 3.34 -- a finite-time
     vacuum, not an attractor. A floor (standard atmosphere treatment) keeps
     the run healthy to t = 11+.
  3. Renormalisation every 25 steps let the separation grow x87 in one block,
     far outside the linear regime, so the statistic measured shock formation.
     Renormalising every step keeps the perturbation tangent.

Then the two checks that decide whether the answer is real: does the running
value plateau, and is it independent of the perturbation size.
"""
import numpy as np
from uma.rsls.stage6 import (Stage6Config, off_diagonal_stress,
                             equilibrium_beta_phi, beta_phi_causal_step)
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step

D_FLOOR = 0.1


def measure(cfg, n_steps=40000, delta0=1e-9, renorm=1, burn=2000,
            coupled=False, drag=True, track=False):
    m = cfg.memory
    Rf = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
    Rc = 0.5 * (Rf[:-1] + Rf[1:])
    dR = (cfg.R_out - cfg.R_in) / cfg.N
    N = cfg.N
    bp0 = (kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
           if drag else np.zeros(N))

    def init():
        D = np.ones(N) * cfg.D_background
        S = cfg.pulse_amp * np.exp(-((Rc - cfg.pulse_center) / cfg.pulse_width) ** 2)
        M = clip_M(cfg.M_saturation_layer_amp * np.exp(
            -((Rc - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2), m)
        return [D, S, np.zeros(N), M, np.zeros(N), bp0.copy()]

    def step(st, dt, k):
        D, S, P, M, J, bp = st
        D = np.maximum(D, D_FLOOR)
        M = clip_M(M, m)
        D, S, P = cylindrical_hll_step(D, S, P, M, bp, Rf, Rc, dt, m)
        D = np.maximum(D, D_FLOOR)
        v = S / D
        M = clip_M(M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v, dR)), m)
        J = cattaneo_step(J, M, dR, dt, m)
        if coupled and k >= cfg.beta_phi_freeze_steps:
            T = off_diagonal_stress(D, S, P)
            beq = equilibrium_beta_phi(T, Rc, cfg.kappa_drag)
            bp = beta_phi_causal_step(bp, 0.5 * beq + 0.5 * bp0, dR, dt,
                                      cfg.tau_beta, cfg.mu_beta)
            bp = np.clip(bp, -3 * cfg.Omega_0, 3 * cfg.Omega_0)
        return [D, S, P, M, J, bp]

    def dt_of(st):
        return min(transport_cfl(st[1] / np.maximum(st[0], D_FLOOR), dR, m,
                                 safety=cfg.cfl_safety),
                   cattaneo_cfl(dR, m, safety=cfg.cfl_safety), 0.005 * dR)

    a = init()
    for k in range(burn):
        a = step(a, dt_of(a), k)
    b = [x.copy() for x in a]
    b[1][cfg.perturb_cell] += delta0

    def flat(st):
        return np.concatenate(st)

    def unflat(v):
        return [np.maximum(v[:N], D_FLOOR), v[N:2*N], v[2*N:3*N],
                clip_M(v[3*N:4*N], m), v[4*N:5*N], v[5*N:6*N]]

    sep = flat(b) - flat(a)
    sn = np.linalg.norm(sep)
    b = unflat(flat(a) + sep / sn * delta0)

    log_sum, T = 0.0, 0.0
    curve, growths = [], []
    for k in range(n_steps):
        dt = dt_of(a)                      # same dt for both twins
        a = step(a, dt, burn + k)
        b = step(b, dt, burn + k)
        T += dt
        if (k + 1) % renorm == 0:
            sep = flat(b) - flat(a)
            sn = np.linalg.norm(sep)
            if sn > 1e-300:
                growths.append(sn / delta0)
                log_sum += np.log(sn / delta0)
                b = unflat(flat(a) + sep / sn * delta0)
            if track and (k + 1) % 2000 == 0:
                curve.append((T, log_sum / T if T > 0 else np.nan))
    g = np.array(growths)
    return (log_sum / T if T > 0 else np.nan), T, g, curve


BASE = dict(N=100, n_steps=1, Omega_0=1.5)
cfg = Stage6Config(**BASE, enable_self_consistency=False)

print("=" * 76)
print("A. Convergence -- does the running value plateau? (Stage 5, drag on)")
lam, T, g, curve = measure(cfg, n_steps=40000, renorm=1, track=True)
print(f"  {'t':>9} {'running lambda':>16}")
for t, L in curve[::2]:
    print(f"  {t:>9.3f} {L:>16.6f}")
print(f"  FINAL lambda = {lam:+.6f}   over t = {T:.3f}")
print(f"  per-step growth: min {g.min():.6f} max {g.max():.6f} "
      f"median {np.median(g):.6f}   (linear regime wants these near 1)")

print()
print("=" * 76)
print("B. Window independence")
print(f"  {'n_steps':>9} {'lambda':>12} {'t':>9}")
for ns in (10000, 20000, 40000, 80000):
    L, T, _, _ = measure(cfg, n_steps=ns, renorm=1)
    print(f"  {ns:>9} {L:>+12.6f} {T:>9.3f}")

print()
print("=" * 76)
print("C. Perturbation-size independence")
print(f"  {'delta':>10} {'lambda':>12}")
for d in (1e-7, 1e-9, 1e-11, 1e-13):
    L, _, _, _ = measure(cfg, n_steps=40000, delta0=d, renorm=1)
    print(f"  {d:>10.0e} {L:>+12.6f}")

print()
print("=" * 76)
print("D. The physics question: drag on vs off vs fully coupled")
for lbl, kw in (("drag ON  (Stage 5)", dict(drag=True, coupled=False)),
                ("drag OFF (control)", dict(drag=False, coupled=False)),
                ("coupled  (Stage 6)", dict(drag=True, coupled=True))):
    c = Stage6Config(**BASE, enable_self_consistency=kw["coupled"])
    L, T, g, _ = measure(c, n_steps=40000, renorm=1, **kw)
    print(f"  {lbl:<20} lambda = {L:+.6f}   (t={T:.2f}, "
          f"median step growth {np.median(g):.6f})")
