#!/bin/sh
# The public proof, one command. Same three batteries CI runs on every push.
# Add --live to also grade the frozen outputs against oeis.org live (~40s, polite).
set -e

bar() { printf '\n\033[1m== %s\033[0m\n\n' "$1"; }

bar "1/3  Architecture prototype — 26 gates (incl. 'the stub can never say VERIFIED')"
python3 prototype/primus_prototype.py selftest

bar "2/3  Browser demo core — 17 gates (incl. 'no stamp without exact held-out proof')"
python3 prototype/browser_core.py selftest

bar "3/3  Grade the engine's frozen outputs — the number that matters is FALSE STAMPS"
python3 eval/grade.py --cache eval/oeis_snapshot_2026-07-07.json

if [ "$1" = "--live" ]; then
  bar "bonus  Same grade, LIVE against oeis.org (ground truth the author does not control)"
  python3 eval/grade.py
fi

printf '\n\033[1mAll public batteries green. The reconciled map: docs/BATTERIES.md\033[0m\n'
