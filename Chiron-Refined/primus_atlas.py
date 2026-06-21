#!/usr/bin/env python3
"""
Primus atlas — run Chiron's collapse over the whole transcribed Caramuel atlas, not
just the two built-in twins.

    python3 primus_atlas.py            # collapse all plates + find cross-plate twins
    python3 primus_atlas.py --json

It reads the transcribed labyrinth plates (Infectatrum's corpus of TAB XIII–XXXIII),
feeds each plate's figure (tokens + ductus walks) into chiron.collapse(), and reports:
the recovered labyrinth topology per plate, structural twin pairs across the atlas
(plates that share one generator), and a grouping by Caramuel's plate families. The
adapter is tiny because the engine already speaks this format natively.
"""
import os
import sys
import json
import glob
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chiron  # noqa: E402


def _genre(family):
    """The plate genre (before the parenthetical description)."""
    return str(family or "?").split("(")[0].strip()


def _corpus_dir():
    for c in (os.path.join(HERE, "..", "Infectatrum", "corpus"),
              os.path.join(HERE, "Infectatrum", "corpus"),
              os.path.join(HERE, "primus_extra")):
        if os.path.isdir(c):
            return os.path.abspath(c)
    return None


def load_plates():
    cdir = _corpus_dir()
    if not cdir:
        return []
    out = []
    for p in sorted(glob.glob(os.path.join(cdir, "plate_0*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        fig = d.get("figure")
        if fig and "walks" in fig:
            out.append((d.get("tabula", "?"), d.get("family", "?"), fig, d))
    return out


def analyze():
    plates = load_plates()
    recs, rows = [], []
    for tab, family, fig, d in plates:
        try:
            inv = chiron.collapse(fig)
            recs.append((tab, family, inv))
            rows.append({"tabula": tab, "family": family,
                         "model_class": inv.model_class,
                         "n_nodes": inv.structure.get("n_nodes"),
                         "walks": len(fig["walks"]),
                         "verified": bool(inv.verified),
                         "source": d.get("source", "")})
        except Exception as e:
            rows.append({"tabula": tab, "family": family, "error": str(e)})
    # structural twins (share one generator across plates)
    twins = []
    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            try:
                if chiron.same_structure(recs[i][2], recs[j][2]).get("same_structure"):
                    twins.append({"a": recs[i][0], "b": recs[j][0],
                                  "family_a": _genre(recs[i][1]), "family_b": _genre(recs[j][1]),
                                  "cross_family": _genre(recs[i][1]) != _genre(recs[j][1])})
            except Exception:
                pass
    families = {}
    for r in rows:
        families.setdefault(_genre(r.get("family", "?")), []).append(r["tabula"])
    return {"plates": len(rows), "verified": sum(1 for r in rows if r.get("verified")),
            "rows": rows, "structural_twins": twins, "by_family": families}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    out = analyze()
    if out["plates"] == 0:
        print("No transcribed plates found (expected ../Infectatrum/corpus/plate_*.json).")
        return 1
    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 0
    print("=" * 72)
    print("PRIMUS ATLAS — Chiron over Caramuel's transcribed labyrinths")
    print("=" * 72)
    print("  %-6s %-32s %-20s %5s %5s %s" % ("TAB", "family", "topology", "nodes", "walks", "ok"))
    for r in out["rows"]:
        if "error" in r:
            print("  %-6s ERROR: %s" % (r["tabula"], r["error"])); continue
        print("  %-6s %-32s %-20s %5s %5s %s" % (
            r["tabula"], (r["family"] or "")[:32], r["model_class"],
            r["n_nodes"], r["walks"], "✓" if r["verified"] else "—"))
    print("\n  plates collapsed + verified: %d / %d" % (out["verified"], out["plates"]))
    print("\nStructural twins (plates sharing one generator):")
    if not out["structural_twins"]:
        print("  (none — every plate is structurally distinct)")
    for t in out["structural_twins"]:
        tag = "CROSS-FAMILY" if t["cross_family"] else "same-family"
        print("  TAB %s ⇔ TAB %s  [%s: %s / %s]" % (t["a"], t["b"], tag, t["family_a"], t["family_b"]))
    print("\nBy family (Caramuel's plate genres):")
    for fam, tabs in sorted(out["by_family"].items()):
        print("  %-34s %s" % (fam[:34], ", ".join(tabs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
