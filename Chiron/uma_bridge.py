#!/usr/bin/env python3
"""
UMA robustness coupling (B-2).

Chiron recovers the exact rule; this asks how that rule survives dynamics. It maps a
recovered signal into Chiron's embedded RSLS State crucible, evolves it under the
Maxwell-Cattaneo + Stage-6 dynamics, and reports robustness *indicators*:
  - Lyapunov forecast (sensitivity to perturbation) and the predictability horizon,
  - a decoherence half-life via the GKLS/Lindblad channel (rate tied to the law's
    compression — a tight law decoheres slower),
  - structure persistence: re-collapse the evolved signal and ask whether the
    generator survived.

These are PoC robustness indicators of the Chiron→UMA coupling, not a physics claim.
See UMA_CHIRON_EXPLORATION.md.

    python3 uma_bridge.py                       # demo on a few signals
    python3 uma_bridge.py --surface "1 2 4 8 16 32 64" --json

Framing dial — civilian: robustness/persistence of recovered structure under
perturbation. Contractor: signal-integrity / structural stress test under noise.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chiron  # noqa: E402
import numpy as np  # noqa: E402


def _nums(s):
    parts = str(s).replace(",", " ").split()
    try:
        return [float(x) for x in parts]
    except ValueError:
        return None


def _to_state(signal):
    g = np.array([signal], dtype=float)
    return chiron.State(g=g, U_flow=np.zeros_like(g), M=np.full_like(g, 0.1))


def _evolve(state, steps=60, dt=0.05):
    cfg = chiron.MemoryConfig()
    states = [state]
    s = state
    for _ in range(steps):
        s = chiron.maxwell_cattaneo_step(s, dt, cfg.tau_J, cfg.mu)
        s = chiron.stage6_coupling_step(s, dt, cfg)
        states.append(s)
    return states


def _decoherence_half_life(gamma, dt=0.05, max_steps=800):
    sm = np.array([[0, 1], [0, 0]], complex)        # lowering |0><1|
    H = 0.5 * np.array([[1, 0], [0, -1]], complex)
    L = [np.sqrt(max(1e-6, gamma)) * sm]
    rho = np.array([[0, 0], [0, 1]], complex)       # start excited
    for k in range(1, max_steps + 1):
        rho = chiron.lindblad_step(rho, H, L, dt)
        if rho[1, 1].real < 0.5:
            return round(k * dt, 3)
    return None


def robustness(surface):
    nums = _nums(surface)
    if not nums or len(nums) < 4:
        return {"error": "need >= 4 numeric terms"}
    inv = chiron.collapse([int(x) if float(x).is_integer() else x for x in nums])
    arr = np.array(nums, float)
    scale = np.max(np.abs(arr)) + 1e-9
    sig = list(arr / scale)
    states = _evolve(_to_state(sig))
    lam = float(chiron.lyapunov_max_forecast(states))
    horizon = chiron.cone_aperture_from_lyapunov(lam)
    cr = inv.compression_ratio if inv.verified else 1.0
    gamma = 1.0 / max(0.2, min(cr, 20.0))           # tight law (high cr) -> slow decoherence
    half = _decoherence_half_life(gamma)
    evolved = np.asarray(states[-1].g, float).flatten()
    ev = evolved / (np.max(np.abs(evolved)) + 1e-9) * scale
    try:
        inv2 = chiron.collapse([int(round(x)) for x in ev])
        persisted = bool(inv2.verified and inv2.model_class == inv.model_class)
        ev_class = inv2.model_class
    except Exception:
        persisted, ev_class = False, "—"
    return {
        "input_class": inv.model_class, "verified": bool(inv.verified),
        "lyapunov_forecast": round(lam, 4),
        "predictability_horizon": horizon,
        "decoherence_half_life": half,
        "structure_persisted_after_evolution": persisted,
        "evolved_class": ev_class,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--surface", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.surface:
        r = robustness(args.surface)
        print(json.dumps(r, indent=2) if args.json else r)
        return 0
    demo = ["1 2 4 8 16 32 64 128", "0 1 1 2 3 5 8 13 21", "2 4 6 8 10 12 14", "3 1 4 1 5 9 2 6"]
    print("=" * 70)
    print("UMA ROBUSTNESS COUPLING — recovered structure under the RSLS crucible")
    print("=" * 70)
    print("  %-22s %-18s %8s %9s %s" % ("signal", "class", "lyapunov", "decohere", "persisted"))
    for s in demo:
        r = robustness(s)
        if "error" in r:
            continue
        print("  %-22s %-18s %8s %9s %s" % (
            s[:22], r["input_class"][:18], r["lyapunov_forecast"],
            r["decoherence_half_life"], r["structure_persisted_after_evolution"]))
    print("\n  Lyapunov forecast = sensitivity to perturbation; decohere = half-life of")
    print("  the excited state under noise (tighter law decoheres slower). Indicators,")
    print("  not physics — the Chiron->UMA coupling PoC (see UMA_CHIRON_EXPLORATION.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
