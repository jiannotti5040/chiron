#!/usr/bin/env python3
"""
llm_certify.py — an accountability certificate over an LLM's output.

This is the Chiron discipline turned into a wrapper for language models. It does NOT bless the model
or call its answer correct. It produces an honest, signed record that separates what is *checkable*
from what is not, and audits the *honesty* of how the claim was stated:

  1. Candor audit       — condescension / unearned confidence / evasion / opacity (chiron.audit).
  2. Verifiable claims  — extract the checkable claims (numeric sequences, arithmetic) and run them
                          through the exact engine: each is VERIFIED, REFUSED, or left UNVERIFIABLE.
  3. Governance gate     — the SoCPM duty-of-care rule over the output (govern.py).
  4. Attestation         — a Merkle root over the output + the certificate (tamper-evident).

The verdict is deliberately modest: "of N checkable claims, M verified and K refused; the rest is
unverifiable by exact methods; candor X." The engine certifies the checkable part and flags the
rest — it never certifies a free-text claim as true. That honesty is the product.

    echo "The sequence 2 4 6 8 10 continues as 12, 14. Also 2+2=5." | python3 llm_certify.py
    python3 llm_certify.py --text "..."         # certify a string
    python3 llm_certify.py selftest

Status: implemented & tested. Reuses the real engine, candor, and governance.
"""
import os
import re
import sys
import json
import time
import hashlib
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402  collapse (verify) + audit (candor)
import govern as _gov  # noqa: E402  SoCPM gate


# ---------------------------------------------------------------------
# claim extraction — only the checkable kinds; everything else is flagged unverifiable
# ---------------------------------------------------------------------
def extract_claims(text):
    claims = []
    # arithmetic equations: a (op) b = c
    for m in re.finditer(r"(-?\d+)\s*([+\-*x×])\s*(-?\d+)\s*=\s*(-?\d+)", text):
        a, op, b, c = int(m.group(1)), m.group(2), int(m.group(3)), int(m.group(4))
        truth = {"+": a + b, "-": a - b}.get(op, a * b if op in "*x×" else None)
        claims.append({"kind": "arithmetic", "text": m.group(0),
                       "verified": truth is not None and truth == c,
                       "expected": truth})
    # numeric sequences: a run of 5+ integers
    for m in re.finditer(r"(?:-?\d+[ ,]+){4,}-?\d+", text):
        seq = [int(x) for x in re.findall(r"-?\d+", m.group(0))]
        if len(seq) >= 5:
            inv = chiron.collapse(seq)
            claims.append({"kind": "sequence", "text": m.group(0).strip()[:60],
                           "verified": bool(inv.verified),
                           "model_class": inv.model_class})
    return claims


# ---------------------------------------------------------------------
def certify_llm_output(text, domain="general", context=None):
    text = str(text or "")
    audit = chiron.audit(text)
    candor = float(getattr(audit, "candor_score", 0.0))

    claims = extract_claims(text)
    verified = [c for c in claims if c.get("verified")]
    refused = [c for c in claims if not c.get("verified")]
    n_check = len(claims)

    # governance: value-alignment proxied by candor; human-impact assumed material for a wrapper
    gov = _gov.govern(0.6, 0.7, 0.6, 0.6, candor, domain, context or {})
    gov_verdict = gov.get("verdict") if isinstance(gov, dict) else getattr(gov, "verdict", str(gov))

    body = {"output_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "candor": round(candor, 3), "claims": claims,
            "governance": gov_verdict, "domain": domain}
    merkle = hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()

    verdict = (f"{len(verified)}/{n_check} checkable claims verified"
               if n_check else "no exactly-checkable claims found")
    return {
        "title": "LLM Output Accountability Certificate",
        "issued": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "what_this_is": "An audit of an LLM output: what is exactly checkable is checked; the rest is "
                        "flagged unverifiable. This certifies accountability, NOT that the answer is true.",
        "candor": {"score": round(candor, 3), "grade": getattr(audit, "grade", None),
                   "findings": getattr(audit, "findings", [])[:5]},
        "checkable_claims": {"total": n_check, "verified": len(verified), "refused": len(refused),
                             "detail": claims},
        "unverifiable_note": "Free-text/semantic factual claims are NOT verifiable by exact methods "
                             "and are neither confirmed nor denied here.",
        "governance": gov_verdict,
        "verdict": verdict,
        "attestation": {"output_sha256": body["output_sha256"], "merkle_root": merkle,
                        "deterministic": True},
        "legal_status": "Assurance/audit artifact. Not a legal determination, not legal advice, and "
                        "not a correctness guarantee.",
    }


