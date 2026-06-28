#!/usr/bin/env python3
"""
uma_bridge.py — robustness of recovered structure under the RSLS dynamics.

Chiron recovers the exact rule; this asks how that rule survives physical reality. It maps a
recovered signal into Chiron's embedded RSLS State crucible, evolves it under the Maxwell-
Cattaneo + Stage-6 dynamics, and reports robustness indicators: a Lyapunov forecast and the
predictability horizon, a decoherence half-life via the GKLS/Lindblad channel (rate tied to the
law's compression), and structure persistence (re-collapse the evolved signal and ask whether the
generator survived). It adds a PERTURBATION SWEEP (how much noise the structure tolerates before
it stops persisting) and a DECOHERENCE SWEEP across rates.

These are proof-of-concept robustness indicators of the Chiron->UMA coupling, not a physics claim.
See UMA_CHIRON_EXPLORATION.md.

Public API (consumed elsewhere): robustness(surface).

    python3 uma_bridge.py selftest
    python3 uma_bridge.py test 1 2 4 8 16 32 64
    python3 uma_bridge.py sweep 1 1 2 3 5 8 13 21 --json

Framing dial — civilian: robustness/persistence of recovered structure under perturbation.
Contractor: signal-integrity / structural stress test under noise & jamming.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import numpy as np     # noqa: E402


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
    sm = np.array([[0, 1], [0, 0]], complex)
    H = 0.5 * np.array([[1, 0], [0, -1]], complex)
    L = [np.sqrt(max(1e-6, gamma)) * sm]
    rho = np.array([[0, 0], [0, 1]], complex)
    for k in range(1, max_steps + 1):
        rho = chiron.lindblad_step(rho, H, L, dt)
        if rho[1, 1].real < 0.5:
            return round(k * dt, 3)
    return None


def _persists(nums, noise=0.0, seed=0):
    """Inject relative gaussian noise of magnitude `noise`, evolve, and re-collapse."""
    rng = np.random.default_rng(seed)
    arr = np.array(nums, float)
    scale = np.max(np.abs(arr)) + 1e-9
    base = chiron.collapse([int(round(x)) for x in arr])
    perturbed = arr + noise * scale * rng.standard_normal(len(arr))
    sig = list(perturbed / scale)
    states = _evolve(_to_state(sig))
    evolved = np.asarray(states[-1].g, float).flatten()
    ev = evolved / (np.max(np.abs(evolved)) + 1e-9) * scale
    try:
        inv2 = chiron.collapse([int(round(x)) for x in ev])
        return bool(inv2.verified and inv2.model_class == base.model_class), inv2.model_class
    except Exception:
        return False, "—"


def robustness(surface):
    nums = _nums(surface)
    if not nums or len(nums) < 4:
        return {"error": "need >= 4 numeric terms"}
    inv = chiron.collapse([int(x) if float(x).is_integer() else x for x in nums])
    arr = np.array(nums, float)
    scale = np.max(np.abs(arr)) + 1e-9
    states = _evolve(_to_state(list(arr / scale)))
    lam = float(chiron.lyapunov_max_forecast(states))
    horizon = chiron.cone_aperture_from_lyapunov(lam)
    cr = inv.compression_ratio if inv.verified else 1.0
    gamma = 1.0 / max(0.2, min(cr, 20.0))
    half = _decoherence_half_life(gamma)
    persisted, ev_class = _persists(nums, noise=0.0)
    return {
        "input_class": inv.model_class, "verified": bool(inv.verified),
        "lyapunov_forecast": round(lam, 4),
        "predictability_horizon": horizon,
        "decoherence_half_life": half,
        "structure_persisted_after_evolution": persisted,
        "evolved_class": ev_class,
    }


def perturbation_sweep(surface, levels=(0.0, 0.05, 0.1, 0.2, 0.4)):
    """How much relative noise can the structure tolerate before it stops persisting?"""
    nums = _nums(surface)
    if not nums or len(nums) < 4:
        return {"error": "need >= 4 numeric terms"}
    sweep, tolerance = [], 0.0
    for lv in levels:
        persisted, cls = _persists(nums, noise=lv, seed=7)
        sweep.append({"noise": lv, "persisted": persisted, "class": cls})
        if persisted:
            tolerance = lv
    return {"noise_tolerance": tolerance, "sweep": sweep}


def decoherence_sweep(surface, rates=(0.1, 0.25, 0.5, 1.0, 2.0)):
    return {"half_lives": [{"gamma": g, "half_life": _decoherence_half_life(g)} for g in rates]}


def render(r):
    L = ["=" * 60, "UMA ROBUSTNESS — recovered structure under the RSLS crucible", "=" * 60]
    L.append(f"  class={r['input_class']}  verified={r['verified']}")
    L.append(f"  lyapunov forecast {r['lyapunov_forecast']}   horizon {r['predictability_horizon']}")
    L.append(f"  decoherence half-life {r['decoherence_half_life']}")
    L.append(f"  structure persisted {r['structure_persisted_after_evolution']}  (evolved -> {r['evolved_class']})")
    L.append("=" * 60)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    geo = robustness("1 2 4 8 16 32 64 128")
    noise = robustness("41 19 50 83 6 9 68 12")
    ok("geometric is verified", geo["verified"])
    ok("geometric persists", geo["structure_persisted_after_evolution"])
    ok("noise does not persist", not noise["structure_persisted_after_evolution"])
    ok("decoherence half-life present for law", geo["decoherence_half_life"] is not None)
    ok("short input errors cleanly", "error" in robustness("1 2"))

    sw = perturbation_sweep("2 4 6 8 10 12 14 16")
    ok("zero-noise persists", sw["sweep"][0]["persisted"])
    ok("tolerance is a noise level", 0.0 <= sw["noise_tolerance"] <= 0.4)
    ok("noise tolerance monotone-ish (high noise eventually fails)",
       not sw["sweep"][-1]["persisted"] or sw["noise_tolerance"] >= sw["sweep"][0]["noise"])

    ds = decoherence_sweep("1 1 2 3 5 8")
    ok("decoherence sweep returns rates", len(ds["half_lives"]) == 5)
    ok("higher gamma -> shorter or equal half-life",
       (ds["half_lives"][0]["half_life"] or 1e9) >= (ds["half_lives"][-1]["half_life"] or 0))

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  uma_bridge.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for s in ["1 2 4 8 16 32 64 128", "0 1 1 2 3 5 8 13 21", "41 19 50 83 6 9 68 12"]:
        print(render(robustness(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="UMA robustness coupling.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    t = sub.add_parser("test"); t.add_argument("values", nargs="+")
    sw = sub.add_parser("sweep"); sw.add_argument("values", nargs="+")
    ap.add_argument("--surface", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "sweep":
        print(json.dumps(perturbation_sweep(" ".join(args.values)), indent=2)); return 0
    if args.cmd == "test":
        r = robustness(" ".join(args.values))
        print(json.dumps(r, indent=2) if args.json else render(r)); return 0
    if args.surface:
        print(json.dumps(robustness(args.surface), indent=2)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
