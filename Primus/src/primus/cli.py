#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Jacob Iannotti
"""
primus.cli — the command-line front door.

    primus collapse "1 1 2 3 5 8 13 21"        recover + verify a generator
    primus collapse --json "3 1 4 1 5 9 2 6"   machine-readable (abstains here)
    primus certify "2+2=5 and 2 4 6 8 continues as 10"
    primus certify --facts facts.json report.txt   check against ground truth
    echo "<model output>" | primus certify -   certify stdin (agent tool-call)
    primus conjecture "0 1 128 2187 16384 ..."  guess-and-prove: GP proposes,
                                               the exact gate stamps or refuses
    primus selftest                            engine + certify + conjecture gates
    primus version
"""
from __future__ import annotations

import argparse
import json
import re
import sys


def _read_text(arg: str) -> str:
    if arg == "-":
        return sys.stdin.read()
    return arg


def _cmd_collapse(args: argparse.Namespace) -> int:
    from primus.engine import collapse

    raw = _read_text(args.surface)
    ints = re.findall(r"-?\d+", raw)
    tokens = re.sub(r"[-\d\s,]+", "", raw)
    surface = [int(x) for x in ints] if ints and not tokens else raw
    inv = collapse(surface)
    if args.json:
        print(json.dumps(inv.to_dict(), indent=2, default=str))
    else:
        print(inv.explanation)
    return 0 if inv.verified or not args.strict else 1


def _load_facts(spec):
    """Ground truth from a JSON literal or a file path, or None.

    Without facts, any claim whose truth lives outside the sentence is
    REFUSED — which on real operational prose is every claim. This is how a
    caller supplies the table the engine has never seen.
    """
    if not spec:
        return None
    import os
    if os.path.isfile(spec):
        with open(spec, "r", encoding="utf-8") as handle:
            return json.load(handle)
    try:
        return json.loads(spec)
    except ValueError:
        raise SystemExit("primus: --facts is neither a readable file nor valid "
                         "JSON: %s" % spec[:60])


def _cmd_certify(args: argparse.Namespace) -> int:
    from primus.certify import certify, render

    facts = _load_facts(getattr(args, "facts", None))

    if args.jsonl:
        # Pipeline mode: one certificate per input line, hash-chained so the
        # sequence of certificates is itself tamper-evident. Gate semantics
        # unchanged: --gate exits 1 if ANY line contained a refuted claim.
        import hashlib

        refuted_lines, prev = 0, "genesis"
        for line in (sys.stdin if args.text == "-" else open(args.text)):
            line = line.rstrip("\n")
            if not line.strip():
                continue
            cert = certify(line, facts=facts)
            cert["chain"] = {"prev_sha256": prev}
            prev = hashlib.sha256(
                (prev + cert["attestation"]["sha256"]).encode()).hexdigest()
            cert["chain"]["this_sha256"] = prev
            refuted_lines += 1 if cert["counts"]["refuted"] else 0
            print(json.dumps(cert, separators=(",", ":"), default=str))
        print(json.dumps({"chain_head": prev, "refuted_lines": refuted_lines},
                         separators=(",", ":")), file=sys.stderr)
        return 1 if (args.gate and refuted_lines) else 0

    cert = certify(_read_text(args.text), facts=facts)
    if args.json:
        print(json.dumps(cert, indent=2, default=str))
    else:
        print(render(cert))
    if args.gate:
        return 1 if cert["counts"]["refuted"] else 0
    return 0


def _cmd_conjecture(args: argparse.Namespace) -> int:
    from primus.conjecture import conjecture, render

    raw = _read_text(args.surface)
    ints = [int(x) for x in re.findall(r"-?\d+", raw)]
    cert = conjecture(ints, seed=args.seed, population=args.population,
                      generations=args.generations, holdout=args.holdout,
                      restarts=args.restarts)
    if args.json:
        print(json.dumps(cert, indent=2, default=str))
    else:
        print(render(cert))
    return 0 if cert["status"] == "VERIFIED" or not args.strict else 1


