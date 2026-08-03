#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
primus.certify — an accountability certificate over LLM / agent output.

This is the refusal discipline turned into a wrapper for language models. It
does NOT bless a model or call its answer correct. It separates what is
*checkable* from what is not, checks the checkable part in exact arithmetic,
and refuses to certify the rest:

  VERIFIED      — the claim was exactly checked and holds.
  REFUTED       — the claim was exactly checked and is false.
  REFUSED       — no exact proof either way (outside the engine's classes,
                  beyond exact-arithmetic bounds, or ambiguous); the gate
                  will not certify it in either direction.
  (remainder)   — free text is honestly reported as unverifiable, never
                  stamped.

Checkable claim kinds (schema primus.certificate/2): integer/rational
arithmetic including powers (``a op b = c``, ``c = a op b``), percentages,
primality/compositeness, binomial coefficients, gcd/lcm, modular arithmetic,
date arithmetic (days after/before, days between), sums/totals/averages of
listed numbers, integer-sequence continuations, closed-form formulas
(``a(n) = <expr> matches <terms>``, checked exactly at every index via
:func:`primus.conjecture.verify_closed_form`), and bare integer runs
(structural recovery with held-out proof via :func:`primus.engine.collapse`).

What is deliberately NOT judged: approximations ("sqrt(2) = 1.414" is
neither verified nor refuted — it is simply not extracted), multi-operation
expressions, and anything requiring outside knowledge. See SCHEMA.md for
the full contract, including the one that matters most: **a passing gate
means "nothing checkable was refuted," never "the output is true."** The
``coverage`` field exists so callers can see how much of the text was
actually checked.

Adversarial-input bounds: input is truncated at ``MAX_TEXT_CHARS`` (recorded
in the certificate), at most ``MAX_CLAIMS`` claims are checked, and integers
beyond ``MAX_INT_DIGITS`` digits are REFUSED rather than computed.

Usage::

    from primus import certify
    cert = certify(model_output_text)
    cert["verdict"]; cert["coverage"]

    $ echo "2+2=5 and gcd(12,18)=6" | primus certify -
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timedelta, timezone
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

from primus.engine import OWNER, collapse

SCHEMA = "primus.certificate/2"

MAX_TEXT_CHARS = 100_000    # input truncated (and recorded) beyond this
MAX_CLAIMS = 200            # claims checked per certificate
MAX_INT_DIGITS = 4_096      # larger integers are REFUSED, not computed
MAX_POW_EXP = 64            # exponent bound for a^b claims
MAX_POW_BASE_DIGITS = 9     # base bound for a^b claims
MAX_SEQ_TERMS = 256         # longer runs are REFUSED, not collapsed (DoS bound)

_NUM = r"-?\d+(?:\.\d+)?"
_SEQ = r"-?\d+(?:\s*[, ]\s*-?\d+){2,}"          # 3+ integers
_MONTH = (r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
          r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
          r"Nov(?:ember)?|Dec(?:ember)?)")
_DATE = rf"(?:{_MONTH}\.?\s+\d{{1,2}},?\s+\d{{4}}|\d{{1,2}}\s+{_MONTH}\.?,?\s+\d{{4}}|\d{{4}}-\d{{2}}-\d{{2}})"
_NUMLIST = rf"{_NUM}(?:\s*(?:,|and)\s*{_NUM})+"

_RE_ARITH = re.compile(
    rf"(?<!\d)(?<!\d\.)({_NUM})\s*(\*\*|[+\-*/x×^])\s*({_NUM})\s*(?:=|equals)\s*({_NUM})(?!\.?\d)")
_RE_ARITH_REV = re.compile(
    rf"(?<!\d)(?<!\d\.)({_NUM})\s*=\s*({_NUM})\s*(\*\*|[+\-*/x×^])\s*({_NUM})(?!\.?\d)")
_RE_PERCENT = re.compile(
    rf"({_NUM})\s*(?:%|percent)\s+of\s+({_NUM})\s*(?:=|is|equals)\s*({_NUM})", re.I)
