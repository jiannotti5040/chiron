# Chiron

> **Checkout is temporarily paused.** Automated paid access to the private subscriber repository is being finalized and acceptance-tested. No self-serve tier is currently for sale. Questions: jiannotti1@gmail.com.

### The verification layer for machine intelligence.

Chiron recovers the exact rule behind data, proves it on evidence the rule never saw, and **refuses to answer when it cannot prove** — then leaves a signed, falsifiable certificate of what it did and why.

Most AI systems assert. They produce an output and you trust it. Chiron inverts that: an output is not a right, it is a **verdict**. On its published gates, Chiron's `verified` stamp has never been wrong on external data — because when it cannot prove a claim exactly, it says so instead of guessing.

**You are not buying code. You are buying certainty about machine output.**

> Free to explore and use noncommercially (PolyForm Noncommercial 1.0.0).
> Commercial use and the full engine are licensed — see **[Pricing](PRICING.md)**.

---

## See it in 30 seconds

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

Chiron is the missing layer between a machine's output and your decision to trust it. It **measures, checks, governs, and certifies** — built on one non-negotiable property: **zero false verifications.** Refusal is a feature. A stamp that has never lied is worth more than a stamp that is usually right.

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
| Full folded sweep, in-repo | **48/48** modules green through the fold |
| Invariant-operation stress probes | **23/23** |
| Pipeline composer (chain / team / swarm) | **7/7** — never a false verify |
| Documented-command smoke (every command in the manual runs as written) | **9/9** |
| The TWIN PROOF (two different poems, one recovered generator) | 279,608,910,057,308,160 verses each, identical fingerprint |

Methodology: **[`docs/GATES.md`](docs/GATES.md)**. Architecture: **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)**. The governance stance: **[`docs/GOVERNANCE.md`](docs/GOVERNANCE.md)**. Why it refuses: **[`docs/PHILOSOPHY.md`](docs/PHILOSOPHY.md)**.

---

## Start

1. **Read** the two demos above and open [`examples/`](examples/) — real, regenerable output.
2. **Run** the [`prototype/`](prototype/) to watch it verify and refuse on your machine.
3. **License** the full engine when you have a decision you need to be able to prove: **[Pricing](PRICING.md)**.

> Required Notice: Copyright © 2026 Jacob Iannotti (THRUPUT). Commercial rights reserved.
> Public materials licensed under PolyForm Noncommercial 1.0.0 — see [LICENSE.md](LICENSE.md).
> Questions: jiannotti1@gmail.com



> **Checkout is temporarily paused.** Automated paid access to the private subscriber repository is being finalized and acceptance-tested. No self-serve tier is currently for sale. Questions: jiannotti1@gmail.com.
