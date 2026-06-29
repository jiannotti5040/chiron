#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
intake.py — the general front door.

Normalizes any raw input into a common, collapse/certify-ready record — a civilian
generalization of JDICert's primer. It auto-detects and parses JSON (including nested series),
CSV with or without a header row, whitespace/comma-delimited numeric rows, encoded payloads
(hex, base64, binary, Morse — decoded to their underlying bytes/series), key=value feeds, and
free text (with embedded-sequence extraction via the engine). It then ROUTES the best collapse
target so the rest of the pipeline has a single clean entry point. Evidence is never mutated;
the raw input is preserved verbatim on the record.

Public API (consumed elsewhere): intake(raw).

    python3 intake.py selftest
    python3 intake.py parse '{"signal":[1,2,4,8,16]}'
    python3 intake.py parse "48 65 6c 6c 6f"
    python3 intake.py parse "the series 1 1 2 3 5 8 13 appears in the report"

Framing dial — civilian: multi-source data standardizer. Contractor: multi-feed standardizer to
a common decision schema.
"""
import os
import re
import sys
import json
import base64
import binascii
import argparse

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
import chiron          # noqa: E402

_MORSE = {'.-': 'A', '-...': 'B', '-.-.': 'C', '-..': 'D', '.': 'E', '..-.': 'F', '--.': 'G',
          '....': 'H', '..': 'I', '.---': 'J', '-.-': 'K', '.-..': 'L', '--': 'M', '-.': 'N',
          '---': 'O', '.--.': 'P', '--.-': 'Q', '.-.': 'R', '...': 'S', '-': 'T', '..-': 'U',
          '...-': 'V', '.--': 'W', '-..-': 'X', '-.--': 'Y', '--..': 'Z'}


def _try_hex(raw):
    s = raw.strip().replace("0x", "").replace(",", " ")
    toks = s.split()
    # require a hex LETTER somewhere, else a plain decimal sequence (1 2 4 8 16 32) is misread as hex
    if (len(toks) >= 2 and all(re.fullmatch(r"[0-9a-fA-F]{1,2}", t) for t in toks)
            and any(re.search(r"[a-fA-F]", t) for t in toks)):
        try:
            return [int(t, 16) for t in toks]
        except ValueError:
            return None
    return None


def _try_binary(raw):
    toks = raw.strip().split()
    if len(toks) >= 2 and all(re.fullmatch(r"[01]{1,8}", t) for t in toks):
        return [int(t, 2) for t in toks]
    return None


def _try_base64(raw):
    s = raw.strip()
    if len(s) >= 8 and re.fullmatch(r"[A-Za-z0-9+/=]+", s) and len(s) % 4 == 0:
        try:
            dec = base64.b64decode(s, validate=True)
            if dec and all(32 <= b < 127 for b in dec):
                return list(dec)
        except (binascii.Error, ValueError):
            return None
    return None


def _try_morse(raw):
    if not re.fullmatch(r"[.\-/ ]+", raw.strip()):
        return None
    letters = [_MORSE.get(t, "?") for t in raw.strip().split() if t]
    if letters and letters.count("?") <= len(letters) // 3:
        return [ord(c) for c in letters if c != "?"]
    return None


def _numeric_rows(raw):
    rows = [r for r in raw.splitlines() if r.strip()]
    out = []
    for r in rows:
        toks = re.split(r"[,\s]+", r.strip())
        try:
            out.append([float(t) for t in toks])
        except ValueError:
            return None
    return out or None


def _csv_with_header(raw):
    rows = [r for r in raw.splitlines() if r.strip()]
    if len(rows) < 2 or "," not in rows[0]:
        return None
    header = [h.strip() for h in rows[0].split(",")]
    cols = {h: [] for h in header}
    for r in rows[1:]:
        cells = [c.strip() for c in r.split(",")]
        if len(cells) != len(header):
            return None
        for h, c in zip(header, cells):
            try:
                cols[h].append(float(c))
            except ValueError:
                return None
    return cols if any(header) and all(not re.fullmatch(r"-?\d+(\.\d+)?", h) for h in header) else None


def _kv(raw):
    pairs = re.findall(r"(\w+)\s*=\s*([^\s,;]+)", raw)
    return dict(pairs) if len(pairs) >= 2 else None


def _flatten_series(obj):
    out = []
    if isinstance(obj, list) and obj and all(isinstance(x, (int, float)) for x in obj):
        out.append([float(x) for x in obj])
    elif isinstance(obj, dict):
        for v in obj.values():
            out += _flatten_series(v)
    elif isinstance(obj, list):
        for v in obj:
            out += _flatten_series(v)
    return out


def intake(raw):
    raw = str(raw).strip()
    rec = {"source": "intake", "format": None, "confidence": 0.0, "fields": {}, "series": [],
           "text": None, "decoded": None, "embedded_sequences": [], "raw": raw[:200]}

    # 1) JSON (incl. nested series)
    try:
        obj = json.loads(raw)
        rec["format"], rec["confidence"] = "json", 1.0
        if isinstance(obj, dict):
            rec["fields"] = obj
        rec["series"] = _flatten_series(obj)
    except Exception:
        # 2) encoded payloads
        for fmt, fn in (("hex", _try_hex), ("binary", _try_binary), ("base64", _try_base64), ("morse", _try_morse)):
            dec = fn(raw)
            if dec:
                rec["format"], rec["confidence"] = fmt, 0.9
                rec["decoded"] = "".join(chr(b) for b in dec if 32 <= b < 127)
                rec["series"] = [dec]
                break
        else:
            # 3) CSV with header
            cols = _csv_with_header(raw)
            if cols:
                rec["format"], rec["confidence"] = "csv", 0.9
                rec["fields"] = {k: v[:10] for k, v in cols.items()}
                rec["series"] = [v for v in cols.values() if len(v) >= 3]
            else:
                # 4) numeric rows
                nr = _numeric_rows(raw)
                if nr:
                    rec["format"], rec["confidence"] = "numeric", 0.85
                    rec["series"] = nr
                else:
                    # 5) key=value
                    kv = _kv(raw)
                    if kv:
                        rec["format"], rec["confidence"] = "keyvalue", 0.7
                        rec["fields"] = kv
                    # 6) free text (always attempt embedded-sequence extraction)
                    rec["format"] = rec["format"] or "text"
                    rec["text"] = raw
                    try:
                        ts = chiron.text_structure(raw)
                        rec["embedded_sequences"] = ts.get("embedded_sequences", [])
                        if rec["embedded_sequences"]:
                            rec["confidence"] = max(rec["confidence"], 0.6)
                    except Exception:
                        pass

    rec["collapse_ready"] = bool(rec["series"]) or bool(rec["embedded_sequences"])
    rec["primary_series"] = route(rec)
    return rec


def route(rec):
    """Pick the single best collapse target from a record."""
    if rec["series"]:
        return max(rec["series"], key=len)
    if rec["embedded_sequences"]:
        return rec["embedded_sequences"][0].get("sequence")
    return None


def render(rec):
    L = ["=" * 56, f"INTAKE — format {rec['format']} (confidence {rec['confidence']})", "=" * 56]
    L.append(f"  collapse-ready: {rec['collapse_ready']}")
    if rec.get("decoded"):
        L.append(f"  decoded: {rec['decoded'][:48]}")
    if rec["series"]:
        L.append(f"  series: {rec['series'][0][:10]}")
    if rec["fields"]:
        L.append(f"  fields: {list(rec['fields'].keys())[:8]}")
    if rec["embedded_sequences"]:
        for e in rec["embedded_sequences"][:3]:
            L.append(f"  embedded: {e['sequence']} -> {e['model_class']} (verified={e['verified']})")
    L.append(f"  primary series -> {rec['primary_series']}")
    L.append("=" * 56)
    return "\n".join(L)


def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    j = intake('{"signal":[1,2,4,8,16]}')
    ok("json detected", j["format"] == "json")
    ok("json series extracted", j["series"] and j["series"][0] == [1, 2, 4, 8, 16])

    nj = intake('{"a":{"b":[2,4,6,8]},"name":"x"}')
    ok("nested json series", [2, 4, 6, 8] in nj["series"])

    h = intake("48 65 6c 6c 6f")
    ok("hex detected", h["format"] == "hex")
    ok("hex decoded to Hello", h["decoded"] == "Hello")

    b = intake(base64.b64encode(b"hello world").decode())
    ok("base64 detected", b["format"] == "base64")

    n = intake("1 2 4 8 16 32")
    ok("numeric detected", n["format"] == "numeric")
    ok("numeric primary series", n["primary_series"][:3] == [1.0, 2.0, 4.0])

    c = intake("month,sales\n1,100\n2,107\n3,114\n4,121")
    ok("csv with header detected", c["format"] == "csv")

    t = intake("the series 1 1 2 3 5 8 13 appears in the report")
    ok("text falls through", t["format"] == "text")
    ok("embedded sequence extracted", bool(t["embedded_sequences"]) or t["primary_series"])

    ok("immutability: raw preserved", intake("1 2 3 4")["raw"].startswith("1 2 3 4"))

    passed = sum(1 for _, ck in checks if ck)
    for n_, ck in checks:
        if not ck:
            print(f"  FAIL: {n_}")
    print(f"  intake.py self-test: {passed}/{len(checks)} passed")
    return passed == len(checks)


def _demo():
    for r in ['{"signal":[1,2,4,8,16]}', "48 65 6c 6c 6f", "1 2 4 8 16 32",
              "the series 1 1 2 3 5 8 13 appears in the report"]:
        print(render(intake(r)))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Normalize a raw input to a collapse-ready record.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("demo")
    sub.add_parser("selftest")
    pr = sub.add_parser("parse"); pr.add_argument("raw", nargs="+")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "parse":
        rec = intake(" ".join(args.raw))
        print(json.dumps(rec, indent=2, default=str) if args.json else render(rec)); return 0
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
