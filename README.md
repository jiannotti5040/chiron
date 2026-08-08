# Chiron

### Every other AI tool competes to be right more often. This one competes to never be wrong.

[![proof](https://github.com/jiannotti5040/chiron/actions/workflows/proof.yml/badge.svg)](https://github.com/jiannotti5040/chiron/actions/workflows/proof.yml)
[![live-eval](https://github.com/jiannotti5040/chiron/actions/workflows/live-eval.yml/badge.svg)](https://github.com/jiannotti5040/chiron/actions/workflows/live-eval.yml)
[![Apache-2.0](https://img.shields.io/badge/code-Apache--2.0-blue)](LICENSE)
[![PyPI](https://img.shields.io/badge/pip-primus--intelligence-informational)](https://pypi.org/project/primus-intelligence/)

The way it does that is by shutting up a lot.

```console
$ primus collapse "1 1 2 3 5 8 13 21 34 55 89 144"
VERIFIED  linear_recurrence_order2 — recovered from the first 9 terms, then
          EXACTLY predicts all 3 held-out terms it was never shown.

$ primus collapse "2 3 5 7 11 13 17 19 23 29 31 37"
Best model in class: 'power_law' — Does Not Meaningfully Compress.
          Held-out prediction: 0/3 — treat as a candidate, not yet verified.
```

It never grades its own homework. It sees a prefix, the rest is withheld, and it must reproduce
the withheld terms *exactly* — right integer, every time — before it is allowed to say anything.

The second command is the product. Any model will hand you a formula for the primes if you ask
nicely: confidently, instantly, wrongly. This one shows its best guess and then tells you the
guess failed the only test that counted.

**Somewhere in your stack a number came out of a language model and got treated as a fact.**
"94% confident" is not something you can put in a change request, a filing, or an incident review.

```console
pip install primus-intelligence
```

---

## What this actually is

Four layers, each answering what the one below it structurally cannot. They were built as
separate projects over two years; they are one system.

| Question | Answer | Where |
|---|---|---|
| Can this claim be proved exactly? | `VERIFIED` · `REFUTED` · `REFUSED` | [`Primus/`](Primus/) · [`Chiron/`](Chiron/) |
| Does it match the system of record? | ontology grounding | [readiness gate ↗](https://github.com/jiannotti5040/operational-readiness-gate) |
| Would this survive being challenged? | an adversarial court — defence, precedent, six judges | [`Chiron/judgment.py`](Chiron/judgment.py) |
| Would the record hold up in a hearing? | Daubert · FRE 702 · FRCP 26 | [`JDICert/`](JDICert/) |

The gap that makes the stack necessary is **measured, not assumed**: every `certify` claim kind is
self-contained, so on realistic operational text coverage is about **0.09**. It verifies
`4200 / 1400 = 3` and leaves *"Unit Bravo has 3 days of fuel"* — the sentence a human acts on —
uncertified. That is not the disappointing part. That is the deliverable: you now know which 9% is
machine-provable and which 91% is yours, *before* you sign your name to it.

**A confidence score cannot be appealed.** The record this produces can — every court in it is
separately addressable and separately wrong-able. → [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)

The current evidence-backed implementation boundary, surface inventory, and
external blockers are recorded in [`docs/RECONSTRUCTION.md`](docs/RECONSTRUCTION.md).

---

## Has it ever lied?

**Yes. Three times. All published, in the commit log, with the repair beside them.**

The worst: the very first external run — against live OEIS data, after ~5,070 internal cases had
passed clean — caught it stamping a wrong number. The cause was that the held-out check compared
with a `1e-6` tolerance while the documentation promised exact equality. At those magnitudes that
forgave an error of about ten thousand.

It got caught because the check runs against data the author does not control. Exact arithmetic is
structural now, and every external run since reports **zero false verifications** — the one number
here that is not allowed to move.

→ [`Primus/EXTERNAL_VALIDATION.md`](Primus/EXTERNAL_VALIDATION.md) — the failures, unedited.

---

## What it has been pointed at

| | Result |
|---|---|
| **3,195 open conjectures** (DeepMind `formal-conjectures`) | discharged 302, **refused 90.5%** — the correct answer |
| **Jacobian conjecture** counterexample (open since 1939) | 12/12 gates, exact polynomial identity over ℚ |
| **Dinitz–Garg–Goemans** counterexample (open since the 1990s) | 15/15 gates; whole family **456/456** in exact integers |
| **Live OEIS**, graded against data the author doesn't control | 20 verified / 0 false / n=29 |
| Head-to-head vs PySR symbolic regression | 18 exact / **0 wrong** / 11 refused, vs 5 exact / 24 wrong |

Open problems are open *because* they are not finitely checkable. A tool reporting a high success
rate on that corpus would be broken, not brilliant.

→ [`docs/AI_CLAIMS.md`](docs/AI_CLAIMS.md) — what was verified and what was refused.

---

## Verify it yourself

```console
./demo.sh                  # prototype + demo-core gates + the frozen-output grade
./demo.sh --live           # the same, plus a live oeis.org grade
python3 bin/chiron test    # the full battery
```

Nothing is held back and nothing needs a key. → [`docs/BATTERIES.md`](docs/BATTERIES.md) is the
single reconciled source for every gate count; if two numbers ever disagree, that page wins.

---

## Repository map

| | |
|---|---|
| [`Primus/`](Primus/) | the seed engine and the `primus-intelligence` package — recovery, certify, MCP server, HTTP server |
| [`Chiron/`](Chiron/) | the flagship: 73 modules — the certification layer, the composer, and the courts |
| [`Chiron Monolith/`](Chiron%20Monolith/) | the whole flagship folded into one deterministic file that runs offline |
| [`JDICert/`](JDICert/) | decision certification — 18 sections, K/U/Ω partition, Daubert analyser, 280/280 |
| [`studies/`](studies/) | the research: OEIS extensions, conjecture sweeps, retractions, replay capsules |
| [`UMA Suite/`](UMA%20Suite/) | the physics framework and its falsification checkpoints |
| [`App/`](App/) | the native macOS front end — SwiftUI over the vault's own engines, no verification logic of its own |
| [`docs/`](docs/) · [`notes/`](notes/) | the published site · the working records, kept unedited including the failures |

---

## Licence

Code is **Apache-2.0**. Prose and books are **CC BY 4.0**. Commercial use, modification and
redistribution are all permitted; attribution is the only condition. There is no paid tier, no
private repository, and nothing behind a licence key.

→ [`LICENSES.md`](LICENSES.md) · [`CONTRIBUTING.md`](CONTRIBUTING.md) · [`NOTICE`](NOTICE)

> Copyright © 2026 Jacob Iannotti
