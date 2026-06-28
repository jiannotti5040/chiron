# CANDOR — the anti-patronization engine

**Author: Jacob Iannotti. Licensed under PolyForm Noncommercial 1.0.0 — free to use, modify, and share for any noncommercial purpose; commercial rights reserved (see the repository-root [LICENSE.md](../LICENSE.md)).**

One file. Offline. Deterministic. Self-auditing.

---

## What it is

Every system in this vault circles one obsession: **machines must be honest
about the limits of their own knowledge, and must not patronize.** The failure
mode that matters is not that AI hallucinates, but *machine patronization,
non-communication, and information loss while accountability stays minimal and
self-referential.* LexGuard gates it. JDICert certifies against it. Primus
returns honest residuals instead of faking confidence. CANDOR is that
through-line pulled out and turned into a single instrument.

It takes any piece of reasoning — a model's answer, a memo, your own draft —
and scores how **candid** it is across four axes, decomposing every point of
the score into the exact spans that caused it:

- **Condescension** — patronizing framing, false reassurance, telling the
  reader how to feel ("Don't worry," "it's actually quite simple," "Great
  question!").
- **Unearned confidence** — assertion past the evidence ("obviously,"
  "definitely," "everyone knows," "without a doubt").
- **Evasion** — hedging used to dodge commitment rather than mark real
  uncertainty ("it depends," "there are many factors," "results may vary").
- **Opacity** — claims made with no traceable basis: no *because*, no source,
  no data, no acknowledgement of what would make them false.

`CANDOR = product of per-axis candor` — being uncandid on **any** axis drags
the whole score down. A purely condescending answer is uncandid even if it
isn't evasive.

## Why it's different from "AI safety" tooling

Most safety tools ask *"is this content harmful?"* CANDOR asks the question your
whole corpus actually cares about: *"is this reasoning being honest about what
it doesn't know?"* And it holds itself to the same standard — it states its own
limits on every single run, and its own output passes its own audit (a gate
proves it). A tool that measures candor and is itself candid.

## Run it

```bash
echo "Great question! Don't worry, this is obviously simple." | python3 candor.py
python3 candor.py --file draft.txt
python3 candor.py --selftest        # 17/17 gates, incl. the self-audit
python3 candor.py --json < input    # machine-readable
```

Example output (patronizing answer):

```
CANDOR audit — score 0.12/1.00  [deeply uncandid]
  condescension 0.59  unearned_confidence 0.61  evasion 0.00  opacity 0.24
    [condescension]  "Don't worry"        — false reassurance pre-empts the reader's judgment
    [unearned_confidence] "without a doubt" — absolute certainty
    [opacity]        "Obviously the answer is yes..." — asserts a claim with no basis
  LIMITS: lexical/structural detector, not semantic. Treat findings as spans
  to inspect, never as a verdict.
```

It also does **candid-repair suggestions** (the move to fix each span, never a
faked replacement) and **transcript audits** (score a multi-turn exchange and
catch a conversation drifting into patronization — `audit_transcript`).

## What it honestly is NOT

A lexical/structural detector, not a semantic one. It can be fooled by content
that is dishonest *without* these surface markers, and it can flag honest
content that happens to use one. It says exactly this on every run. Treat its
findings as spans worth a human's eye — never as a verdict. That refusal to
overclaim is not a disclaimer bolted on; it is the entire point of the tool.

## Where it could go

A live filter on model output; a writing tool that grades your own drafts
before you send them; a deterministic, auditable signal in an LLM evaluation
pipeline (it has no model dependency, so it can sit anywhere); a calibration
target — train or prompt a model to maximize candor on held-out content. It is
the smallest, sharpest expression of the discipline the whole vault is built on.
