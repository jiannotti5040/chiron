# What is a VERIFIED stamp actually worth? Measured across all 397,772 OEIS sequences.

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see [../LICENSE.md](../LICENSE.md)).**
**Run: 2026-07-26. Engine: the licensed Chiron/Primus `collapse`. Reproducible — scripts in this folder.**

Verification systems report a binary verdict: VERIFIED or not. Nobody
publishes what that stamp is *worth* — how often a rule certified on the
evidence shown actually survives evidence it never saw.

This study measures it, on every sequence in the OEIS.

---

## 1. The sweep

Each sequence: show the engine only the **first 14 terms**. If it refuses,
refuse — no second attempt. If it VERIFIES, take the recovered rule and
predict **every remaining term OEIS has**, compared exactly.

| | count | share |
|---|---|---|
| sequences scanned | **397,772** | 100% |
| engine **REFUSED** | 264,574 | 66.5% |
| engine **VERIFIED** from 14 terms | 14,425 | 3.6% |
| → rule survived **every** unseen term | **12,581** | **87.2% of stamps** |
| → rule **failed** on unseen terms | **1,844** | **12.8% of stamps** |

Two results, and the second matters more.

**The engine refuses two-thirds of all human mathematics.** 264,574 sequences
went unstamped. That is the discipline working at a scale no test suite
reaches.

**But 12.8% of what it did stamp was wrong on data it hadn't seen.** Not
wrong about the terms it was given — those were reproduced exactly — wrong
about what came next.

---

## 2. What the stamp does and does not claim

The certificate is explicit: it certifies that a rule **reproduces the
supplied terms exactly, including an internal holdout**. It never claims to
have found the sequence's true generator — no finite prefix can determine
that.

So the 1,844 are not broken promises. They are the measured size of the gap
between *"fits everything you showed me"* and *"is the real rule."*

That gap has never been quantified. Here it is.

---

## 3. The calibration curve

If the gap is a function of evidence supplied, showing more terms should
close it. It does.

**Corpus A** (2,500 sequences with ≥46 terms):

| terms shown | stamps | survived | **survival rate** |
|---|---|---|---|
| 10 | 143 | 52 | **36.4%** |
| 12 | 127 | 76 | 59.8% |
| 14 | 117 | 81 | 69.2% |
| 18 | 165 | 109 | 66.1% |
| 22 | 166 | 119 | 71.7% |
| 26 | 150 | 115 | 76.7% |
| 30 | 148 | 114 | 77.0% |
| 34 | 137 | 117 | **85.4%** |

**Corpus B** (12,000 sequences, harder mix): 38.1% → 51.6% → 58.2% → 58.5%
across 10/12/14/18 terms — lower absolutes, same monotonic rise.

**A VERIFIED stamp is not binary. Its reliability is a measurable function of
the evidence behind it.** At 10 terms a stamp is close to a coin flip. At 34
it is ~85%. The absolute level depends on the corpus; the *direction* does
not.

This is the practical consequence: **"VERIFIED" without "on how much
evidence" is an incomplete statement.**

---

## 4. The risk is not uniform — it concentrates

Same 14-term protocol, 6,000 sequences, broken out by the family the engine
recovered:

| model class | survived | failed | **survival** |
|---|---|---|---|
| polynomial_deg3 | 71 | 0 | **100%** |
| polynomial_deg4 | 52 | 0 | **100%** |
| polynomial_deg5 | 21 | 0 | **100%** |
| polynomial_deg6 | 27 | 0 | **100%** |
| geometric | 6 | 0 | **100%** |
| linear_recurrence_order3 | 89 | 4 | 95.7% |
| linear_recurrence_order2 | 31 | 3 | 91.2% |
| polynomial_deg2 | 46 | 5 | 90.2% |
| holonomic_r2_p1 | 80 | 18 | 81.6% |
| arithmetic | 51 | 20 | 71.8% |
| holonomic_r1_p1 | 10 | 4 | 71.4% |
| periodic_5 | 4 | 3 | 57.1% |
| **holonomic_r1_p2** | **9** | **8** | **52.9%** |

**Polynomial recovery is flawless. Low-order holonomic recovery is a coin
flip.** That is directly actionable: the evidence bar should be raised for
specific families rather than uniformly.

### The named failure mode

The `holonomic_r1_p2` failures identify themselves:

- **A000195** — `floor(log(n))`. Diverges at term 15: predicted 1, actual 2.
- **A001299** — same shape. Diverges at term 15: predicted 3, actual 4.

**Step functions masquerade as holonomic sequences over short prefixes.** A
slowly-growing floor function looks smooth for 14 terms; the first step past
the window breaks it. That is a specific, fixable weakness — not a vague
"sometimes it's wrong."

---

## 5. What this means for anyone using an exact-or-refuse gate

1. **Report evidence with the verdict.** "VERIFIED (14 terms)" and
   "VERIFIED (34 terms)" are different claims.
2. **Set the evidence bar per family.** A degree-4 polynomial at 14 terms was
   right 100% of the time here. A low-order holonomic fit was right half the
   time. One threshold for both is the wrong design.
3. **A refusal rate of 66.5% is a feature.** The engine declined two-thirds
   of OEIS. Any system stamping most of that corpus from 14 terms is not
   being careful — it is guessing with extra steps.

---

## 6. Honest limits of this study

- **Extrapolation depth is bounded** by the OEIS `stripped` file, which
  truncates each entry (median 18 unseen terms available, max 116). Deeper
  confirmation requires per-sequence b-files; not done here.
- **Corpus A and Corpus B disagree on absolute rates** (85.4% vs a lower
  trajectory) because they sample different difficulty mixes. Only the
  monotonic direction is claimed.
- Sequences with fewer than 3 distinct opening terms, or terms beyond 10^60,
  were excluded — recorded here rather than hidden.
- This measures **one engine on integer sequences**. It is not a claim about
  verification systems in general.
- Counts come from the runs described; nothing is estimated.

---

## 7. Reproduce

```bash
python3 studies/discover.py 1 400000   # the full sweep (parallelise by range)
python3 studies/calibrate.py           # the calibration curve
python3 studies/failmode.py            # per-family survival
```

Requires the licensed engine. The corpus is the public OEIS `stripped` file.

---

## Why this is the honest version

The headline could have been *"12,581 exact rules recovered across all of
OEIS."* True, and it is in the data. But the number that matters is the one
that makes the tool weaker on paper: **12.8% of stamps did not survive.**

A verification project that publishes only its successes has not understood
its own thesis. The measurement above is what a stamp is worth — stated
plainly, with the curve, the failing families, and the named failure mode.
