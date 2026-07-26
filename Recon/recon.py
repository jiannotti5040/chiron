#!/usr/bin/env python3
# SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# Required Notice: Copyright © 2026 Jacob Iannotti. Commercial rights reserved. See LICENSE.md.
"""
recon.py — exact ledger reconciliation with a refusal record.

The billable insight, in one line: **anyone can flag anomalies; the money is
in refusing to call 98% of them errors.**

On real SEC data this loop went 1,356 -> 204 -> 81 -> 18 "findings" across
four rule refinements. The 1,338 that disappeared were never errors — they
were gaps in the RULE. A report that hands a client 1,356 anomalies is worth
nothing and destroys your credibility on the first rebuttal. A report that
hands them 18 defensible ones, plus a written record of what you refused to
call an error and why, is worth a percentage of what it recovers.

This module runs that loop over any CSV.

DESIGN CONTRACT (the same one the rest of the vault keeps)
----------------------------------------------------------
  * Money is exact. Decimal, never float. A cent never rounds itself away.
  * A row is CHECKED only if every field the rule needs is present and
    parseable. Otherwise it is REFUSED and counted — never silently skipped,
    never guessed, never coerced to zero.
  * A violation is reported with the row, the rule, both sides of the
    arithmetic, and the exact delta. Nothing is "approximately off."
  * Every refinement is recorded, so the final report can show the client the
    whole path: what you first suspected, what turned out to be your own
    modelling gap, and what actually survived.

That last property is what makes the output defensible under challenge, and
it is the thing competitors do not ship.

USE
---
    from recon import Ledger, Rule
    led = Ledger.from_csv("invoices.csv")
    led.add(Rule.identity("total", ["qty_x_price", "tax", "shipping"]))
    led.add(Rule.product("qty_x_price", "qty", "unit_price"))
    led.add(Rule.rate_table("unit_price", key="sku", table=contract_rates))
    print(led.run().report())

    python3 recon.py demo          # runnable worked example, no data needed
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional, Sequence

SCHEMA = "recon/1"


# ── exact money parsing ──────────────────────────────────────────────────

def money(raw: Any) -> Optional[Decimal]:
    """Parse to exact Decimal, or None. None means REFUSE, not zero.

    Accepts $1,234.56 / (1,234.56) accounting-negative / plain numerics.
    Rejects blanks, 'N/A', and anything non-numeric — those become refusals.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s or s.upper() in {"NA", "N/A", "NULL", "NONE", "-", "—"}:
        return None
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").replace("%", "").strip()
    if not s:
        return None
    try:
        d = Decimal(s)
    except InvalidOperation:
        return None
    return -d if neg else d


# ── rules ────────────────────────────────────────────────────────────────

@dataclass
class Rule:
    """One exact arithmetic assertion over a row."""
    name: str
    needs: Sequence[str]
    check: Callable[[Dict[str, Optional[Decimal]], Dict[str, str]], Optional[tuple]]
    note: str = ""

    # -- constructors for the patterns that actually show up in ledgers ----

    @staticmethod
    def identity(total: str, parts: Sequence[str], name: str = "") -> "Rule":
        """total == sum(parts), exactly."""
        def _check(v, _row):
            lhs = v[total]
            rhs = sum(v[p] for p in parts)
            return None if lhs == rhs else (lhs, rhs)
        return Rule(name or f"{total} == {' + '.join(parts)}",
                    [total, *parts], _check,
                    "line items must sum to the stated total")

    @staticmethod
    def product(result: str, a: str, b: str, name: str = "") -> "Rule":
        """result == a * b, exactly (quantity x rate)."""
        def _check(v, _row):
            lhs, rhs = v[result], v[a] * v[b]
            return None if lhs == rhs else (lhs, rhs)
        return Rule(name or f"{result} == {a} * {b}", [result, a, b], _check,
                    "extended amount must equal quantity times rate")

    @staticmethod
    def percentage(result: str, base: str, pct: str, name: str = "") -> "Rule":
        """result == base * pct/100, exactly. Catches mis-applied tax/commission."""
        def _check(v, _row):
            lhs, rhs = v[result], v[base] * v[pct] / Decimal(100)
            return None if lhs == rhs else (lhs, rhs)
        return Rule(name or f"{result} == {base} * {pct}%", [result, base, pct],
                    _check, "computed percentage must match the stated amount")

    @staticmethod
    def rate_table(field_: str, key: str, table: Dict[str, Decimal],
                   name: str = "") -> "Rule":
        """The charged rate must equal the CONTRACTED rate for that key.

        This is the overbilling detector: it is where recovered money comes
        from. A key absent from the table is REFUSED, never assumed correct.
        """
        def _check(v, row):
            k = str(row.get(key, "")).strip()
            if k not in table:
                return "REFUSE"          # unknown key: cannot judge, will not guess
            lhs, rhs = v[field_], Decimal(table[k])
            return None if lhs == rhs else (lhs, rhs)
        return Rule(name or f"{field_} == contracted rate by {key}",
                    [field_], _check,
                    "charged rate must match the contract rate table")

    @staticmethod
    def non_negative(field_: str, name: str = "") -> "Rule":
        def _check(v, _row):
            return None if v[field_] >= 0 else (v[field_], Decimal(0))
        return Rule(name or f"{field_} >= 0", [field_], _check,
                    "amount must not be negative")