_RE_CONTINUATION = re.compile(
    rf"({_SEQ})\s*(?:,)?\s*(?:continues?\s+as|followed\s+by|"
    rf"next\s+(?:terms?|numbers?|values?)\s+(?:is|are)|then\s+comes?)\s*[:]?\s*({_SEQ}|-?\d+)", re.I)
_RE_CLOSED_FORM = re.compile(
    rf"a\(n\)\s*=\s*([0-9n()+\-*/^ ]{{1,200}}?)\s*"
    rf"(?:\(\s*n\s+from\s+(-?\d{{1,9}})\s*\)\s*)?matches\s+({_SEQ})")
_RE_RUN = re.compile(r"(?:-?\d+\s*[, ]\s*){4,}-?\d+")
_RE_PRIME = re.compile(r"(?<!\d)(\d+)\s+is\s+(?:a\s+|an\s+)?(not\s+)?(prime|composite)\b", re.I)
_RE_CHOOSE = re.compile(
    r"(?:C\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)|(\d+)\s+choose\s+(\d+)|binomial\s*\(\s*(\d+)\s*,\s*(\d+)\s*\))"
    r"\s*(?:=|is|equals)\s*(\d+)", re.I)
_RE_GCDLCM = re.compile(
    r"\b(gcd|lcm)\s*(?:\(\s*(\d+)\s*,\s*(\d+)\s*\)|of\s+(\d+)\s+and\s+(\d+))"
    r"\s*(?:=|is|equals)\s*(\d+)", re.I)
_RE_MOD = re.compile(r"(?<!\d)(\d+)\s+mod(?:ulo)?\s+(\d+)\s*(?:=|is|equals)\s*(\d+)", re.I)
_RE_MOD_CONG = re.compile(r"(?<!\d)(\d+)\s*≡\s*(\d+)\s*\(\s*mod\s+(\d+)\s*\)")
_RE_DATE_SHIFT = re.compile(
    rf"(\d{{1,4}})\s+days?\s+(after|before)\s+({_DATE})\s+(?:is|=|falls?\s+on|was)\s+({_DATE})", re.I)
_RE_DATE_BETWEEN = re.compile(
    rf"(?:number\s+of\s+)?days\s+(?:between|from)\s+({_DATE})\s+(?:and|to|until)\s+({_DATE})"
    rf"\s+(?:is|=|equals)\s+(\d+)", re.I)
_RE_AGG = re.compile(
    rf"\b(sum|total|average|mean)\s+of\s+({_NUMLIST})\s+(?:is|=|equals)\s+({_NUM})", re.I)

_DATE_FORMATS = ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y", "%Y-%m-%d")


# ---------------------------------------------------- bounded regex scanning
# A gate gets attacked. Two deterministic work bounds keep hostile input from
# turning claim extraction quadratic: (1) digit runs longer than the exact-
# arithmetic bound are clamped before scanning (semantics preserved — any
# claim touching one still overflows into REFUSED); (2) anchored patterns
# are only scanned inside windows around their keyword/'=' anchors, using
# pattern.finditer(text, pos, endpos) so spans stay absolute.
_CLAMP_RUN = re.compile(rf"\d{{{MAX_INT_DIGITS + 8},}}")


def _clamp_digit_runs(text: str) -> str:
    return _CLAMP_RUN.sub(lambda m: m.group(0)[:MAX_INT_DIGITS + 8], text)


def _find(pattern, text: str, anchors: str, radius: int):
    windows: List[Tuple[int, int]] = []
    for m in re.finditer(anchors, text, re.I):
        s, e = max(0, m.start() - radius), min(len(text), m.end() + radius)
        if windows and s <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(windows[-1][1], e))
        else:
            windows.append((s, e))
    for ws, we in windows:
        yield from pattern.finditer(text, ws, we)


_R_EQ = r"=|equals"
_ARITH_RADIUS = 2 * (MAX_INT_DIGITS + 32)


# ------------------------------------------------------------------ helpers
def _frac(s: str) -> Fraction:
    if len(s.lstrip("-").split(".")[0]) > MAX_INT_DIGITS:
        raise OverflowError("integer exceeds exact-arithmetic bounds")
    return Fraction(s)


