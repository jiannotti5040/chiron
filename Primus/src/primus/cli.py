#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
primus.cli — the command-line front door.

    primus collapse "1 1 2 3 5 8 13 21"        recover + verify a generator
    primus collapse --json "3 1 4 1 5 9 2 6"   machine-readable (abstains here)
    primus certify "2+2=5 and 2 4 6 8 continues as 10"
    echo "<model output>" | primus certify -   certify stdin (agent tool-call)
    primus selftest                            engine + certify gates
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


def _cmd_certify(args: argparse.Namespace) -> int:
    from primus.certify import certify, render

    cert = certify(_read_text(args.text))
    if args.json:
        print(json.dumps(cert, indent=2, default=str))
    else:
        print(render(cert))
    if args.gate:
        return 1 if cert["counts"]["refuted"] else 0
    return 0


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
    c.add_argument("--gate", action="store_true",
                   help="exit 1 if any claim was REFUTED (agent gating)")
    c.set_defaults(fn=_cmd_certify)

    c = sub.add_parser("selftest", help="run the built-in gates")
    c.set_defaults(fn=_cmd_selftest)

    c = sub.add_parser("version", help="print version")
    c.set_defaults(fn=_cmd_version)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
