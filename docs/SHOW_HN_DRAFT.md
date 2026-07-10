# Show HN draft

> **HOLD before posting.** The whole hook here is "zero false verifications,"
> and there is currently a live false stamp in the seed engine (companion Pell —
> see `EXTERNAL_VALIDATION_ADDENDUM_2026-07-07.md`). Land that fix first, then
> post. The fix actually *strengthens* this draft — see the bracketed line in the
> body.

## Title (pick one)

- Show HN: Primus – it proves an LLM's math claim exactly, or refuses (no false stamps)
- Show HN: A deterministic certifier that verifies or refuses math, never guesses
- Show HN: Abstain-or-prove verification for sequences and arithmetic (non-LLM)

## Body

Primus is a small, offline, deterministic engine — not an LLM — that sits over a
claim and returns one of three verdicts: **VERIFIED**, **REFUTED**, or
**REFUSED**. VERIFIED means it recovered an exact rule (exact rational
arithmetic, no floats on the stamping path) and then confirmed that rule by
predicting held-out terms *exactly*. REFUSED means the claim is outside its
declared hypothesis classes and it won't guess. The design goal is a gate that
**only stamps what it can exactly prove, and abstains otherwise.**

I built it because LLMs assert confidently and uniformly, and I wanted a
verification layer whose "verified" mark has never lied on external data.

The honest part, which is really the whole point: that zero-false-verification
claim survived ~5,070 self-generated cases, then the **first** run against
live OEIS data falsified it — repunits were stamped VERIFIED with a wrong
predicted term (float drift + a tolerance hole). I fixed it at the root (exact
Fraction arithmetic, exact-integer holdout, floats past 2^53 refused). [When I
extended the external battery again this month, it caught a *second* false stamp
on the seed engine — companion Pell — which I root-caused to the same defect
class on a different code path and repaired the same way. Both misses are
published, not buried.] The claim is worth something precisely because it has
been falsified and repaired in the open.

What it does today, reproducible by command:
- Recovers linear recurrences, polynomials, geometric, and P-recursive
  (holonomic) sequences, and **proves** them by exact prediction of unseen terms
  — or refuses (primes, partitions, Bell numbers, φ(n), etc., where refusal is
  the correct answer).
- Head-to-head vs gplearn symbolic regression on the same external set:
  16 exact / 0 wrong, vs 2 / 22.
- Ships an MCP server, so an agent can call the gate over its own output
  (`claude mcp add primus -- primus-mcp`).
- `pip install ./Primus`; `primus certify`; everything offline and deterministic.

What it is not: the recovered rules are rediscoveries of known structure, not
new mathematics; the external battery is curated (dozens of sequences, not all
of OEIS — the full keyword:core sweep is the next escalation); and it certifies
only the claim kinds it declares. It's a gate, not an oracle.

License: PolyForm Noncommercial. Repo and a browser playground (runs the real
engine) linked below. Please try to break it — the fuzz suite exists because
someone's inputs will.

- Repo: https://github.com/jiannotti5040/Jacob-s-Portfolio-Vault
- Playground: (enable GitHub Pages first — see steps in RELEASE_AND_REACH.md)