def _ints(s: str) -> List[int]:
    return [int(x) for x in re.findall(r"-?\d+", s)]


def _nums(s: str) -> List[Fraction]:
    return [_frac(x) for x in re.findall(_NUM, s)]


def _parse_date(s: str) -> Optional[datetime]:
    s = re.sub(r"[.,]", "", s.strip())
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s.title() if "%b" in fmt.lower() else s, fmt)
        except ValueError:
            continue
    return None


_MR_WITNESSES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
_MR_DETERMINISTIC_BOUND = 3_317_044_064_679_887_385_961_981


def _is_prime(n: int) -> Optional[bool]:
    """Deterministic Miller–Rabin below the proven witness bound; None
    (→ REFUSED) above it — the gate does not do probabilistic certainty."""
    if n >= _MR_DETERMINISTIC_BOUND or len(str(n)) > MAX_INT_DIGITS:
        return None
    if n < 2:
        return False
    for p in _MR_WITNESSES:
        if n == p:
            return True
        if n % p == 0:
            return False
    d, r = n - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in _MR_WITNESSES:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _check_arith(a: str, op: str, b: str, c: str) -> Optional[bool]:
    """Exact rational check; None → REFUSED (undecidable within bounds)."""
    fa, fb, fc = _frac(a), _frac(b), _frac(c)
    if op in ("^", "**"):
        if fa.denominator != 1 or fb.denominator != 1:
            return None
        base, exp = int(fa), int(fb)
        if exp < 0 or exp > MAX_POW_EXP or len(str(abs(base))) > MAX_POW_BASE_DIGITS:
            return None
        return Fraction(base) ** exp == fc
    if op in "*x×":
        return fa * fb == fc
    if op == "+":
        return fa + fb == fc
    if op == "-":
        return fa - fb == fc
    if op == "/":
        return None if fb == 0 else fa / fb == fc
    return None


def _status(ok: Optional[bool]) -> str:
    return "REFUSED" if ok is None else ("VERIFIED" if ok else "REFUTED")


# ----------------------------------------------------------- claim checkers
def _claims_closed_form(text, add):
    """`a(n) = <expr> matches t0, t1, ...` — the expression is checked at
    EVERY index in exact rational arithmetic (n from 0 unless `(n from k)`
    is stated). The guess-and-prove layer (primus.conjecture) emits exactly
    this claim shape, so its output round-trips through this gate."""
    from primus.conjecture import verify_closed_form
    for m in _find(_RE_CLOSED_FORM, text, r"a\(n\)", 200 + 22 * MAX_SEQ_TERMS):
        expr = m.group(1).strip()
        offset = int(m.group(2)) if m.group(2) else 0
        seq = _ints(m.group(3))
        detail: Dict[str, Any] = {"expression": expr, "offset": offset,
                                  "n_terms": len(seq)}
        if len(seq) > MAX_SEQ_TERMS:
            add(m, "closed_form", "REFUSED",
                {"reason": f"run exceeds the {MAX_SEQ_TERMS}-term per-claim bound"})
            continue
        v = verify_closed_form(expr, seq, offset=offset)
        for k in ("reason", "expected", "got", "n"):
            if k in v:
                detail[k] = v[k]
        add(m, "closed_form", v["status"], detail)


def _claims_continuation(text, add):
    for m in _find(_RE_CONTINUATION, text, r"continues?|followed|next|then\s+comes?", 22 * MAX_SEQ_TERMS):
        prefix, claimed = _ints(m.group(1)), _ints(m.group(2))
        detail: Dict[str, Any] = {"prefix": prefix[:20], "claimed_continuation": claimed[:8]}
        if len(prefix) + len(claimed) > MAX_SEQ_TERMS:
            add(m, "sequence_continuation", "REFUSED",
                {"reason": f"run exceeds the {MAX_SEQ_TERMS}-term per-claim bound"})
            continue
        try:
            inv = collapse(prefix)
            if inv.verified:
                predicted = list(inv.predict(len(prefix) + len(claimed)))[len(prefix):]
                ok = len(predicted) == len(claimed) and all(
                    (isinstance(p, int) and p == q) or
                    Fraction(str(p)).limit_denominator(10**9) == Fraction(q)
                    for p, q in zip(predicted, claimed))
                status = "VERIFIED" if ok else "REFUTED"
                detail.update(model_class=inv.model_class,
                              predicted=[int(p) if float(p).is_integer() else float(p)
                                         for p in predicted])
            else:
                status = "REFUSED"
                detail["reason"] = ("no exactly-verified generator for the prefix; "
                                    "the engine will not certify the continuation "
                                    "in either direction")
        except Exception as exc:
            status, detail["reason"] = "REFUSED", f"engine declined: {type(exc).__name__}"
        add(m, "sequence_continuation", status, detail)


