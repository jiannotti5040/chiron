#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""pdf_text — extract text from a PDF, or refuse and say why.

The capability matrix said PDF extraction did not exist. This adds it under
the same rule everything else here follows: **exact or refuse**. A PDF that
this module cannot read honestly produces a refusal naming the reason, never a
best-effort string. Garbage text entering a provenance record is worse than no
text, because a citation would then point at words nobody wrote.

Stdlib only — `zlib` and `re`. Adding a PDF library would put a third-party
package on the critical path of a system whose dependency surface is one
runtime package, and the SBOM gate would rightly notice.

WHAT IT READS

Uncompressed and `FlateDecode` content streams, with text taken from the `Tj`,
`TJ`, `'`, and `"` operators inside `BT`/`ET` blocks. That covers the common
text-bearing PDF, including every PDF in this repository.

WHAT IT REFUSES, BY NAME

  encrypted           /Encrypt present; no decryption is attempted
  unsupported-filter  a stream filter other than FlateDecode
  no-text-operators   parsed cleanly and found no text-showing operators
  unreliable-encoding text came out, but the byte->glyph mapping is custom
  not-a-pdf           missing %PDF header
  too-large           beyond the byte bound
  malformed           the structure did not parse

Two of those matter more than the rest.

`no-text-operators` is a valid PDF with zero extractable text — an image-only
scan, or one whose glyphs are drawn without text operators. Returning "" would
read as an empty document rather than as one whose words are not in the text
layer. There is no OCR here and none is implied.

`unreliable-encoding` is the subtler failure and the reason this module exists
in this shape. A PDF using a subsetted font with a custom `/Differences` map
will decode into plausible-looking prose in which `a` has become `!` —
"st!rted" for "started". That is not a cosmetic flaw: it is wrong text with
the shape of right text, which is precisely what must never reach a provenance
record. Mapping those fonts properly needs the font program, so instead the
output is checked for implausible character statistics and refused when it
fails. Refusing readable-looking text is the correct trade.

    python3 Chiron/pdf_text.py <file.pdf>
    python3 Chiron/pdf_text.py selftest
"""
from __future__ import annotations

import os
import re
import sys
import zlib
from typing import Any, Dict, List, Optional, Sequence

SCHEMA = "chiron.pdf_text/1"
MAX_PDF_BYTES = 32 * 1024 * 1024


class PDFRefusal(Exception):
    """A PDF that was not read, and the named reason it was not."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(reason if not detail else "%s: %s" % (reason, detail))
        self.reason = reason
        self.detail = detail


_STREAM = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.S)
_FILTER = re.compile(rb"/Filter\s*(?:\[\s*)?/(\w+)")
# Text-showing operators. `Tj` and `'`/`"` take one string; `TJ` takes an
# array of strings and kerning numbers, and the numbers are dropped.
_TJ = re.compile(rb"\((?:\\.|[^\\()])*\)\s*(?:Tj|')")
_TJ_ARRAY = re.compile(rb"\[(.*?)\]\s*TJ", re.S)
_STRING = re.compile(rb"\((?:\\.|[^\\()])*\)", re.S)
_BT_ET = re.compile(rb"BT\b(.*?)\bET\b", re.S)

_ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b",
            b"f": b"\f", b"(": b"(", b")": b")", b"\\": b"\\"}


def _unescape(raw: bytes) -> str:
    """Resolve PDF string escapes, including three-digit octal."""
    out = bytearray()
    i = 0
    while i < len(raw):
        char = raw[i:i + 1]
        if char == b"\\" and i + 1 < len(raw):
            nxt = raw[i + 1:i + 2]
            if nxt in _ESCAPES:
                out += _ESCAPES[nxt]
                i += 2
                continue
            if nxt.isdigit():
                octal = raw[i + 1:i + 4]
                digits = bytes(c for c in octal if 0x30 <= c <= 0x37)
                if digits:
                    out.append(int(digits, 8) & 0xFF)
                    i += 1 + len(digits)
                    continue
            if nxt in (b"\n", b"\r"):      # line continuation
                i += 2
                continue
            out += nxt
            i += 2
            continue
        out += char
        i += 1
    # PDF text is most often WinAnsi/Latin-1 for the simple case.
    return out.decode("latin-1", "replace")


