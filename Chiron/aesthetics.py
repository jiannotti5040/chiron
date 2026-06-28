#!/usr/bin/env python3
"""
aesthetics.py — mathematical beauty as a measured, multi-signal quantity.

The missing axiological pillar. Ethics is covered (govern.py / SoCPM), value is covered
(ontological.py / V-Units), but beauty was not. Dirac held mathematical beauty as a guide to
truth, and it is not subjective decoration: it decomposes into Elegance, Symmetry, and
Resonance — each of which is a real, computable quantity on the metrics Chiron and UMA already
produce. This module computes each from several independent estimators and fuses them.

  ELEGANCE   — a complex surface from a simple rule. Estimators:
                 mdl_saturation, generative_leverage, parsimony_margin
  SYMMETRY   — structural balance and self-similarity. Estimators:
                 mirror, periodicity, scale_symmetry (Higuchi fractal dimension)
  RESONANCE  — does the structure hold together under dynamics. Estimators:
                 lyapunov_stability (RSLS), spectral_concentration (FFT), persistence

  BEAUTY     B = (E · S · R) ** (1/3)   — geometric mean: one low component sinks it.

A recovered signal with high Beauty AND high Harmony (ontological.py) is, in Dirac's sense, a
fundamental and elegant truth of the system. This module makes that criterion computable, and
can RANK a set of candidate surfaces by beauty.

    python3 aesthetics.py selftest
    python3 aesthetics.py score 1 2 4 8 16 32 64 128
    python3 aesthetics.py components 1 1 2 3 5 8 13 21
    python3 aesthetics.py compare "1 2 4 8 16" "1 1 2 3 5 8" "41 19 50 83 6"

Framing dial — civilian: elegance / quality score for recovered structure. Contractor:
parsimony & concordance scoring across candidate models.
"""
import os
import sys
import math
import json
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402
import uma_bridge      # noqa: E402
import numpy as np     # noqa: E402

try:
    import ontological as _ont
except Exception:      # pragma: no cover
    _ont = None

ABSTAIN = ("incompressible", "general", "random")


def _nums(surface):
    if isinstance(surface, str):
        surface = surface.replace(",", " ").split()
    return [int(x) if str(x).lstrip("-").isdigit() else float(x) for x in surface]


def _clip01(x):
    return max(0.0, min(1.0, float(x)))


# ---------------------------------------------------------------------------
# ELEGANCE estimators
# ---------------------------------------------------------------------------
def mdl_saturation(inv):
    """How far the description collapses. cr=2.9 -> 0.66, cr=20 -> 0.95."""
    if inv.model_class in ABSTAIN or not inv.verified:
        return _clip01(min(0.15, 1.0 - 1.0 / max(1.0, float(inv.compression_ratio))))
    return _clip01(1.0 - 1.0 / max(1.0, float(inv.compression_ratio)))


def generative_leverage(inv):
    """Surface description bits per model bit, squashed — a tiny rule that makes a lot."""
    mb = float(getattr(inv, "model_bits", 0.0)) or 1.0
    sb = float(getattr(inv, "surface_bits", mb))
    return _clip01(math.tanh((sb / mb - 1.0) / 3.0)) if inv.verified else 0.0


def parsimony_margin(vals):
    """How decisively the winning generator beats the runner-up (MDL bit gap)."""
    try:
        cands = chiron.top_generators(vals, k=3)
    except Exception:
        return 0.0
    real = [c for c in cands if "mdl_cost_bits" in c]
    if len(real) < 2:
        return 0.6 if real and real[0].get("model_class") not in ABSTAIN else 0.0
    gap = float(real[1]["mdl_cost_bits"]) - float(real[0]["mdl_cost_bits"])
    return _clip01(math.tanh(gap / 12.0))


def elegance(inv, vals):
    parts = [mdl_saturation(inv), generative_leverage(inv), parsimony_margin(vals)]
    return round(sum(parts) / len(parts), 4), {"mdl_saturation": round(parts[0], 4),
                                                "generative_leverage": round(parts[1], 4),
                                                "parsimony_margin": round(parts[2], 4)}


# ---------------------------------------------------------------------------
# SYMMETRY estimators
# ---------------------------------------------------------------------------
def _corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.std() < 1e-12 or b.std() < 1e-12:
        return 0.0
    return float(np.clip(np.corrcoef(a, b)[0, 1], -1, 1))


def mirror_symmetry(vals):
    x = np.asarray(vals, float)
    if len(x) < 3:
        return 0.0
    x = (x - x.mean()) / (x.std() + 1e-12)
    return _clip01(_corr(x, x[::-1]))


