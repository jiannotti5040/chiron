#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
# ============================================================================
#  PRIMUS — INVARIANT ENGINE (clean core, v2)
#  PolyForm Noncommercial 1.0.0 — noncommercial use permitted; commercial rights reserved. Author: Jacob Iannotti.
#  Licensed under PolyForm Noncommercial 1.0.0: noncommercial use, modification,
#  and sharing permitted; commercial rights reserved. See LICENSE.md.
# ============================================================================
"""
A domain-agnostic compression-and-invariant-discovery framework.

HONEST STATEMENT OF WHAT THIS DOES (epistemic, not ontological):
  Given a codified surface, it searches an EXPLICIT, FINITE hypothesis class
  for the model that best compresses the surface under a two-part Minimum
  Description Length criterion, and reports:
     - the best model found IN THAT CLASS (not "the" true generator),
     - its parameters and a runnable predictor,
     - the residual it could not compress,
     - a fit_score and the evidence in bits (model bits + residual bits
       vs. raw surface bits),
     - a structural fingerprint and a generator fingerprint.

  It does NOT claim to recover underlying reality. It claims to find the
  best explanation expressible in its language, and to be honest about the
  residual and about its own uncertainty.

THE THREE QUESTIONS IT ANSWERS (each distinct, none conflated):
  collapse(x)            -> best compressing model of x (+ residual + bits)
  same_family(a, b)      -> same MODEL CLASS?         (weak: arithmetic vs geometric)
  same_generator(a, b)   -> same model class AND params? (strong: exact rule)
  same_structure(a, b)   -> graph/figure isomorphism-class match (relabel-invariant)

GENERATIVE INVERSES:
  cast(model, vocab)     -> a new surface with the same skeleton (twin-maker)
  transcode(A, B)        -> a structural correspondence A->B (the ontology map)

The two-part MDL penalty makes Occam bite: a degree-(n-1) polynomial that
fits n points exactly pays for n parameters and loses to a degree-2 model
with a small residual. Accidental low-order recurrences are penalized the
same way. Noise is modeled: a model may fit within tolerance and report a
fit_score < 1 instead of collapsing to "incompressible."
"""
from __future__ import annotations
import math
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

OWNER = "Jacob Iannotti"
_AUTHOR = "ARCHITECT AND SOLE OWNER: Jacob Iannotti"

__all__ = [
    "collapse", "same_family", "same_generator", "same_structure", "cast",
    "transcode", "build_record_translator", "discover_twins",
    "CombinatorialSpace", "TwinBijection", "make_twin", "compose_spaces",
    "caramuel_twin_spaces", "Invariant", "InvariantError", "OWNER",
]


class InvariantError(ValueError):
    """Raised when a surface cannot be collapsed for a structural reason."""


# ---------------------------------------------------------------------------
# description-length primitives (bits)
# ---------------------------------------------------------------------------
def _dl_int(n: int) -> float:
    n = abs(int(n))
    if n == 0:
        return 2.0
    bits, x, c = 0.0, float(n), math.log2(2.382)
    while x > 1.0:
        x = math.log2(x); bits += x
    return bits + c + 1.0


def _dl_real(x: float, precision: float) -> float:
    """Bits to encode a real to a given absolute precision."""
    if not math.isfinite(x):
        return 64.0
    q = int(round(abs(x) / max(precision, 1e-18)))
    return _dl_int(q) + 1.0  # +1 sign


def _sig(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"),
                         default=str) + "::" + _AUTHOR
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _round_params(params: Dict[str, Any], nd: int = 6) -> Dict[str, Any]:
    out = {}
    for k, v in params.items():
        if isinstance(v, float):
            out[k] = round(v, nd)
        elif isinstance(v, (list, tuple)):
            out[k] = [round(x, nd) if isinstance(x, float) else x for x in v]
        elif callable(v):
            continue
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# the Invariant result
# ---------------------------------------------------------------------------
@dataclass
class Invariant:
    domain: str
    model_class: str                    # the hypothesis family that won
    params: Dict[str, Any]
    structure: Dict[str, Any]           # surface-INDEPENDENT skeleton
    model_bits: float
    residual_bits: float
    surface_bits: float
    residuals: List[Any]
    fit_score: float                    # honest name: NOT statistical confidence
    explanation: str
    _predict: Optional[Callable[[int], List[Any]]] = field(default=None, repr=False)

    @property
    def total_bits(self) -> float:
        return self.model_bits + self.residual_bits

    @property
    def compression_ratio(self) -> float:
        return self.surface_bits / self.total_bits if self.total_bits > 0 else float("inf")

    @property
    def compressible(self) -> bool:
        """Did we actually find structure (beat the raw surface) with margin?"""
        return self.total_bits < 0.85 * self.surface_bits

    @property
    def verified(self) -> bool:
        """True only if the recovered rule exactly predicted held-out terms.
        Convenience accessor over ``structure["verified"]`` (same API as
        Chiron's Invariant)."""
        return bool(self.structure.get("verified", False))

    @property
    def family_fingerprint(self) -> str:
        """Surface- AND parameter-independent: same MODEL CLASS / skeleton."""
        return _sig({"domain": self.domain, "model_class": self.model_class,
                     "structure": self.structure})

    @property
    def generator_fingerprint(self) -> str:
        """Includes rounded parameters: the EXACT rule."""
        return _sig({"domain": self.domain, "model_class": self.model_class,
                     "structure": self.structure, "params": _round_params(self.params)})

    def predict(self, n: int) -> List[Any]:
        if self._predict is None:
            raise ValueError("this invariant is not runnable")
        return self._predict(n)

    def to_dict(self) -> Dict[str, Any]:
        return {"domain": self.domain, "model_class": self.model_class,
                "params": _round_params(self.params), "structure": self.structure,
                "model_bits": round(self.model_bits, 2),
                "residual_bits": round(self.residual_bits, 2),
                "surface_bits": round(self.surface_bits, 2),
                "compression_ratio": round(self.compression_ratio, 3),
                "compressible": self.compressible,
                "fit_score": round(self.fit_score, 4),
                "family_fingerprint": self.family_fingerprint[:16],
                "generator_fingerprint": self.generator_fingerprint[:16],
                "residual_summary": _residual_summary(self.residuals),
                "explanation": self.explanation, "owner": OWNER}


def _residual_summary(res: List[Any]) -> Any:
    nums = [r for r in res if isinstance(r, (int, float)) and math.isfinite(r)]
    if not nums:
        return res if len(res) < 6 else f"{len(res)} items"
    arr = np.array(nums, dtype=float)
    return {"n": len(nums), "max_abs": round(float(np.max(np.abs(arr))), 6),
            "rms": round(float(np.sqrt(np.mean(arr ** 2))), 6)}


# ===========================================================================
# NUMERIC DOMAIN — with a noise model and a real Occam penalty
# ===========================================================================
def _numeric_precision(seq: np.ndarray) -> float:
    scale = float(np.max(np.abs(seq))) if seq.size else 1.0
    return max(1e-9, 1e-6 * (scale + 1.0))


def _score_numeric(seq: np.ndarray, predicted: np.ndarray, n_params: int,
                   param_vals: List[float], precision: float) -> Tuple[float, float, List[float]]:
    residuals = (seq - predicted).tolist()
    model_bits = _dl_int(n_params) + sum(_dl_real(p, precision) for p in param_vals) + 2.0
    residual_bits = 0.0
    for r in residuals:
        if abs(r) < precision:
            continue                       # predicted exactly -> ~free
        residual_bits += _dl_real(r, precision)
    return model_bits, residual_bits, residuals


def _cand_constant(seq, precision):
    c = float(np.mean(seq))
    pred = np.full_like(seq, c)
    mb, rb, res = _score_numeric(seq, pred, 1, [c], precision)
    return ("constant", {"c": c}, {"family": "constant"}, mb, rb, res,
            lambda n, c=c: [c] * n)


def _exact_int_view(seq, exact_ints=None):
    """The ONLY trusted route from a surface to exact integers. If the caller
    preserved python ints (threaded down from collapse_numeric), use them at
    any magnitude. Otherwise fall back to the float values — but only below
    2**53, where float64 still represents integers exactly. Above that, a
    float that LOOKS like an integer has already lost digits (the Apéry
    lesson, v0.5.0: 29-digit terms were being rounded at the front door
    before any exact solver could see them)."""
    if exact_ints is not None:
        return list(exact_ints)
    try:
        if all(float(v).is_integer() and abs(float(v)) < 2.0 ** 53 for v in seq):
            return [int(v) for v in seq]
    except (TypeError, ValueError, OverflowError):
        pass
    return None