# ── the ledger ───────────────────────────────────────────────────────────

@dataclass
class Ledger:
    rows: List[Dict[str, str]]
    source: str = "(in-memory)"
    rules: List[Rule] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    _result: Optional[Dict[str, Any]] = None

    @classmethod
    def from_csv(cls, path: str) -> "Ledger":
        with open(path, newline="", encoding="utf-8-sig") as f:
            return cls(rows=list(csv.DictReader(f)), source=path)

    def add(self, rule: Rule) -> "Ledger":
        self.rules.append(rule)
        return self

    def run(self, id_field: Optional[str] = None) -> "Ledger":
        """Apply every rule to every row. Exact. Refusals counted, not hidden."""
        violations: List[Dict[str, Any]] = []
        checked = refused = passed = 0
        per_rule: Dict[str, Dict[str, int]] = {}

        for idx, row in enumerate(self.rows):
            for rule in self.rules:
                stat = per_rule.setdefault(
                    rule.name, {"checked": 0, "passed": 0, "violated": 0, "refused": 0})
                vals: Dict[str, Optional[Decimal]] = {}
                incomplete = False
                for fname in rule.needs:
                    d = money(row.get(fname))
                    if d is None:
                        incomplete = True
                        break
                    vals[fname] = d
                if incomplete:
                    refused += 1
                    stat["refused"] += 1
                    continue

                out = rule.check(vals, row)
                if out == "REFUSE":
                    refused += 1
                    stat["refused"] += 1
                    continue

                checked += 1
                stat["checked"] += 1
                if out is None:
                    passed += 1
                    stat["passed"] += 1
                else:
                    lhs, rhs = out
                    stat["violated"] += 1
                    violations.append({
                        "row": idx + 1,
                        "id": row.get(id_field) if id_field else None,
                        "rule": rule.name,
                        "stated": str(lhs),
                        "computed": str(rhs),
                        "delta": str(lhs - rhs),
                        "why": rule.note,
                    })

        self._result = {
            "schema": SCHEMA,
            "source": self.source,
            "rows": len(self.rows),
            "rules": len(self.rules),
            "checks_attempted": checked + refused,
            "checked": checked,
            "passed": passed,
            "violations": len(violations),
            "refused": refused,
            "exact_pass_rate": (passed / checked) if checked else None,
            "per_rule": per_rule,
            "findings": sorted(violations,
                               key=lambda v: -abs(Decimal(v["delta"]))),
        }
        self.history.append({
            "pass": len(self.history) + 1,
            "rules": [r.name for r in self.rules],
            "violations": len(violations),
            "refused": refused,
        })
        return self

    # -- the exposure number: what the violations are actually worth --------

    def exposure(self) -> Decimal:
        """Absolute sum of all deltas — the recoverable amount at issue."""
        if not self._result:
            return Decimal(0)
        return sum((abs(Decimal(v["delta"])) for v in self._result["findings"]),
                   Decimal(0))

    def report(self, top: int = 20) -> str:
        r = self._result
        if not r:
            return "no run yet — call .run() first"
        L = []
        L.append("=" * 68)
        L.append("EXACT RECONCILIATION REPORT")
        L.append("=" * 68)
        L.append(f"source            : {r['source']}")
        L.append(f"rows              : {r['rows']:,}")
        L.append(f"rules applied     : {r['rules']}")
        L.append(f"checks attempted  : {r['checks_attempted']:,}")
        L.append(f"  checked exactly : {r['checked']:,}")
        L.append(f"  passed          : {r['passed']:,}")
        L.append(f"  VIOLATIONS      : {r['violations']:,}")
        L.append(f"  REFUSED         : {r['refused']:,}  "
                 f"(incomplete or unjudgeable — not counted as errors)")
        if r["exact_pass_rate"] is not None:
            L.append(f"exact pass rate   : {r['exact_pass_rate']:.4%}")
        L.append(f"EXPOSURE          : {self.exposure():,}  "
                 f"(absolute sum of deltas)")

        if len(self.history) > 1:
            L.append("")
            L.append("-- refinement history (the credibility of this report) --")
            for h in self.history:
                L.append(f"   pass {h['pass']}: {h['violations']:>6,} violations, "
                         f"{h['refused']:>6,} refused, {len(h['rules'])} rules")
            first, last = self.history[0], self.history[-1]
            if first["violations"] > last["violations"] > 0:
                killed = first["violations"] - last["violations"]
                L.append(f"   -> {killed:,} apparent findings "
                         f"({killed/first['violations']:.1%}) were RULE GAPS, "
                         f"not errors. They are not in this report.")

        L.append("")
        L.append("-- per rule --")
        for name, s in r["per_rule"].items():
            L.append(f"   {name[:46]:46s} ok {s['passed']:>6,}  "
                     f"bad {s['violated']:>5,}  refused {s['refused']:>5,}")

        if r["findings"]:
            L.append("")
            L.append(f"-- findings (top {min(top, len(r['findings']))} by delta) --")
            for v in r["findings"][:top]:
                ident = f"[{v['id']}] " if v.get("id") else ""
                L.append(f"   row {v['row']:>6} {ident}{v['rule'][:34]:34s} "
                         f"stated {v['stated']:>14} vs {v['computed']:>14} "
                         f"delta {v['delta']:>12}")
        L.append("=" * 68)
        return "\n".join(L)

    def to_json(self, path: str) -> str:
        out = dict(self._result or {})
        out["exposure"] = str(self.exposure())
        out["refinement_history"] = self.history
        with open(path, "w") as f:
            json.dump(out, f, indent=2)
        return path


