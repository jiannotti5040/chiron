"""Is the Stage-5/6 'Lyapunov exponent' a converged exponent at all?

A genuine lambda_max plateaus as the measurement window grows, and no single
renormalisation block dominates the sum. Test both.
"""
import numpy as np
from uma.rsls.frame_dragging import FrameDraggingConfig, lyapunov_kernel
from uma.rsls.stage6 import Stage6Config, stage6_lyapunov
from uma.rsls.memory import clip_M
from uma.rsls.cattaneo import cattaneo_step, cattaneo_cfl
from uma.rsls.hll import transport_cfl
from uma.rsls.frame_dragging import kerr_like_drag, cylindrical_hll_step


def block_logs(cfg):
    """Stage-5 kernel, returning the per-block log-growths instead of a mean."""
    mcfg = cfg.memory
    Rf = np.linspace(cfg.R_in, cfg.R_out, cfg.N + 1)
    Rc = 0.5 * (Rf[:-1] + Rf[1:])
    dR = (cfg.R_out - cfg.R_in) / cfg.N
    bp = (kerr_like_drag(Rc, cfg.R_in, cfg.Omega_0, cfg.drag_exponent)
          if cfg.enable_drag else np.zeros(cfg.N))
    D = np.ones(cfg.N) * cfg.D_background
    S_R = cfg.pulse_amp * np.exp(-((Rc - cfg.pulse_center) / cfg.pulse_width) ** 2)
    S_phi = np.zeros(cfg.N)
    M = clip_M(cfg.M_saturation_layer_amp * np.exp(
        -((Rc - cfg.M_saturation_layer_R0) / cfg.M_saturation_layer_width) ** 2), mcfg)
    J = np.zeros(cfg.N)
    D2, S_R2, S_phi2, M2, J2 = D.copy(), S_R.copy(), S_phi.copy(), M.copy(), J.copy()
    S_R2[cfg.perturb_cell] += cfg.perturb_delta
    d0 = cfg.perturb_delta
    dt = min(transport_cfl(S_R / np.maximum(D, 1e-12), dR, mcfg, safety=cfg.cfl_safety),
             cattaneo_cfl(dR, mcfg, safety=cfg.cfl_safety), 0.005 * dR)

    def st(D, S_R, S_phi, M, J):
        M = clip_M(M, mcfg)
        D, S_R, S_phi = cylindrical_hll_step(D, S_R, S_phi, M, bp, Rf, Rc, dt, mcfg)
        v = S_R / np.maximum(D, 1e-12)
        M = clip_M(M + dt * (-np.gradient(J, dR) - 0.5 * np.gradient(v, dR)), mcfg)
        return D, S_R, S_phi, M, cattaneo_step(J, M, dR, dt, mcfg)

    nb = min(200, cfg.n_steps // 4)
    for _ in range(nb):
        D, S_R, S_phi, M, J = st(D, S_R, S_phi, M, J)
        D2, S_R2, S_phi2, M2, J2 = st(D2, S_R2, S_phi2, M2, J2)
    N = cfg.N

    def stack(a, b, c, d):
        return np.concatenate([a, b, c, d])
    s1, s2 = stack(D, S_R, S_phi, M), stack(D2, S_R2, S_phi2, M2)
    sep = s2 - s1; sn = np.linalg.norm(sep)
    if sn > 0:
        s2 = s1 + sep / sn * d0
        D2 = np.maximum(s2[:N], 1e-6); S_R2 = s2[N:2*N]
        S_phi2 = s2[2*N:3*N]; M2 = clip_M(s2[3*N:], mcfg)
    logs = []
    nm = cfg.n_steps - nb; sc = 0
    while sc < nm:
        for _ in range(cfg.lyap_renorm_every):
            if sc >= nm:
                break
            D, S_R, S_phi, M, J = st(D, S_R, S_phi, M, J)
            D2, S_R2, S_phi2, M2, J2 = st(D2, S_R2, S_phi2, M2, J2)
            sc += 1
        s1, s2 = stack(D, S_R, S_phi, M), stack(D2, S_R2, S_phi2, M2)
        sep = s2 - s1; sn = np.linalg.norm(sep)
        if sn > 1e-30:
            logs.append(np.log(sn / d0))
            s2 = s1 + sep / sn * d0
            D2 = np.maximum(s2[:N], 1e-6); S_R2 = s2[N:2*N]
            S_phi2 = s2[2*N:3*N]; M2 = clip_M(s2[3*N:], mcfg)
    return np.array(logs), cfg.lyap_renorm_every * dt


cfg = FrameDraggingConfig(N=100, n_steps=2000, Omega_0=1.5, enable_drag=True)
logs, blk_t = block_logs(cfg)
tot_t = len(logs) * blk_t
lam = logs.sum() / tot_t
print("=" * 70)
print("Stage 5, N=100, n_steps=2000  (test asserts lambda > 0.3)")
print(f"  blocks={len(logs)}  block_time={blk_t:.4f}  total_time={tot_t:.4f}")
print(f"  lambda = {lam:+.6f}")
i = int(np.argmax(logs))
print(f"  largest single block: #{i}, log-growth={logs[i]:+.4f} "
      f"(growth x{np.exp(logs[i]):.1f})")
print(f"  that ONE block is {100*logs[i]/logs.sum():.1f}% of the entire sum")
rest = np.delete(logs, i)
print(f"  lambda with it removed = {rest.sum()/ (len(rest)*blk_t):+.6f}")
print(f"  median block log-growth = {np.median(logs):+.6e}  "
      f"({(logs<0).sum()}/{len(logs)} blocks CONTRACT)")

print()
print("=" * 70)
print("Convergence: a real exponent plateaus as the window grows")
print(f"  {'n_steps':>8} {'Stage5 lambda':>15} {'Stage6 lambda':>15}")
for ns in (1000, 2000, 4000, 8000, 16000):
    l5 = lyapunov_kernel(FrameDraggingConfig(N=100, n_steps=ns, Omega_0=1.5,
                                             enable_drag=True))
    l6 = stage6_lyapunov(Stage6Config(N=100, n_steps=ns, Omega_0=1.5,
                                      enable_self_consistency=True))
    print(f"  {ns:>8} {l5:>+15.6f} {l6:>+15.6f}")

print()
print("=" * 70)
print("Perturbation-size independence: a real exponent is delta-independent")
print(f"  {'delta':>10} {'Stage5 lambda':>15} {'Stage6 lambda':>15}")
for d in (1e-6, 1e-8, 1e-10, 1e-12):
    l5 = lyapunov_kernel(FrameDraggingConfig(N=100, n_steps=2000, Omega_0=1.5,
                                             enable_drag=True, perturb_delta=d))
    l6 = stage6_lyapunov(Stage6Config(N=100, n_steps=2000, Omega_0=1.5,
                                      enable_self_consistency=True, perturb_delta=d))
    print(f"  {d:>10.0e} {l5:>+15.6f} {l6:>+15.6f}")
