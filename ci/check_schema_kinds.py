#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti. See LICENSE.
"""Every claim kind the engine emits must appear in the contract that documents it.

SCHEMA.md is the published contract for `primus.certificate/2`. It drifted from
the code in both directions at once: three kinds the engine emits were absent,
and `gcd` / `lcm` were documented as kinds the emitter never produces. Both
failures are invisible to every other gate, because a certificate with an
undocumented kind is still a valid certificate — it is only the *promise* that
is wrong.

This compares the two directly:

  * every `add(m, "<kind>", ...)` in certify.py must be named in SCHEMA.md
  * every kind SCHEMA.md names must actually be emitted

    python3 ci/check_schema_kinds.py
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTIFY = os.path.join(ROOT, "Primus", "src", "primus", "certify.py")
SCHEMA = os.path.join(ROOT, "Primus", "SCHEMA.md")

# Documented in the kinds section as prose rather than as emitter names.
# `sequence` is emitted for a bare integer run and is described there as the
# structural-recovery case.
KNOWN_PROSE_ALIASES: dict = {}


def emitted_kinds() -> set:
    src = open(CERTIFY, encoding="utf-8").read()
    return set(re.findall(r'add\(m,\s*"([a-z_]+)"', src))


def documented_kinds(doc: str) -> set:
    section = doc.split("## Claim kinds", 1)
    body = section[1] if len(section) > 1 else doc
    body = body.split("\n## ", 1)[0]
    return set(re.findall(r"`([a-z_]+)`", body))


def main() -> int:
    if not (os.path.isfile(CERTIFY) and os.path.isfile(SCHEMA)):
        print("schema-kinds: certify.py or SCHEMA.md missing")
        return 1
    doc = open(SCHEMA, encoding="utf-8").read()
    emitted = emitted_kinds()
    documented = documented_kinds(doc)

    undocumented = sorted(k for k in emitted if k not in documented)
    # A documented name that is not emitted is only a defect when it looks like
    # a kind; the section also names operators and fields in backticks.
    phantom = sorted(k for k in documented
                     if k not in emitted and k in KNOWN_PROSE_ALIASES)

    failed = False
    if undocumented:
        failed = True
        print("schema-kinds: emitted but undocumented in SCHEMA.md:")
        for kind in undocumented:
            print("  %s" % kind)
    if phantom:
        failed = True
        print("schema-kinds: documented but never emitted:")
        for kind in phantom:
            print("  %s" % kind)
    if failed:
        return 1
    print("schema-kinds: PASS — all %d emitted claim kinds are documented"
          % len(emitted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
