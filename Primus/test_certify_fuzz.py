#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
test_certify_fuzz.py — adversarial gates for the certificate layer.

A gate gets attacked. These tests throw hostile input at `certify` and
demand four properties: (1) no crash, ever; (2) bounded time; (3) bounds
respected (truncation / claim cap / integer cap recorded honestly); and
(4) the verdict on planted claims is unchanged by surrounding garbage —
noise must not flip VERIFIED/REFUTED/REFUSED.

    python3 test_certify_fuzz.py
"""
import os
import random
import string
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
from primus.certify import (MAX_CLAIMS, MAX_INT_DIGITS,  # noqa: E402
                            MAX_TEXT_CHARS, certify)

FAILS = 0
BUDGET_S = 10.0     # generous wall-clock bound per hostile case (CI-safe)


def gate(name, cond):
    global FAILS
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    FAILS += 0 if cond else 1


def timed(text):
    t0 = time.time()
    cert = certify(text)
    return cert, time.time() - t0


def main():
    rng = random.Random(0)

    # 1. random garbage — printable, unicode, control chars
    for label, alphabet in [
        ("printable", string.printable),
        ("unicode", "π≡×÷∑√∞°±µ†‡§¶•ﬁ🙂🤖" + string.ascii_letters + string.digits),
    ]:
        ok = True
        for _ in range(50):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 2000)))
            try:
                cert, dt = timed(s)
                ok &= dt < BUDGET_S and isinstance(cert["counts"], dict)
            except Exception:
                ok = False
                break
        gate(f"random {label} garbage: no crash, bounded time", ok)

    # 2. pathological digit floods
    cert, dt = timed(("1," * 20000))
    gate("20k-comma digit flood: bounded time, no crash", dt < BUDGET_S)
    cert, dt = timed(" ".join(str(i) for i in range(5000)))
    gate("5k-term integer run: bounded time", dt < BUDGET_S)
    cert, dt = timed(("9" * 300 + " + ") * 500 + "1 = 2")
    gate("repeated huge-operand soup: bounded time", dt < BUDGET_S)

    # 3. bounds are enforced AND recorded
    cert, _ = timed("x" * (MAX_TEXT_CHARS + 5000))
    gate("oversize input truncated and recorded",
         cert["input"]["truncated"] is True and cert["input"]["chars"] == MAX_TEXT_CHARS + 5000)
    many = " ".join(f"{i}+{i}={2*i}." for i in range(MAX_CLAIMS + 100))
    cert, dt = timed(many)
    gate("claim cap enforced and flagged",
         cert["counts"]["checkable"] <= MAX_CLAIMS and cert["claims_capped"] is True
         and dt < BUDGET_S)
    big = "9" * (MAX_INT_DIGITS + 50)
    cert, _ = timed(f"{big} * 2 = {big}0")
    gate("giant integers refused, never computed",
         cert["counts"]["refused"] >= 1 and cert["counts"]["verified"] == 0)
    cert, dt = timed("2 ** 9999999 = 4")
    gate("huge exponent refused fast",
         cert["counts"]["refused"] == 1 and dt < BUDGET_S)

    # 4. verdicts are stable under surrounding noise
    noise = "".join(rng.choice(string.ascii_letters + " .,;!") for _ in range(3000))
    planted = f"{noise[:1500]} 2+2=5 {noise[1500:]} gcd(12, 18) = 6 and 97 is prime."
    cert, _ = timed(planted)
    gate("planted claims survive noise: 1 refuted + 2 verified",
         cert["counts"]["refuted"] == 1 and cert["counts"]["verified"] == 2)
    gate("coverage small when text is mostly noise", cert["coverage"] < 0.10)

    # 4b. the closed_form scan under attack (anchor-windowed like the rest)
    cert, dt = timed("a(n) = " + "(" * 4000 + "n" + ")" * 4000 + " matches 1, 2, 3")
    gate("closed-form paren bomb: bounded time, nothing falsely verified",
         dt < BUDGET_S and cert["counts"]["verified"] == 0)
    cert, dt = timed("a(n) = n matches 0, 1, 2. " * 2000)
    gate("closed-form anchor flood: claim cap + bounded time",
         dt < BUDGET_S and cert["counts"]["checkable"] <= MAX_CLAIMS)
    planted_cf = f"{noise[:800]} a(n) = n*n + 1 matches 1, 2, 5, 10, 17 {noise[800:]}"
    cert, _ = timed(planted_cf)
    gate("planted closed form survives noise: verified exactly once",
         cert["counts"]["verified"] == 1)

    # 5. determinism (modulo timestamp/attestation)
    a, b = certify(planted), certify(planted)
    for k in ("created_utc", "attestation"):
        a.pop(k), b.pop(k)
    gate("same input -> same certificate (minus timestamp)", a == b)

    # 6. zero-division and degenerate forms neither crash nor verify falsely
    cert, _ = timed("5 / 0 = 0 and 17 mod 0 = 3 and lcm of 0 and 0 is 0")
    gate("division/mod by zero refused or exactly judged, no crash",
         cert["counts"]["refuted"] + cert["counts"]["refused"] +
         cert["counts"]["verified"] == cert["counts"]["checkable"])

    print(f"\n  {16 - FAILS}/16 fuzz gates passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