def _claims_dates(text, add):
    for m in _find(_RE_DATE_SHIFT, text, r"days?", 400):
        n, direction = int(m.group(1)), m.group(2).lower()
        d0, d1 = _parse_date(m.group(3)), _parse_date(m.group(4))
        if d0 is None or d1 is None:
            add(m, "date_arithmetic", "REFUSED", {"reason": "unparseable date"})
            continue
        expected = d0 + timedelta(days=n if direction == "after" else -n)
        add(m, "date_arithmetic", _status(expected.date() == d1.date()),
            {"expected": expected.date().isoformat()})
    for m in _find(_RE_DATE_BETWEEN, text, r"days", 400):
        d0, d1 = _parse_date(m.group(1)), _parse_date(m.group(2))
        if d0 is None or d1 is None:
            add(m, "date_arithmetic", "REFUSED", {"reason": "unparseable date"})
            continue
        expected = abs((d1.date() - d0.date()).days)
        add(m, "date_arithmetic", _status(expected == int(m.group(3))),
            {"expected": expected})


def _claims_aggregate(text, add):
    for m in _find(_RE_AGG, text, r"sum|total|average|mean", 6000):
        kind = m.group(1).lower()
        try:
            vals, claimed = _nums(m.group(2)), _frac(m.group(3))
        except OverflowError:
            add(m, "aggregate", "REFUSED", {"reason": "exceeds exact-arithmetic bounds"})
            continue
        total = sum(vals, Fraction(0))
        expected = total if kind in ("sum", "total") else total / len(vals)
        add(m, "aggregate", _status(expected == claimed),
            {"operation": kind, "n_values": len(vals),
             "expected": str(int(expected)) if expected.denominator == 1 else str(expected)})


