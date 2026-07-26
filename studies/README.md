# 376,616 balance sheets. 655 don't balance. Here's how they fail.

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see [../LICENSE.md](../LICENSE.md)).**
**Run: 2026-07-25, live against data.sec.gov. Reproducible — the scripts are in this folder.**

Every balance sheet must satisfy one identity:

```
Assets == LiabilitiesAndStockholdersEquity
```

Both are tagged XBRL concepts. If they disagree *inside a single filing*, that
filing does not balance. I checked **every SEC filer that reported both, in
every quarter from 2009 through 2025**, in exact integer arithmetic.

## Result

| | |
|---|---|
| filing-periods checked (both facts, same accession, same instant) | **376,616** |
| tie exactly | **375,961** |
| **do not tie** | **655** |
| refused (one side missing, or period mismatch) | 26,909 |
| exact-identity rate | **99.8261%** |

Coverage: 68 quarterly instants, 2009Q1 → 2025Q4, ~5,000–8,000 filers each.

## How they fail — the taxonomy

Classifying the 655 by **exact ratio test only** (no fuzzy matching, no
judgment calls):

| failure mode | count | share | test |
|---|---|---|---|
| material, unexplained (> $1k) | 275 | 42.0% | no clean pattern |
| rounding ($1–2) | 211 | 32.2% | \|gap\| ≤ 2 |
| small (≤ $1k) | 121 | 18.5% | \|gap\| ≤ 1000 |
| **sign flip** | **26** | 4.0% | L+E == exactly −Assets |
| assets tagged zero | 14 | 2.1% | Assets == 0 |
| L+E tagged zero | 6 | 0.9% | L+E == 0 |
| **scale error** | **2** | 0.3% | exact power-of-ten ratio |

### Sign flips — unambiguous, and some are enormous

`LiabilitiesAndStockholdersEquity` tagged as exactly the **negative** of
`Assets`. There is no accounting interpretation of this; it is a defect.

| filer | period | gap |
|---|---|---|
| **ENTERGY CORPORATION** | 2009-06-30 | **$72,970,440,000** |
| GREAT WOLF RESORTS, INC. | 2012-03-31 | −$1,418,222,000 |
| TEXAS PACIFIC LAND TRUST | 2011-06 / 2011-09 / 2012-06 | ~−$50,000,000 each |
| CITIZENS CAPITAL CORP | 5 consecutive periods | ~$37,700,000 each |

### Scale errors — off by exactly a power of ten

| filer | period | gap | ratio |
|---|---|---|---|
| CANNABIS SCIENCE, INC. | 2013-06-30 | −$727,353,918 | 1000× |
| Lightning Gaming, Inc. | 2018-12-31 | $33,828,300 | 10× |

### Repeat offenders

The same filer failing across multiple periods — a persistent process defect,
not a one-off typo:

```
7x  AVANT TECHNOLOGIES INC.        6x  Chee Corp.
7x  RADTEK, INC                    6x  CAMBELL INTERNATIONAL HOLDING CORP.
6x  VITASPRING BIOMEDICAL CO. LTD. 5x  CITIZENS CAPITAL CORP
5x  ROGUE ONE, INC.                5x  NATION ENERGY INC
```

Full records with accession numbers:
[`sec_balance_2009_2025_full.json`](sec_balance_2009_2025_full.json) ·
[`sec_balance_taxonomy.json`](sec_balance_taxonomy.json)

## Who this is actually for

**If you build anything quantitative on SEC XBRL data, these 655 filings are
in your dataset and they are broken.** A sign-flipped $72.97B on Entergy, a
1000× scale error on Cannabis Science, and 26,909 records where one side of
the identity is simply absent. Screens, factor models, training corpora and
research pipelines ingest these silently.

This folder is the list, the failure taxonomy, and the script to regenerate
both.

## Prior art — this is not a discovery

> **CORRECTION (2026-07-26, added after publication).** This study does not
> uncover an unknown problem. **XBRL US operates a Data Quality Committee**
> whose entire purpose is finding defects of exactly this kind; it has
> published ~30 rule sets, and filers using them cut errors by 64%. Data
> vendors clean raw XBRL for the same reason. What is offered here is a
> *retrospective, reproducible catalogue with a published refusal count* — not
> a finding the field was missing. The original framing overstated novelty and
> is withdrawn.

## What this does and does not claim

- It does **not** allege misconduct, fraud, or restatement by any filer named.
  A tagging error and a reporting error are **indistinguishable from outside**;
  telling them apart requires the filer's own records. Most of these — the
  2009–2012 cluster especially — are almost certainly XBRL tagging defects
  from the early mandate years, not accounting problems.
- It checks **one** identity. Not revenue, not cash flow, not disclosure.
- It **refused** 26,909 comparisons rather than guess. Those are published in
  the open, not dropped.
- Pre-2009 filings are unstructured and out of scope. IFRS filers use a
  different taxonomy and are not covered. Private companies do not file.

## The method is the point: 1,356 → 18 → 655

My first rule was the textbook one, `Assets = Liabilities + StockholdersEquity`,
on a single quarter. It produced **1,356 "violations."** Every one was wrong —
not about the data, about **my rule**:

| pass | rule | findings | what the drop was |
|---|---|---|---|
| 1 | Assets = Liabilities + Equity | 1,356 | — |
| 2 | + noncontrolling interests | 204 | equity concept excluded minority interest |
| 3 | + mezzanine / temporary equity | 81 | redeemable preferred is in neither bucket |
| 4 | the identity XBRL itself must satisfy | **18** | earlier passes compared mismatched periods |
| 5 | same rule, **all 68 quarters** | **655** | scope, not rule change |

**98.7% of the apparent findings in pass 1 were gaps in my own model.** KKR,
Apollo, Blackstone, Exxon and 1,300 others were never wrong. The honest move
was to fix the rule and publish the refusals, not the list.

That loop is the whole method. Anyone can flag 1,356 anomalies with a
spreadsheet. Producing 655 that survive challenge across 17 years — and being
able to show precisely which ones you *declined* to call errors, and why — is
the difference between a report that gets paid for and one that dies in the
first rebuttal.

## Reproduce

```bash
python3 studies/sec_full_history.py    # the full 2009-2025 sweep (~5 min)
python3 studies/classify.py            # the failure taxonomy
python3 studies/sec_balance_check.py   # a fast 3-quarter version
```

Stdlib only. Public XBRL frames API. No key — the SEC asks only for a contact
string in the User-Agent, which the scripts set.

This check re-runs automatically every quarter in public CI
([`sec-quarterly.yml`](../.github/workflows/sec-quarterly.yml)), so the record
extends itself on data the author does not control.