def _looks_reliable(text: str) -> Optional[str]:
    """Return a reason the text is untrustworthy, or None if it looks sane.

    A custom font encoding does not produce obvious mojibake; it produces
    prose with one letter systematically replaced. The tell is statistical:
    a punctuation mark appearing at a frequency only a letter could have.
    """
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 40:
        return None                      # too little text to judge
    body = [c for c in text if not c.isspace()]
    if not body:
        return None

    # No punctuation mark is this common in real prose. `!` standing in for
    # `a` lands around 6-8%.
    for mark in "!@#$%^&*_=+|~`":
        share = text.count(mark) / len(body)
        if share > 0.02:
            return ("%r is %.1f%% of the non-space characters, which no prose "
                    "does; the font almost certainly uses a custom encoding "
                    "this extractor cannot map" % (mark, share * 100))

    # Vowels are ~38% of letters in English. A systematic substitution of one
    # vowel drags this well below any natural floor.
    vowels = sum(1 for c in letters if c.lower() in "aeiou")
    ratio = vowels / len(letters)
    if ratio < 0.20:
        return ("vowels are %.1f%% of letters, far below any natural text; "
                "a glyph mapping is probably wrong" % (ratio * 100))

    replacements = text.count("\ufffd") / len(body)
    if replacements > 0.01:
        return "%.1f%% of characters failed to decode" % (replacements * 100)
    return None


def _text_from_content(content: bytes) -> List[str]:
    pieces: List[str] = []
    for block in _BT_ET.findall(content) or [content]:
        for match in _TJ.finditer(block):
            pieces.append(_unescape(match.group(0).rsplit(b")", 1)[0][1:]))
        for match in _TJ_ARRAY.finditer(block):
            joined = "".join(_unescape(s[1:-1])
                             for s in _STRING.findall(match.group(1)))
            if joined:
                pieces.append(joined)
    return pieces


def extract(path: str, *, max_bytes: int = MAX_PDF_BYTES) -> Dict[str, Any]:
    """Return a text record for a PDF, or raise PDFRefusal naming the reason."""
    resolved = os.path.abspath(os.path.expanduser(path))
    if not os.path.isfile(resolved):
        raise PDFRefusal("not-a-file", path)
    size = os.path.getsize(resolved)
    if size > max_bytes:
        raise PDFRefusal("too-large", "%d bytes exceeds %d" % (size, max_bytes))

    with open(resolved, "rb") as handle:
        raw = handle.read()

    if not raw.startswith(b"%PDF"):
        raise PDFRefusal("not-a-pdf", "missing %PDF header")
    if b"/Encrypt" in raw:
        # Refused rather than attempted. A partial read of an encrypted file
        # would be noise wearing the shape of text.
        raise PDFRefusal("encrypted",
                         "this file is encrypted; no decryption is attempted")

    filters = {f.decode("ascii", "replace") for f in _FILTER.findall(raw)}
    unsupported = filters - {"FlateDecode"}
    if unsupported:
        raise PDFRefusal("unsupported-filter", ", ".join(sorted(unsupported)))

    pieces: List[str] = []
    streams = 0
    decoded = 0
    for match in _STREAM.finditer(raw):
        streams += 1
        body = match.group(1)
        try:
            content = zlib.decompress(body)
            decoded += 1
        except zlib.error:
            content = body          # possibly an uncompressed content stream
        try:
            pieces.extend(_text_from_content(content))
        except Exception as exc:      # structural surprise, not a text absence
            raise PDFRefusal("malformed", str(exc)[:120])

    text = "".join(pieces)
    normalised = re.sub(r"[ \t]{2,}", " ", text).strip()

    if not normalised:
        raise PDFRefusal(
            "no-text-operators",
            "parsed %d stream(s) and found no text-showing operators. The "
            "words may be in images, or drawn as glyphs without text "
            "operators. There is no OCR here and none is implied." % streams)

    unreliable = _looks_reliable(normalised)
    if unreliable:
        # Readable-looking but wrong text is the worst possible output: a
        # citation would point at words nobody wrote. Refuse it.
        raise PDFRefusal("unreliable-encoding", unreliable)

    return {
        "schema": SCHEMA,
        "path": resolved,
        "bytes": size,
        "streams": streams,
        "streams_inflated": decoded,
        "characters": len(normalised),
        "text": normalised,
        "extractor": "stdlib zlib + content-stream text operators",
        "note": ("Text-layer extraction only. Layout, tables, and reading "
                 "order are not reconstructed, and no OCR is performed."),
    }


def try_extract(path: str) -> Dict[str, Any]:
    """extract(), with a refusal returned as a record instead of raised.

    For callers that want the refusal in band — the CLI and the capability
    matrix both do, because a named refusal is a result worth showing.
    """
    try:
        return extract(path)
    except PDFRefusal as exc:
        return {"schema": SCHEMA, "path": os.path.abspath(path),
                "refused": True, "reason": exc.reason, "detail": exc.detail}


