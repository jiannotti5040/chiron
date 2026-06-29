#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
Generate the worked examples and certificates in this folder from REAL engine
output — nothing here is hand-written result text.

    python3 examples/build_examples.py

Writes, next to this script:
  <name>.md                 a walkthrough: input -> collapse -> residual -> meaning
  certificates/<name>.json  the engine's own certificate (what found / why / falsify)
  README.md                 an index

Re-run it any time; the output is deterministic.
"""
import os
import sys
import json
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))            # the folder holding chiron.py
from chiron import collapse, solve_cipher, human_report  # noqa: E402

CERTS = os.path.join(HERE, "certificates")
os.makedirs(CERTS, exist_ok=True)

# (name, kind, input, plain-language meaning)
CASES = [
    ("fibonacci", "seq", "0 1 1 2 3 5 8 13 21 34",
     "Two seeds and one rule — each term is the sum of the previous two — regenerate "
     "the whole sequence and every future term. Chiron proves it by predicting terms "
     "it was never shown."),
    ("catalan", "seq", "1 1 2 5 14 42 132 429 1430 4862 16796 58786 208012 742900",
     "A holonomic (P-recursive) rule, the kind behind the Catalan numbers. These are "
     "not polynomials or simple recurrences, yet the exact generator is still pinned "
     "and verified on held-out terms."),
    ("squares", "seq", "0 1 4 9 16 25 36 49 64 81",
     "A degree-2 polynomial, recovered exactly in rational arithmetic. A naive "
     "curve-fit would also get this one — but only this kind."),
    ("powers_of_two", "seq", "1 2 4 8 16 32 64 128 256",
     "A geometric law (ratio 2): constant-size to store, infinite to extend."),
    ("primes", "seq", "2 3 5 7 11 13 17 19 23 29",
     "No closed-form generator exists in Chiron's hypothesis classes, so it ABSTAINS "
     "rather than fabricate one. This honest negative is the property the whole design "
     "is built around."),
    ("caesar_cipher", "cipher", "WKLV LV D VHFUHW PHVVDJH",
     "Given only ciphertext and no key, the solver recovers the plaintext and names "
     "the method, ranked against every classical scheme by English-likeness."),
    ("python_source", "code",
     "def f(x):\n    total = 0\n    for i in range(x):\n        total = total + i\n    return total",
     "Source collapses to a relabel-invariant structural skeleton: rename every "
     "variable or reformat the file and the skeleton — and therefore the fingerprint "
     "— is unchanged. A clone detector by construction."),
]


def _nums(s):
    return [int(x) if float(x).is_integer() else Fraction(x) for x in s.split()]


def _fmt(x):
    return str(x.numerator) if isinstance(x, Fraction) and x.denominator == 1 else str(x)


def _seq_md(name, raw, meaning):
    seq = _nums(raw)
    inv = collapse(seq)
    d = inv.to_dict()
    cert = human_report(inv)
    pred = ""
    if inv.verified:
        try:
            nxt = inv.predict(len(seq) + 3)[len(seq):]
            pred = ", ".join(_fmt(x) for x in nxt)
        except Exception:
            pred = ""
    lines = [
        "# Example — %s" % name.replace("_", " "),
        "",
        "**Input (a surface):** `%s`" % raw,
        "",
        "**Reproduce:**",
        "",
        "```bash",
        'python3 chiron.py explain %s' % raw,
        "```",
        "",
        "## What Chiron recovered",
        "",
        "| field | value |",
        "|---|---|",
        "| model class | `%s` |" % d["model_class"],
        "| verified (held-out, exact) | **%s** |" % d["verified"],
        "| description length | %s bits (vs %s bits to list the raw terms) |"
        % (d["model_bits"], d["surface_bits"]),
        "| compression ratio | %sx |" % d["compression_ratio"],
        "| residual | %s |" % (d["residual"] if d["residual"] else "none — fully explained"),
    ]
    if pred:
        lines.append("| next terms (predicted, unseen) | %s |" % pred)
    lines += [
        "",
        "## Why",
        "",
        "> %s" % d["explanation"],
        "",
        "## What this means",
        "",
        meaning,
        "",
        "## Certificate",
        "",
        "The engine's own certificate for this run is in "
        "[`certificates/%s.json`](certificates/%s.json) — *what was discovered, why it "
        "is believed, and what would falsify it.*" % (name, name),
        "",
    ]
    return "\n".join(lines), cert


def _cipher_md(name, raw, meaning):
    sol = solve_cipher(raw)
    inv = collapse(raw)
    cert = human_report(inv)
    cert["decoding"] = sol
    runners = "\n".join("| %s | `%s` |" % (r["method"], r["plaintext"][:48])
                        for r in sol.get("runners_up", []))
    lines = [
        "# Example — %s" % name.replace("_", " "),
        "",
        "**Input (ciphertext only, no key):** `%s`" % raw,
        "",
        "**Reproduce:**",
        "",
        "```bash",
        'python3 chiron.py solve "%s"' % raw,
        "```",
        "",
        "## What the solver recovered",
        "",
        "| field | value |",
        "|---|---|",
        "| method | **%s** |" % sol["method"],
        "| plaintext | **%s** |" % sol["plaintext"],
        "| confidence | %s |" % sol["confidence"],
        "| schemes tried | %s |" % sol["candidates_tried"],
        "",
        "Runners-up it ranked below the winner:",
        "",
        "| method | decoding |",
        "|---|---|",
        runners,
        "",
        "## What this means",
        "",
        meaning,
        "",
    ]
    return "\n".join(lines), cert


def _code_md(name, raw, meaning):
    inv = collapse({"code": raw})
    d = inv.to_dict()
    cert = human_report(inv)
    shown = raw.replace("\n", "\n    ")
    lines = [
        "# Example — %s" % name.replace("_", " "),
        "",
        "**Input (Python source):**",
        "",
        "```python",
        raw,
        "```",
        "",
        "## What Chiron recovered",
        "",
        "| field | value |",
        "|---|---|",
        "| model class | `%s` |" % d["model_class"],
        "| verified | **%s** |" % d["verified"],
        "| structure fingerprint | `%s` |" % d["family_fingerprint"],
        "",
        "## Why",
        "",
        "> %s" % d["explanation"],
        "",
        "## What this means",
        "",
        meaning,
        "",
    ]
    return "\n".join(lines), cert


def main():
    index = ["# Worked examples",
             "",
             "Every result below is real, deterministic engine output, regenerated by "
             "`python3 examples/build_examples.py`. Each shows a surface going in, the "
             "rule (or honest abstention) coming out, and what it means.",
             ""]
    for name, kind, raw, meaning in CASES:
        if kind == "seq":
            md, cert = _seq_md(name, raw, meaning)
        elif kind == "cipher":
            md, cert = _cipher_md(name, raw, meaning)
        else:
            md, cert = _code_md(name, raw, meaning)
        with open(os.path.join(HERE, name + ".md"), "w") as f:
            f.write(md)
        with open(os.path.join(CERTS, name + ".json"), "w") as f:
            json.dump(cert, f, indent=2, default=str)
        index.append("- [%s](%s.md) — %s" % (name.replace("_", " "), name,
                                              meaning.split(".")[0] + "."))
    index += ["",
              "Certificates (the engine's own *what found / why / falsify* records) are "
              "in [`certificates/`](certificates/)."]
    with open(os.path.join(HERE, "README.md"), "w") as f:
        f.write("\n".join(index) + "\n")
    print("wrote %d examples + certificates to %s" % (len(CASES), HERE))


if __name__ == "__main__":
    main()