def _cand_poly(seq, precision, max_deg=6, exact_ints=None):
    out = []
    n = len(seq)

    # --- exact path (the float purge): integer surfaces with a constant
    # d-th finite difference ARE that degree-d polynomial, exactly. Recover
    # it by Newton forward differences in integer arithmetic and predict via
    # p(m) = sum_k diff_k[0] * C(m, k) — no polyfit, no float drift, valid
    # far beyond 2^53. polyfit remains only for non-integer/noisy surfaces.
    _iv = _exact_int_view(seq, exact_ints)
    if n >= 3 and _iv is not None:
        row = _iv
        table = [row]
        for d in range(1, min(max_deg, n - 2) + 1):
            row = [row[i + 1] - row[i] for i in range(len(row) - 1)]
            table.append(row)
            if len(row) >= 2 and all(v == row[0] for v in row):
                if any(v != 0 for v in row):
                    lead = [table[k][0] for k in range(d + 1)]

                    def predict(m, _lead=list(lead), _d=d):
                        return [sum(_lead[k] * math.comb(i, k)
                                    for k in range(_d + 1)) for i in range(m)]

                    pred = np.array([float(v) for v in seq])  # exact by construction
                    mb, rb, res = _score_numeric(
                        seq, pred, d + 1, [float(v) for v in lead], precision)
                    name = "arithmetic" if d == 1 else f"polynomial_deg{d}"
                    out.append((name,
                                {"newton_coeffs": [int(v) for v in lead],
                                 "degree": d, "exact": True},
                                {"family": "polynomial", "degree": d},
                                mb, rb, res, predict))
                    return out          # exact recovery supersedes float fits
                break                   # all-zero differences: constant; let
                                        # _cand_constant own it

    x = np.arange(len(seq), dtype=float)
    for deg in range(1, min(max_deg, len(seq) - 1) + 1):
        try:
            coeffs = np.polyfit(x, seq, deg)
        except Exception:
            continue
        pred = np.polyval(coeffs, x)
        mb, rb, res = _score_numeric(seq, pred, deg + 1,
                                     [float(c) for c in coeffs], precision)
        name = "arithmetic" if deg == 1 else f"polynomial_deg{deg}"
        struct = {"family": "polynomial", "degree": deg}
        out.append((name, {"coeffs": [float(c) for c in coeffs], "degree": deg},
                    struct, mb, rb, res,
                    (lambda n, c=coeffs: list(np.polyval(c, np.arange(n))))))
    return out


def _cand_geometric(seq, precision, exact_ints=None):
    # --- exact path (the float purge): integer surfaces whose consecutive
    # ratio is a constant rational ARE geometric, exactly. Detect the ratio
    # in Fraction arithmetic and predict with it — no log-space regression,
    # no exp/round drift, valid beyond 2^53 and for negative ratios too.
    _iv = _exact_int_view(seq, exact_ints)
    if len(seq) >= 3 and _iv is not None and all(v != 0 for v in _iv):
        from fractions import Fraction
        iseq = _iv
        r = Fraction(iseq[1], iseq[0])
        if all(Fraction(iseq[i + 1], iseq[i]) == r for i in range(1, len(iseq) - 1)):
            a0 = iseq[0]

            def predict(n, _a0=a0, _r=r):
                out, cur = [], Fraction(_a0)
                for _ in range(n):
                    out.append(int(cur) if cur.denominator == 1 else float(cur))
                    cur *= _r
                return out

            pred = np.array([float(v) for v in iseq])   # exact by construction
            mb, rb, res = _score_numeric(seq, pred, 2, [float(a0), float(r)],
                                         precision)
            return ("geometric", {"a0": float(a0), "r": float(r), "exact": True},
                    {"family": "geometric"}, mb, rb, res, predict)

    if np.any(seq <= 0):
        return None
    logs = np.log(seq)
    x = np.arange(len(seq), dtype=float)
    slope, intercept = np.polyfit(x, logs, 1)
    r, a0 = math.exp(slope), math.exp(intercept)
    pred = a0 * (r ** x)
    mb, rb, res = _score_numeric(seq, pred, 2, [a0, r], precision)
    return ("geometric", {"a0": a0, "r": r}, {"family": "geometric"}, mb, rb, res,
            lambda n, a0=a0, r=r: [a0 * (r ** i) for i in range(n)])


