#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
primus.certify — an accountability certificate over LLM / agent output.

This is the refusal discipline turned into a wrapper for language models. It
does NOT bless a model or call its answer correct. It separates what is
*checkable* from what is not, checks the checkable part in exact arithmetic,
and refuses to certify the rest:

  VERIFIED      — the claim was exactly checked and holds.
  REFUTED       — the claim was exactly checked and is false.
  REFUSED       — the engine found no exactly-verifiable structure; it will
                  not certify the claim in either direction.
  (remainder)   — free text is honestly reported as unverifiable, never
                  stamped.

The verdict is deliberately modest: "of N checkable claims, V verified and
R refuted; K refused; the rest is unverifiable by exact methods." A
certificate that cannot say "the whole answer is true" and refuses to
pretend otherwise — that honesty is the product.

Checkable claim kinds (v1): integer/rational arithmetic (``a op b = c``),
percentage claims (``p% of m is k``), integer-sequence continuations
(``1 1 2 3 5 8 continues as 13, 21``), and bare integer runs (structural
recovery with held-out proof via :func:`primus.engine.collapse`).

Usage::

    from primus import certify
    cert = certify(model_output_text)
    cert["verdict"]

    $ echo "2+2=5 and the sequence 2 4 6 8 continues as 10" | primus certify -
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from fractions import Fraction
from typing import Any, Dict, List, Optional

from primus.engine import OWNER, collapse

SCHEMA = "primus.certificate/1"

_NUM = r"-?\d+(?:\.\d+)?"
_SEQ = r"-?\d+(?:\s*[, ]\s*-?\d+){2,}"  # 3+ integers separated by space/comma

_RE_ARITH = re.compile(
    rf"(?<!\d)(?<!\d\.)({_NUM})\s*([+\-*/x×])\s*({_NUM})\s*(?:=|equals)\s*({_NUM})(?!\.?\d)"
)
_RE_PERCENT = re.compile(
    rf"({_NUM})\s*(?:%|percent)\s+of\s+({_NUM})\s*(?:=|is|equals)\s*({_NUM})",
    re.IGNORECASE,
)
_RE_CONTINUATION = re.compile(
    rf"({_SEQ})\s*(?:,)?\s*(?:continues?\s+as|followed\s+by|"
    rf"next\s+(?:terms?|numbers?|values?)\s+(?:is|are)|then\s+comes?)\s*[:]?\s*({_SEQ}|-?\d+)",
    re.IGNORECASE,
)
_RE_RUN = re.compile(r"(?:-?\d+\s*[, ]\s*){4,}-?\d+")  # 5+ integer run


def _frac(s: str) -> Fraction:
    return Fraction(s)  # exact for both integers and decimal strings


def _ints(s: str) -> List[int]:
    return [int(x) for x in re.findall(r"-?\d+", s)]


def _check_arith(a: str, op: str, b: str, c: str) -> Optional[bool]:
    """Exact rational check; None means not decidable (e.g. division by zero)."""
    fa, fb, fc = _frac(a), _frac(b), _frac(c)
    if op in "*x×":
        return fa * fb == fc
    if op == "+":
        return fa + fb == fc
    if op == "-":
        return fa - fb == fc
    if op == "/":
        if fb == 0:
            return None
        return fa / fb == fc
    return None


def extract_claims(text: str) -> List[Dict[str, Any]]:
    """Extract and exactly check every checkable claim in *text*.

    Returns a list of claim dicts, each with ``kind``, ``text`` and
    ``status`` in {VERIFIED, REFUTED, REFUSED}. Spans consumed by a
    higher-priority pattern (continuation) are not double-counted as bare
    runs.
    """
    claims: List[Dict[str, Any]] = []
    consumed: List[tuple] = []

    def _overlaps(span: tuple) -> bool:
        return any(not (span[1] <= s or span[0] >= e) for s, e in consumed)

    # 1) sequence continuations — the strongest checkable kind: recover the
    #    generator from the stated prefix, then exactly compare its prediction
    #    against the claimed continuation.
    for m in _RE_CONTINUATION.finditer(text):
        prefix, claimed = _ints(m.group(1)), _ints(m.group(2))
        detail: Dict[str, Any] = {"prefix": prefix, "claimed_continuation": claimed}
        try:
            inv = collapse(prefix)
            if inv.verified:
                predicted = list(inv.predict(len(prefix) + len(claimed)))[len(prefix):]
                # exact integer comparison (engine may return floats/ints)
                ok = all(
                    Fraction(str(p)).limit_denominator(10**9) == Fraction(q)
                    for p, q in zip(predicted, claimed)
                ) and len(predicted) == len(claimed)
                status = "VERIFIED" if ok else "REFUTED"
                detail.update(model_class=inv.model_class,
                              predicted=[int(p) if float(p).is_integer() else float(p)
                                         for p in predicted])
            else:
                status = "REFUSED"
                detail["reason"] = ("no exactly-verified generator for the prefix; "
                                    "the engine will not certify the continuation "
                                    "in either direction")
        except Exception as exc:  # engine abstention surfaces as refusal, not a crash
            status = "REFUSED"
            detail["reason"] = f"engine declined: {type(exc).__name__}"
        claims.append({"kind": "sequence_continuation", "text": m.group(0)[:100],
                       "status": status, **detail})
        consumed.append(m.span())

    # 2) exact arithmetic
    for m in _RE_ARITH.finditer(text):
        if _overlaps(m.span()):
            continue
        ok = _check_arith(m.group(1), m.group(2), m.group(3), m.group(4))
        status = "REFUSED" if ok is None else ("VERIFIED" if ok else "REFUTED")
        claims.append({"kind": "arithmetic", "text": m.group(0), "status": status})
        consumed.append(m.span())

    # 3) percentage claims
    for m in _RE_PERCENT.finditer(text):
        if _overlaps(m.span()):
            continue
        ok = (_frac(m.group(1)) / 100) * _frac(m.group(2)) == _frac(m.group(3))
        claims.append({"kind": "percentage", "text": m.group(0),
                       "status": "VERIFIED" if ok else "REFUTED"})
        consumed.append(m.span())

    # 4) bare integer runs — structural recovery with held-out proof; an
    #    abstention here is the honest common case for numbers in prose.
    for m in _RE_RUN.finditer(text):
        if _overlaps(m.span()):
            continue
        seq = _ints(m.group(0))
        detail = {"sequence": seq[:20]}
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
            status = "REFUSED"
            detail["reason"] = f"engine declined: {type(exc).__name__}"
        claims.append({"kind": "sequence", "text": m.group(0).strip()[:80],
                       "status": status, **detail})
        consumed.append(m.span())

    claims.sort(key=lambda c: text.find(c["text"][:20]) if c["text"] else 0)
    return claims


