#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Refuse to ship credentials or one machine's filesystem layout.

Run before making the repository public, and on every push once it is. The
checks are deliberately narrow: a scanner that flags everything is one nobody
reads, and this must stay trustworthy enough that a hit means act now.

What it refuses:

  * credentials — provider API keys, GitHub and PyPI tokens, AWS access keys,
    Slack tokens, private key blocks, and literal bearer values
  * machine paths — a real home directory baked into a tracked file, which
    both leaks the maintainer's layout and breaks for everyone else

What it deliberately allows:

  * the author's own published contact address, which CITATION.cff exists to
    carry
  * `/Users/you/` and similar placeholders in documentation
  * audit records under docs/inventory/, which quote findings rather than
    make claims

    python3 ci/check_publishable.py
"""
from __future__ import annotations

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_SUFFIX = (".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".pages",
               ".ipynb", ".car")
MAX_BYTES = 3_000_000

CREDENTIALS = {
    "OpenAI-style key": re.compile(r"\bsk-[A-Za-z0-9]{32,}"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),
    "PyPI token": re.compile(r"\bpypi-Ag[A-Za-z0-9_\-]{40,}"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "Slack token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}"),
    "private key block": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}

# The two forms above miss the credential this project is most likely to meet:
# a Foundry session token, which has no recognisable prefix at all and travels
# as an opaque bearer value. Prefix matching cannot find it, so these two look
# for the shape instead -- a bearer header or a named assignment carrying a
# long opaque literal.
#
# This docstring used to claim the gate caught "literal bearer values" while no
# such check existed. In a repository whose whole discipline is refusing to
# assert what it cannot demonstrate, that was the worst available defect, and
# it is why the pair below is tested in both directions.
_BEARER = re.compile(r"\b[Bb]earer\s+([A-Za-z0-9._~+/=-]{20,})")
# The leading [A-Za-z0-9_]* is load-bearing: `\btoken` does not match inside
# PALANTIR_TOKEN, because `_` is a word character and there is no boundary
# before it. The first draft missed the exact credential this check exists for.
_ASSIGNED = re.compile(
    r"(?i)[A-Za-z0-9_]*(?:api[_-]?key|secret|token|password|passwd|credential)"
    r"\s*[:=]\s*[\"']([^\"'\s]{24,})[\"']")

# A value that is obviously not a secret. Documentation is full of these and a
# gate that flags them is a gate people learn to ignore.
_PLACEHOLDER = re.compile(
    r"(?i)^(?:[<${]|\.\.\.|x{4,}|your|my|the|placeholder|example|dummy|fake|"
    r"redacted|removed|test|sample|changeme|insert|paste|token|secret|value|"
    r"none|null|true|false)")
_HEXish = re.compile(r"^[0-9a-f]+$")


def _looks_like_a_real_secret(value: str) -> bool:
    """Reject the things that merely resemble one.

    Placeholders are excluded by prefix. Pure hexadecimal is excluded because
    this repository is full of SHA-256 digests -- 31 tracked files carry them,
    including NOTICE and every manifest -- and a digest is a published fact,
    not a credential. Requiring mixed character classes leaves the opaque,
    high-entropy values an actual token has.
    """
    if _PLACEHOLDER.match(value) or _HEXish.match(value):
        return False
    if value.count("/") >= 2 or value.startswith(("http", "com.", "org.")):
        return False          # a path, URL, or bundle identifier
    return (any(c.isdigit() for c in value)
            and any(c.isalpha() for c in value)
            and len(set(value)) >= 8)


def literal_secrets(text: str):
    """Bearer headers and named assignments carrying an opaque literal."""
    for name, pattern in (("literal bearer value", _BEARER),
                          ("assigned credential literal", _ASSIGNED)):
        for value in pattern.findall(text):
            if _looks_like_a_real_secret(value):
                yield name, value[:12] + "…"

# A real home directory. `/Users/you/` and `/path/to/` are placeholders and are
# the form documentation should use.
HOME_PATH = re.compile(r"/Users/(?!you/)[A-Za-z0-9_.-]+/")

ALLOWED_PREFIXES = ("docs/inventory/",)


def tracked_files() -> list:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    return [f for f in out.split("\n") if f]


def main() -> int:
    findings = []
    for rel in tracked_files():
        if rel.endswith(SKIP_SUFFIX) or rel.startswith(ALLOWED_PREFIXES):
            continue
        path = os.path.join(ROOT, rel)
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue

        for name, pattern in CREDENTIALS.items():
            if pattern.search(text):
                findings.append(("CREDENTIAL", rel, name))
        for name, shown in literal_secrets(text):
            findings.append(("CREDENTIAL", rel, "%s (%s)" % (name, shown)))
        for match in set(HOME_PATH.findall(text)):
            findings.append(("MACHINE PATH", rel, match))

    if findings:
        print("publishable: FAIL — %d issue(s)" % len(findings))
        for kind, rel, detail in findings[:40]:
            print("  [%s] %s  %s" % (kind, rel, detail))
        print("\nA credential must be revoked and removed from history, not "
              "merely deleted from the working tree.")
        return 1

    print("publishable: PASS — no credentials, no machine-specific paths in "
          "%d tracked files" % len(tracked_files()))
    return 0


def selftest() -> int:
    """The claims in this file's docstring, as tests.

    A scanner is trusted in two directions at once, and only one of them shows
    up in normal use: a gate that never fires looks identical whether it is
    working or broken. These pin both -- what must be caught, and what must be
    left alone, because a check that flags placeholders and digests is one
    people learn to scroll past.
    """
    # The fixtures are assembled from fragments rather than written whole.
    # Spelled out, this file would flag ITSELF -- and the honest fix is not to
    # exclude the scanner from its own scan, which would put a blind spot in
    # the one file that must never hide anything. No fragment matches alone;
    # the value under test is still the full string.
    jwt = "eyJhbGciOiJIUzI1NiJ9." + "aGVsbG8gd29ybGQ" + ".x7Qk2mZ"
    foundry = "ri.foundry.main-" + "9f2ab73c41de8890xyz"
    google = "AIzaSy" + "D3x9Kq2mNpQ7rVtL8wXyZ0aB1cD2eF3gH"
    must_catch = [
        ('Authorization: "Bearer %s"' % jwt,
         "bearer header carrying a real value"),
        ('PALANTIR_TOKEN = "%s"' % foundry,
         "the Foundry token this check exists for"),
        ('api_key: "%s"' % google,
         "a named key assignment"),
    ]
    must_ignore = [
        ("Authorization: Bearer $PALANTIR_TOKEN", "a shell variable"),
        ("Authorization: Bearer <your-token-here>", "a documentation placeholder"),
        ('token = "YOUR_TOKEN_HERE"', "an obvious placeholder"),
        ('"sha256": "a2ae55eb3ad81119dd119410121832ef02d97803dd043d7baca8cab751072f10"',
         "a published digest, of which this repo has thousands"),
        ('bundle_id = "com.jacobiannotti.chiron.mobile"', "an identifier"),
    ]
    failures = 0
    for text, why in must_catch:
        if not list(literal_secrets(text)):
            print("  [FAIL] missed: %s" % why); failures += 1
        else:
            print("  [PASS] caught: %s" % why)
    for text, why in must_ignore:
        if list(literal_secrets(text)):
            print("  [FAIL] false positive on %s" % why); failures += 1
        else:
            print("  [PASS] ignored: %s" % why)
    total = len(must_catch) + len(must_ignore)
    print("  publishable selftest: %d/%d passed" % (total - failures, total))
    return 1 if failures else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        raise SystemExit(selftest())
    raise SystemExit(main())
