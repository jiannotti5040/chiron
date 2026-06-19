#!/usr/bin/env python3
"""
PDF source adapter (optional dependency) — extract text from a PDF and run Chiron's
structural analysis on it, including recovery of any embedded numeric sequence.

    python3 ingest_pdf.py document.pdf
    python3 ingest_pdf.py --json document.pdf

Text extraction uses `pypdf` if installed (`pip install pypdf`). If it is not
present, the adapter says so honestly and exits cleanly — consistent with the
project's rule that optional capabilities degrade, they do not crash. The engine
itself remains offline and dependency-free.
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
    reader = pypdf.PdfReader(path)
    pages = reader.pages[:max_pages]
    return "\n".join((p.extract_text() or "") for p in pages)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", nargs="?", help="path to a PDF")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    status = {"pypdf_available": _HAVE}
    if not _HAVE:
        status["note"] = ("pypdf not installed — run `pip install pypdf` to enable PDF "
                          "ingestion. The engine is unaffected and stays dependency-free.")
        print(json.dumps(status, indent=2) if args.json else status["note"])
        return 0
    if not args.pdf:
        print("usage: python3 ingest_pdf.py document.pdf"); return 2
    if not os.path.exists(args.pdf):
        print("no such file: %s" % args.pdf); return 2

    text = extract_text(args.pdf)
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
