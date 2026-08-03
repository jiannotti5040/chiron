# Launch copy

Ready-to-paste posts. Every number below is from a run in this repo and is
reproducible by a reader in one command. Nothing here is aspirational — if a
claim can't be checked from the public repo, it isn't in this file.

---

## Show HN (title + body)

**Title:**

> Show HN: Chiron – a verifier that refuses to certify what it can't prove exactly

**Body:**

Two long-open conjectures were refuted by AI-produced counterexamples in one
week of July 2026 — the Jacobian conjecture (open since 1939) and the
Dinitz–Garg–Goemans conjecture. Both were announced ahead of peer review. Both
are short enough to state on a napkin.

That's now a recurring situation: a machine produces a claim, and somebody has
to decide whether the arithmetic is real.

I built a verifier for the part of that question a machine can answer exactly.
It recovers rules from data, checks claims, and — the part I care about —
**refuses to stamp anything it cannot prove.** Refusal is the output, not a
failure mode.

What it did with those two announcements, without being written for either:

- **Jacobian:** `det J ≡ −2` as an exact polynomial identity over ℚ, plus a
  two-point rational collision denying injectivity. 12/12 gates.
- **DGG:** fractional flow feasible at cost 58; all 2³ unsplittable routings
  enumerated; cheapest congestion-admissible one costs 60. 15/15 gates. Every
  admissible instance with b ≤ 25 — 456 of them — refutes, exhaustively, in
  exact integers.

The wording matters and I'll keep it precise: it **certified the finite
computational claims constituting each published counterexample, under the
encoded formulation.** It did not certify either conjecture false. Provenance,
minimality, the Jacobian n=2 case, the DGG theorem itself, and peer review are
all recorded as refusals.

Then I pointed it at a corpus nobody here curated —
`google-deepmind/formal-conjectures`, 850 Lean files, 3,195 tagged theorems —
and asked the only question it's entitled to ask of each: *is there a finite
exact obligation here I can discharge?*

    REFUSED-NEEDS-LEAN     1,545   48.4%
    REFUSED-INFINITARY       922   28.9%
    REFUSED-NO-ANSWER        426   13.3%
    FINITE-CHECKABLE         302    9.5%

**It refuses 90.5% of that corpus, and that's the correct answer.** Open
conjectures are open because they aren't finitely checkable. A tool reporting a
high success rate there would be broken, not capable.

The calibration argument is what makes the number mean something: the
classifier never sees DeepMind's own category labels, yet independently
rediscovers them — 215 of the 302 dischargeable obligations sit in the 18% of
the corpus tagged `test`, while `research open` returns 432 infinitary and 418
unanswered against just 18 finite.

Reproduce that yourself, no licence, no account, no engine:

```bash
git clone --depth 1 https://github.com/google-deepmind/formal-conjectures
python3 eval/conjecture_triage.py triage formal-conjectures
```

Free and offline as an agent tool:

```bash
pip install primus-intelligence
claude mcp add primus -- primus-mcp
```

The external eval is frozen and graded against OEIS ground truth I don't
control: 22 stamped / 22 externally correct / 0 false stamps / 12 honest
refusals. An earlier 109-sequence sweep caught **3 false stamps** — those were
published, root-caused, and fixed, then re-run with 44 verified and zero false.
The falsification is in the repo on purpose; a caught-and-repaired defect is
worth more than an unblemished claim.

PolyForm Noncommercial — free to use, study, and modify noncommercially.

https://github.com/jiannotti5040/chiron

---

## r/math (title + body)

**Title:**

> I built an exact-or-refuse verifier and ran it over 1,171 open conjectures. It refused 90.5% of them, which is the point.

**Body:**

After the Jacobian and DGG counterexamples landed in July, I wanted to know how
much of the open-conjecture literature is actually reachable by exact
computation. So I ran a verifier over every open conjecture in
`google-deepmind/formal-conjectures` — 1,171 of them — and gave each a recorded
status.

Six have finite obligations a computation can attack. **Six, out of 1,171.**

The rest break down as 564 infinitary (asymptotic, infinite sets, statements
about ℝ), 329 where the corpus itself marks the answer unknown, and 272 whose
truth depends on definitions the tool can't evaluate. The breakdown by trigger:
279 `Filter.atTop`, 89 asserting an infinite set, 37 existentials over the
reals, 37 natural density, 22 irrationality, 18 transcendence.

I think that 0.5% is the interesting number. It's a concrete measure of how
thin the finitely-checkable surface of the open literature actually is, and I
haven't seen it quantified anywhere.

Two caveats I want to be straight about. First, the classifier is
conservative — a later re-triage recovered 127 conjectures it had wrongly
dismissed, including Legendre's, Oppermann's, Brocard's, and Kurepa's, so the
first pass was demonstrably incomplete. Second, no refutation was found, and
the bounded searches I ran on the reachable ones are all far below the
published state of the art (Gilbreath is verified to 10¹³; I did 10⁴).

Method and every number: https://github.com/jiannotti5040/chiron

---

## LinkedIn / X (short)

Two open conjectures fell to AI-generated counterexamples in one week of July.
Both announced before peer review.

The bottleneck stopped being discovery. It's verification.

I built an exact-or-refuse verifier and pointed it at 1,171 open conjectures
from DeepMind's corpus. It refused 90.5% of them — and that's the correct
answer. Open problems are open because they aren't finitely checkable.

It discharged the finite core of both July counterexamples without being
written for either.

Reproducible in two commands, no licence:
https://github.com/jiannotti5040/chiron

---

## Notes for posting

- **Lead with the July counterexamples.** That's the reason anyone should care
  today, and it's verifiable in thirty seconds.
- **Never write "certified the conjecture false."** Write "certified the finite
  computational claims constituting the published counterexample, under the
  encoded formulation." The precision is the credibility.
- **Volunteer the 3 false stamps.** Someone will find them; better they hear it
  from the README. It is the strongest thing in the repo.
- **Don't claim the bounded searches advance anything.** Gilbreath and Juggler
  are verified far past what's here, and the README says so in a prior-art
  column. Anyone who checks will find that column and trust the rest more.
- Expect "so it just says no a lot?" — yes, and the calibration cross-tab is
  the answer: it independently rediscovers DeepMind's own labels without
  seeing them.
