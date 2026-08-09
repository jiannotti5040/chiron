#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
PDF source adapter (optional dependency) — extract text from a PDF and run Chiron's
structural analysis on it, including recovery of any embedded numeric sequence.

    python3 ingest_pdf.py document.pdf
    python3 ingest_pdf.py --json document.pdf

Text extraction prefers `pypdf` when installed (`pip install pypdf`), because
it can read embedded font programs and therefore handles encodings the stdlib
reader must refuse. Without it, this adapter falls back to `pdf_text`, which
is stdlib-only and always available — so PDF ingestion works out of the box
and pypdf is an upgrade rather than a requirement. The engine itself remains
offline and dependency-free either way.
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chiron import text_structure  # noqa: E402

try:
    import pypdf  # type: ignore
    _HAVE = True
except Exception:
    _HAVE = False


def extract_text(path, max_pages=50):
    """Text from a PDF, preferring pypdf and falling back to the stdlib reader.

    Two tiers, one path. `pypdf` handles font encodings this repository cannot
    (it can read the embedded font program), so it is preferred when present.
    When it is absent — which is the default state of this checkout — the
    stdlib reader in `pdf_text` takes over rather than the whole capability
    going dark.

    The fallback refuses rather than guessing. A PDF whose glyph mapping it
    cannot trust comes back as a named refusal, because wrong text carrying
    the shape of right text is worse here than no text at all.
    """
    if _HAVE:
        reader = pypdf.PdfReader(path)
        pages = reader.pages[:max_pages]
        return "\n".join((p.extract_text() or "") for p in pages)

    import pdf_text
    record = pdf_text.try_extract(path)
    if record.get("refused"):
        raise pdf_text.PDFRefusal(record["reason"], record.get("detail", ""))
    return record["text"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="?", help="path to a PDF")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    status = {"pypdf_available": _HAVE,
              "extractor": "pypdf" if _HAVE else "stdlib (Chiron/pdf_text.py)"}
    if not _HAVE and not args.pdf:
        status["note"] = ("pypdf is not installed; the stdlib reader in "
                          "pdf_text.py will be used. `pip install pypdf` "
                          "handles font encodings the stdlib reader refuses.")
        print(json.dumps(status, indent=2) if args.json else status["note"])
        return 0
    if not args.pdf:
        print("usage: python3 ingest_pdf.py document.pdf"); return 2
    if not os.path.exists(args.pdf):
        print("no such file: %s" % args.pdf); return 2

    try:
        text = extract_text(args.pdf)
    except Exception as exc:
        # A named refusal is a result, not a crash. The rule this file already
        # states — optional capabilities degrade, they do not crash — applies
        # to the extractor's refusals too.
        reason = getattr(exc, "reason", "extraction-failed")
        detail = getattr(exc, "detail", str(exc))
        record = {"schema": "chiron.pdf_ingest/1", "refused": True,
                  "reason": reason, "detail": detail,
                  "source": os.path.basename(args.pdf),
                  "extractor": status["extractor"]}
        if args.json:
            print(json.dumps(record, indent=2))
        else:
            print("PDF not ingested: %s — %s" % (reason, detail))
            if reason == "unreliable-encoding":
                print("  `pip install pypdf` reads embedded font programs and "
                      "can usually handle this file.")
        return 0

    analysis = text_structure(text)
    analysis["source"] = os.path.basename(args.pdf)
    analysis["extracted_chars"] = len(text)
    if args.json:
        print(json.dumps(analysis, indent=2, default=str))
        return 0
    print("PDF ingested: %s (%d chars)" % (analysis["source"], analysis["extracted_chars"]))
    print("  words: %d  unique: %d  type/token: %s"
          % (analysis["words"], analysis["unique_words"], analysis["type_token_ratio"]))
    print("  exact string structure: %s" % analysis["exact_string_structure"])
    if analysis["embedded_sequences"]:
        print("  embedded numeric sequences recovered:")
        for e in analysis["embedded_sequences"]:
            print("    %s -> %s (verified=%s)" % (e["sequence"], e["model_class"], e["verified"]))
    print("  verdict: %s" % analysis["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
