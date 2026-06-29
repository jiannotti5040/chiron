#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Primus verses — run Caramuel's machine forward.

    python3 primus_verses.py                      # plate verses + the Tot tibi proteus run
    python3 primus_verses.py --plate XIII         # reconstruct one plate's verses from its walks
    python3 primus_verses.py --proteus "Tot tibi sunt dotes Virgo quot sidera caelo" --max 40320

Two things the engine already supports:
  1. Reconstruct a labyrinth's verses by walking its ductus paths and joining the
     cell tokens, then meter-validate each with the native dactylic-hexameter scanner.
  2. Proteus generation: permute a verse's words and keep only those that still scan
     as a hexameter (op_proteus + the scanner). The count is the proteus yield.

Note: op_proteus caps its search (default 5040). The full n! space for longer verses
is exactly the bulk, parallel job the optional native kernel targets — see FORMAL/
ARCHITECTURE. Counts below are reported as 'valid / searched' so the cap is explicit.
"""
import os
import sys
import json
import glob
import time
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chiron  # noqa: E402

TOT_TIBI = "Tot tibi sunt dotes Virgo quot sidera caelo"


def _corpus_dir():
    for c in (os.path.join(HERE, "..", "Infectatrum", "corpus"),
              os.path.join(HERE, "Infectatrum", "corpus")):
        if os.path.isdir(c):
            return os.path.abspath(c)
    return None


def _load_plate(tab):
    cdir = _corpus_dir()
    if not cdir:
        return None
    for p in glob.glob(os.path.join(cdir, "plate_0*.json")):
        d = json.load(open(p, encoding="utf-8"))
        if str(d.get("tabula")) == str(tab):
            return d
    return None


def plate_verses(d):
    """Reconstruct each ductus verse by walking the figure and joining tokens."""
    fig = d.get("figure", {})
    toks, walks = fig.get("tokens", {}), fig.get("walks", {})
    out = []
    for name, path in walks.items():
        words = [toks.get(n, "?") for n in path]
        line = " ".join(words)
        out.append({"ductus": name, "verse": line,
                    "scans_hexameter": chiron.scans_as_hexameter(line)})
    return out


def scanner_mode():
    try:
        import cltk  # noqa: F401
        return "strict (CLTK prosody)"
    except Exception:
        return "coarse (pure-Python fallback — rejects non-metrical junk but over-accepts word-order)"


def proteus(words, max_perms):
    """Permute the words, keep those whose space-joined line scans as a hexameter
    under whatever scanner is available. Honest about the scanner's strictness."""
    import itertools
    import math
    valid, searched = [], 0
    t = time.time()
    for i, perm in enumerate(itertools.permutations(words)):
        if i >= max_perms:
            break
        searched += 1
        line = " ".join(perm)
        if chiron.scans_as_hexameter(line):
            valid.append(line)
    return {"words": words, "n": len(words), "n_factorial": math.factorial(len(words)),
            "searched": searched, "admitted": len(valid), "seconds": round(time.time() - t, 3),
            "scanner": scanner_mode(), "samples": valid[:5]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plate", default=None)
    ap.add_argument("--proteus", default=None)
    ap.add_argument("--max", type=int, default=5040)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.proteus:
        r = proteus(args.proteus.split(), args.max)
        print(json.dumps(r, indent=2) if args.json else
              "proteus: admitted %d of %d searched (n!=%d, %.3fs)\n  scanner: %s\n  e.g. %s"
              % (r["admitted"], r["searched"], r["n_factorial"], r["seconds"],
                 r["scanner"], (r["samples"][0] if r["samples"] else "—")))
        return 0

    if args.plate:
        d = _load_plate(args.plate)
        if not d:
            print("plate not found:", args.plate); return 1
        vs = plate_verses(d)
        if args.json:
            print(json.dumps({"tabula": d.get("tabula"), "verses": vs}, indent=2)); return 0
        print("TAB %s — %s" % (d.get("tabula"), d.get("title_translation", "")))
        for v in vs:
            print("  [%-12s] %s  %s" % (v["ductus"], "✓scan" if v["scans_hexameter"] else "      ", v["verse"]))
        return 0

    # default: a couple plates + the Tot tibi proteus showcase
    print("=" * 70)
    print("PRIMUS VERSES — running the labyrinth forward")
    print("=" * 70)
    for tab in ("XIII", "XXVI"):
        d = _load_plate(tab)
        if not d:
            continue
        print("\nTAB %s — %s" % (tab, d.get("title_translation", "")[:60]))
        for v in plate_verses(d)[:4]:
            print("  [%-12s]%s %s" % (v["ductus"], " ✓" if v["scans_hexameter"] else "  ", v["verse"][:78]))
    print("\nProteus showcase — '%s'" % TOT_TIBI)
    r = proteus(TOT_TIBI.split(), 40320)
    print("  admitted %d of %d permutations searched (n! = %d), %.2fs"
          % (r["admitted"], r["searched"], r["n_factorial"], r["seconds"]))
    print("  scanner: %s" % r["scanner"])
    print("  Honest read: the coarse fallback over-accepts word-order, so this is an")
    print("  UPPER BOUND, not the true proteus count. A strict scanner (CLTK, or a")
    print("  native Rust kernel) yields the real, smaller number — exactly the bulk,")
    print("  parallel job native backing targets.")
    for s in r["samples"][:3]:
        print("    -", s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
