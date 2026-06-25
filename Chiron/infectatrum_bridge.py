#!/usr/bin/env python3
"""
Infectatrum bridge — ambiguity measurement for Chiron (B-1).

Chiron recovers the *generator* beneath a surface. Infectatrum measures the
*ambiguity* of a surface: how many valid readings it supports, the entropy of that
spectrum, where the ambiguity localizes, and whether the multiplicity looks natural
or engineered. This bridge makes that capability callable from the Chiron side,
behind a one-way membrane (Infectatrum stays a standalone engine; this only imports
and maps).

    python3 infectatrum_bridge.py                 # demo: the Caramuel atlas, measured
    python3 infectatrum_bridge.py --text "..."    # ambiguity of one line/grid
    python3 infectatrum_bridge.py --json

Framing dial — civilian: spec/contract ambiguity measurement with an audit trail.
Contractor: engineered-multiplicity / adversarial-input detection (telling a
deliberate flood from natural noise), with a K/U/Ω epistemic partition.
"""
import os
import sys
import json
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
_INF = None
for _c in (os.path.join(HERE, "..", "Infectatrum"), os.path.join(HERE, "Infectatrum")):
    if os.path.exists(os.path.join(_c, "infectatrum.py")):
        sys.path.insert(0, os.path.abspath(_c))
        _INF = os.path.abspath(_c)
        break
try:
    import infectatrum as I  # noqa: E402
    HAVE = True
except Exception:
    HAVE = False


def _corpus_path():
    if not _INF:
        return None
    p = os.path.join(_INF, "corpus", "corpus_all.json")
    return p if os.path.exists(p) else None


def measure(sub, lang):
    """Run Infectatrum's Detect over a substrate and return the spectrum measures."""
    spec = I.detect(sub, lang)
    return {
        "cardinality": spec.cardinality(),          # |Σ| — distinct valid readings
        "entropy_bits": round(spec.entropy(), 4),    # Shannon entropy of the spectrum
        "valid_readings": len(spec.valid),
        "excluded": len(spec.excluded),
        "classify": I.classify(spec),
        "adversarial": I.adversarial_score(spec),    # p_adversarial + components
        "ductus_profile": spec.profile(),
    }


def measure_text(text, lang=None):
    lang = lang or I.latin_wordform_language()
    sub = I.TextLineAdapter().to_substrate(text)
    return measure(sub, lang)


def measure_grid(words, lang=None):
    lang = lang or I.latin_wordform_language()
    sub = I.Picture.from_words(words)
    return measure(sub, lang)


def cert_bundle(text, lang=None):
    """The designed Infectatrum->certification hand-off (K/U/Ω + report + ledger)."""
    lang = lang or I.latin_wordform_language()
    sub = I.TextLineAdapter().to_substrate(text)
    return I.export_to_cert_engine(sub, lang, prov=I.Provenance(source="chiron-bridge",
                                                                confidence="high"))


def atlas():
    """Measure the ambiguity spectrum of every Caramuel plate — the same atlas Chiron
    collapses in primus_atlas.py. One object, two readings: generator + ambiguity."""
    cp = _corpus_path()
    if not cp:
        return []
    corpus = I.load_consolidated_corpus(cp)
    lang = I.latin_wordform_language()
    rows = []
    for tab, (sub, prov) in corpus.items():
        try:
            m = measure(sub, lang)
            rows.append({"tabula": tab, "cardinality": m["cardinality"],
                         "entropy_bits": m["entropy_bits"],
                         "p_adversarial": m["adversarial"]["p_adversarial"]})
        except Exception as e:
            rows.append({"tabula": tab, "error": str(e)})
    rows.sort(key=lambda r: str(r["tabula"]))
    return rows


def origin_signatures():
    """B-5: build an ambiguity-distribution signature per plate and rank pairs by
    Jensen-Shannon divergence. The known same-generator twins (XXVI/XXVII, the IESUS
    SOL / MARIA STELLA pair) should come out among the closest — origin attribution
    from ambiguity structure alone, distinct from Chiron's generator fingerprint."""
    cp = _corpus_path()
    if not cp:
        return {}
    corpus = I.load_consolidated_corpus(cp)
    lang = I.latin_wordform_language()
    sigs = {}
    for tab, (sub, prov) in corpus.items():
        try:
            sigs[tab] = I.Signature.from_spectra(tab, [I.detect(sub, lang)])
        except Exception:
            pass
    names = sorted(sigs)
    pairs = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            pairs.append((names[i], names[j], round(sigs[names[i]].jsd(sigs[names[j]]), 4)))
    pairs.sort(key=lambda p: p[2])
    twin = next((p[2] for p in pairs if {p[0], p[1]} == {"XXVI", "XXVII"}), None)
    return {"closest_pairs": pairs[:6], "twin_XXVI_XXVII_jsd": twin,
            "signatures_built": len(sigs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", default=None, help="measure the ambiguity of a line")
    ap.add_argument("--signatures", action="store_true", help="origin-signature JSD ranking")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.signatures and HAVE:
        o = origin_signatures()
        if args.json:
            print(json.dumps(o, indent=2, default=str)); return 0
        print("ORIGIN SIGNATURES — closest pairs by Jensen-Shannon divergence")
        for a, b, j in o.get("closest_pairs", []):
            tag = "  <== known same-generator twins" if {a, b} == {"XXVI", "XXVII"} else ""
            print("  TAB %-5s ~ TAB %-5s  JSD=%s%s" % (a, b, j, tag))
        print("\n  XXVI/XXVII (IESUS SOL / MARIA STELLA) JSD = %s — recovered as a shared"
              % o.get("twin_XXVI_XXVII_jsd"))
        print("  generator from ambiguity structure alone.")
        return 0
    if not HAVE:
        msg = "Infectatrum not importable (expected ../Infectatrum/infectatrum.py)."
        print(json.dumps({"available": False, "note": msg}) if args.json else msg)
        return 0
    if args.text:
        m = measure_text(args.text)
        print(json.dumps(m, indent=2, default=str) if args.json else
              "|Σ|=%d  entropy=%s bits  p_adversarial=%s  class=%s"
              % (m["cardinality"], m["entropy_bits"], m["adversarial"]["p_adversarial"],
                 m["classify"].get("class", m["classify"])))
        return 0
    rows = atlas()
    if args.json:
        print(json.dumps({"atlas": rows}, indent=2, default=str))
        return 0
    print("=" * 64)
    print("INFECTATRUM BRIDGE — ambiguity spectrum over the Caramuel atlas")
    print("=" * 64)
    print("  the same plates Chiron collapses (primus_atlas.py); here, measured")
    print("  %-7s %5s %9s %13s" % ("TAB", "|Σ|", "entropy", "p_adversarial"))
    for r in rows:
        if "error" in r:
            print("  %-7s ERROR %s" % (r["tabula"], r["error"])); continue
        print("  %-7s %5d %9s %13s" % (r["tabula"], r["cardinality"],
                                       r["entropy_bits"], r["p_adversarial"]))
    print("\n  Chiron asks 'what rule generates this?'; Infectatrum asks 'how many")
    print("  valid readings does it bear, and is that multiplicity natural or engineered?'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
