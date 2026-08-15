# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Tangent-space Lyapunov exponent for the RSLS kernel, with a
differentiability audit.

Every previous attempt used two finite-difference twins. That fails here for a
reason now understood: the separation compounds over the renormalisation
interval, leaves the linear regime, and ends up measuring shock crossings
rather than a growth rate.

A tangent-space method removes that failure mode by construction. Instead of a
second trajectory it propagates the linearisation

    v_{n+1} = DF(x_n) . v_n

renormalising v to unit length EVERY step, so the perturbation is never
anything but infinitesimal. DF is applied matrix-free as a directional
derivative with a per-step epsilon chosen at the roundoff optimum, evaluated
freshly at the base point each time -- so no error compounds.

But a tangent method presupposes that DF EXISTS. This kernel is only
piecewise-smooth:

  * `np.maximum(D, floor)` and `clip_M` are non-differentiable wherever a cell
    sits exactly on its constraint;
  * the HLL flux selects `lambda_plus = max(0, lL, lR)` and
    `lambda_minus = min(0, lL, lR)`, so the flux formula switches branch
    whenever a wave speed changes sign.

So this module measures the exponent AND audits differentiability, by
comparing the active-constraint set and the wave-speed sign pattern between
the base point and the displaced point at every step. A step where they differ
has no derivative, and the "tangent" vector crossing it is meaningless.

The outcome is decisive either way:

  * few non-differentiable steps  -> the tangent lambda is a real measurement;
  * many                          -> the exponent is not merely hard to
                                     measure, it is NOT DEFINED for this map,
                                     and no estimator can fix that.

Validated against Lorenz with its analytic Jacobian before being trusted here.

