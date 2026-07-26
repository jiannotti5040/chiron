# I checked 16,990 SEC filings. 18 don't balance.

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see [../LICENSE.md](../LICENSE.md)).**
**Run: 2026-07-25, live against data.sec.gov. Reproducible with the script in this folder.**

Every balance sheet must satisfy one identity:

```
Assets == LiabilitiesAndStockholdersEquity
```

Both are tagged concepts in XBRL. If they disagree inside a single filing, the
balance sheet does not balance. I checked every SEC filer that reported both,
across three quarterly instants, in exact integer arithmetic.

## Result

| | |
|---|---|
| filings checked (both facts, same accession, same instant) | **16,990** |
| tie exactly | **16,972** |
| **do not tie** | **18** |
| refused (one side missing, or period mismatch) | 929 |
| exact-identity rate | **99.894%** |

### The 18

| Company | Period end | Gap |
|---|---|---|
| American Resources Corporation | 2024-09-30 | **−$1,000,000** |
| SUPERCOM LTD. | 2024-06-30 | −$2,000 |
| NATIONAL BANKSHARES, INC. | 2024-12-31 | −$1,000 |
| Twinlab Consolidated Holdings | 2024-12-31 | −$1,000 |
| GEN Restaurant Group, Inc. | 2024-09-30 | −$1,000 |
| FAT Brands Inc. | 2024-06-30 | −$1,000 |
| Enertopia Corporation | 2024-11-30 | +$500 |
| 11 others | various | ±$1–2 |

Full records, with accession numbers so any one can be pulled and read:
[`sec_balance_violations_2024.json`](sec_balance_violations_2024.json).

Most are immaterial rounding. One is a million dollars. **All eighteen are
filed documents whose stated total assets differ from their stated total of
liabilities and equity** — which is worth knowing whichever bucket it lands in.

## The part that matters: 1,356 → 18

The first rule I wrote was the textbook one:

```
Assets == Liabilities + StockholdersEquity
```

It produced **1,356 "violations."** Every one was wrong — not wrong about the
data, wrong about *my rule*:

| pass | rule | "findings" | what the drop actually was |
|---|---|---|---|
| 1 | Assets = Liabilities + Equity | 1,356 | — |
| 2 | + noncontrolling interests | 204 | equity concept excluded minority interest |
| 3 | + mezzanine / temporary equity | 81 | redeemable preferred sits in neither bucket |
| 4 | the identity XBRL itself must satisfy | **18** | earlier passes compared across mismatched periods |

**98.7% of my apparent findings were gaps in my own model.** KKR, Apollo,
Blackstone, Exxon and 1,300 others were never wrong. My arithmetic was
incomplete, and the honest move was to fix the rule rather than publish the
list.

That loop is the entire method. Anyone can flag 1,356 anomalies with a
spreadsheet. Producing 18 that survive challenge — and being able to show a
client exactly which 1,338 you *declined* to call errors, and why — is the
difference between a report that gets paid for and one that gets rebutted in
the first meeting.

## What this does and does not claim

- It does **not** allege misconduct, fraud, or restatement by any company
  listed. A tagging error and a reporting error look identical from outside;
  distinguishing them requires the filer's own records.
- It does **not** check any other accounting relationship — only the single
  identity above.
- It **refused** 929 comparisons rather than guess at them. Those are counted
  in the open, not dropped.
- Rounding-scale gaps (±$1–2) are almost certainly presentation artifacts and
  are reported as such rather than dressed up.

## Reproduce it

```bash
python3 studies/sec_balance_check.py
```

Stdlib only. Hits `data.sec.gov`'s public XBRL frames API. No key required —
set a contact string in the User-Agent header, as the SEC asks.

## Why this is in a verification repo

This project's claim is that a stamp is worth something only when it can be
withheld. This study is that claim applied to 17,000 real documents: the
useful output was not the 18 violations — it was the 1,338 refusals that came
before them.

The same loop, pointed at a company's own invoices, commissions, royalties or
billing data — where a 0.1% exact-rule violation rate is real money — is
[what the engine is for](../README.md).
