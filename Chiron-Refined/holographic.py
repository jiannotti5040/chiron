#!/usr/bin/env python3
"""
holographic.py — distributed redundancy: recover the whole from a fragment (O-3, hardened).

HCT Theorem T7: an identity-bearing structure encodes its global identity distributively, so
any sufficient subset of the boundary reconstructs the whole — the holographic quantum-error-
correction property. This module applies it to two things:

  1. THE LAW. The hardcoded legal corpus (legal_corpus.py) is holographically encoded so that
     the entire body of doctrine survives the destruction of a fragment of its storage — below
     the recovery threshold, any sufficient subset reconstructs every provision. Doctrine, like
     a hologram, is not stored in one place; it is distributed.
  2. A FINDING. A recovered structure is encoded, a boundary fragment is erased, and the
     structure is still recovered exactly — the resilience axis complementary to uma_bridge's
     dynamic robustness: not "does it survive perturbation" but "does it survive losing pieces."

    python3 holographic.py selftest
    python3 holographic.py doctrine --erase 0.4
    python3 holographic.py sweep
    python3 holographic.py recover 1 1 2 3 5 8 13 21

Framing dial — civilian: recover the full picture / full ruleset from partial data. Contractor:
erasure-resilient reconstruction of doctrine and intelligence with a measured recovery threshold.
"""
import os
import sys
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "JDICert"))
import chiron          # noqa: E402
import legal_corpus as law  # noqa: E402
import numpy as np     # noqa: E402
import cert_engine as ce   # noqa: E402


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _encode(vec):
    cdim = len(vec)
    bdim = 2 * cdim + 4
    agent = ce.HolographicQECAgent(context_dim=cdim, boundary_dim=bdim)
    return agent, np.asarray(agent.encode(np.asarray(vec, float))), bdim


def doctrine_resilience(erase_frac=0.4, tol=1e-6):
    """Encode the entire legal corpus; erase a boundary fragment; recover all provisions."""
    vec = np.asarray(law.corpus_vector(), float)
    agent, enc, bdim = _encode(vec)
    k = max(1, int(round(erase_frac * bdim)))
    rec = np.asarray(agent.decode_erased(enc, np.arange(k)))
    err = float(np.linalg.norm(rec - vec))
    provisions_recovered = int(np.sum(np.abs(rec - vec) < 1e-4))
    return {
        "provisions": len(vec),
        "boundary_dim": bdim,
        "erased_fragment": k,
        "erased_fraction": round(k / bdim, 3),
        "doctrine_recovered": bool(err < tol),
        "recovery_error": round(err, 8),
        "provisions_recovered_exactly": provisions_recovered,
        "interpretation": "the full body of law reconstructs from any sufficient surviving fragment",
    }


def threshold_sweep(tol=1e-6):
    vec = np.asarray(law.corpus_vector(), float)
    agent, enc, bdim = _encode(vec)
    sweep, threshold = [], 0.0
    for pct in range(5, 70, 5):
        frac = pct / 100.0
        k = max(1, int(round(frac * bdim)))
        rec = np.asarray(agent.decode_erased(enc, np.arange(k)))
        err = float(np.linalg.norm(rec - vec))
        recovered = err < tol
        sweep.append({"erased_fraction": frac, "recovered": recovered, "error": round(err, 6)})
        if recovered:
            threshold = frac
    return {"recovery_threshold": threshold, "sweep": sweep,
            "empirical_threshold": round(float(agent.empirical_recovery_threshold(n_trials=20)), 3)}


def _finding_vector(vals, dim=6):
    arr = np.array(vals, float)
    nv = arr / (np.max(np.abs(arr)) + 1e-9)
    return nv[:dim] if len(nv) >= dim else np.concatenate([nv, np.zeros(dim - len(nv))])


def holographic(surface, erase_frac=0.4):
    vals = _nums(surface)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    vec = _finding_vector(vals)
    agent, enc, bdim = _encode(vec)
    k = max(1, int(round(erase_frac * bdim)))
    rec = np.asarray(agent.decode_erased(enc, np.arange(k)))
    err = float(np.linalg.norm(rec - vec))
    return {
        "law": inv.model_class, "verified": bool(inv.verified),
        "context_dim": len(vec), "boundary_dim": bdim,
        "erased_fragment": k, "erased_fraction": round(k / bdim, 3),
        "recovered_exactly": bool(err < 1e-6), "recovery_error": round(err, 8),
        "empirical_recovery_threshold": round(float(agent.empirical_recovery_threshold(n_trials=20)), 3),
    }


def render_doctrine(d):
    L = ["=" * 62, "HOLOGRAPHIC DOCTRINE — the law survives partial destruction", "=" * 62]
    L.append(f"  corpus provisions .. {d['provisions']}")
    L.append(f"  erased {d['erased_fragment']}/{d['boundary_dim']} ({d['erased_fraction']}) of the boundary store")
    L.append(f"  DOCTRINE RECOVERED . {d['doctrine_recovered']}  (error {d['recovery_error']})")
    L.append(f"  provisions exact ... {d['provisions_recovered_exactly']}/{d['provisions']}")
    L.append("=" * 62)
    return "\n".join(L)


def render(h):
    L = ["=" * 60, "HOLOGRAPHIC RECOVERY — the whole from a fragment", "=" * 60]
    L.append(f"  law={h['law']}  verified={h['verified']}")
    L.append(f"  erased {h['erased_fragment']}/{h['boundary_dim']} ({h['erased_fraction']})")
    L.append(f"  RECOVERED EXACTLY .. {h['recovered_exactly']}  (error {h['recovery_error']})")
    L.append(f"  recovery threshold . {h['empirical_recovery_threshold']}")
    L.append("=" * 60)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    d = doctrine_resilience(0.4)
    ok("corpus encodes >= 60 provisions", d["provisions"] >= 60)
    ok("doctrine recovers below threshold (40% erased)", d["doctrine_recovered"])
    ok("all provisions recovered exactly", d["provisions_recovered_exactly"] == d["provisions"])

    sw = threshold_sweep()
    ok("recovery threshold > 0", sw["recovery_threshold"] > 0)
    ok("low erasure recovers", sw["sweep"][0]["recovered"])
    ok("threshold is a fraction", 0 < sw["recovery_threshold"] <= 0.7)

    h = holographic("1 1 2 3 5 8 13 21 34")
    ok("finding recovers exactly", h["recovered_exactly"])
    ok("finding boundary > context", h["boundary_dim"] > h["context_dim"])

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  holographic.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    print(render_doctrine(doctrine_resilience(0.4)))
    print()
    sw = threshold_sweep()
    print(f"recovery threshold (corpus): {sw['recovery_threshold']}  empirical: {sw['empirical_threshold']}")
    print()
    print(render(holographic("1 1 2 3 5 8 13 21 34 55")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Holographic erasure-recovery of doctrine and findings.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    sub.add_parser("sweep")
    dd = sub.add_parser("doctrine"); dd.add_argument("--erase", type=float, default=0.4)
    rc = sub.add_parser("recover"); rc.add_argument("values", nargs="+"); rc.add_argument("--erase", type=float, default=0.4)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in (None, "demo"):
        return _demo()
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "sweep":
        print(json.dumps(threshold_sweep(), indent=2)); return 0
    if args.cmd == "doctrine":
        d = doctrine_resilience(args.erase)
        print(json.dumps(d, indent=2) if args.json else render_doctrine(d)); return 0
    h = holographic(" ".join(args.values), erase_frac=args.erase)
    print(json.dumps(h, indent=2) if args.json else render(h))
    return 0


if __name__ == "__main__":
    sys.exit(main())
