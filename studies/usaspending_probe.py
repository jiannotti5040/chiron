#!/usr/bin/env python3
"""
usaspending_probe.py -- exact arithmetic identity probe against USAspending.gov.

Discipline (non-negotiable):
  * Money is NEVER a float. Every JSON number is parsed straight from the wire
    text into Decimal via json.loads(parse_float=Decimal). No float ever exists.
  * A record is CHECKED only when every field the identity needs is present and
    parses. Otherwise it is REFUSED and COUNTED. Never guessed, never coerced to
    zero, never silently skipped.
  * Degenerate all-zero records are counted separately so they cannot inflate
    the exact-tie rate.

API: https://api.usaspending.gov/api/v2/  (free, no key)

Identities tested -- see IDENTITIES below for the naive and refined forms.

Usage:
    python3 usaspending_probe.py --awards 400 --out usaspending_results.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any

import requests

API = "https://api.usaspending.gov/api/v2"
ZERO = Decimal(0)

# Transactions are paged 100 at a time. An award with more pages than this is
# REFUSED (counted), never partially summed.
MAX_TX_PAGES = 60
TX_PAGE = 100

_local = threading.local()


def session() -> requests.Session:
    s = getattr(_local, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": "chiron-identity-probe/1.0"})
        _local.s = s
    return s


class ApiError(Exception):
    pass


def _decode(resp: requests.Response) -> Any:
    """Parse JSON with every number token kept exact as Decimal."""
    return json.loads(resp.text, parse_float=Decimal, parse_int=Decimal)


def api_get(path: str, tries: int = 4) -> Any:
    last = None
    for i in range(tries):
        try:
            r = session().get(f"{API}{path}", timeout=120)
            if r.status_code == 200:
                return _decode(r)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                time.sleep(1.5 * (i + 1))
                continue
            raise ApiError(f"HTTP {r.status_code} on GET {path}")
        except requests.RequestException as e:  # network flake
            last = str(e)
            time.sleep(1.5 * (i + 1))
    raise ApiError(f"GET {path} failed after {tries} tries: {last}")


def api_post(path: str, payload: dict, tries: int = 4) -> Any:
    last = None
    for i in range(tries):
        try:
            r = session().post(f"{API}{path}", json=payload, timeout=120)
            if r.status_code == 200:
                return _decode(r)
            if r.status_code in (429, 500, 502, 503, 504):
                last = f"HTTP {r.status_code}"
                time.sleep(1.5 * (i + 1))
                continue
            raise ApiError(f"HTTP {r.status_code} on POST {path}: {r.text[:200]}")
        except requests.RequestException as e:
            last = str(e)
            time.sleep(1.5 * (i + 1))
    raise ApiError(f"POST {path} failed after {tries} tries: {last}")


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------

TYPE_GROUPS = {
    "contract": ["A", "B", "C", "D"],
    "idv": ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"],
    "grant": ["02", "03", "04", "05"],
    "loan": ["07", "08"],
    "direct_payment": ["06", "10"],
    "other": ["09", "11"],
}

FISCAL_YEARS = [
    ("2019-10-01", "2020-09-30"),
    ("2020-10-01", "2021-09-30"),
    ("2021-10-01", "2022-09-30"),
    ("2022-10-01", "2023-09-30"),
    ("2023-10-01", "2024-09-30"),
    ("2024-10-01", "2025-09-30"),
]


def sample_awards(target: int, seed: int = 20260726) -> list[dict]:
    """Stratified pseudo-random sample of awards across type group x fiscal year.

    Sorting by 'Award ID' and jumping to a pseudo-random page spreads the draw
    across the identifier space rather than concentrating on megadeals (which a
    sort by Award Amount would do).
    """
    rng = random.Random(seed)
    strata = [(g, fy) for g in TYPE_GROUPS for fy in FISCAL_YEARS]
    rng.shuffle(strata)
    per = max(1, target // len(strata) + 1)

    seen: set[str] = set()
    out: list[dict] = []
    for group, (start, end) in strata:
        if len(out) >= target:
            break
        page = rng.randint(1, 40)
        try:
            r = api_post(
                "/search/spending_by_award/",
                {
                    "filters": {
                        "award_type_codes": TYPE_GROUPS[group],
                        "time_period": [{"start_date": start, "end_date": end}],
                    },
                    "fields": [
                        "Award ID",
                        "Recipient Name",
                        "Award Amount",
                        "Awarding Agency",
                        "generated_internal_id",
                    ],
                    "limit": per,
                    "page": page,
                    "sort": "Award ID",
                    "order": "asc" if rng.random() < 0.5 else "desc",
                    "subawards": False,
                },
            )
        except ApiError as e:
            print(f"  [sample] stratum {group}/{start} failed: {e}", file=sys.stderr)
            continue
        for row in r.get("results", []):
            gid = row.get("generated_internal_id")
            if not gid or gid in seen:
                continue
            seen.add(gid)
            out.append(
                {
                    "generated_internal_id": gid,
                    "search_award_id": row.get("Award ID"),
                    "search_recipient": row.get("Recipient Name"),
                    "search_award_amount": row.get("Award Amount"),
                    "stratum_group": group,
                    "stratum_fy_end": end,
                }
            )
        print(f"  [sample] {group:<15} FY{end[:4]} page{page:<3} -> {len(out)} total",
              file=sys.stderr)
    return out[:target]


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------

def fetch_transactions(award_id: str) -> tuple[list[dict] | None, str | None]:
    """Return (all transactions, None) or (None, refusal_reason)."""
    rows: list[dict] = []
    page = 1
    while page <= MAX_TX_PAGES:
        r = api_post(
            "/transactions/",
            {
                "award_id": award_id,
                "limit": TX_PAGE,
                "page": page,
                "sort": "action_date",
                "order": "asc",
            },
        )
        rows.extend(r.get("results", []))
        if not r.get("page_metadata", {}).get("hasNext"):
            return rows, None
        page += 1
    return None, f"transaction_count_exceeds_cap({MAX_TX_PAGES * TX_PAGE})"


def fetch_award(rec: dict) -> dict:
    gid = rec["generated_internal_id"]
    out = dict(rec)
    try:
        detail = api_get(f"/awards/{gid}/")
    except ApiError as e:
        out["fetch_error"] = f"detail: {e}"
        return out
    out["detail"] = detail
    try:
        tx, refusal = fetch_transactions(gid)
        out["transactions"] = tx
        out["tx_refusal"] = refusal
    except ApiError as e:
        out["fetch_error"] = f"transactions: {e}"
    return out


# --------------------------------------------------------------------------
# Identities
# --------------------------------------------------------------------------
#
# I1  transaction obligation sum
#       sum(tx.federal_action_obligation) == award.total_obligation
#     NAIVE : applied to every award category.
#     REFINED: loans excluded. For a loan, federal_action_obligation is
#       structurally 0 and the money lives in original_loan_subsidy_cost /
#       face_value_loan_guarantee, so the naive form is a degenerate 0 == 0
#       pass that says nothing. Loans get I1L instead.
#
# I1L loan sum identities (loans only)
#       sum(tx.original_loan_subsidy_cost)   == award.total_subsidy_cost
#       sum(tx.face_value_loan_guarantee)    == award.total_loan_value
#
# I2  value ordering
#       total_obligation <= base_exercised_options <= base_and_all_options
#     NAIVE : applied wherever the fields are non-null, all categories.
#     REFINED: contracts only for the three-way chain; IDVs carry
#       base_and_all_options but no base_exercised_options, so they get the
#       two-way total_obligation <= base_and_all_options. Assistance awards
#       carry neither and are REFUSED.
#
# I3  subaward containment
#       NAIVE  : total_subaward_amount <= total_obligation
#       REFINED: total_subaward_amount <= max(total_obligation,
#                                             base_and_all_options)
#       Rationale for the refinement, established from real rows below: an FSRS
#       subaward row reports the *cumulative value of the subcontract*, which is
#       scoped to the prime's ceiling (base_and_all_options), not to the amount
#       obligated to date. Obligations also lag the ceiling by design. Comparing
#       a ceiling-scoped number against an obligations-to-date number is a rule
#       gap, not a filer error.

ASSIST_CATEGORIES = {"grant", "loan", "direct payment", "other"}


def dec(v: Any) -> Decimal | None:
    """Accept only an already-exact Decimal. Never coerce, never guess."""
    return v if isinstance(v, Decimal) else None


def check_award(rec: dict) -> dict:
    """Run every identity on one award. Returns a per-award verdict record."""
    res: dict[str, Any] = {
        "award_id": rec["generated_internal_id"],
        "piid_fain": rec.get("search_award_id"),
        "recipient": rec.get("search_recipient"),
        "stratum": rec.get("stratum_group"),
    }
    if "fetch_error" in rec:
        res["status"] = "REFUSED"
        res["reason"] = rec["fetch_error"]
        return res

    d = rec.get("detail") or {}
    category = (d.get("category") or "").lower()
    res["category"] = category
    res["type"] = d.get("type")
    res["recipient"] = ((d.get("recipient") or {}).get("recipient_name")) or res["recipient"]
    agency = ((d.get("awarding_agency") or {}).get("toptier_agency") or {}).get("name")
    res["awarding_agency"] = agency

    total_obl = dec(d.get("total_obligation"))
    base_ex = dec(d.get("base_exercised_options"))
    base_all = dec(d.get("base_and_all_options"))
    sub_total = dec(d.get("total_subaward_amount"))
    sub_count = d.get("subaward_count")
    subsidy = dec(d.get("total_subsidy_cost"))
    loan_val = dec(d.get("total_loan_value"))

    res["total_obligation"] = str(total_obl) if total_obl is not None else None
    res["base_exercised_options"] = str(base_ex) if base_ex is not None else None
    res["base_and_all_options"] = str(base_all) if base_all is not None else None
    res["total_subaward_amount"] = str(sub_total) if sub_total is not None else None
    res["subaward_count"] = str(sub_count) if sub_count is not None else None

    tx = rec.get("transactions")
    res["tx_count"] = len(tx) if tx is not None else None

    # ---------------- I1 / I1L : transaction sums ----------------
    i1: dict[str, Any] = {}
    if tx is None:
        i1 = {"naive": "REFUSED", "refined": "REFUSED",
              "reason": rec.get("tx_refusal") or "transactions_unavailable"}
    elif not tx:
        i1 = {"naive": "REFUSED", "refined": "REFUSED", "reason": "zero_transactions_returned"}
    else:
        missing = sum(1 for t in tx if dec(t.get("federal_action_obligation")) is None)
        if missing:
            i1 = {"naive": "REFUSED", "refined": "REFUSED",
                  "reason": f"federal_action_obligation_null_in_{missing}_transactions"}
        elif total_obl is None:
            i1 = {"naive": "REFUSED", "refined": "REFUSED",
                  "reason": "total_obligation_null"}
        else:
            s = sum((dec(t["federal_action_obligation"]) for t in tx), ZERO)
            delta = s - total_obl
            res["tx_sum_federal_action_obligation"] = str(s)
            res["i1_delta"] = str(delta)
            verdict = "EXACT" if delta == ZERO else "VIOLATION"
            i1["naive"] = verdict
            # refined: loans are excluded (degenerate 0==0), routed to I1L
            if category == "loan":
                i1["refined"] = "REFUSED"
                i1["reason"] = "loan_obligation_semantics_use_I1L"
            else:
                i1["refined"] = verdict
            i1["degenerate_zero"] = bool(total_obl == ZERO and s == ZERO)

    res["I1"] = i1

    if category == "loan" and tx:
        i1l: dict[str, Any] = {}
        sub_missing = sum(1 for t in tx if dec(t.get("original_loan_subsidy_cost")) is None)
        fv_missing = sum(1 for t in tx if dec(t.get("face_value_loan_guarantee")) is None)
        if sub_missing or subsidy is None:
            i1l["subsidy"] = "REFUSED"
        else:
            s = sum((dec(t["original_loan_subsidy_cost"]) for t in tx), ZERO)
            i1l["subsidy"] = "EXACT" if s == subsidy else "VIOLATION"
            i1l["subsidy_delta"] = str(s - subsidy)
        if fv_missing or loan_val is None:
            i1l["face_value"] = "REFUSED"
        else:
            s = sum((dec(t["face_value_loan_guarantee"]) for t in tx), ZERO)
            i1l["face_value"] = "EXACT" if s == loan_val else "VIOLATION"
            i1l["face_value_delta"] = str(s - loan_val)
        res["I1L"] = i1l

    # ---------------- I2 : value ordering ----------------
    i2: dict[str, Any] = {}
    # naive: three-way chain wherever all three are present, any category
    if total_obl is None or base_ex is None or base_all is None:
        i2["naive"] = "REFUSED"
        i2["naive_reason"] = "missing_one_of(total_obligation,base_exercised_options,base_and_all_options)"
    else:
        ok = total_obl <= base_ex <= base_all
        i2["naive"] = "EXACT" if ok else "VIOLATION"
        if not ok:
            i2["naive_detail"] = {
                "obl_gt_exercised": str(total_obl - base_ex) if total_obl > base_ex else None,
                "exercised_gt_potential": str(base_ex - base_all) if base_ex > base_all else None,
            }

    # refined: contracts get the 3-way chain; IDVs get the 2-way (no exercised
    # field exists for them); assistance is REFUSED, the fields do not exist.
    if category == "contract":
        if total_obl is None or base_ex is None or base_all is None:
            i2["refined"] = "REFUSED"
            i2["refined_reason"] = "contract_missing_value_fields"
        else:
            ok = total_obl <= base_ex <= base_all
            i2["refined"] = "EXACT" if ok else "VIOLATION"
            i2["refined_form"] = "obl<=exercised<=potential"
            i2["degenerate_zero"] = bool(total_obl == ZERO and base_all == ZERO)
    elif category == "idv":
        if total_obl is None or base_all is None:
            i2["refined"] = "REFUSED"
            i2["refined_reason"] = "idv_missing_value_fields"
        else:
            ok = total_obl <= base_all
            i2["refined"] = "EXACT" if ok else "VIOLATION"
            i2["refined_form"] = "obl<=potential (IDV has no exercised-options field)"
            i2["excess"] = str(total_obl - base_all) if not ok else None
            i2["degenerate_zero"] = bool(total_obl == ZERO and base_all == ZERO)
    else:
        i2["refined"] = "REFUSED"
        i2["refined_reason"] = f"category_{category or 'unknown'}_has_no_contract_value_fields"

    res["I2"] = i2

    # ---------------- I3 : subaward containment ----------------
    i3: dict[str, Any] = {}
    if sub_total is None:
        i3["naive"] = "REFUSED"
        i3["refined"] = "REFUSED"
        i3["reason"] = "total_subaward_amount_null_no_subawards_reported"
    elif total_obl is None:
        i3["naive"] = "REFUSED"
        i3["refined"] = "REFUSED"
        i3["reason"] = "total_obligation_null"
    else:
        i3["naive"] = "EXACT" if sub_total <= total_obl else "VIOLATION"
        ceiling = total_obl
        basis = "total_obligation"
        if base_all is not None and base_all > ceiling:
            ceiling, basis = base_all, "base_and_all_options"
        i3["refined"] = "EXACT" if sub_total <= ceiling else "VIOLATION"
        i3["refined_basis"] = basis
        i3["excess_over_obligation"] = str(sub_total - total_obl) if sub_total > total_obl else None
        i3["excess_over_ceiling"] = str(sub_total - ceiling) if sub_total > ceiling else None
        i3["degenerate_zero"] = bool(sub_total == ZERO and total_obl == ZERO)
    res["I3"] = i3

    res["status"] = "CHECKED"
    return res


# --------------------------------------------------------------------------
# Tally
# --------------------------------------------------------------------------

def tally(results: list[dict]) -> dict:
    def blank() -> dict:
        return {"checked": 0, "exact": 0, "violations": 0, "refused": 0,
                "degenerate_zero_exact": 0}

    t: dict[str, dict] = defaultdict(blank)

    def note(key: str, verdict: str | None, degenerate: bool = False) -> None:
        if verdict == "EXACT":
            t[key]["checked"] += 1
            t[key]["exact"] += 1
            if degenerate:
                t[key]["degenerate_zero_exact"] += 1
        elif verdict == "VIOLATION":
            t[key]["checked"] += 1
            t[key]["violations"] += 1
        elif verdict == "REFUSED":
            t[key]["refused"] += 1

    refused_awards = 0
    refusal_reasons: Counter = Counter()
    for r in results:
        if r.get("status") != "CHECKED":
            refused_awards += 1
            refusal_reasons[str(r.get("reason"))[:80]] += 1
            continue
        i1 = r.get("I1", {})
        note("I1_naive", i1.get("naive"), i1.get("degenerate_zero", False))
        note("I1_refined", i1.get("refined"), i1.get("degenerate_zero", False))
        if i1.get("naive") == "REFUSED":
            refusal_reasons[f"I1: {i1.get('reason')}"] += 1
        i1l = r.get("I1L")
        if i1l:
            note("I1L_subsidy", i1l.get("subsidy"))
            note("I1L_face_value", i1l.get("face_value"))
        i2 = r.get("I2", {})
        note("I2_naive", i2.get("naive"))
        note("I2_refined", i2.get("refined"), i2.get("degenerate_zero", False))
        i3 = r.get("I3", {})
        note("I3_naive", i3.get("naive"), i3.get("degenerate_zero", False))
        note("I3_refined", i3.get("refined"), i3.get("degenerate_zero", False))

    for k, v in t.items():
        v["exact_rate"] = (f"{(Decimal(v['exact']) * 100 / v['checked']).quantize(Decimal('0.01'))}%"
                           if v["checked"] else "n/a (0 checked)")
        nd_checked = v["checked"] - v["degenerate_zero_exact"]
        nd_exact = v["exact"] - v["degenerate_zero_exact"]
        v["nondegenerate_checked"] = nd_checked
        v["nondegenerate_exact_rate"] = (
            f"{(Decimal(nd_exact) * 100 / nd_checked).quantize(Decimal('0.01'))}%"
            if nd_checked else "n/a (0 checked)")

    return {"per_identity": dict(t),
            "awards_refused_entirely": refused_awards,
            "refusal_reasons": dict(refusal_reasons.most_common(20))}


def largest(results: list[dict], identity: str, field: str, n: int = 12) -> list[dict]:
    rows = []
    for r in results:
        blk = r.get(identity, {})
        if blk.get("refined") != "VIOLATION":
            continue
        v = blk.get(field)
        if v is None:
            v = r.get("i1_delta")
        if v is None:
            continue
        try:
            mag = abs(Decimal(v))
        except Exception:
            continue
        rows.append((mag, {
            "award_id": r["award_id"], "piid_fain": r.get("piid_fain"),
            "recipient": r.get("recipient"), "agency": r.get("awarding_agency"),
            "category": r.get("category"), "type": r.get("type"),
            "magnitude": str(mag),
            "total_obligation": r.get("total_obligation"),
            "base_and_all_options": r.get("base_and_all_options"),
            "base_exercised_options": r.get("base_exercised_options"),
            "total_subaward_amount": r.get("total_subaward_amount"),
            "tx_sum": r.get("tx_sum_federal_action_obligation"),
            "tx_count": r.get("tx_count"),
        }))
    rows.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in rows[:n]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--awards", type=int, default=400)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20260726)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "usaspending_results.json"))
    a = ap.parse_args()

    t0 = time.time()
    print(f"[1/3] sampling ~{a.awards} awards ...", file=sys.stderr)
    sample = sample_awards(a.awards, a.seed)
    print(f"      sampled {len(sample)} distinct awards", file=sys.stderr)

    print(f"[2/3] fetching detail + all transactions ({a.workers} workers) ...", file=sys.stderr)
    fetched: list[dict] = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(fetch_award, r): r for r in sample}
        for i, f in enumerate(as_completed(futs), 1):
            try:
                fetched.append(f.result())
            except Exception as e:
                rec = dict(futs[f])
                rec["fetch_error"] = f"unhandled: {e}"
                fetched.append(rec)
            if i % 25 == 0:
                print(f"      {i}/{len(sample)}", file=sys.stderr)

    print("[3/3] running identities in exact Decimal ...", file=sys.stderr)
    results = [check_award(r) for r in fetched]
    summary = tally(results)

    payload = {
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": "https://api.usaspending.gov/api/v2/",
        "sample_size_requested": a.awards,
        "awards_retrieved": len(results),
        "seed": a.seed,
        "elapsed_seconds": round(time.time() - t0, 1),
        "summary": summary,
        "largest_I1_violations": largest(results, "I1", "i1_delta"),
        "largest_I2_violations": largest(results, "I2", "excess"),
        "largest_I3_violations": largest(results, "I3", "excess_over_ceiling"),
        "largest_I3_naive_only": [
            {"award_id": r["award_id"], "recipient": r.get("recipient"),
             "category": r.get("category"),
             "total_subaward_amount": r.get("total_subaward_amount"),
             "total_obligation": r.get("total_obligation"),
             "base_and_all_options": r.get("base_and_all_options"),
             "excess_over_obligation": r["I3"].get("excess_over_obligation")}
            for r in results
            if r.get("I3", {}).get("naive") == "VIOLATION"
            and r.get("I3", {}).get("refined") == "EXACT"
        ][:15],
        "results": results,
    }
    with open(a.out, "w") as fh:
        json.dump(payload, fh, indent=2, default=str)

    print("\n" + "=" * 72, file=sys.stderr)
    print(json.dumps(summary, indent=2, default=str))
    print("=" * 72, file=sys.stderr)
    print(f"wrote {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