def render(c):
    L = ["=" * 60, "LLM OUTPUT ACCOUNTABILITY CERTIFICATE", "=" * 60]
    L.append("  " + c["what_this_is"])
    L.append(f"  Candor ......... {c['candor']['score']}  ({c['candor']['grade']})")
    cc = c["checkable_claims"]
    L.append(f"  Checkable ...... {cc['verified']}/{cc['total']} verified, {cc['refused']} refused")
    for d in cc["detail"][:8]:
        mark = "VERIFIED" if d.get("verified") else "REFUSED "
        L.append(f"     [{mark}] {d['kind']}: {d['text']}")
    L.append(f"  Unverifiable ... {c['unverifiable_note'][:70]}…")
    L.append(f"  Governance ..... {c['governance']}")
    L.append(f"  Verdict ........ {c['verdict']}")
    L.append(f"  Attestation .... merkle={c['attestation']['merkle_root'][:24]}…")
    L.append(f"  Legal status ... {c['legal_status']}")
    L.append("=" * 60)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    good = certify_llm_output("The pattern 2 4 6 8 10 12 continues, and 2+2=4.")
    ok("verifies a true sequence claim",
       any(d["kind"] == "sequence" and d["verified"] for d in good["checkable_claims"]["detail"]))
    ok("verifies a true arithmetic claim",
       any(d["kind"] == "arithmetic" and d["verified"] for d in good["checkable_claims"]["detail"]))

    bad = certify_llm_output("Obviously 2+2=5, and the sequence 3 1 4 1 5 9 2 6 is clearly arithmetic.")
    ok("refuses a false arithmetic claim",
       any(d["kind"] == "arithmetic" and not d["verified"] for d in bad["checkable_claims"]["detail"]))
    ok("refuses a non-structured sequence claim",
       any(d["kind"] == "sequence" and not d["verified"] for d in bad["checkable_claims"]["detail"]))
    ok("overconfident phrasing lowers candor", bad["candor"]["score"] <= good["candor"]["score"])

    ok("never certifies correctness (verdict is modest)",
       "verified" in good["verdict"] and "correct" not in good["verdict"].lower())
    ok("attestation present + deterministic",
       len(good["attestation"]["merkle_root"]) >= 32
       and certify_llm_output("The pattern 2 4 6 8 10 12 continues, and 2+2=4.")["attestation"]["merkle_root"]
       == good["attestation"]["merkle_root"])
    ok("states it is not a legal determination", "Not a legal determination" in good["legal_status"])
    ok("flags the unverifiable as neither confirmed nor denied",
       "neither confirmed nor denied" in good["unverifiable_note"])

    passed = sum(1 for _, c in checks if c)
    print("llm_certify self-test")
    for n, c in checks:
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
    print(f"  {passed}/{len(checks)} checks")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Accountability certificate over an LLM output.")
    ap.add_argument("rest", nargs="*")
    ap.add_argument("--text", default=None)
    ap.add_argument("--domain", default="general")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    if args.rest and args.rest[0] == "selftest":
        return 0 if _selftest() else 1
    text = args.text if args.text is not None else (
        " ".join(args.rest) or (sys.stdin.read() if not sys.stdin.isatty() else ""))
    if not text.strip():
        return 0 if _selftest() else 1
    c = certify_llm_output(text, args.domain)
    print(json.dumps(c, indent=2, default=str) if args.json else render(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