def _cmd_selftest(_args: argparse.Namespace) -> int:
    from primus.certify import _selftest
    from primus.engine import InvariantError, collapse

    fails = 0

    def gate(name: str, cond: bool) -> None:
        nonlocal fails
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        fails += 0 if cond else 1

    print("engine gates:")
    inv = collapse([1, 1, 2, 3, 5, 8, 13, 21])
    gate("fibonacci recovered + verified",
         inv.verified and "recurrence" in inv.model_class)
    inv = collapse([9, 16, 25, 36, 49, 64, 81, 100])
    gate("polynomial recovered + verified", inv.verified)
    inv = collapse([7, 2, 9, 4, 4, 8, 3, 1, 6, 5])
    gate("random surface honestly not verified", not inv.verified)
    try:
        collapse([])
        gate("empty surface raises, not crashes", False)
    except (InvariantError, ValueError):
        gate("empty surface raises, not crashes", True)
    print("certify gates:")
    fails += _selftest()
    print("conjecture gates:")
    from primus.conjecture import _selftest as _conjecture_selftest
    fails += _conjecture_selftest()
    print(f"PRIMUS {'GREEN' if fails == 0 else 'RED'} — "
          f"{'all gates passed' if fails == 0 else f'{fails} gate(s) failed'}")
    return 1 if fails else 0


def _cmd_version(_args: argparse.Namespace) -> int:
    import primus

    print(f"primus {primus.__version__} — exact recovery, held-out proof, "
          f"refusal over confidence. Owner: {primus.OWNER}.")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="primus",
        description="Exact invariant recovery with held-out verification and "
                    "refusal — and a certificate layer for LLM/agent output.")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collapse", help="recover the generator beneath a surface")
    c.add_argument("surface", help="integers ('1 1 2 3 5 8') or any string; '-' for stdin")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    c.add_argument("--strict", action="store_true",
                   help="exit 1 unless the result is exactly verified")
    c.set_defaults(fn=_cmd_collapse)

    c = sub.add_parser("certify", help="certify the checkable claims in text; "
                                       "refuse to bless the rest")
    c.add_argument("text", help="text to certify; '-' for stdin")
    c.add_argument("--json", action="store_true", help="emit the full certificate")
    c.add_argument("--facts", metavar="JSON|FILE",
                   help="ground truth for claims whose subject lives outside "
                        "the sentence: an object of subject -> value, or a "
                        "list of {subject, value, unit}. Without it such "
                        "claims are REFUSED.")
    c.add_argument("--gate", action="store_true",
                   help="exit 1 if any claim was REFUTED (agent gating)")
    c.add_argument("--jsonl", action="store_true",
                   help="pipeline mode: certify each input line, emit one "
                        "hash-chained certificate per line (chain head on stderr)")
    c.set_defaults(fn=_cmd_certify)

    c = sub.add_parser("conjecture",
                       help="guess-and-prove: a GP proposer behind the exact "
                            "gate — stamps only what verifies exactly")
    c.add_argument("surface", help="integers ('0 1 128 2187 ...'); '-' for stdin")
    c.add_argument("--json", action="store_true", help="machine-readable output")
    c.add_argument("--seed", type=int, default=0)
    c.add_argument("--population", type=int, default=1500)
    c.add_argument("--generations", type=int, default=20)
    c.add_argument("--holdout", type=int, default=4,
                   help="terms withheld from the search and required to "
                        "match exactly (default 4)")
    c.add_argument("--restarts", type=int, default=2)
    c.add_argument("--strict", action="store_true",
                   help="exit 1 unless a closed form was exactly verified")
    c.set_defaults(fn=_cmd_conjecture)

    c = sub.add_parser("selftest", help="run the built-in gates")
    c.set_defaults(fn=_cmd_selftest)

    c = sub.add_parser("version", help="print version")
    c.set_defaults(fn=_cmd_version)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
