#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Counts asserted in documentation must equal counts the repository produces.

Four documents asserted four different totals for the same folded sweep — 49,
52, 54 and 58 — while the fold actually reported 61. Each number was right when
it was written and none was wrong in a way any test could see, because a
document is not executed. That is exactly the drift this checks.

It compares every documented `N/N` sweep figure and every "N modules" claim
against values read from the repository at run time: the monolith's own
selftest, and `Chiron/manifest.json`.

    python3 ci/check_counts.py          # report
    python3 ci/check_counts.py --fix    # rewrite the documents to the truth
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MONO_DIR = os.path.join(ROOT, "Chiron Monolith")
MONOLITH = os.path.join(MONO_DIR, "chiron_monolith.py")
MANIFEST = os.path.join(ROOT, "Chiron", "manifest.json")

# Documents that quote the folded-sweep total.
SWEEP_DOCS = ("docs/GATES.md", "docs/BATTERIES.md")
# Documents that quote how many modules the fold embeds.
EMBED_DOCS = ("Chiron/README.md",)


def observed_sweep() -> int | None:
    """Run the fold's own selftest and read the total it prints."""
    if not os.path.isfile(MONOLITH):
        return None
    try:
        out = subprocess.run([sys.executable, MONOLITH, "--selftest"],
                             cwd=MONO_DIR, capture_output=True, text=True,
                             timeout=1800).stdout
    except Exception:
        return None
    m = re.search(r"(\d+)/(\d+) modules green through the fold", out)
    return int(m.group(2)) if m else None


def observed_embedded() -> int | None:
    """How many modules the fold actually contains, from the manifest the
    build writes beside it."""
    path = os.path.join(MONO_DIR, "manifest.json")
    for candidate in (path, MANIFEST):
        if os.path.isfile(candidate):
            try:
                data = json.load(open(candidate, encoding="utf-8"))
            except Exception:
                continue
            if isinstance(data.get("scripts"), list):
                return len(data["scripts"])
    return None


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    fix = "--fix" in argv

    sweep = observed_sweep()
    if sweep is None:
        print("counts: could not observe the folded sweep; skipping")
        return 0

    problems = []
    for rel in SWEEP_DOCS:
        path = os.path.join(ROOT, rel)
        if not os.path.isfile(path):
            continue
        text = open(path, encoding="utf-8").read()
        # Only lines that are *about* the folded sweep. These documents record
        # many separate batteries, and 23/23 or 26/26 are other suites whose
        # totals are correct. An earlier draft matched every N/N in the file
        # and would have rewritten those to the sweep total, destroying right
        # answers to fix a wrong one.
        lines = text.splitlines(keepends=True)
        out = []
        for line in lines:
            is_sweep_line = re.search(r"fold(ed)?\s+sweep|through the fold",
                                      line, re.I)
            if is_sweep_line:
                for pair in re.findall(r"\b(\d+)/(\1)\b", line):
                    value = pair[0]
                    if int(value) != sweep:
                        problems.append((rel, "%s/%s" % (value, value),
                                         "%d/%d" % (sweep, sweep)))
                        if fix:
                            line = line.replace("%s/%s" % (value, value),
                                                "%d/%d" % (sweep, sweep))
            out.append(line)
        if fix:
            open(path, "w", encoding="utf-8").write("".join(out))

    # The two manifests must agree. The fold copies Chiron/manifest.json next
    # to the artifact, so when `chiron build` folded before regenerating it the
    # artifact shipped the previous build's manifest -- 96 modules beside a
    # source tree of 92 -- and rebuilding could not converge, because each run
    # copied what the run before it wrote. `bin/chiron` now builds the manifest
    # first; this fails if that order is ever reversed again. It is not a
    # documentation check, so `--fix` cannot paper over it.
    source_manifest = os.path.join(ROOT, "Chiron", "manifest.json")
    folded_manifest = os.path.join(MONO_DIR, "manifest.json")
    if os.path.isfile(source_manifest) and os.path.isfile(folded_manifest):
        try:
            a = len(json.load(open(source_manifest, encoding="utf-8"))["scripts"])
            b = len(json.load(open(folded_manifest, encoding="utf-8"))["scripts"])
        except Exception:
            a = b = None
        if a is not None and a != b:
            print("counts: FAIL — the artifact ships a stale manifest "
                  "(source describes %d modules, the fold beside it %d)." % (a, b))
            print("  Run `python3 bin/chiron build`. If one build does not "
                  "converge, the manifest is being written after the fold "
                  "copies it.")
            return 1

    embedded = observed_embedded()
    if embedded:
        for rel in EMBED_DOCS:
            path = os.path.join(ROOT, rel)
            if not os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8").read()
            for value in {v for v in re.findall(r"all (\d+) modules", text)
                          if int(v) != embedded}:
                problems.append((rel, "all %s modules" % value,
                                 "all %d modules" % embedded))
                if fix:
                    text = text.replace("all %s modules" % value,
                                        "all %d modules" % embedded)
            if fix:
                open(path, "w", encoding="utf-8").write(text)

    if problems:
        print("counts: documentation disagrees with the repository "
              "(observed sweep %d, embedded %s):" % (sweep, embedded))
        for rel, was, should in problems:
            print("  %-24s %-12s -> %s" % (rel, was, should))
        if fix:
            print("counts: rewritten. Re-run without --fix to confirm.")
            return 0
        print("counts: run `python3 ci/check_counts.py --fix` to correct them.")
        return 1
    print("counts: PASS — documented totals match the fold (%d/%d)"
          % (sweep, sweep))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