def _cand_linear_recurrence(seq, precision, max_order=4, exact_ints=None):
    n = len(seq)
    out = []
    for p in range(2, min(max_order, n // 2) + 1):
        rows = n - p
        if rows < p + 1:                  # require OVERDETERMINED fit (anti-accident)
            continue
        A = np.array([seq[i:i + p] for i in range(rows)])
        b = seq[p:p + rows]
        try:
            coeffs, *_ = np.linalg.lstsq(A, b, rcond=None)
        except np.linalg.LinAlgError:
            continue
        seeds = list(seq[:p])
        cc = [float(c) for c in coeffs]

        # --- exact rational refinement (the repunit fix) -------------------
        # lstsq coefficients carry float error that COMPOUNDS when the
        # recurrence is iterated (found live on OEIS A002275, where
        # a(n)=11a(n-1)-10a(n-2) drifted past the old tolerance). For integer
        # surfaces, snap the coefficients to nearby small rationals and demand
        # they reproduce EVERY shown term in exact Fraction arithmetic; only
        # then use an exact integer predictor immune to drift.
        exact = None
        _iv = _exact_int_view(seq, exact_ints)
        if _iv is not None:
            from fractions import Fraction
            snapped = [Fraction(c).limit_denominator(64) for c in cc]
            iseq = _iv
            gen_ex = [Fraction(s) for s in iseq[:p]]
            ok_ex = True
            for i in range(p, n):
                v = sum(snapped[j] * gen_ex[i - p + j] for j in range(p))
                if v != iseq[i]:
                    ok_ex = False
                    break
                gen_ex.append(v)
            if ok_ex:
                exact = snapped

        if exact is not None:
            cc = [float(c) for c in exact]
            pred = np.array([float(x) for x in seq], dtype=float)  # exact reproduction

            def predict(m, seeds=None, cc=None, p=p, _ex=list(exact),
                        _s=[int(x) for x in seq[:p]]):
                from fractions import Fraction
                o = [Fraction(s) for s in _s]
                while len(o) < m:
                    o.append(sum(_ex[j] * o[-p + j] for j in range(p)))
                return [int(x) if x.denominator == 1 else float(x) for x in o[:m]]
        else:
            gen = list(seeds)
            for i in range(p, n):
                gen.append(float(np.dot(coeffs, gen[i - p:i])))
            pred = np.array(gen)

            def predict(m, seeds=list(seeds), cc=cc, p=p):
                o = list(seeds)
                while len(o) < m:
                    o.append(sum(cc[j] * o[-p + j] for j in range(p)))
                return o[:m]
        mb, rb, res = _score_numeric(seq, pred, 2 * p, cc + list(seeds), precision)
        out.append((f"linear_recurrence_order{p}",
                    {"coeffs": cc, "seeds": [float(s) for s in seeds]},
                    {"family": "linear_recurrence", "order": p}, mb, rb, res, predict))
    return out


def _cand_periodic(seq, precision):
    n = len(seq)
    out = []
    for period in range(1, n // 2 + 1):
        reps = n / period
        if reps < 2:
            continue
        unit = seq[:period]
        pred = np.array([unit[i % period] for i in range(n)])
        mb, rb, res = _score_numeric(seq, pred, period, list(unit), precision)
        out.append((f"periodic_{period}", {"unit": [float(u) for u in unit],
                    "period": period}, {"family": "periodic", "period": period},
                    mb, rb, res, lambda m, u=list(unit), p=period:
                    [u[i % p] for i in range(m)]))
    return out


def _cand_factorial_products(seq, precision, exact_ints=None):
    """Factorial / running-product families: a_n = a_{n-1} * (linear in n).
    Catches n!, double factorials, Catalan-like products, etc.

    On integer surfaces this runs in EXACT Fraction arithmetic end to end
    (2026-07-11, live OEIS A001147: the float ratio fit reproduced the shown
    window but drifted in the last digits of the 15th and 16th terms — the
    repunit defect class in another family). alpha/beta are solved from two
    exact ratios and must reproduce EVERY ratio exactly, or there is no
    candidate; the predictor multiplies Fractions, never floats."""
    n = len(seq)
    if n < 4 or np.any(seq == 0):
        return None

    _iv = _exact_int_view(seq, exact_ints)
    if _iv is not None:
        from fractions import Fraction
        iseq = _iv
        rat = [Fraction(iseq[k + 1], iseq[k]) for k in range(n - 1)]
        # r_k = alpha*k + beta for k = 1..n-1, solved exactly from the first
        # two ratios, then REQUIRED to hold exactly everywhere.
        alpha_ex = rat[1] - rat[0]
        beta_ex = rat[0] - alpha_ex
        if any(rat[k - 1] != alpha_ex * k + beta_ex for k in range(1, n)):
            return None
        a0_ex = Fraction(iseq[0])

        def predict(m, _a0=a0_ex, _al=alpha_ex, _be=beta_ex):
            from fractions import Fraction
            o = [_a0]
            for k in range(1, m):
                o.append(o[-1] * (_al * k + _be))
            return [int(x) if x.denominator == 1 else float(x) for x in o[:m]]
        pred = np.array([float(x) for x in seq], dtype=float)  # exact reproduction
        mb, rb, res = _score_numeric(seq, pred, 3,
                                     [float(a0_ex), float(alpha_ex), float(beta_ex)],
                                     precision)
        return ("multiplicative_ratio",
                {"a0": float(a0_ex), "ratio_slope": float(alpha_ex),
                 "ratio_intercept": float(beta_ex), "exact": True},
                {"family": "multiplicative"}, mb, rb, res, predict)

    # non-integer surfaces: the float path remains, and _holdout_verify's
    # 2^53 guard plus exact-equality rule keep it from stamping big integers.
    ratios = seq[1:] / seq[:-1]                       # r_k = a_{k+1}/a_k
    x = np.arange(1, n, dtype=float)
    # is the ratio itself linear/affine in k?  r_k ~ alpha*k + beta
    try:
        alpha, beta = np.polyfit(x, ratios, 1)
    except Exception:
        return None
    a0 = float(seq[0])

    def predict(m, a0=a0, alpha=float(alpha), beta=float(beta)):
        o = [a0]
        for k in range(1, m):
            o.append(o[-1] * (alpha * k + beta))
        return o[:m]
    pred = np.array(predict(n))
    mb, rb, res = _score_numeric(seq, pred, 3, [a0, float(alpha), float(beta)], precision)
    return ("multiplicative_ratio", {"a0": a0, "ratio_slope": float(alpha),
            "ratio_intercept": float(beta)},
            {"family": "multiplicative"}, mb, rb, res, predict)


def _cand_alternating(seq, precision):
    """Sign-alternating envelope: a_n = (-1)^n * b_n where b_n is smooth.
    Detect, strip the sign, and fit the envelope as a polynomial/geometric."""
    n = len(seq)
    if n < 5:
        return None
    signs = np.sign(seq)
    if not np.all(signs[signs != 0][::2] * signs[signs != 0][1::2][:len(signs[signs != 0][::2])] <= 0):
        # crude: require strict alternation among nonzero terms
        nz = signs[signs != 0]
        if len(nz) < 4 or not np.all(nz[:-1] * nz[1:] < 0):
            return None
    env = np.abs(seq)
    x = np.arange(n, dtype=float)
    best = None
    for deg in (1, 2, 3):
        try:
            coeffs = np.polyfit(x, env, deg)
        except Exception:
            continue
        envpred = np.polyval(coeffs, x)
        sgn0 = float(signs[0]) if signs[0] != 0 else 1.0
        pred = sgn0 * ((-1.0) ** x) * envpred
        mb, rb, res = _score_numeric(seq, pred, deg + 2,
                                     [float(c) for c in coeffs] + [sgn0], precision)
        cand = ("alternating_polynomial", {"sign0": sgn0, "envelope_coeffs":
                [float(c) for c in coeffs], "degree": deg},
                {"family": "alternating", "envelope_degree": deg}, mb, rb, res,
                (lambda m, c=coeffs, s=sgn0: list(s * ((-1.0) ** np.arange(m))
                                                   * np.polyval(c, np.arange(m)))))
        if best is None or (cand[3] + cand[4]) < (best[3] + best[4]):
            best = cand
    return best


def _cand_holonomic_exact(seq, precision, max_order=2, max_pdeg=3, exact_ints=None):
    """Exact P-recursive recovery for integer surfaces (the float purge,
    continued): find integer-polynomial coefficients p_j with

        sum_{j=0..r} p_j(n) * a(n+j) = 0

    by EXACT rational nullspace (Fraction Gaussian elimination — no SVD, no
    thresholds), demand exact reproduction of every shown term by forward
    iteration, and predict in exact arithmetic. This closes the boundary the
    live-OEIS run identified: order-2 P-recurrences (Motzkin, Schröder) sit
    one step beyond single-term rational ratios. The overdetermination
    margin is rows >= unknowns + 1 (the float path demanded +2, which made
    candidates unformable on holdout prefixes — the second reason Motzkin
    could never verify); the real gate remains exact holdout prediction.
    pdeg 3 (v0.5.0) reaches the Apéry class — with the evidence economics
    made visible: a (r=2, pdeg=3) rule has 12 unknowns, so it cannot even
    FORM on a 12-term surface; rich rules require the deep-evidence
    protocol tier (20 shown terms) before verification is possible at all.
    That is MDL's appetite, not a tuning choice.
    pdeg >= 1 by design: degree-0 coefficients ARE constant-coefficient
    recurrences, which _cand_linear_recurrence already owns."""
    from fractions import Fraction

    n = len(seq)
    _iv = _exact_int_view(seq, exact_ints)
    if n < 7 or _iv is None:
        return []
    a = _iv
    out = []
    combos = sorted(((r, d) for r in range(1, max_order + 1)
                     for d in range(1, max_pdeg + 1)),
                    key=lambda rd: (rd[0] + 1) * (rd[1] + 1))
    for r, pdeg in combos:
        ncols = (r + 1) * (pdeg + 1)
        rows = n - r
        if rows < ncols + 1:
            continue
        # homogeneous system M x = 0 over Q, columns ordered (j, n-power)
        M = [[Fraction(i ** dp) * a[i + j]
              for j in range(r + 1) for dp in range(pdeg + 1)]
             for i in range(rows)]
        # exact Gaussian elimination to row-echelon form
        pivots, prow = [], 0
        for col in range(ncols):
            piv = next((k for k in range(prow, rows) if M[k][col] != 0), None)
            if piv is None:
                continue
            M[prow], M[piv] = M[piv], M[prow]
            inv = M[prow][col]
            M[prow] = [v / inv for v in M[prow]]
            for k in range(rows):
                if k != prow and M[k][col] != 0:
                    f = M[k][col]
                    M[k] = [vk - f * vp for vk, vp in zip(M[k], M[prow])]
            pivots.append(col)
            prow += 1
            if prow == rows:
                break
        free = [c for c in range(ncols) if c not in pivots]
        if not free:
            continue                        # trivial nullspace only
        if len(free) > 1:
            # Nullspace dimension > 1: the data admits MULTIPLE rules of
            # this (r, pdeg) class, so any basis vector is an arbitrary
            # mixture — it reproduces the shown terms (they ARE the
            # constraint rows) yet predicts whatever the mixture says. An
            # ambiguous rule is not a rule; refuse this class outright.
            # (Found via Apéry, v0.5.0: on a 15-term holdout prefix the
            # (2,3) system left a 2-dim nullspace and the mixture's tail
            # disagreed with OEIS — the holdout caught it, but uniqueness
            # belongs in the solver, not only in the safety net.)
            continue

        def _basis_vector(fv):
            x = [Fraction(0)] * ncols
            x[fv] = Fraction(1)
            for k, col in enumerate(pivots):
                x[col] = -sum(M[k][c] * x[c] for c in free)
            mult = 1
            for v in x:
                mult = mult * v.denominator // math.gcd(mult, v.denominator)
            ix = [int(v * mult) for v in x]
            g = 0
            for v in ix:
                g = math.gcd(g, abs(v))
            return [v // g for v in ix] if g > 1 else ix

        def _rank_one(polys_):
            """True if all p_j are pairwise proportional — then the
            recurrence is a polynomial multiple of a CONSTANT-coefficient
            one, which _cand_linear_recurrence canonically owns. Without
            this exclusion the solver dresses Fibonacci up as holonomic."""
            vecs = [p for p in polys_ if any(c != 0 for c in p)]
            for a_ in range(len(vecs)):
                for b_ in range(a_ + 1, len(vecs)):
                    u, w = vecs[a_], vecs[b_]
                    for i1 in range(len(u)):
                        for i2 in range(i1 + 1, len(u)):
                            if u[i1] * w[i2] != u[i2] * w[i1]:
                                return False
            return True

        polys = None
        for fv in free:                     # first genuinely-polynomial basis vector
            ix = _basis_vector(fv)
            cand_polys = [ix[j * (pdeg + 1):(j + 1) * (pdeg + 1)]
                          for j in range(r + 1)]
            if all(c == 0 for c in cand_polys[r]):
                continue                    # leading coefficient must live
            if _rank_one(cand_polys):
                continue                    # constant-coefficient in disguise
            polys = cand_polys
            break
        if polys is None:
            continue

        def pval(p, x_):
            return sum(p[dp] * (x_ ** dp) for dp in range(len(p)))

        # exact reproduction of every shown term, or no candidate at all
        gen = [Fraction(v) for v in a[:r]]
        ok = True
        for i in range(0, n - r):
            lead = pval(polys[r], i)
            if lead == 0:
                ok = False
                break
            nxt = -Fraction(sum(pval(polys[j], i) * gen[i + j]
                                for j in range(r)), 1) / lead
            if nxt != a[i + r]:
                ok = False
                break
            gen.append(nxt)
        if not ok:
            continue

        def predict(m, _a=a[:r], _polys=[list(p) for p in polys], _r=r):
            o = [Fraction(v) for v in _a]
            i = 0
            while len(o) < m:
                lead = pval(_polys[_r], i)
                if lead == 0:
                    raise InvariantError("leading polynomial vanishes; "
                                         "prediction refused")
                o.append(-sum(pval(_polys[j], i) * o[i + j]
                              for j in range(_r)) / lead)
                i += 1
            return [int(v) if v.denominator == 1 else float(v) for v in o[:m]]

        pred = np.array([float(v) for v in a], dtype=float)  # exact by construction
        mb, rb, res = _score_numeric(seq, pred, ncols,
                                     [float(c) for c in ix], precision)
        out.append((f"holonomic_r{r}_p{pdeg}",
                    {"poly_coeffs": polys, "order": r, "pdeg": pdeg, "exact": True},
                    {"family": "holonomic", "order": r, "pdeg": pdeg},
                    mb, rb, res, predict))
    return out


def _cand_holonomic(seq, precision, max_order=3, max_pdeg=2):
    """P-recursive / holonomic recovery: find a recurrence whose COEFFICIENTS
    are polynomials in n —  sum_{j=0..r} p_j(n) * a_{n+j} = 0.  This is the big
    jump: it captures Catalan numbers, central binomial coefficients, n!, and
    any C-finite or P-finite sequence, which fixed-coefficient recurrences miss.
    Solved as a homogeneous linear system over the data; verified by forward
    iteration (solving the leading coefficient for the next term)."""
    n = len(seq)
    if n < 8:
        return None
    s = seq.astype(float)
    for r in range(1, max_order + 1):           # recurrence order
        for pdeg in range(1, max_pdeg + 1):     # poly-coeff degree >=1 (new cap.)
            ncols = (r + 1) * (pdeg + 1)
            rows = n - r
            if rows < ncols + 2:                # demand an overdetermined system
                continue
            M = np.zeros((rows, ncols))
            for i in range(rows):
                col = 0
                for j in range(r + 1):
                    for dpow in range(pdeg + 1):
                        M[i, col] = (i ** dpow) * s[i + j]
                        col += 1
            # null space via SVD; smallest singular vector
            try:
                _, sv, Vt = np.linalg.svd(M)
            except np.linalg.LinAlgError:
                continue
            if sv[-1] > 1e-6 * max(1.0, sv[0]):   # no genuine null vector
                continue
            coef = Vt[-1]                          # the polynomial-coeff vector
            # build p_j(n) polynomials (length pdeg+1 each)
            polys = [coef[j * (pdeg + 1):(j + 1) * (pdeg + 1)] for j in range(r + 1)]

            def pval(p, x):
                return sum(p[d] * (x ** d) for d in range(len(p)))

            def predict(m, s=s, r=r, polys=polys, n0=n):
                o = list(s[:max(r, min(len(s), m))])
                # extend using the leading coefficient p_r(i) for a_{i+r}
                i = len(o) - r
                while len(o) < m:
                    lead = pval(polys[r], i)
                    if abs(lead) < 1e-9:
                        o.append(float("nan")); i += 1; continue
                    acc = sum(pval(polys[j], i) * o[i + j] for j in range(r))
                    o.append(-acc / lead)
                    i += 1
                return o[:m]
            try:
                pred = np.array(predict(n), dtype=float)
            except Exception:
                continue
            if not np.all(np.isfinite(pred)):
                continue
            mb, rb, res = _score_numeric(s, pred, ncols,
                                         [float(c) for c in coef], precision)
            # only worth reporting if it reproduces the data well
            if rb < 0.25 * (sum(_dl_real(float(x), precision) for x in s)):
                return (f"holonomic_r{r}_p{pdeg}",
                        {"order": r, "coeff_degree": pdeg,
                         "polys": [[float(x) for x in p] for p in polys]},
                        {"family": "holonomic", "order": r, "coeff_degree": pdeg},
                        mb, rb, res, predict)
    return None


def _cand_power_law(seq, precision):
    """a_n ~ c * n^p  (n>=1). Log-log linear fit."""
    n = len(seq)
    if n < 4 or np.any(seq <= 0):
        return None
    idx = np.arange(1, n + 1, dtype=float)
    lx, ly = np.log(idx), np.log(seq)
    try:
        p, logc = np.polyfit(lx, ly, 1)
    except Exception:
        return None
    c = math.exp(logc)
    pred = c * idx ** p
    mb, rb, res = _score_numeric(seq, pred, 2, [c, float(p)], precision)
    return ("power_law", {"c": c, "exponent": float(p)}, {"family": "power_law"},
            mb, rb, res, lambda m, c=c, p=float(p): [c * (i + 1) ** p for i in range(m)])


def _best_numeric_model(arr: np.ndarray, precision: float, exact_ints=None) -> Optional[Tuple]:
    cands: List[Tuple] = []
    c = _cand_constant(arr, precision)
    if c:
        cands.append(c)
    cands += _cand_poly(arr, precision, exact_ints=exact_ints)
    g = _cand_geometric(arr, precision, exact_ints=exact_ints)
    if g:
        cands.append(g)
    cands += _cand_linear_recurrence(arr, precision, exact_ints=exact_ints)
    cands += _cand_periodic(arr, precision)
    try:
        hx = _cand_holonomic_exact(arr, precision, exact_ints=exact_ints)
    except Exception:
        hx = []
    cands += hx
    # exact holonomic supersedes the float/SVD path on integer surfaces
    _holo_fns = () if hx else (_cand_holonomic,)
    try:
        r = _cand_factorial_products(arr, precision, exact_ints=exact_ints)
    except Exception:
        r = None
    if r:
        cands.append(r)
    for fn in (_cand_alternating, _cand_power_law, *_holo_fns):
        try:
            r = fn(arr, precision)
        except Exception:
            r = None
        if r:
            cands.append(r)
    if not cands:
        return None
    # Integer-surface guard (found live on OEIS A002203, companion Pell): a
    # float/SVD holonomic rule has enough free parameters to overfit, scoring a
    # SHORTER description than the true exact rule and then clearing a prefix
    # holdout it happens to match within the shown window — a false stamp
    # (seed predicted 551612 vs 551614; Chiron, which classifies it as the
    # exact order-2 linear recurrence, is correct). Rule: if ANY candidate
    # reproduces the integer surface EXACTLY in integer arithmetic, the
    # non-exact holonomic path must not be allowed to mask it. Only float
    # holonomic is dropped, and only when a genuine exact reproducer exists, so
    # no currently-verifying case changes.
    if exact_ints is not None:
        def _reproduces_exactly(cand):
            try:
                pr = cand[6](len(exact_ints))
            except Exception:
                return False
            return (len(pr) >= len(exact_ints) and
                    all(isinstance(pr[i], int) and pr[i] == exact_ints[i]
                        for i in range(len(exact_ints))))
        if any(_reproduces_exactly(c) for c in cands):
            cands = [c for c in cands
                     if not (c[0].startswith("holonomic")
                             and not c[1].get("exact"))]
    # Occam with a CANONICAL tie-break: among models that compress within a
    # couple of bits of the best, prefer the simpler/more-canonical family
    # (so a straight line reads as 'arithmetic', not 'power_law c*n^1').
    RANK = {"constant": 0, "arithmetic": 1, "geometric": 2}

    def rank(name):
        if name in RANK:
            return RANK[name]
        if name.startswith("polynomial_deg"):
            return 3 + int(name.split("deg")[1])
        if name.startswith("linear_recurrence_order"):
            return 12 + int(name.split("order")[1])
        if name.startswith("holonomic"):
            return 22
        return {"power_law": 25, "multiplicative_ratio": 26,
                "alternating_polynomial": 27}.get(name, 40)  # periodic last
    best_total = min(c[3] + c[4] for c in cands)
    near = [c for c in cands if (c[3] + c[4]) <= best_total + 2.0]
    return min(near, key=lambda c: (rank(c[0]), c[3] + c[4]))


def _holdout_verify(arr: np.ndarray, precision: float, model_class: str,
                    exact_ints=None) -> Tuple[bool, int, int, float]:
    """Prove the rule, don't assume it: refit on a PREFIX and predict the
    held-out tail. Returns (verified, correct, held_out, evidence_bits)."""
    n = len(arr)
    if n < 6:
        return (False, 0, 0, 0.0)
    h = max(2, n // 4)
    prefix = arr[:n - h]
    # The refit must judge the prefix at the PREFIX's own scale. Reusing the
    # full-surface precision breaks fast-growing sequences: Apéry grows ~33x
    # per term, so a tail-dominated tolerance (~1e26) makes every prefix
    # residual quantize to zero and a one-parameter constant 'wins' the
    # refit, sinking the holdout (v0.5.0 lesson).
    best_pref = _best_numeric_model(
        prefix, _numeric_precision(prefix),
        exact_ints=exact_ints[:n - h] if exact_ints is not None else None)
    if best_pref is None:
        return (False, 0, h, 0.0)
    pname, _, _, _, _, _, predict = best_pref
    # Held-out evidence must scale with model capacity (2026-07-11, A002808):
    # an order-4 recurrence (8 free parameters) fit the composites EXACTLY
    # through all 12 shown terms — no in-window test can catch it — and was
    # then judged by only 3 held-out terms. A rule with 2p parameters buys a
    # stamp only from at least p held-out hits; below that, refuse.
    m_ord = re.match(r"linear_recurrence_order(\d+)$", pname or "")
    if m_ord and h < int(m_ord.group(1)):
        return (False, 0, h, 0.0)
    try:
        raw_full = list(predict(n))
        raw = raw_full[n - h:]
    except Exception:
        return (False, 0, h, 0.0)
    actual = exact_ints[n - h:] if exact_ints is not None else arr[n - h:]
    int_surface = exact_ints is not None or bool(np.all(np.mod(arr, 1) == 0))
    # A rule that misfits the very prefix it was fitted on has recovered
    # nothing — tail hits are then coincidence, and on small alphabets the
    # coincidence is cheap (2026-07-11, A000002 Kolakoski: a residual-bearing
    # periodic_3 hit 3 held-out terms at ~1/8 odds). On integer surfaces the
    # refit must reproduce its OWN prefix exactly before tail hits count.
    if int_surface:
        pref_actual = exact_ints[:n - h] if exact_ints is not None else arr[:n - h]
        for p_val, a_val in zip(raw_full[:n - h], pref_actual):
            try:
                if isinstance(p_val, int):
                    pi, close = p_val, True
                else:
                    f = float(p_val)
                    if not math.isfinite(f) or abs(f) >= 2.0 ** 53:
                        return (False, 0, h, 0.0)
                    pi = int(round(f))
                    close = abs(f - pi) <= max(precision, 1e-6)
                truth = a_val if isinstance(a_val, int) else int(round(float(a_val)))
                if not (close and pi == truth):
                    return (False, 0, h, 0.0)
            except (OverflowError, ValueError):
                return (False, 0, h, 0.0)
    if int_surface:
        # "verified" must mean EXACT equality on integer surfaces. The old
        # 1e-6 relative tolerance let a drifted recurrence stamp repunits
        # (live OEIS A002275) — at a(n)~1e10 it forgave errors of ~1e4.
        hits = 0
        for p_val, a_val in zip(raw, actual):
            try:
                if isinstance(p_val, int):
                    pi, close = p_val, True
                else:
                    f = float(p_val)
                    if not math.isfinite(f) or abs(f) >= 2.0 ** 53:
                        continue  # float cannot certify exactness up here
                    pi = int(round(f))
                    close = abs(f - pi) <= max(precision, 1e-6)
                truth = a_val if isinstance(a_val, int) else int(round(float(a_val)))
                if close and pi == truth:
                    hits += 1
            except (OverflowError, ValueError):
                continue
    else:
        pred = np.array([float(x) for x in raw], dtype=float)
        tol = np.maximum(precision, 1e-6 * (np.abs(actual) + 1.0))
        hits = int(np.sum(np.abs(pred - actual) < tol))
    # evidence = bits you'd have needed to send the held-out tail WITHOUT the rule
    evidence = float(sum(_dl_real(float(x), precision) for x in actual)) if hits == h else 0.0
    # verification is about PREDICTIVE POWER, not label stability: a rule
    # recovered from the prefix that exactly predicts the unseen tail is
    # verified regardless of what family name it carries.
    verified = (hits == h)
    return (verified, hits, h, evidence)


def collapse_numeric(seq: List[float]) -> Invariant:
    try:
        arr = np.array([float(x) for x in seq], dtype=float)
    except (TypeError, ValueError) as e:
        raise InvariantError(f"numeric collapse needs numbers: {e}") from e
    if arr.size == 0:
        raise InvariantError("cannot collapse an empty sequence")
    if not np.all(np.isfinite(arr)):
        return Invariant("numeric", "non_finite", {"values": list(arr)},
                         {"family": "none"}, 0.0, 0.0, 0.0, list(arr), 0.0,
                         "Sequence contains NaN/inf; no invariant over "
                         "non-finite values (honest negative).")
    if arr.size < 3:
        return Invariant("numeric", "too_short", {"values": list(arr)},
                         {"family": "none"}, 0.0, 0.0, 0.0, list(arr), 0.0,
                         "Need at least 3 terms to propose a generator.")
    precision = _numeric_precision(arr)
    surface_bits = sum(_dl_real(float(x), precision) for x in arr) + _dl_int(len(arr))

    # Preserve EXACT integers when the caller provided them (the Apéry fix):
    # float64 corrupts integers beyond 2**53 at the front door, so the exact
    # list must ride alongside the float array for the exact solvers and for
    # the holdout truth. Floats that merely look integral are trusted only
    # below 2**53, via _exact_int_view's fallback.
    exact_ints = None
    if all(isinstance(x, (int, np.integer)) and not isinstance(x, bool)
           for x in seq):
        exact_ints = [int(x) for x in seq]

    best = _best_numeric_model(arr, precision, exact_ints=exact_ints)
    if best is None:
        return Invariant("numeric", "incompressible", {"values": list(arr)},
                         {"family": "none"}, surface_bits, 0.0, surface_bits,
                         list(arr), 0.0,
                         "No model in the hypothesis class compresses this "
                         "sequence (honest negative).")
    name, params, structure, mb, rb, res, predict = best
    total = mb + rb
    fit = max(0.0, 1.0 - (rb / max(surface_bits, 1e-9)))
    verified, hits, h, evidence = _holdout_verify(arr, precision, name,
                                                   exact_ints=exact_ints)
    # The same evidence rule the holdout refit obeys, applied to the
    # FULL-surface winner (2026-07-11, A002808): an order-p recurrence may
    # describe the surface, but it cannot STAMP unless the holdout offered
    # at least p held-out terms (h = max(2, n // 4)).
    m_ord = re.match(r"linear_recurrence_order(\d+)$", name or "")
    if m_ord and max(2, len(arr) // 4) < int(m_ord.group(1)):
        verified = False
    structure = dict(structure)
    structure["verified"] = bool(verified)
    inv = Invariant("numeric", name, params, structure, mb, rb, surface_bits,
                    res, fit, "", _predict=predict)
    comp = "compresses" if inv.compressible else "does NOT meaningfully compress"
    rsum = _residual_summary(res)
    rms = rsum.get('rms', 0) if isinstance(rsum, dict) else rsum
    if verified:
        inv.explanation = (
            f"VERIFIED generator '{name}' {_round_params(params)}. Recovered "
            f"from the first {len(arr) - h} terms, this rule then EXACTLY "
            f"predicts all {h} held-out terms — {evidence:.0f} bits of data it "
            f"had never seen, reproduced from a {_param_count(params)}-parameter "
            f"rule. That is proof it captured the law, not an artifact of "
            f"fitting. Compresses {surface_bits:.0f}->{total:.0f} bits "
            f"(ratio {inv.compression_ratio:.2f}).")
    else:
        inv.explanation = (
            f"Best model in class: '{name}' {_round_params(params)}. {comp.title()} "
            f"the surface ({surface_bits:.0f}->{total:.0f} bits, ratio "
            f"{inv.compression_ratio:.2f}; residual rms {rms}; fit {fit:.3f}). "
            f"Held-out prediction: {hits}/{h} — treat as a candidate, not yet "
            f"verified.")
    return inv


def _param_count(params: Dict[str, Any]) -> int:
    n = 0
    for v in params.values():
        if isinstance(v, (list, tuple)):
            n += len(v)
        elif isinstance(v, (int, float)):
            n += 1
    return max(1, n)


# ===========================================================================
# STRING / TRANSFORM DOMAINS
# ===========================================================================
def collapse_string(s: str) -> Invariant:
    n = len(s); alpha = max(2, len(set(s)))
    surface_bits = n * math.log2(alpha) + _dl_int(n)
    for period in range(1, n // 2 + 1):
        if all(s[i] == s[i % period] for i in range(n)):
            mb = period * math.log2(alpha) + _dl_int(period) + 2
            inv = Invariant("string", f"periodic_{period}",
                            {"unit": s[:period], "period": period},
                            {"family": "periodic", "period": period}, mb, 0.0,
                            surface_bits, [], 1.0, "",
                            _predict=lambda m, u=s[:period]: "".join(u[i % len(u)] for i in range(m)))
            inv.explanation = (f"Periodic string, unit '{s[:period]}' "
                               f"(period {period}); ratio {inv.compression_ratio:.2f}.")
            return inv
    if n > 1 and s == s[::-1]:
        half = s[:(n + 1) // 2]
        mb = len(half) * math.log2(alpha) + 3
        inv = Invariant("string", "palindrome", {"half": half, "length": n},
                        {"family": "mirror_symmetry"}, mb, 0.0, surface_bits,
                        [], 1.0, "")
        inv.explanation = f"Mirror symmetry (palindrome); invariant is half '{half}'."
        return inv
    return Invariant("string", "incompressible", {"value": s}, {"family": "none"},
                     surface_bits, 0.0, surface_bits, list(s), 0.0,
                     "No structural model found (honest negative).")


def collapse_transform(a: str, b: str) -> Invariant:
    if len(a) != len(b):
        return Invariant("transform", "no_uniform_transform", {"a": a, "b": b},
                         {"family": "none"}, 1e9, 1e9, 1e9, [], 0.0,
                         "Different lengths; no uniform symbol transform.")
    shifts = [(ord(cb.upper()) - ord(ca.upper())) % 26
              for ca, cb in zip(a, b) if ca.isalpha() and cb.isalpha()]
    if shifts and len(set(shifts)) == 1:
        k = shifts[0]
        inv = Invariant("transform", "caesar_shift", {"shift": k},
                        {"family": "affine_cipher", "kind": "shift"},
                        _dl_int(k) + 2, 0.0, len(a) * math.log2(26), [], 1.0, "")
        inv.params["decode"] = lambda s, k=k: "".join(
            chr((ord(c.upper()) - 65 - k) % 26 + 65) if c.isalpha() else c for c in s)
        inv.explanation = (f"Both surfaces share one generator: Caesar shift {k} "
                           f"(decode = shift by -{k}).")
        return inv
    mapping: Dict[str, str] = {}
    for ca, cb in zip(a, b):
        if ca in mapping and mapping[ca] != cb:
            return Invariant("transform", "no_consistent_transform", {"a": a, "b": b},
                             {"family": "none"}, 1e9, 1e9, 1e9, [], 0.0,
                             "No consistent symbol-level transform (honest negative).")
        mapping[ca] = cb
    inv = Invariant("transform", "substitution", {"map": mapping},
                    {"family": "substitution_cipher", "alphabet_size": len(mapping)},
                    len(mapping) * 5 + 2, 0.0, len(a) * math.log2(max(2, len(set(a + b)))),
                    [], 1.0, "")
    inv.explanation = f"Monoalphabetic substitution over {len(mapping)} symbols."
    return inv


# ===========================================================================
# GRAPH DOMAIN — relabel-invariant fingerprint + WL node roles
# ===========================================================================
def _adjacency(nodes: List[str], edges: List[Tuple[str, str]]):
    idx = {nd: i for i, nd in enumerate(nodes)}
    n = len(nodes)
    A = np.zeros((n, n), dtype=float)
    for u, v in edges:
        if u in idx and v in idx:
            A[idx[u], idx[v]] = 1.0
            A[idx[v], idx[u]] = 1.0
    return A, idx


def _graph_invariants(nodes: List[str], edges: List[Tuple[str, str]],
                      spectral_round: int = 4) -> Dict[str, Any]:
    A, _ = _adjacency(nodes, edges)
    n = len(nodes)
    deg = A.sum(axis=1)
    degree_seq = sorted(int(d) for d in deg)
    tri = int(round(np.trace(A @ A @ A) / 6)) if n else 0
    try:
        eig = np.linalg.eigvalsh(A) if n else np.array([])
        spectrum = sorted(round(float(e), spectral_round) for e in eig)
    except np.linalg.LinAlgError:
        spectrum = []
    return {"family": "graph", "n_nodes": n, "n_edges": int(A.sum() / 2),
            "degree_sequence": degree_seq, "triangle_count": tri,
            "adjacency_spectrum": spectrum}


def collapse_graph(nodes: List[str], edges: List[Tuple[str, str]]) -> Invariant:
    structure = _graph_invariants(nodes, edges)
    surface_bits = len(nodes) * 6.0 + len(edges) * 8.0
    model_bits = (structure["n_nodes"] * 1.5 + len(structure["degree_sequence"]) * 1.2
                  + len(structure["adjacency_spectrum"]) * 1.2)
    inv = Invariant("graph", "graph_structure", {"nodes": nodes, "edges": edges},
                    structure, model_bits, 0.0, surface_bits, [], 1.0, "")
    inv.explanation = (
        f"Recovered the graph's relabel-invariant structure: "
        f"{structure['n_nodes']} nodes, {structure['n_edges']} edges, "
        f"{structure['triangle_count']} triangles, degree signature "
        f"{structure['degree_sequence'][:8]}{'...' if len(structure['degree_sequence'])>8 else ''}, "
        f"adjacency spectrum (rounded). Two graphs with this fingerprint are "
        f"isomorphism-class candidates regardless of node labels.")
    return inv


def _distance_profile(nd: str, adj: Dict[str, List[str]]) -> str:
    """Sorted multiset of shortest-path distances from a node — a strong,
    relabel-invariant signature of the node's GLOBAL position in the graph."""
    seen = {nd: 0}
    frontier = [nd]
    d = 0
    while frontier:
        d += 1
        nxt = []
        for u in frontier:
            for w in adj[u]:
                if w not in seen:
                    seen[w] = d; nxt.append(w)
        frontier = nxt
    return ",".join(str(x) for x in sorted(seen.values()))


def wl_signatures(nodes: List[str], edges: List[Tuple[str, str]],
                  rounds: int = 4) -> Dict[str, str]:
    """Weisfeiler-Leman colour-refinement, seeded with each node's global
    distance profile, giving a strong relabel-invariant structural role per
    node. The basis for deterministic node-to-node correspondence. Nodes that
    remain identically coloured are GENUINELY structurally interchangeable —
    the engine reports them ambiguous rather than guessing between them."""
    adj: Dict[str, List[str]] = {nd: [] for nd in nodes}
    for u, v in edges:
        if u in adj and v in adj:
            adj[u].append(v); adj[v].append(u)
    # seed colour = (degree, global distance profile) — already very discriminating
    colour = {nd: hashlib.sha1(
        (str(len(adj[nd])) + "#" + _distance_profile(nd, adj)).encode()
    ).hexdigest()[:10] for nd in nodes}
    for _ in range(rounds):
        newc = {}
        for nd in nodes:
            neigh = sorted(colour[m] for m in adj[nd])
            newc[nd] = hashlib.sha1(
                (colour[nd] + "|" + ",".join(neigh)).encode()).hexdigest()[:10]
        colour = newc
    return colour


# ===========================================================================
# FIGURE-GRAPH DOMAIN (the plates) — robust shared-skeleton fingerprint
# ===========================================================================
def collapse_figuregraph(walks: Dict[str, List[str]],
                         tokens: Optional[Dict[str, str]] = None,
                         invariants: Optional[Dict[str, Any]] = None) -> Invariant:
    walk_names = sorted(walks.keys())
    distinct = {n for w in walks.values() for n in w}
    walk_shape = sorted(len(walks[wn]) for wn in walk_names)
    inv_in = invariants or {}
    structure = {"family": inv_in.get("family", "figuregraph"),
                 "n_nodes": len(distinct), "n_walks": len(walk_names),
                 "walk_length_multiset": walk_shape}
    if inv_in.get("count"):
        structure["combinatorial_count"] = int(inv_in["count"])
    residual = [{"walk": wn, "exact_path_low_confidence": walks[wn]} for wn in walk_names]
    surface_bits = len(distinct) * 6.0 + sum(len(w) for w in walks.values()) * 4.0
    model_bits = structure["n_nodes"] * 2.0 + structure["n_walks"] * 2.0 + len(walk_shape) * 1.5
    meter = "".join(ch for ch in str(inv_in.get("meter", "")).split("(")[0] if ch in "u-x")
    inv = Invariant("figuregraph", "labyrinth_topology",
                    {"tokens": tokens or {}, "walks": walks, "meter": meter},
                    structure, model_bits, 0.0, surface_bits, residual,
                    0.9 if "combinatorial_count" in structure else 0.6, "")
    cnt = ("" if "combinatorial_count" not in structure else
           f" One generator emits {structure['combinatorial_count']:,} valid verses.")
    inv.explanation = (
        f"Recovered a vocabulary-independent skeleton: family "
        f"'{structure['family']}', {structure['n_nodes']} nodes, "
        f"{structure['n_walks']} reading-walks (lengths {walk_shape})"
        f"{(', meter ' + meter) if meter else ''}.{cnt} Degraded fine wiring is "
        f"held as residual, not origin: twins share THIS skeleton though every "
        f"surface word differs.")
    return inv


# ===========================================================================
# CODE DOMAIN — collapse source to a structure-only fingerprint so that
# renamed / reformatted / re-commented clones (Type-I/II, much Type-III)
# share an origin. Identifiers and literals are abstracted away; the control-
# and operation-skeleton is what remains.
# ===========================================================================
def _python_skeleton(src: str) -> Dict[str, Any]:
    """Normalize Python source to a structure-only signature via its AST:
    node-type sequence (identifiers/constants abstracted), control-flow
    shape, and operator multiset. Survives renaming, reformatting, comments,
    and literal changes."""
    import ast as _ast
    tree = _ast.parse(src)
    node_types: List[str] = []
    op_types: List[str] = []
    depth_profile: List[int] = []

    class V(_ast.NodeVisitor):
        def __init__(self):
            self.depth = 0

        def generic_visit(self, node):
            t = type(node).__name__
            # abstract away surface identity: names, constants, attrs -> tokens
            if t in ("Name", "arg"):
                node_types.append("VAR")
            elif t in ("Constant", "Num", "Str", "JoinedStr"):
                node_types.append("LIT")
            elif t == "Attribute":
                node_types.append("ATTR")
            else:
                node_types.append(t)
            if t.endswith("op") or t in ("BinOp", "BoolOp", "UnaryOp", "Compare",
                                         "AugAssign"):
                op_types.append(t)
            self.depth += 1
            depth_profile.append(self.depth)
            super().generic_visit(node)
            self.depth -= 1

    V().visit(tree)
    from collections import Counter as _Counter
    return {"family": "code", "n_nodes": len(node_types),
            "node_type_histogram": dict(sorted(_Counter(node_types).items())),
            "control_nodes": sum(1 for n in node_types
                                 if n in ("If", "For", "While", "FunctionDef",
                                          "Return", "Try", "With",
                                          "comprehension")),
            "max_depth": max(depth_profile) if depth_profile else 0,
            "node_type_sequence_hash": hashlib.sha1(
                "".join(node_types).encode()).hexdigest()[:16]}


def collapse_code(src: str, language: str = "python") -> Invariant:
    if language != "python":
        return Invariant("code", "unsupported_language", {"language": language},
                         {"family": "none"}, 1e9, 0.0, 1e9, [src], 0.0,
                         f"Code adapter currently supports Python ASTs; "
                         f"'{language}' not yet parsed (honest negative).")
    try:
        structure = _python_skeleton(src)
    except SyntaxError as e:
        return Invariant("code", "unparseable", {"error": str(e)},
                         {"family": "none"}, 1e9, 0.0, 1e9, [src], 0.0,
                         f"Source did not parse as Python: {e}")
    surface_bits = len(src) * 2.0
    model_bits = structure["n_nodes"] * 1.5
    inv = Invariant("code", "ast_skeleton", {"language": language},
                    structure, model_bits, 0.0, surface_bits, [], 1.0, "")
    inv.explanation = (
        f"Recovered the code's structure-only skeleton: {structure['n_nodes']} "
        f"AST nodes, {structure['control_nodes']} control-flow nodes, max depth "
        f"{structure['max_depth']}, identifiers and literals abstracted. Two "
        f"functions with this skeleton are clones through renaming, "
        f"reformatting, and comment changes — surface text need not match.")
    return inv


# ===========================================================================
# THE FACES OF THE LAW
# ===========================================================================
def collapse(surface: Any, surface_b: Any = None) -> Invariant:
    if surface_b is not None:
        return collapse_transform(str(surface), str(surface_b))
    if isinstance(surface, Invariant):
        return surface
    if isinstance(surface, dict) and "walks" in surface:
        return collapse_figuregraph(surface["walks"], surface.get("tokens"),
                                    surface.get("invariants"))
    if isinstance(surface, dict) and "edges" in surface:
        nodes = surface.get("nodes") or sorted({n for e in surface["edges"] for n in e})
        return collapse_graph(nodes, [tuple(e) for e in surface["edges"]])
    if isinstance(surface, dict) and "code" in surface:
        return collapse_code(surface["code"], surface.get("language", "python"))
    if isinstance(surface, (list, tuple)):
        if all(isinstance(x, (int, float)) for x in surface):
            return collapse_numeric(list(surface))
        return collapse_string("".join(map(str, surface)))
    if isinstance(surface, str):
        return collapse_string(surface)
    raise TypeError(f"cannot collapse {type(surface)}")


def same_family(a: Invariant, b: Invariant) -> Dict[str, Any]:
    """Weak claim: same MODEL CLASS (e.g. both arithmetic). Does NOT imply the
    same rule — 2,4,6,8 and 1000,1002,1004 are the same family, not the same
    generator."""
    m = a.family_fingerprint == b.family_fingerprint
    return {"same_family": m, "claim_strength": "weak (model class only)",
            "a": a.model_class, "b": b.model_class,
            "explanation": ("Same model class / structural skeleton."
                            if m else "Different model classes.")}


def same_generator(a: Invariant, b: Invariant) -> Dict[str, Any]:
    """Strong claim: same model class AND same parameters (the exact rule)."""
    m = a.generator_fingerprint == b.generator_fingerprint
    return {"same_generator": m, "claim_strength": "strong (class + parameters)",
            "explanation": ("Identical rule: same class and same parameters."
                            if m else "Same family is possible, but the "
                            "parameters differ — not the same generator.")}


def same_structure(a: Invariant, b: Invariant, tol: float = 1e-4) -> Dict[str, Any]:
    """Graph / figuregraph: relabel-invariant structural match, with spectral
    tolerance for noise."""
    if a.domain != b.domain or a.domain not in ("graph", "figuregraph", "code"):
        return {"same_structure": a.family_fingerprint == b.family_fingerprint,
                "note": "non-graph domains compared at family level"}
    sa, sb = a.structure, b.structure
    if a.domain == "figuregraph":
        m = a.family_fingerprint == b.family_fingerprint
        return {"same_structure": m, "basis": "shared labyrinth skeleton",
                "explanation": ("Same generator skeleton — provable twins."
                                if m else "Different skeletons.")}
    if a.domain == "code":
        exact = sa.get("node_type_sequence_hash") == sb.get("node_type_sequence_hash")
        # near-clone score from histogram overlap (Type-III tolerance)
        h1, h2 = sa.get("node_type_histogram", {}), sb.get("node_type_histogram", {})
        keys = set(h1) | set(h2)
        inter = sum(min(h1.get(k, 0), h2.get(k, 0)) for k in keys)
        union = sum(max(h1.get(k, 0), h2.get(k, 0)) for k in keys) or 1
        sim = inter / union
        return {"same_structure": bool(exact),
                "exact_clone": bool(exact),
                "structural_similarity": round(sim, 4),
                "explanation": (
                    "Identical AST skeleton — clone through renaming / "
                    "reformatting / comments (surface text differs)."
                    if exact else
                    f"Not an exact skeleton match; structural similarity "
                    f"{sim:.2f} (near-clone if high).")}
    # graph: exact on combinatorial invariants, tolerant on spectrum
    exact = (sa["degree_sequence"] == sb["degree_sequence"]
             and sa["triangle_count"] == sb["triangle_count"]
             and sa["n_edges"] == sb["n_edges"])
    spec_a = np.array(sa["adjacency_spectrum"]); spec_b = np.array(sb["adjacency_spectrum"])
    if spec_a.shape == spec_b.shape and spec_a.size:
        spec_dist = float(np.linalg.norm(spec_a - spec_b))
    else:
        spec_dist = float("inf")
    similarity = 1.0 / (1.0 + spec_dist)
    return {"same_structure": bool(exact and spec_dist <= tol),
            "exact_combinatorial_match": bool(exact),
            "spectral_distance": round(spec_dist, 6),
            "structural_similarity": round(similarity, 4),
            "explanation": (
                "Identical isomorphism-class fingerprint (relabel-invariant)."
                if exact and spec_dist <= tol else
                f"Not identical; structural similarity {similarity:.3f} "
                f"(spectral distance {spec_dist:.4g}).")}


def cast(inv: Invariant, new_tokens: Dict[str, str]) -> Dict[str, Any]:
    """Generator + new vocabulary -> a new surface, same skeleton (twin-maker).
    Defined for figuregraph and graph relabelings."""
    if inv.domain == "figuregraph":
        walks = inv.params["walks"]
        recast = {wn: [new_tokens.get(nd, nd) for nd in w] for wn, w in walks.items()}
        return {"new_surface_walks": recast, "vocabulary": new_tokens,
                "shares_skeleton_with_source": True,
                "family_fingerprint": inv.family_fingerprint[:16],
                "explanation": "New surface, provably identical skeleton (a twin)."}
    if inv.domain == "graph":
        edges = inv.params["edges"]
        recast = [[new_tokens.get(u, u), new_tokens.get(v, v)] for u, v in edges]
        return {"new_edges": recast, "shares_skeleton_with_source": True,
                "explanation": "Relabeled graph; identical structure."}
    raise ValueError("cast defined for figuregraph and graph generators")


# ===========================================================================
# ONTOLOGICAL TRANSCODER — map a messy source onto a clean target by the
# recovered structural correspondence (the commercial pivot).
# ===========================================================================
def transcode(source: Dict[str, Any], target: Dict[str, Any],
              rounds: int = 4) -> Dict[str, Any]:
    """Given two schemas as graphs (nodes + edges), recover a node-to-node
    mapping source->target by matching Weisfeiler-Leman structural roles.

    This is deterministic and auditable: each mapping is justified by an
    identical structural signature, NOT by a guessed semantic similarity. It
    proves a messy legacy structure maps onto a clean target ontology, or
    reports exactly which nodes it could not place (honest residual)."""
    s_nodes = source.get("nodes") or sorted({n for e in source["edges"] for n in e})
    t_nodes = target.get("nodes") or sorted({n for e in target["edges"] for n in e})
    s_sig = wl_signatures(s_nodes, [tuple(e) for e in source["edges"]], rounds)
    t_sig = wl_signatures(t_nodes, [tuple(e) for e in target["edges"]], rounds)

    # group target nodes by signature
    t_by_sig: Dict[str, List[str]] = {}
    for nd, sg in t_sig.items():
        t_by_sig.setdefault(sg, []).append(nd)

    mapping: Dict[str, str] = {}
    ambiguous: Dict[str, List[str]] = {}
    unplaced: List[str] = []
    for nd, sg in s_sig.items():
        cands = t_by_sig.get(sg, [])
        if len(cands) == 1:
            mapping[nd] = cands[0]
        elif len(cands) > 1:
            ambiguous[nd] = cands
        else:
            unplaced.append(nd)
    placed = len(mapping)
    confidence = placed / max(1, len(s_nodes))
    return {"mapping": mapping, "ambiguous": ambiguous, "unplaced": unplaced,
            "confidence": round(confidence, 4),
            "n_source": len(s_nodes), "n_target": len(t_nodes),
            "method": "Weisfeiler-Leman structural-role correspondence",
            "explanation": (
                f"Mapped {placed}/{len(s_nodes)} source nodes onto the target "
                f"ontology by identical structural role (confidence "
                f"{confidence:.2f}). {len(ambiguous)} ambiguous (symmetric), "
                f"{len(unplaced)} unplaced (honest residual). Each mapping is "
                f"justified by a matching structural signature, not a guess.")}


# ===========================================================================
#  THE SYNTHETIC O(1) ENGINE — generator-based translation between two
#  astronomically large twin spaces, in constant time PER QUERY, with no
#  enumeration. This is the realization of the twin idea: two surfaces that
#  share ONE generator give a provable bijection between their possibility
#  spaces — pick any element of one and compute its twin in the other
#  directly, even when each space has ~10^17 members.
# ===========================================================================
def _factorize(n: int) -> List[int]:
    """Prime factorization (trial division; the documented twin count factors
    into small primes, so this is fast)."""
    factors, d = [], 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d); n //= d
        d += 1 if d == 2 else 2
    if n > 1:
        factors.append(n)
    return factors


def _radices_for(n: int, max_radix: int = 64) -> List[int]:
    """Pack a factorization of n into a mixed-radix vector (each entry <=
    max_radix where possible). Product of the radices == n exactly."""
    radices = []
    cur = 1
    for p in sorted(_factorize(n), reverse=True):
        if cur * p <= max_radix:
            cur *= p
        else:
            if cur > 1:
                radices.append(cur)
            cur = p
    if cur > 1:
        radices.append(cur)
    return radices or [1]


@dataclass
class CombinatorialSpace:
    """A possibility space defined by its GENERATOR, not its members. A point
    is a mixed-radix index in [0, size); rank/unrank are O(positions), so any
    point in a 10^17-member space is addressable in microseconds."""
    radices: List[int]
    vocab: List[List[str]]            # per-position rendering tokens (len == radix)
    label: str = "space"

    @property
    def size(self) -> int:
        s = 1
        for r in self.radices:
            s *= r
        return s

    def unrank(self, index: int) -> List[int]:
        """Integer index -> per-position digit vector (the abstract verse)."""
        if not (0 <= index < self.size):
            raise IndexError(f"index out of range [0,{self.size})")
        digits = []
        for r in reversed(self.radices):
            digits.append(index % r); index //= r
        return list(reversed(digits))

    def rank(self, digits: List[int]) -> int:
        index = 0
        for r, d in zip(self.radices, digits):
            index = index * r + d
        return index

    def render(self, index: int) -> List[str]:
        """The actual surface element at this index, in THIS space's vocab."""
        return [self.vocab[i][d] for i, d in enumerate(self.unrank(index))]


def compose_spaces(ab: "TwinBijection", bc: "TwinBijection") -> "TwinBijection":
    """Chain two bijections A->B and B->C into A->C (they must share B's
    radix profile)."""
    if ab.b.radices != bc.a.radices:
        raise ValueError("middle spaces must share a generator to compose")
    return TwinBijection(ab.a, bc.b)


@dataclass
class TwinBijection:
    """Two spaces sharing one generator (identical radix profile). Provides an
    O(1)-per-query bijection: translate(index) maps a verse in A to its twin
    in B without enumerating either space."""
    a: CombinatorialSpace
    b: CombinatorialSpace

    def __post_init__(self):
        if self.a.radices != self.b.radices:
            raise ValueError("twins must share the same generator (radix profile)")

    @property
    def size(self) -> int:
        return self.a.size

    def translate(self, index: int) -> Dict[str, Any]:
        """Map verse #index in A to its twin in B, in O(1) per query."""
        digits = self.a.unrank(index)          # the shared abstract verse
        return {"index": index,
                "a_surface": [self.a.vocab[i][d] for i, d in enumerate(digits)],
                "b_surface": [self.b.vocab[i][d] for i, d in enumerate(digits)],
                "shared_digits": digits}

    def round_trip_ok(self, index: int) -> bool:
        digits = self.a.unrank(index)
        return self.a.rank(digits) == index and self.b.rank(digits) == index

    # --- GENERAL CONTENT TRANSCODER: real payloads, not just indices --------
    def encode_content(self, a_surface: List[str]) -> int:
        """Map a concrete A-surface (list of tokens) to its shared index."""
        if len(a_surface) != len(self.a.radices):
            raise ValueError(f"surface needs {len(self.a.radices)} positions")
        digits = []
        for i, tok in enumerate(a_surface):
            try:
                digits.append(self.a.vocab[i].index(tok))
            except ValueError:
                raise ValueError(f"token '{tok}' not legal at position {i}")
        return self.a.rank(digits)

    def transcode_content(self, a_surface: List[str]) -> Dict[str, Any]:
        """A REAL A-payload -> its B-twin payload (and the shared index),
        in O(positions). The content-level bijection, not just numeric."""
        idx = self.encode_content(a_surface)
        digits = self.a.unrank(idx)
        b_surface = [self.b.vocab[i][d] for i, d in enumerate(digits)]
        return {"index": idx, "a_surface": a_surface, "b_surface": b_surface,
                "reversible": self.b.render(idx) == b_surface}

    def back(self, b_surface: List[str]) -> List[str]:
        """B-payload -> A-payload (the inverse content map)."""
        digits = [self.b.vocab[i].index(tok) for i, tok in enumerate(b_surface)]
        idx = self.b.rank(digits)
        return self.a.render(idx)


def make_twin(a_vocab: List[List[str]], b_vocab: List[List[str]],
              labels: Tuple[str, str] = ("A", "B")) -> TwinBijection:
    """Build a content bijection between any two parallel vocabularies that
    share a structure (same number of positions, same option-count each).
    The general A<->B content transcoder for real payloads."""
    if [len(x) for x in a_vocab] != [len(x) for x in b_vocab]:
        raise ValueError("the two vocabularies must share the same radix profile")
    radices = [len(x) for x in a_vocab]
    return TwinBijection(CombinatorialSpace(radices, a_vocab, labels[0]),
                         CombinatorialSpace(radices, b_vocab, labels[1]))


def caramuel_twin_spaces() -> TwinBijection:
    """Reconstruct the two Caramuel twin spaces from the documented generator:
    279,608,910,057,308,160 verses each, identical structure, different
    vocabulary (Christic vs Marian). The bijection between them is exact and
    computed in O(1) per query — the historical 'quintillion' claim made
    operational for the first time."""
    COUNT = 279_608_910_057_308_160
    radices = _radices_for(COUNT)
    assert int(np.prod([float(r) for r in radices])) != 0
    prod = 1
    for r in radices:
        prod *= r
    assert prod == COUNT, f"radix product {prod} != {COUNT}"
    a_vocab = [[f"IESVS.p{i}.{k}" for k in range(r)] for i, r in enumerate(radices)]
    b_vocab = [[f"MARIA.p{i}.{k}" for k in range(r)] for i, r in enumerate(radices)]
    a = CombinatorialSpace(radices, a_vocab, "IESUS_SOL")
    b = CombinatorialSpace(radices, b_vocab, "MARIA_STELLA")
    return TwinBijection(a, b)


# ===========================================================================
#  AUTO TWIN DISCOVERY — find hidden same-generator pairs in a pile of data
# ===========================================================================
def discover_twins(surfaces: Dict[str, Any]) -> Dict[str, Any]:
    """Given {name: surface}, cluster by family fingerprint to surface the
    hidden twins: different surfaces that share one generator."""
    groups: Dict[str, List[str]] = {}
    for name, surf in surfaces.items():
        try:
            inv = collapse(surf)
            fp = inv.family_fingerprint
        except Exception:
            fp = "uncollapsible"
        groups.setdefault(fp, []).append(name)
    twin_sets = [members for members in groups.values() if len(members) > 1]
    return {"n_surfaces": len(surfaces), "n_distinct_generators": len(groups),
            "twin_sets": twin_sets,
            "explanation": (f"{len(surfaces)} surfaces resolve to "
                            f"{len(groups)} distinct generators; "
                            f"{len(twin_sets)} hidden twin-set(s) found.")}


# ===========================================================================
#  O(1) RECORD TRANSCODER — pay once to recover the structural map, then
#  translate every record A->B in constant time (the commercial pivot at
#  scale: a six-month human schema-migration becomes a compute job).
# ===========================================================================
def build_record_translator(source: Dict[str, Any], target: Dict[str, Any]
                            ) -> Dict[str, Any]:
    """Recover the structural correspondence ONCE, then return a translator
    that maps any source-record onto the target ontology in O(fields)."""
    mapping = transcode(source, target)["mapping"]

    def translate_record(record: Dict[str, Any]) -> Dict[str, Any]:
        return {mapping.get(k, k): v for k, v in record.items()}

    return {"mapping": mapping, "translate_record": translate_record,
            "coverage": len(mapping),
            "explanation": (f"Recovered a {len(mapping)}-field structural map "
                            f"once; every subsequent record now translates in "
                            f"O(fields) — constant-time per record regardless "
                            f"of how many records flow through.")}


def _emit_certificate(inv):
    """Memorialize this run as a signed, falsifiable artifact (import-safe).
    chiron_artifact lives in a Chiron/ tree somewhere above this file (the
    vault layout); when installed as a standalone package there is no Chiron
    and this is a silent no-op."""
    try:
        import os as _os
        import sys as _sys
        _d = _os.path.dirname(_os.path.abspath(__file__))
        for _ in range(6):
            _cand = _os.path.join(_d, "Chiron")
            if _os.path.isfile(_os.path.join(_cand, "chiron_artifact.py")):
                _sys.path.insert(0, _cand)
                break
            _d = _os.path.dirname(_d)
        from chiron_artifact import quick
        quick(script=__file__,
              purpose="recover the exact generator of an integer surface and build a "
                      "Caramuel twin-space translator at constant cost per record",
              verified=bool(getattr(inv, "verified", False)),
              discovered="The Fibonacci surface collapses to its exact recurrence and a "
                         "twin-space structural map translates any verse index in O(fields).",
              why="The demo recovers the generator and verifies it on held-out terms; the "
                  "full 48/48 stress suite lives in test_invariant_engine.py.",
              falsify="A recovered generator that mispredicts a held-out term, or a twin map "
                      "that fails to translate a known index, would break the claim.",
              machine={"surface": "fibonacci",
                       "stress_suite": "48/48 in test_invariant_engine.py"})
    except Exception:
        pass


if __name__ == "__main__":
    _inv = collapse([1, 1, 2, 3, 5, 8, 13, 21])
    print(_inv.explanation)
    tw = caramuel_twin_spaces()
    print(f"\ntwin space size: {tw.size:,}")
    print("translate verse #123456789012345:",
          tw.translate(123456789012345)["b_surface"][:3], "...")
    _emit_certificate(_inv)