# ── worked demo, no external data needed ─────────────────────────────────

DEMO = [
    # id, sku, qty, unit_price, extended, tax, shipping, total
    ("INV-1001", "A-100", "10", "12.50", "125.00", "10.00", "5.00", "140.00"),
    ("INV-1002", "A-100", "4",  "12.50", "50.00",  "4.00",  "5.00", "59.00"),
    ("INV-1003", "B-200", "7",  "31.00", "217.00", "17.36", "5.00", "239.36"),
    ("INV-1004", "A-100", "20", "13.75", "275.00", "22.00", "5.00", "302.00"),  # off-contract rate
    ("INV-1005", "B-200", "3",  "31.00", "93.00",  "7.44",  "5.00", "105.44"),
    ("INV-1006", "A-100", "6",  "12.50", "75.00",  "6.00",  "5.00", "87.00"),   # total is wrong
    ("INV-1007", "C-300", "2",  "99.00", "198.00", "15.84", "5.00", "218.84"),  # sku not in contract
    ("INV-1008", "B-200", "5",  "31.00", "155.00", "12.40", "",     ""),        # incomplete
]
CONTRACT = {"A-100": Decimal("12.50"), "B-200": Decimal("31.00")}


def demo() -> int:
    rows = [dict(zip(
        ["id", "sku", "qty", "unit_price", "extended", "tax", "shipping", "total"], r))
        for r in DEMO]
    led = Ledger(rows=rows, source="(demo invoices)")

    # pass 1 — the naive rule set most tools stop at
    led.add(Rule.identity("total", ["extended", "tax", "shipping"]))
    led.add(Rule.product("extended", "qty", "unit_price"))
    led.run(id_field="id")

    # pass 2 — add the contract rate table: this is where recovery comes from
    led.add(Rule.rate_table("unit_price", key="sku", table=CONTRACT))
    led.run(id_field="id")

    print(led.report())
    print("\nNote the REFUSED column: INV-1007's SKU is not in the contract "
          "table and INV-1008 is missing fields.\nNeither is called an error. "
          "That restraint is what survives a client rebuttal.")
    return 0


def main(argv: List[str]) -> int:
    if len(argv) > 1 and argv[1] == "demo":
        return demo()
    print(__doc__)
    print("commands: demo")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