def certify(text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Certify the checkable claims in *text*; refuse to bless the rest.

    Returns a certificate dict (schema ``primus.certificate/1``) with per-claim
    statuses, honest counts, a modest verdict, and a SHA-256 attestation over
    input and certificate. Designed to be called as a tool by agents: feed it
    a model's answer, gate on ``counts["refuted"] == 0``, and treat
    ``unverifiable_remainder`` as exactly that — unverified, not endorsed.
    """
    from primus import __version__  # local import to avoid a cycle at package load

    text = text if isinstance(text, str) else str(text)
    claims = extract_claims(text)
    counts = {
        "checkable": len(claims),
        "verified": sum(c["status"] == "VERIFIED" for c in claims),
        "refuted": sum(c["status"] == "REFUTED" for c in claims),
        "refused": sum(c["status"] == "REFUSED" for c in claims),
    }
    # is there meaningful text beyond the checkable spans?
    stripped = text
    for c in claims:
        if c["text"]:
            stripped = stripped.replace(c["text"], " ", 1)
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
                  "chars": len(text)},
        "claims": claims,
        "counts": counts,
        "unverifiable_remainder": unverifiable,
        "verdict": verdict,
    }
    if meta:
        cert["meta"] = meta
    body = json.dumps(cert, sort_keys=True, separators=(",", ":"), default=str)
    cert["attestation"] = {"sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
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
        if c["status"] == "REFUSED" and c.get("reason"):
            lines.append(f"      {c['reason']}")
    if not cert["claims"]:
        lines.append("  (no checkable claims found)")
    lines += ["", f"  VERDICT: {cert['verdict']}",
              f"  attestation sha256 {cert['attestation']['sha256'][:32]}…"]
    return "\n".join(lines)


def _selftest() -> int:
    """Fast offline gates for the certify layer. Returns count of failures."""
    fails = 0

    def gate(name: str, cond: bool) -> None:
        nonlocal fails
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        fails += 0 if cond else 1

    c = certify("2+2=4")
    gate("true arithmetic verified", c["counts"]["verified"] == 1 and c["counts"]["refuted"] == 0)
    c = certify("2+2=5")
    gate("false arithmetic refuted", c["counts"]["refuted"] == 1)
    c = certify("50% of 80 is 40")
    gate("percentage verified", c["counts"]["verified"] == 1)
    c = certify("The sequence 1 1 2 3 5 8 13 continues as 21, 34")
    gate("true continuation verified", c["counts"]["verified"] == 1)
    c = certify("The sequence 1 1 2 3 5 8 13 continues as 22, 34")
    gate("false continuation refuted", c["counts"]["refuted"] == 1)
    c = certify("The primes 2 3 5 7 11 13 continue as 17, 19")
    gate("out-of-class continuation refused (not guessed)",
         c["counts"]["refused"] == 1 and c["counts"]["verified"] == 0)
    c = certify("I believe this is broadly the right approach for your team.")
    gate("pure prose: nothing certified", c["counts"]["checkable"] == 0
         and c["unverifiable_remainder"])
    c = certify("7 2 9 4 4 8 3 1 6 5 look meaningful")
    gate("random run refused, not hallucinated", c["counts"]["refused"] == 1)
    print(f"  certify gates: {8 - fails}/8 passed")
    return fails


if __name__ == "__main__":
    raise SystemExit(_selftest())