def periodicity(vals):
    x = np.asarray(vals, float)
    n = len(x)
    if n < 4:
        return 0.0
    x = (x - x.mean()) / (x.std() + 1e-12)
    best = 0.0
    for lag in range(1, n // 2 + 1):
        best = max(best, _corr(x[:-lag], x[lag:]))
    return _clip01(best)


def higuchi_fd(vals, kmax=None):
    """Higuchi fractal dimension of a 1-D sequence: ~1 smooth/structured, ~2 noise."""
    x = np.asarray(vals, float)
    N = len(x)
    if N < 5:
        return 1.0
    kmax = kmax or min(8, N // 2)
    lnL, lnk = [], []
    for k in range(1, kmax + 1):
        Lm = []
        for m in range(k):
            cnt = (N - m - 1) // k
            if cnt < 1:
                continue
            idx = np.arange(1, cnt + 1)
            dist = np.sum(np.abs(x[m + idx * k] - x[m + (idx - 1) * k]))
            norm = (N - 1) / (cnt * k)
            Lm.append(dist * norm / k)
        if Lm:
            lnL.append(math.log(np.mean(Lm) + 1e-12))
            lnk.append(math.log(1.0 / k))
    if len(lnL) < 2:
        return 1.0
    slope = float(np.polyfit(lnk, lnL, 1)[0])
    return max(1.0, min(2.0, slope))


def scale_symmetry(vals):
    """Self-similarity across scales: 2 - Higuchi FD, normalised to [0,1]."""
    return _clip01(2.0 - higuchi_fd(vals))


def symmetry(vals):
    parts = [mirror_symmetry(vals), periodicity(vals), scale_symmetry(vals)]
    return round(max(parts), 4), {"mirror": round(parts[0], 4),
                                  "periodicity": round(parts[1], 4),
                                  "scale_symmetry": round(parts[2], 4)}


# ---------------------------------------------------------------------------
# RESONANCE estimators
# ---------------------------------------------------------------------------
def spectral_concentration(vals):
    """1 - spectral flatness. Flat spectrum (noise) -> 0; peaked/tonal (structure) -> 1."""
    x = np.asarray(vals, float)
    x = x - x.mean()
    if np.allclose(x, 0) or len(x) < 4:
        return 0.0
    ps = np.abs(np.fft.rfft(x)) ** 2
    ps = ps[1:]
    ps = ps[ps > 1e-12]
    if len(ps) == 0:
        return 0.0
    flatness = float(np.exp(np.mean(np.log(ps))) / (np.mean(ps) + 1e-12))
    return _clip01(1.0 - flatness)


def resonance(surface_str, vals):
    rob = uma_bridge.robustness(surface_str)
    lam = float(rob.get("lyapunov_forecast", 0.0)) if "error" not in rob else 0.0
    lyap_stab = _clip01(1.0 / (1.0 + math.exp(2.0 * lam)))
    persisted = bool(rob.get("structure_persisted_after_evolution"))
    spec = spectral_concentration(vals)
    base = (lyap_stab + spec) / 2.0
    if persisted:
        base += 0.15 * (1.0 - base)
    return round(_clip01(base), 4), {"lyapunov_stability": round(lyap_stab, 4),
                                     "spectral_concentration": round(spec, 4),
                                     "persisted": persisted}


# ---------------------------------------------------------------------------
# The Beauty functional
# ---------------------------------------------------------------------------
def _band(b):
    return ("sublime" if b >= 0.8 else "elegant" if b >= 0.65 else "shapely"
            if b >= 0.45 else "plain" if b >= 0.25 else "inelegant")


def aesthetic(surface, weights=(1.0, 1.0, 1.0)):
    vals = _nums(surface)
    surface_str = " ".join(str(v) for v in vals)
    inv = chiron.collapse([int(v) if float(v).is_integer() else v for v in vals])
    E, Edet = elegance(inv, vals)
    S, Sdet = symmetry(vals)
    R, Rdet = resonance(surface_str, vals)
    wE, wS, wR = weights
    comps = [(E, wE), (S, wS), (R, wR)]
    logsum = sum(w * math.log(max(1e-6, c)) for c, w in comps)
    beauty = round(math.exp(logsum / sum(w for _, w in comps)), 4)

    out = {
        "law": inv.model_class, "verified": bool(inv.verified),
        "elegance": E, "elegance_detail": Edet,
        "symmetry": S, "symmetry_detail": Sdet,
        "resonance": R, "resonance_detail": Rdet,
        "beauty": beauty, "band": _band(beauty),
    }
    if _ont is not None and inv.verified:
        try:
            v = _ont.v_units(surface_str)
            harmony = _ont.harmony([E, S, R])
            out["harmony"] = round(float(harmony), 4)
            out["value_V"] = round(float(v.get("V_units", 0.0)), 4)
            out["fundamental_truth"] = bool(beauty >= 0.6 and harmony >= 0.6 and out["value_V"] >= 0.6)
        except Exception:
            pass
    return out


def compare(surfaces):
    scored = [(s, aesthetic(s)) for s in surfaces]
    scored.sort(key=lambda x: -x[1]["beauty"])
    return [{"surface": s if isinstance(s, str) else " ".join(map(str, s)),
             "beauty": a["beauty"], "band": a["band"],
             "E": a["elegance"], "S": a["symmetry"], "R": a["resonance"]} for s, a in scored]


# ---------------------------------------------------------------------------
# render + selftest + CLI
# ---------------------------------------------------------------------------
def render(b):
    L = ["=" * 60, "AESTHETIC SCORE — elegance · symmetry · resonance", "=" * 60]
    L.append(f"  law={b['law']}  verified={b['verified']}")
    L.append(f"  ELEGANCE  {b['elegance']}   {b['elegance_detail']}")
    L.append(f"  SYMMETRY  {b['symmetry']}   {b['symmetry_detail']}")
    L.append(f"  RESONANCE {b['resonance']}   {b['resonance_detail']}")
    L.append(f"  BEAUTY    {b['beauty']}   [{b['band']}]")
    if "fundamental_truth" in b:
        L.append(f"  harmony={b['harmony']}  value_V={b['value_V']}  fundamental_truth={b['fundamental_truth']}")
    L.append("=" * 60)
    return "\n".join(L)


_SUITE = {
    "powers_of_two": "1 2 4 8 16 32 64 128 256 512",
    "fibonacci": "1 1 2 3 5 8 13 21 34 55",
    "arithmetic": "5 10 15 20 25 30 35 40",
    "palindrome": "1 2 3 4 3 2 1",
    "random": "41 19 50 83 6 9 68 12 46 74",
}


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    a = {k: aesthetic(v) for k, v in _SUITE.items()}
    ok("powers_of_two is elegant (>=0.6)", a["powers_of_two"]["beauty"] >= 0.6)
    ok("random is inelegant (<0.3)", a["random"]["beauty"] < 0.3)
    ok("structured beats random", a["fibonacci"]["beauty"] > a["random"]["beauty"])
    ok("palindrome has high symmetry", aesthetic(_SUITE["palindrome"])["symmetry"] >= 0.8)
    ok("higuchi: line ~1", abs(higuchi_fd([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]) - 1.0) < 0.3)
    ok("higuchi: noise > line", higuchi_fd([3, 1, 4, 1, 5, 9, 2, 6, 5, 3]) > higuchi_fd(list(range(10))))
    ok("spectral: sine concentrated > noise",
       spectral_concentration([math.sin(i) for i in range(20)]) > spectral_concentration([41, 19, 50, 83, 6, 9, 68, 12, 46, 74]))
    ok("elegance in [0,1]", 0 <= a["arithmetic"]["elegance"] <= 1)
    ok("beauty geom-mean penalises", aesthetic(_SUITE["palindrome"])["beauty"] < aesthetic(_SUITE["palindrome"])["symmetry"])
    comp = compare(list(_SUITE.values()))
    ok("compare ranks powers_of_two/fibonacci above random", comp[0]["beauty"] >= comp[-1]["beauty"] and comp[-1]["beauty"] < 0.3)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  aesthetics.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for label, s in _SUITE.items():
        print(f"\n### {label}: {s}")
        print(render(aesthetic(s)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Mathematical-beauty score over recovered structure.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    sc = sub.add_parser("score"); sc.add_argument("values", nargs="+")
    cp = sub.add_parser("components"); cp.add_argument("values", nargs="+")
    cm = sub.add_parser("compare"); cm.add_argument("surfaces", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd in (None, "demo"):
        return _demo()
    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "compare":
        out = compare(args.surfaces)
        print(json.dumps(out, indent=2) if args.json else
              "\n".join(f"  {r['beauty']:.3f} [{r['band']:<9}] {r['surface']}" for r in out))
        return 0
    b = aesthetic(" ".join(args.values))
    if args.cmd == "components" or args.json:
        print(json.dumps(b, indent=2))
    else:
        print(render(b))
    return 0


if __name__ == "__main__":
    sys.exit(main())
