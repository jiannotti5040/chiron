#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""Reject active license claims that contradict the repository's Apache map.

Historical records may correctly mention the previous PolyForm license. This
gate does not rewrite or grade those hash-pinned records. It scans tracked
current code, configuration, and public documentation for wording that would
misstate Apache-2.0 as imposing owner-controlled commercial restrictions.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_SUFFIXES = {".md", ".py", ".json", ".txt", ".swift", ".sh", ".yml", ".toml"}
EXCLUDED_PREFIXES = ("Chiron/artifacts/", "studies/")
FORBIDDEN = (
    re.compile(r"commercial\s+use\s+is\s+reserved\s+to\s+(?:the\s+)?owner", re.I),
    re.compile(r"free\s+for\s+any\s+noncommercial\s+use", re.I),
    re.compile(r"commercial\s+use\s+is\s+licensed", re.I),
    re.compile(r"License\s+1\.0\.0:\s*noncommercial\s+use", re.I),
    re.compile(r"Apache[- ]2\.0[^\n]*\bnoncommercial", re.I),
    re.compile(r"Proprietary\s+and\s+strictly\s+restricted", re.I),
)


def tracked_paths():
    raw = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [item.decode("utf-8") for item in raw.split(b"\0") if item]


def main() -> int:
    findings = []
    for relative in tracked_paths():
        if relative.startswith(EXCLUDED_PREFIXES):
            continue
        if os.path.splitext(relative)[1].lower() not in TEXT_SUFFIXES:
            continue
        path = os.path.join(ROOT, relative)
        try:
            with open(path, encoding="utf-8") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(lines, start=1):
            if any(pattern.search(line) for pattern in FORBIDDEN):
                findings.append((relative, line_number, line.strip()[:160]))

    if findings:
        print("[license] contradictory active license claims found:")
        for path, line, text in findings:
            print(f"  {path}:{line}: {text}")
        return 1
    print("[license] PASS — no active Apache/noncommercial or owner-restricted claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