def _claims_number_theory(text, add):
    for m in _find(_RE_CHOOSE, text, r"choose|binomial|C\s*\(", 300):
        g = [x for x in m.groups()[:6] if x is not None]
        n, k, claimed = int(g[0]), int(g[1]), int(m.group(7))
        if n > 100_000 or k > n:
            ok = None if n > 100_000 else (claimed == 0)
        else:
            ok = math.comb(n, k) == claimed
        add(m, "binomial", _status(ok),
            {} if ok is None else {"expected": math.comb(n, k) if k <= n else 0})
    for m in _find(_RE_GCDLCM, text, r"gcd|lcm", 300):
        fn = m.group(1).lower()
        a = int(m.group(2) or m.group(4)); b = int(m.group(3) or m.group(5))
        if max(len(str(a)), len(str(b))) > MAX_INT_DIGITS:
            add(m, fn, "REFUSED", {"reason": "exceeds exact-arithmetic bounds"})
            continue
        expected = math.gcd(a, b) if fn == "gcd" else (abs(a * b) // math.gcd(a, b) if a and b else 0)
        add(m, fn, _status(expected == int(m.group(6))), {"expected": expected})
    for m in _find(_RE_MOD, text, r"mod", 300):
        a, mod, c = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ok = None if mod == 0 else (a % mod == c)
        add(m, "modular", _status(ok), {} if mod == 0 else {"expected": a % mod})
    for m in _find(_RE_MOD_CONG, text, r"mod", 300):
        a, c, mod = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ok = None if mod == 0 else ((a - c) % mod == 0)
        add(m, "modular", _status(ok), {})
    for m in _find(_RE_PRIME, text, r"prime|composite", 120):
        n = int(m.group(1))
        negated, word = bool(m.group(2)), m.group(3).lower()
        p = _is_prime(n)
        if p is None:
            add(m, "primality", "REFUSED",
                {"reason": "beyond the deterministic Miller-Rabin bound; "
                           "the gate does not certify probabilistically"})
            continue
        asserted_prime = (word == "prime") != negated       # "not composite" ≈ prime claim for n>1
        if word == "composite":
            actual = (n > 1 and not p) if not negated else not (n > 1 and not p)
            ok = actual
        else:
            ok = p == asserted_prime
        add(m, "primality", _status(ok), {"n_is_prime": p})


def _claims_arith(text, add):
    for m in _find(_RE_ARITH, text, _R_EQ, _ARITH_RADIUS):
        try:
            ok = _check_arith(m.group(1), m.group(2), m.group(3), m.group(4))
        except OverflowError:
            ok = None
        add(m, "arithmetic", _status(ok), {})
    for m in _find(_RE_ARITH_REV, text, _R_EQ, _ARITH_RADIUS):
        try:
            ok = _check_arith(m.group(2), m.group(3), m.group(4), m.group(1))
        except OverflowError:
            ok = None
        add(m, "arithmetic", _status(ok), {})
    for m in _find(_RE_PERCENT, text, r"%|percent", 300):
        try:
            ok = (_frac(m.group(1)) / 100) * _frac(m.group(2)) == _frac(m.group(3))
        except OverflowError:
            ok = None
        add(m, "percentage", _status(ok), {})


def _claims_runs(text, add):
    for m in _RE_RUN.finditer(text):
        seq = _ints(m.group(0))
        detail: Dict[str, Any] = {"sequence": seq[:20]}
        if len(seq) > MAX_SEQ_TERMS:
            add(m, "sequence", "REFUSED",
                {"reason": f"run exceeds the {MAX_SEQ_TERMS}-term per-claim bound"})
            continue
        try:
            inv = collapse(seq)
            if inv.verified:
                status = "VERIFIED"
                detail.update(model_class=inv.model_class,
                              note="an exact generator reproduces this run, "
                                   "verified on held-out terms")
            else:
                status = "REFUSED"
                detail["reason"] = "no exactly-verified structure in this run"
        except Exception as exc:
            status, detail["reason"] = "REFUSED", f"engine declined: {type(exc).__name__}"
        add(m, "sequence", status, detail)


# ------------------------------------------------------------------- public
def extract_claims(text: str) -> List[Dict[str, Any]]:
    """Public helper: extract and exactly check every checkable claim."""
    return _extract_claims(text)[0]


def _extract_claims(text: str) -> Tuple[List[Dict[str, Any]], List[Tuple[int, int]], bool]:
    """Extract and exactly check every checkable claim in *text*.

    Returns (claims, consumed_spans, claim_cap_hit). Earlier (more specific)
    patterns consume their spans; later patterns skip overlaps so nothing is
    double-counted.
    """
    text = _clamp_digit_runs(text)
    claims: List[Dict[str, Any]] = []
    consumed: List[Tuple[int, int]] = []
    capped = False

    def _overlaps(span):
        return any(not (span[1] <= s or span[0] >= e) for s, e in consumed)

    def add(m, kind, status, detail):
        nonlocal capped
        if len(claims) >= MAX_CLAIMS:
            capped = True
            return
        if _overlaps(m.span()):
            return
        claims.append({"kind": kind, "text": m.group(0).strip()[:100],
                       "status": status, "span": list(m.span()), **detail})
        consumed.append(m.span())

    # specificity order: structured kinds first, generic number-runs last
    _claims_closed_form(text, add)
    _claims_continuation(text, add)
    _claims_dates(text, add)
    _claims_aggregate(text, add)
    _claims_number_theory(text, add)
    _claims_arith(text, add)
    _claims_runs(text, add)
    claims.sort(key=lambda c: c["span"][0])
    return claims, consumed, capped


def certify(text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Certify the checkable claims in *text*; refuse to bless the rest.

    Returns a certificate dict (schema ``primus.certificate/2``; contract in
    SCHEMA.md). Agent gating: pass iff ``counts["refuted"] == 0`` — and read
    ``coverage`` before trusting the pass, because a passing gate means only
    that nothing checkable was refuted, never that the output is true.
    """
    from primus import __version__

    text = text if isinstance(text, str) else str(text)
    truncated = len(text) > MAX_TEXT_CHARS
    body_text = text[:MAX_TEXT_CHARS]

    claims, consumed, capped = _extract_claims(body_text)
    counts = {
        "checkable": len(claims),
        "verified": sum(c["status"] == "VERIFIED" for c in claims),
        "refuted": sum(c["status"] == "REFUTED" for c in claims),
        "refused": sum(c["status"] == "REFUSED" for c in claims),
    }
    covered_chars = sum(e - s for s, e in consumed)
    coverage = round(covered_chars / len(body_text), 4) if body_text else 0.0
    stripped = body_text
    for c in reversed(claims):                       # spans are sorted; blank them
        s, e = c["span"]
        stripped = stripped[:s] + " " * (e - s) + stripped[e:]
    unverifiable = bool(re.search(r"[A-Za-z]{3,}", stripped))

    verdict = (
        f"Of {counts['checkable']} checkable claim(s): {counts['verified']} verified, "
        f"{counts['refuted']} refuted, {counts['refused']} refused (no exact proof either way)."
        + (" The remaining free text is unverifiable by exact methods and is not certified."
           if unverifiable else "")
        + (" Nothing in this output was checkable; nothing is certified."
           if counts["checkable"] == 0 else "")
    )

    cert: Dict[str, Any] = {
        "schema": SCHEMA,
        "engine": {"name": "primus", "version": __version__},
        "owner": OWNER,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "input": {"sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                  "chars": len(text), "truncated": truncated},
        "claims": claims,
        "counts": counts,
        "coverage": coverage,
        "claims_capped": capped,
        "unverifiable_remainder": unverifiable,
        "verdict": verdict,
    }
    if meta:
        cert["meta"] = meta
    body = json.dumps(cert, sort_keys=True, separators=(",", ":"), default=str)
    # Tamper-EVIDENT hash over input + certificate — an integrity check, NOT
    # an unforgeable signature (anyone can recompute it). For cryptographic
    # provenance, sign externally (see ../JDICert).
    cert["attestation"] = {"sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
                           "kind": "tamper-evident-hash"}
    return cert


def render(cert: Dict[str, Any]) -> str:
    """Human-readable rendering of a certificate."""
    lines = [
        "PRIMUS CERTIFICATE  (exact verification; refusal over confidence)",
        f"  engine primus {cert['engine']['version']}   input sha256 "
        f"{cert['input']['sha256'][:16]}…   {cert['created_utc']}",
        "",
    ]
    for c in cert["claims"]:
        mark = {"VERIFIED": "✓", "REFUTED": "✗", "REFUSED": "∅"}[c["status"]]
        lines.append(f"  [{mark} {c['status']:8s}] {c['kind']:22s} {c['text']}")
        if c["status"] == "REFUTED" and "predicted" in c:
            lines.append(f"      exact prediction was: {c['predicted']}")
        if c["status"] == "REFUTED" and "expected" in c:
            lines.append(f"      exact value is: {c['expected']}")
        if c["status"] == "REFUSED" and c.get("reason"):
            lines.append(f"      {c['reason']}")
    if not cert["claims"]:
        lines.append("  (no checkable claims found)")
    lines += ["", f"  VERDICT: {cert['verdict']}",
              f"  coverage: {cert['coverage']:.1%} of input was checkable"
              + ("   [claims capped]" if cert.get("claims_capped") else ""),
              f"  attestation sha256 {cert['attestation']['sha256'][:32]}… "
              f"(tamper-evident hash, not a signature)"]
    return "\n".join(lines)


def _selftest() -> int:
    """Fast offline gates for the certify layer. Returns count of failures."""
    fails = 0

    def gate(name: str, cond: bool) -> None:
        nonlocal fails
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        fails += 0 if cond else 1

    def counts(text):
        return certify(text)["counts"]

    c = counts("2+2=4")
    gate("true arithmetic verified", c["verified"] == 1 and c["refuted"] == 0)
    gate("false arithmetic refuted", counts("2+2=5")["refuted"] == 1)
    gate("reversed arithmetic (91 = 7 x 13) verified", counts("91 = 7 x 13")["verified"] == 1)
    gate("power claim verified (2^10 = 1024)", counts("2^10 = 1024")["verified"] == 1)
    gate("percentage verified", counts("50% of 80 is 40")["verified"] == 1)
    gate("primality: 97 is prime verified", counts("97 is prime")["verified"] == 1)
    gate("primality: 91 is prime refuted", counts("91 is prime")["refuted"] == 1)
    gate("primality: 91 is composite verified", counts("91 is composite")["verified"] == 1)
    gate("primality beyond MR bound refused",
         counts(str(10**30 + 57) + " is prime")["refused"] == 1)
    gate("binomial verified (10 choose 3 is 120)", counts("10 choose 3 is 120")["verified"] == 1)
    gate("binomial refuted (C(10,3) = 130)", counts("C(10,3) = 130")["refuted"] == 1)
    gate("gcd verified", counts("gcd(12, 18) = 6")["verified"] == 1)
    gate("lcm refuted (lcm of 4 and 6 is 24)", counts("lcm of 4 and 6 is 24")["refuted"] == 1)
    gate("modular verified (17 mod 5 = 2)", counts("17 mod 5 = 2")["verified"] == 1)
    gate("date shift verified (leap year)",
         counts("60 days after January 1, 2024 is March 1, 2024")["verified"] == 1)
    gate("date shift refuted",
         counts("60 days after January 1, 2024 is March 2, 2024")["refuted"] == 1)
    gate("days between verified",
         counts("days between 2026-01-01 and 2026-07-04 is 184")["verified"] == 1)
    gate("sum verified (total of 12, 15 and 20 is 47)",
         counts("the total of 12, 15 and 20 is 47")["verified"] == 1)
    gate("average verified exactly", counts("the average of 2, 4 and 9 is 5")["verified"] == 1)
    gate("average refuted", counts("the average of 2, 4 and 9 is 6")["refuted"] == 1)
    gate("closed form verified (a(n) = n*n + 1)",
         counts("a(n) = n*n + 1 matches 1, 2, 5, 10, 17")["verified"] == 1)
    gate("closed form refuted with counterexample",
         counts("a(n) = n*n + 1 matches 1, 2, 5, 10, 18")["refuted"] == 1)
    gate("closed form with offset verified (n from 1)",
         counts("a(n) = n*n (n from 1) matches 1, 4, 9, 16")["verified"] == 1)
    gate("closed form beyond bounds refused (n^70)",
         counts("a(n) = n^70 matches 1, 2, 3")["refused"] == 1)
    c = counts("The sequence 1 1 2 3 5 8 13 continues as 21, 34")
    gate("true continuation verified", c["verified"] == 1)
    gate("false continuation refuted",
         counts("The sequence 1 1 2 3 5 8 13 continues as 22, 34")["refuted"] == 1)
    gate("out-of-class continuation refused (not guessed)",
         counts("The primes 2 3 5 7 11 13 continue as 17, 19")["refused"] == 1)
    cert = certify("I believe this is broadly the right approach for your team.")
    gate("pure prose: nothing certified, coverage 0",
         cert["counts"]["checkable"] == 0 and cert["coverage"] == 0.0
         and cert["unverifiable_remainder"])
    gate("random run refused, not hallucinated",
         counts("7 2 9 4 4 8 3 1 6 5 look meaningful")["refused"] == 1)
    big = "9" * (MAX_INT_DIGITS + 10)
    gate("oversize integer refused, not computed",
         counts(f"{big} + 1 = 1{'0' * (MAX_INT_DIGITS + 10)}")["refused"] == 1)
    cert = certify("2+2=4. " * 5)
    gate("coverage reported and sane", 0.0 < cert["coverage"] <= 1.0)
    print(f"  certify gates: {31 - fails}/31 passed")
    return fails


if __name__ == "__main__":
    raise SystemExit(_selftest())
