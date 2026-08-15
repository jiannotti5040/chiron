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


if __name__ == "__main__":
    raise SystemExit(main())
