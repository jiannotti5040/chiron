#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
test_twins_exact.py  --  EXTERNAL cross-lock for the Caramuel twin count.

Grows the vault OUTWARD (external validation, exactness), it does not touch
any source of truth. It asserts ONLY already-true exact facts, so it cannot
manufacture a false verification -- it can only catch a future regression.

It cross-locks the twin headline number across three independent sources that
should never be allowed to drift apart:

  (1) EXACT ARITHMETIC   279,608,910,057,308,160 = 2**31 * 3**12 * 5 * 7**2
                          69,902,227,514,327,040 = 2**29 * 3**12 * 5 * 7**2
                          and simple == 4 * retrograde  (two frozen binary
                          toggles between the reading modes).
  (2) THE CORPUS         Infectatrum/corpus/plate_026.json (IESVS SOL)
                          Infectatrum/corpus/plate_027.json (MARIA STELLA)
  (3) THE ENGINE         Chiron.twins_proof()  and  caramuel_twin_spaces()

NOTE (no overclaiming): the 2**31 * 3**12 * 5 * 7**2 *slot reading* (which
factor plays which combinatorial role) is a hypothesis about the generator.
What is asserted here is only the EXACT INTEGER IDENTITY and that all three
sources carry the same integer -- nothing about how Caramuel's wheels are
physically arranged.

Run:  python3 test_twins_exact.py     (exit 0 iff every cross-lock holds)
"""

import json
import sys
from pathlib import Path

SIMPLE = 279608910057308160
RETRO = 69902227514327040

_HERE = Path(__file__).resolve().parent          # .../Primus
_VAULT = _HERE.parent                            # .../chiron-vault
_CHIRON = _VAULT / "Chiron"
_CORPUS = _VAULT / "Infectatrum" / "corpus"


def _find_key(obj, key):
    """Recursively collect every value stored under `key` (schema-agnostic)."""
    out = []

    def rec(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == key:
                    out.append(v)
                rec(v)
        elif isinstance(o, list):
            for v in o:
                rec(v)

    rec(obj)
    return out


def _load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run() -> int:
    checks = []

    def check(name, cond):
        checks.append((name, bool(cond)))

    # -- (1) exact arithmetic ------------------------------------------------
    check("arithmetic: 2^31 * 3^12 * 5 * 7^2 == 279,608,910,057,308,160",
          2 ** 31 * 3 ** 12 * 5 * 7 ** 2 == SIMPLE)
    check("arithmetic: 2^29 * 3^12 * 5 * 7^2 == 69,902,227,514,327,040",
          2 ** 29 * 3 ** 12 * 5 * 7 ** 2 == RETRO)
    check("arithmetic: simple == 4 * retrograde (two frozen toggles)",
          SIMPLE == 4 * RETRO)
    check("arithmetic: twins share the core 3^12 * 5 * 7^2",
          SIMPLE // (2 ** 31) == RETRO // (2 ** 29) == 3 ** 12 * 5 * 7 ** 2)

    # -- (2) the corpus ------------------------------------------------------
    try:
        p26 = _load(_CORPUS / "plate_026.json")
        p27 = _load(_CORPUS / "plate_027.json")
        check("corpus: plate_026 claimed_simple_verses == SIMPLE",
              SIMPLE in _find_key(p26, "claimed_simple_verses"))
        check("corpus: plate_027 claimed_simple_verses == SIMPLE",
              SIMPLE in _find_key(p27, "claimed_simple_verses"))
        check("corpus: plate_027 claimed_retrograde_distichs == RETRO",
              RETRO in _find_key(p27, "claimed_retrograde_distichs"))
    except Exception as e:  # a missing/renamed corpus file is a real regression
        check("corpus: plates load and carry the twin counts (%r)" % e, False)

    # -- (3) the engine ------------------------------------------------------
    try:
        if str(_CHIRON) not in sys.path:
            sys.path.insert(0, str(_CHIRON))
        import chiron  # noqa: E402  (path set above)
        pr = chiron.twins_proof()
        check("engine: twins_proof() reports same_origin",
              pr["same_origin"] is True)
        check("engine: XXVI fingerprint == XXVII fingerprint",
              pr["xxvi_fingerprint"] == pr["xxvii_fingerprint"])
        check("engine: verses_each == SIMPLE == 2^31*3^12*5*7^2",
              pr["verses_each"] == SIMPLE == 2 ** 31 * 3 ** 12 * 5 * 7 ** 2)
        tw = chiron.caramuel_twin_spaces()
        check("engine: caramuel_twin_spaces().size == SIMPLE", tw.size == SIMPLE)
        # -- the cross-lock itself: all three sources carry ONE integer ------
        corpus_val = _find_key(_load(_CORPUS / "plate_026.json"),
                               "claimed_simple_verses")[0]
        check("CROSS-LOCK: arithmetic == corpus == engine (one integer)",
              (2 ** 31 * 3 ** 12 * 5 * 7 ** 2) == corpus_val == pr["verses_each"])
    except Exception as e:
        check("engine: Chiron twin proof imports and agrees (%r)" % e, False)

    # -- report --------------------------------------------------------------
    passed = sum(1 for _, ok in checks if ok)
    print("=" * 70)
    print("test_twins_exact  --  external cross-lock for the Caramuel twins")
    print("=" * 70)
    for name, ok in checks:
        print("  [%s] %s" % ("PASS" if ok else "FAIL", name))
    print("-" * 70)
    print("  %d/%d cross-lock gates passed" % (passed, len(checks)))
    if passed == len(checks):
        print("  GREEN -- corpus, exact arithmetic, and the engine agree exactly.")
    print("=" * 70)
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(run())