Run:  PYTHONPATH=. python3.12 studies/rsls_lyapunov/tangent_lyapunov.py
"""
from __future__ import annotations

import numpy as np

from uma.rsls.stage6 import Stage6Config
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step

D_FLOOR = 0.1
MACH = np.finfo(float).eps


# ----------------------------------------------------------------- the map
class Kernel:
    """A floored, adaptive-dt copy of the Stage-5/6 step.

    Deliberately a COPY: fixing the shipped kernel's timestep and adding a
    density floor changes every published Stage-5/6 number, which is a
    modelling decision. Nothing here touches uma/rsls.
    """

    def __init__(self, cfg, drag=True):
        self.cfg = cfg
        self.m = cfg.memory
        self.N = cfg.N
        self.Rf = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
        self.Rc = 0.5 * (self.Rf[:-1] + self.Rf[1:])
        self.dR = (cfg.R_out - cfg.R_in) / cfg.N
        self.bp = (kerr_like_drag(self.Rc, cfg.R_in, cfg.Omega_0,
                                  cfg.drag_exponent) if drag
                   else np.zeros(cfg.N))

    def initial(self):
        c, N = self.cfg, self.N
        D = np.ones(N) * c.D_background
        S = c.pulse_amp * np.exp(-((self.Rc - c.pulse_center) / c.pulse_width) ** 2)
        M = clip_M(c.M_saturation_layer_amp * np.exp(
            -((self.Rc - c.M_saturation_layer_R0) / c.M_saturation_layer_width) ** 2),
            self.m)
        return np.concatenate([D, S, np.zeros(N), M, np.zeros(N)])

    def split(self, x):
        N = self.N
        return x[:N], x[N:2*N], x[2*N:3*N], x[3*N:4*N], x[4*N:5*N]

    def dt_of(self, x):
        D, S, _, _, _ = self.split(x)
        v = S / np.maximum(D, D_FLOOR)
        return min(transport_cfl(v, self.dR, self.m, safety=self.cfg.cfl_safety),
                   cattaneo_cfl(self.dR, self.m, safety=self.cfg.cfl_safety),
                   0.005 * self.dR)

    def step(self, x, dt):
        D, S, P, M, J = self.split(x)
        D = np.maximum(D, D_FLOOR)
        M = clip_M(M, self.m)
        D, S, P = cylindrical_hll_step(D, S, P, M, self.bp, self.Rf, self.Rc,
                                       dt, self.m)
        D = np.maximum(D, D_FLOOR)
        v = S / D
        M = clip_M(M + dt * (-np.gradient(J, self.dR)
                             - 0.5 * np.gradient(v, self.dR)), self.m)
        J = cattaneo_step(J, M, self.dR, dt, self.m)
        return np.concatenate([D, S, P, M, J])

    def regime(self, x):
        """The active-constraint set and wave-speed sign pattern.

        Two states with the same regime lie in the same smooth piece of the
        map; a difference means a clip toggled or an HLL branch switched, and
        the derivative between them does not exist.
        """
        D, S, P, M, J = self.split(x)
        at_floor = D <= D_FLOOR + 1e-15
        at_top = M >= self.m.M_max - 1e-15
        at_bot = M <= 1e-15
        v = S / np.maximum(D, D_FLOOR)
        c = self.m.c_eff
        lL = np.sign(v[:-1] - c)
        lR = np.sign(v[1:] + c)
        return (at_floor.tobytes() + at_top.tobytes() + at_bot.tobytes()
                + lL.tobytes() + lR.tobytes())


def jvp(kernel, x, v, dt, eps=None):
    """DF(x) . v, matrix-free, with the roundoff-optimal step.

    Returns (image, differentiable) -- the second flag is False when the
    displaced point falls in a different smooth piece of the map.
    """
    nx = np.linalg.norm(x)
    nv = np.linalg.norm(v)
    if nv == 0:
        return v.copy(), True
    if eps is None:
        eps = np.sqrt(MACH) * max(nx, 1.0) / nv
    xp = x + eps * v
    same = kernel.regime(x) == kernel.regime(xp)
    fx = kernel.step(x, dt)
    fp = kernel.step(xp, dt)
    return (fp - fx) / eps, same


def tangent_lyapunov(cfg, T_target=20.0, T_burn=2.0, drag=True, eps=None,
                     seed=0):
    """Benettin in tangent space, one renormalisation per step."""
    k = Kernel(cfg, drag=drag)
    x = k.initial()
    t = 0.0
    while t < T_burn:
        dt = k.dt_of(x)
        x = k.step(x, dt)
        t += dt
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(x.size)
    v /= np.linalg.norm(v)

    log_sum = 0.0
    T = 0.0
    nsteps = nbad = 0
    logs = []
    while T < T_target:
        dt = k.dt_of(x)
        w, ok = jvp(k, x, v, dt, eps=eps)
        x = k.step(x, dt)
        nw = np.linalg.norm(w)
        nsteps += 1
        if not ok:
            nbad += 1
        if nw <= 0 or not np.isfinite(nw):
            break
        log_sum += np.log(nw)
        logs.append(np.log(nw))
        v = w / nw
        T += dt
    logs = np.array(logs)
    return {
        "lambda": log_sum / T if T > 0 else float("nan"),
        "T": T,
        "steps": nsteps,
        "nondiff": nbad,
        "nondiff_frac": nbad / max(nsteps, 1),
        "second_half": (logs[len(logs) // 2:].sum()
                        / (T / 2) if len(logs) > 4 else float("nan")),
        "top_share": (np.abs(logs).max() / np.abs(logs).sum()
                      if logs.size and np.abs(logs).sum() > 0 else float("nan")),
    }


# ------------------------------------------------- positive control: Lorenz
def lorenz_tangent(n=200000, dt=0.005, s=10.0, r=28.0, b=8.0 / 3.0):
    """Same accumulation logic, exact analytic Jacobian. Must give ~+0.906."""
    def f(u):
        x, y, z = u
        return np.array([s * (y - x), x * (r - z) - y, x * y - b * z])

    def Df(u, v):
        x, y, z = u
        Jm = np.array([[-s, s, 0.0], [r - z, -1.0, -x], [y, x, -b]])
        return Jm @ v

    def rk4(g, u, h, *a):
        k1 = g(u, *a); k2 = g(u + 0.5 * h * k1, *a)
        k3 = g(u + 0.5 * h * k2, *a); k4 = g(u + h * k3, *a)
        return u + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)

    u = np.array([1.0, 1.0, 1.0])
    for _ in range(4000):
        u = rk4(lambda w: f(w), u, dt)
    v = np.array([1.0, 0.0, 0.0])
    tot = 0.0
    for _ in range(n):
        # propagate tangent and state together with matched RK4 stages
        k1 = Df(u, v); u1 = u + 0.5 * dt * f(u)
        k2 = Df(u1, v + 0.5 * dt * k1); u2 = u + 0.5 * dt * f(u1)
        k3 = Df(u2, v + 0.5 * dt * k2); u3 = u + dt * f(u2)
        k4 = Df(u3, v + dt * k3)
        v = v + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        u = rk4(lambda w: f(w), u, dt)
        nv = np.linalg.norm(v)
        tot += np.log(nv)
        v /= nv
    return tot / (n * dt)


if __name__ == "__main__":
    print("=" * 78)
    print("CONTROL -- Lorenz with the analytic Jacobian, same accumulation")
    lam = lorenz_tangent()
    print(f"  lambda = {lam:+.4f}   (literature +0.906)   "
          f"{'OK' if abs(lam - 0.906) < 0.05 else 'MISMATCH'}")

    base = dict(N=100, n_steps=1, Omega_0=1.5, enable_self_consistency=False)

    print()
    print("=" * 78)
    print("RSLS kernel -- tangent lambda AND the differentiability audit")
    print(f"  {'run':>10} {'T':>6} {'lambda':>11} {'2nd half':>11} "
          f"{'top share':>10} {'non-diff steps':>15}")
    for label, drag, T in (("drag ON", True, 20.0), ("drag OFF", False, 20.0)):
        r = tangent_lyapunov(Stage6Config(**base), T_target=T, drag=drag)
        print(f"  {label:>10} {r['T']:>6.1f} {r['lambda']:>+11.4f} "
              f"{r['second_half']:>+11.4f} {r['top_share']:>10.4f} "
              f"{r['nondiff']:>7}/{r['steps']:<7} ({r['nondiff_frac']:.1%})")

    print()
    print("=" * 78)
    print("epsilon independence -- a real derivative does not depend on it")
    print(f"  {'eps':>10} {'lambda':>11} {'non-diff':>10}")
    for e in (1e-6, 1e-8, 1e-10, None):
        r = tangent_lyapunov(Stage6Config(**base), T_target=12.0, eps=e)
        tag = "auto" if e is None else f"{e:.0e}"
        print(f"  {tag:>10} {r['lambda']:>+11.4f} {r['nondiff_frac']:>9.1%}")

    print()
    print("=" * 78)
    print("window independence -- a real exponent plateaus")
    print(f"  {'T':>6} {'lambda':>11} {'non-diff':>10}")
    for T in (5.0, 10.0, 20.0, 40.0):
        r = tangent_lyapunov(Stage6Config(**base), T_target=T)
        print(f"  {T:>6.1f} {r['lambda']:>+11.4f} {r['nondiff_frac']:>9.1%}")