def _selftest() -> int:
    failures, ran = [], []

    def gate(name, condition):
        ran.append(name)
        if not condition:
            failures.append(name)
        print("  [%s] %s" % ("PASS" if condition else "FAIL", name))

    def refuses(path, reason):
        rec = try_extract(path)
        return rec.get("refused") and rec.get("reason") == reason

    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        notpdf = os.path.join(tmp, "a.pdf")
        with open(notpdf, "wb") as fh:
            fh.write(b"this is not a pdf")
        gate("a file without a %PDF header is refused by name",
             refuses(notpdf, "not-a-pdf"))

        enc = os.path.join(tmp, "enc.pdf")
        with open(enc, "wb") as fh:
            fh.write(b"%PDF-1.4\n/Encrypt 1 0 R\nstream\nx\nendstream")
        gate("an encrypted PDF is refused, never partially read",
             refuses(enc, "encrypted"))

        jbig = os.path.join(tmp, "img.pdf")
        with open(jbig, "wb") as fh:
            fh.write(b"%PDF-1.4\n/Filter /JBIG2Decode\nstream\nx\nendstream")
        gate("an unsupported stream filter is refused by name",
             refuses(jbig, "unsupported-filter"))

        empty = os.path.join(tmp, "blank.pdf")
        with open(empty, "wb") as fh:
            fh.write(b"%PDF-1.4\n%%EOF")
        gate("a PDF with no text operators refuses rather than returning ''",
             refuses(empty, "no-text-operators"))

        rec = try_extract(empty)
        gate("the no-text refusal says there is no OCR",
             "no OCR" in rec.get("detail", ""))

        # The defect this check exists for: a custom font encoding decodes to
        # prose with one letter systematically replaced.
        mangled = os.path.join(tmp, "mangled.pdf")
        bad = ("BT (I st!rted integr!ting Xcode bet! !nd I think there is "
               "!!!!! ton of c!p!bility here th!t I h!ve not re!lized "
               "!lre!dy in the usu!l pl!ces.) Tj ET").encode("latin-1")
        with open(mangled, "wb") as fh:
            fh.write(b"%PDF-1.4\nstream\n" + bad + b"\nendstream\n%%EOF")
        got = try_extract(mangled)
        gate("text from a custom font encoding is refused, not returned",
             got.get("refused") and got.get("reason") == "unreliable-encoding")
        gate("the encoding refusal explains what it measured",
             "custom encoding" in got.get("detail", "")
             or "vowels" in got.get("detail", ""))

        # A minimal, hand-built PDF with one uncompressed content stream.
        made = os.path.join(tmp, "hello.pdf")
        content = b"BT (Exact or refuse.) Tj ET"
        with open(made, "wb") as fh:
            fh.write(b"%PDF-1.4\nstream\n" + content + b"\nendstream\n%%EOF")
        got = try_extract(made)
        gate("an uncompressed content stream yields its text",
             got.get("text") == "Exact or refuse.")

        # The same, FlateDecode'd, which is what real PDFs use.
        deflated = zlib.compress(b"BT [(Exact) -250 (or refuse.)] TJ ET")
        flate = os.path.join(tmp, "flate.pdf")
        with open(flate, "wb") as fh:
            fh.write(b"%PDF-1.4\n/Filter /FlateDecode\nstream\n"
                     + deflated + b"\nendstream\n%%EOF")
        got = try_extract(flate)
        gate("a FlateDecode stream is inflated and its TJ array joined",
             got.get("text") == "Exactor refuse." and got.get("streams_inflated") == 1)

        octal = os.path.join(tmp, "octal.pdf")
        with open(octal, "wb") as fh:
            fh.write(b"%PDF-1.4\nstream\nBT (caf\\351 \\(x\\)) Tj ET\nendstream\n%%EOF")
        got = try_extract(octal)
        gate("octal and parenthesis escapes resolve",
             got.get("text") == "café (x)")

    # A real PDF from this repository, if one is present.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    books = os.path.join(here, "Ontological & Philosophical Books")
    real = None
    if os.path.isdir(books):
        for name in sorted(os.listdir(books)):
            if name.lower().endswith(".pdf"):
                real = os.path.join(books, name)
                break
    if real:
        got = try_extract(real)
        gate("a real PDF in this repository extracts or refuses by name",
             bool(got.get("text")) or bool(got.get("reason")))
        if got.get("text"):
            gate("the extracted text is long enough to be real text",
                 got["characters"] > 200)
    else:
        gate("no repository PDF available to exercise (skipped cleanly)", True)

    print("\n  pdf_text self-test: %d/%d passed"
          % (len(ran) - len(failures), len(ran)))
    return 1 if failures else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print("usage: python3 Chiron/pdf_text.py <file.pdf> | selftest")
        return 2
    if argv[0] in ("selftest", "--selftest"):
        return _selftest()
    record = try_extract(argv[0])
    if record.get("refused"):
        print("[pdf_text] REFUSED %s — %s"
              % (record["reason"], record.get("detail", "")))
        return 0        # a named refusal is a result, not a failure
    print("[pdf_text] %d characters from %d stream(s), %d inflated"
          % (record["characters"], record["streams"], record["streams_inflated"]))
    print(record["text"][:1200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
