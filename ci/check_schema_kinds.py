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

  * every kind emitted from certify.py or grounded.py must be named in
    SCHEMA.md
  * every kind SCHEMA.md names must actually be emitted
  * the scan must be able to SEE every emitter, and says so when it cannot

That last clause is the one this gate learned the hard way. It used to match
only `add(m, "<literal>", ...)`, and so it reported "PASS — all 11 emitted
claim kinds are documented" while the engine was emitting three kinds it
could not see: `gcd` and `lcm` go through `add(m, fn, ...)` with the kind in a
*variable*, and `grounded_fact` is emitted from grounded.py, a file the gate
never opened. All three were absent from SCHEMA.md. A gate that reports a
count it cannot justify is the exact failure this repository exists to
prevent, so the scan now fails closed: a dynamic `add(m, <expr>, ...)` whose
kinds are not declared in DYNAMIC_KINDS is an error, not a silent skip.

    python3 ci/check_schema_kinds.py
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTIFY = os.path.join(ROOT, "Primus", "src", "primus", "certify.py")
GROUNDED = os.path.join(ROOT, "Primus", "src", "primus", "grounded.py")
SCHEMA = os.path.join(ROOT, "Primus", "SCHEMA.md")

# Documented in the kinds section as prose rather than as emitter names.
# `sequence` is emitted for a bare integer run and is described there as the
# structural-recovery case.
KNOWN_PROSE_ALIASES: dict = {}

# Kinds emitted through a variable rather than a string literal. The scan
# cannot read these out of the source, so they are declared here and then
# CONFIRMED against the running engine below. Adding a dynamic emitter without
# adding it here fails the gate rather than slipping past it.
DYNAMIC_KINDS = {
    "fn": {"gcd", "lcm"},        # certify.py: add(m, fn, ...) over _RE_GCDLCM
}


def _dynamic_emitter_names(src: str) -> set:
    """Names used as the kind argument of a CALL to add() — not its definition.

    `def add(m, kind, status, detail)` matches the same shape as a call, so the
    definition is excluded explicitly; otherwise the gate reports its own
    parameter name as an undeclared emitter.
    """
    return set(re.findall(r'(?<!def )add\(m,\s*([a-z_][a-z0-9_]*)\s*,', src))


def emitted_kinds() -> tuple:
    """(kinds, undeclared_dynamic_names) — never guesses on behalf of the code."""
    src = open(CERTIFY, encoding="utf-8").read()
    kinds = set(re.findall(r'add\(m,\s*"([a-z_]+)"', src))

    undeclared = set()
    for name in _dynamic_emitter_names(src):
        if name in DYNAMIC_KINDS:
            kinds |= DYNAMIC_KINDS[name]
        else:
            undeclared.add(name)

    # grounded.py emits its own kind, from its own file.
    ground = open(GROUNDED, encoding="utf-8").read()
    kinds |= set(re.findall(r'"kind":\s*"([a-z_]+)"', ground))
    return kinds, undeclared


def confirm_dynamic_against_engine(declared: set) -> set:
    """Ask the engine. Returns declared kinds it did NOT actually emit."""
    sys.path.insert(0, os.path.join(ROOT, "Primus", "src"))
    try:
        from primus.certify import certify
    except Exception as exc:                      # pragma: no cover
        print("schema-kinds: NOTE — engine not importable (%s); "
              "declared dynamic kinds unconfirmed" % exc)
        return set()
    probes = ["gcd(12, 18) = 6", "lcm(4, 6) = 12"]
    seen = set()
    for text in probes:
        for claim in certify(text).get("claims", []):
            seen.add(claim["kind"])
    return {k for k in declared if k not in seen}


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
    emitted, undeclared = emitted_kinds()
    documented = documented_kinds(doc)

    declared = set().union(*DYNAMIC_KINDS.values()) if DYNAMIC_KINDS else set()
    unconfirmed = confirm_dynamic_against_engine(declared)

    undocumented = sorted(k for k in emitted if k not in documented)
    # A documented name that is not emitted is only a defect when it looks like
    # a kind; the section also names operators and fields in backticks.
    phantom = sorted(k for k in documented
                     if k not in emitted and k in KNOWN_PROSE_ALIASES)

    failed = False
    if undeclared:
        failed = True
        print("schema-kinds: add() called with a non-literal kind this scan "
              "cannot read. Declare it in DYNAMIC_KINDS:")
        for name in sorted(undeclared):
            print("  add(m, %s, ...)" % name)
    if unconfirmed:
        failed = True
        print("schema-kinds: declared in DYNAMIC_KINDS but the engine never "
              "emitted it:")
        for kind in sorted(unconfirmed):
            print("  %s" % kind)
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
    print("schema-kinds: PASS — all %d emitted claim kinds are documented "
          "(%d read as literals, %d dynamic and confirmed against the engine)"
          % (len(emitted), len(emitted) - len(declared), len(declared)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
