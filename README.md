# Chiron

### The verification layer for machine intelligence.

[![proof](https://github.com/jiannotti5040/chiron/actions/workflows/proof.yml/badge.svg)](https://github.com/jiannotti5040/chiron/actions/workflows/proof.yml)
[![live-eval](https://github.com/jiannotti5040/chiron/actions/workflows/live-eval.yml/badge.svg)](https://github.com/jiannotti5040/chiron/actions/workflows/live-eval.yml)

Chiron recovers the exact rule behind data, proves it on evidence the rule never saw, and **refuses to answer when it cannot prove** — then leaves a signed, falsifiable certificate of what it did and why.

Most AI systems assert. They produce an output and you trust it. Chiron inverts that: an output is not a right, it is a **verdict** — and the verdict is policed by live external testing. On the current battery (2026-07-21): **22 stamped / 22 externally correct / 0 false stamps** on the frozen public eval, graded live against oeis.org — and the badges above re-prove that in public CI on every push and every week. The zero has been earned, not kept: a 109-sequence OEIS sweep once caught 3 false stamps; they were published the same night, fixed at the root within hours, and that sweep's re-run graded 44 verified, zero false. When Chiron cannot prove a claim exactly, it says so instead of guessing. The record is stronger for having been falsified and repaired in the open.

**You are not buying code. You are buying certainty about machine output.**

<p align="center"><img src="docs/assets/chiron_demo.gif" width="880" alt="Real terminal session, outputs unedited: Chiron verifies a geometric rule on held-out terms, then refuses to certify a formula that fits the primes but fails the withheld terms, then shows a certificate that names its own falsifier."></p>

> Free to explore and use noncommercially (PolyForm Noncommercial 1.0.0).
> Commercial use and the full engine are licensed — see **[Pricing](PRICING.md)**.

---

## Verify it yourself — three depths, no purchase

Each tier says exactly what it proves and what it does not. That restraint is the product.

### 10 seconds — watch it refuse, in your browser

**[The playground](docs/playground/)**: paste any integer sequence and watch a real Python core
verify-or-refuse live — Fibonacci verifies, primes are refused with the reason, and the certificate
renders in full. The page fetches [`prototype/browser_core.py`](prototype/browser_core.py) verbatim
and runs it via CPython-in-WebAssembly; there is no server and no JavaScript reimplementation.

*Proves:* the contract, live on your input — exact arithmetic, a stamp only on exact held-out
prediction, refusal otherwise. *Does not prove:* the licensed engine's reach — the demo core is
strictly weaker by design (it refuses Tribonacci, Catalan and factorials, which the engine stamps).

**Live now: [jiannotti5040.github.io/chiron/playground](https://jiannotti5040.github.io/chiron/playground/)** —
or locally, no install: `python3 -m http.server` from the repo root, then
`http://localhost:8000/docs/playground/`.

### 2 minutes — grade the engine against ground truth the author does not control

```
git clone https://github.com/jiannotti5040/chiron && cd chiron
python3 eval/grade.py        # live oeis.org; add --cache eval/oeis_snapshot_2026-07-07.json for offline
```

Real session, 2026-07-21, output unedited (18 mid-table rows elided, every one reads "externally CORRECT"):

```
frozen file: engine 0.6.0+source  frozen 2026-07-21T11:26:51+00:00  commit 1652af0acc
tamper check: recomputed rows sha256 MATCHES the recorded one
ground truth: LIVE from oeis.org (b-files, ~1 req/s — the strong mode)

A-number   model class                 graded  verdict
A000032    linear_recurrence_order2      8/8   externally CORRECT
A000045    linear_recurrence_order2      8/8   externally CORRECT
   ...
A006318    holonomic_r2_p1               8/8   externally CORRECT

  stamped 22   externally correct 22   ungraded 0   refused (honest abstentions) 12
  FALSE STAMPS: 0   <- the number this eval exists to check
  RESULT: PASS — zero false verifications on external data
```

*Proves:* the headline property itself — the licensed engine's frozen, hash-bound outputs contain
zero stamps that external data contradicts; and with [`eval/challenge.py`](eval/challenge.py) you
can run the same protocol on sequences **you** choose. *Does not prove:* that everything gets
stamped (12 of 34 are refusals — that is the design). The protocol and its one residual assumption
are stated plainly in [`eval/README.md`](eval/README.md).

And if you want the **real engine on your own input, right now** — a live demo endpoint runs it:

```
python3 eval/remote.py --url https://chiron-engine.onrender.com collapse "1 1 2 3 5 8 13 21 34 55 89 144"   # VERIFIED
python3 eval/remote.py --url https://chiron-engine.onrender.com collapse "2 3 5 7 11 13 17 19 23 29 31 37"   # refuses
```

The licensed engine, served over HTTP — certificate out, source never serialized, rate-limited,
refuses over budget (18/18 endpoint gates). It's a free-tier demo instance (~30 s cold start after
idle); `remote.py` works against any deployment.

### 30 minutes — run every public battery and read the reconciled map

```
./demo.sh          # prototype 26 gates + demo core 17 gates + the frozen-output grade
./demo.sh --live   # the same, plus the live oeis.org grade
```

Then read **[`docs/BATTERIES.md`](docs/BATTERIES.md)** — every gate count in the project on one
page, tiered by what you can verify before paying — and **[`docs/GATES.md`](docs/GATES.md)** for
how to read the numbers honestly.

*Proves:* every public claim in this README, reproduced on your machine, and exactly which claims
are only provable post-license (the vault tiers). *Does not prove:* the vault batteries themselves —
those run with the licensed engine (`bin/chiron test`), and this repo says so rather than asserting
them on trust.

---

## The licensed engine, in 30 seconds

Chiron is handed six numbers and asked for the rule. It finds one, then **checks itself against held-out terms it was not given**:

```
$ chiron collapse 2 4 8 16 32 64
```
```json
{
  "model_class": "geometric",
  "verified": true,
  "exact": true,
  "explanation": "VERIFIED generator 'geometric'. Recovered in EXACT arithmetic
   from the first 4 terms, this rule reproduces every term and predicts all 2
   held-out terms exactly (==, not a tolerance). Compresses 69 bits to 14."
}
```

Now the part nobody else ships. Hand it a sequence it *can* fit but *cannot* prove:

```
$ chiron collapse 2 3 5 7 11 13 17
```
```json
{
  "model_class": "linear_recurrence_order3",
  "verified": false,
  "explanation": "Recovered a model that reproduces the given terms exactly,
   but its held-out prediction did not confirm (0/2). Status: recovered_unstamped.
   Treat as a candidate, not verified."
}
```

It found a formula that fits every number you gave it — and **still refused to certify it**, because it failed on the numbers you didn't. That refusal is the product. A system that only tells you what it can prove is a system you can build on.

Every run can emit a certificate — machine-readable evidence, a plain-language view, and (required on every certificate) **the exact thing that would prove it wrong**:

```json
{
  "system": "CHIRON", "verified": true,
  "human_view": {
    "what_was_discovered": "exact collapse recovers and verifies generators on
     held-out terms, refuses the incompressible, and escalates unsafe actions.",
    "what_would_falsify": "Any core gate failing — a false-verify, a missed
     escalation, or exec-of-string in the core path — would break the claim."
  },
  "self_hash": "fa07ee792bbe970d"
}
```

Real outputs, reproducible today, are in **[`examples/`](examples/)**. A runnable taste is in **[`prototype/`](prototype/)** — clone it and watch it verify and refuse for yourself.

---

## The problem Chiron solves

Organizations are deploying AI into decisions they cannot afford to get wrong — and they have no system of record for **what the machine did, whether it was allowed, and how to prove it after the fact.**

Today the answers are fragmented: internal testing, screenshots, human review, vendor promises. None of them produce evidence that survives an audit, a regulator, an incident, or a courtroom.

Chiron is the missing layer between a machine's output and your decision to trust it. It **measures, checks, governs, and certifies** — built on one non-negotiable property: **zero false verifications.** Refusal is a feature. A stamp whose every miss is published and repaired at the root is worth more than a stamp that is usually right.

---

## Who it's for

The same engine answers a different pain for each buyer. They compose — a team can use all four at once.

**Developers — "Build AI you can inspect."**
You ship systems whose failures you can't reliably explain. Chiron gives you exact recovery, held-out verification, adversarial checks, and a repeatable trace of *why* an output was accepted or refused.

**Compliance & risk — "Deploy AI with evidence."**
You're accountable for AI behavior you can't currently prove was in-bounds. Chiron produces audit trails, policy checks, and signed certificates — the paper an auditor or regulator actually accepts. One prevented failure costs more than the license.

**Security & red teams — "Find the failure before your users do."**
You need to know where a system breaks. Chiron is adversarial-evaluation infrastructure: it hunts for the input that makes a model assert something it cannot support, and reports it as a bounded, reproducible finding.

**Researchers & labs — "A laboratory for machine behavior."**
AI evaluation is inconsistent and unreproducible. Chiron is an extensible, deterministic framework — exact arithmetic, no hidden state, every result regenerable from its certificate.

---

## What makes it different: governance all the way down

Most "AI safety" tools bolt a policy check onto the outside of a black box. Chiron's governance is **structural** — it runs on the same exact-verification spine as the engine, at every layer:

- An action the system cannot justify as reversible and in-policy is **escalated to a human by construction** — not by a rule someone can switch off, but because the architecture cannot advance an unproven step.
- Every decision carries its lineage: what was checked, which policy applied, what would falsify it. Provenance is not a log you enable; it is how the output is produced.
- A verification stamp cannot be upgraded by a downstream component — no stage can launder another stage's "maybe" into a "yes."

This is the part that is genuinely hard to copy, and the part enterprises pay for: **accountability that is load-bearing, not decorative.**

---

## The model: closed-open-source

Chiron is neither locked away nor given away. It is a **governed ecosystem**.

- **This public repository** is the trust layer: the thesis, real examples, a runnable prototype, the architecture, the governance philosophy, and the honest gate results. It answers *why this exists* and lets you verify the claims before you pay.
- **The licensed engine** (`chiron-vault`) is the full system: 72+ folded modules, the certification brain, the composer, the dashboard — delivered as **one self-contained deterministic file** that runs offline with nothing to install.
- **License holders can read, run, modify, and extend** the full engine, and contribute improvements back. Changes to the certified core are owner-approved so the `verified` stamp never loses its meaning — you get the freedom of open source with a guarantee the honesty property is preserved.

Buying a license is closer to **joining the circle** than purchasing a file: you get the engine, the right to build on it, and a channel to send improvements back into an exclusive, verified body of work.

See **[Pricing](PRICING.md)** for the individual, team, business, and enterprise tiers.

---

## Proof, honestly

Everything above is backed by gates you can run, not adjectives. On the current build (2026-07-16, Python 3.14), the full battery is green:

| Gate | Result |
|---|---|
| Core engine smoke, as **one standalone file** | **5/5** (semic 56/56, chiron core incl. JDICert 280/280, density-emotion 8/8, semic-energy 8/8, epistemic 13/13) |
| Full folded sweep, in-repo | **49/49** modules green through the fold (2026-07-21 build; 48/48 on 2026-07-16 — the sweep grows with the spine) |
| Invariant-operation stress probes | **23/23** |
| Pipeline composer (chain / team / swarm) | **7/7** — never a false verify |
| Documented-command smoke (every command in the manual runs as written) | **9/9** |
| The TWIN PROOF (two different poems, one recovered generator) | 279,608,910,057,308,160 verses each, identical fingerprint |

**Verify the headline property before paying: [`eval/`](eval/)** — the engine's frozen predictions on 34 public OEIS sequences (12 terms shown, 8 held-out terms per stamp), graded live against oeis.org by a stdlib script, tamper-evident, **22 stamped / 22 externally correct / 0 false stamps / 12 honest refusals** on the 2026-07-21 freeze. `eval/challenge.py` lets you run the same protocol on sequences *you* choose. No engine code ships; outputs are what zero-false is a property of.

**How it compares to symbolic regression: [`docs/SYMREG.md`](docs/SYMREG.md)** — Primus 18 exact / 0 wrong / 11 refused vs PySR's 5 exact / 24 wrong on the same live-OEIS protocol; both the dated original runs and a 2026-07-21 reproduction, identical counts. The regressor must always answer; the refusals are the difference being sold.

**Every gate count in this project, reconciled on one page: [`docs/BATTERIES.md`](docs/BATTERIES.md)** — each battery, what it covers, where it runs (public prototype / vault / single file), and which tier you can verify before paying. If two numbers ever disagree, that page wins.

Methodology: **[`docs/GATES.md`](docs/GATES.md)**. Architecture: **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**. The governance stance: **[`docs/GOVERNANCE.md`](docs/GOVERNANCE.md)**. Why it refuses: **[`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md)**.

And one exhibit that is neither code nor spec: **[`VerifiedInk/`](VerifiedInk/)** — an essay on ink as verdict. It is in this repo on purpose: the aesthetic case for the same thesis the gates make mechanically — that a mark you cannot take back should never be made casually. Read it as the philosophy of the stamp; the code is the enforcement of it.

---

## Start

1. **Open** the [playground](docs/playground/) — paste a sequence, watch it verify or refuse, in your browser.
2. **Run** `./demo.sh` — every public battery plus the frozen-output grade, one command; then [`eval/grade.py`](eval/grade.py) live for the strong mode.
3. **License** the full engine when you have a decision you need to be able to prove: **[Pricing](PRICING.md)**.

> Required Notice: Copyright © 2026 Jacob Iannotti (THRUPUT). Commercial rights reserved.
> Public materials licensed under PolyForm Noncommercial 1.0.0 — see [LICENSE.md](LICENSE.md).
> Questions: jiannotti1@gmail.com
