# The 2026 Dinitz–Garg–Goemans cost-conjecture counterexample, verified by this suite's own arithmetic

**Author: Jacob Iannotti. Licensed under PolyForm Noncommercial 1.0.0 (see the repository-root LICENSE.md).**
**Epistemic status: the verification machinery and the arithmetic claims below are implemented-and-tested (`uma/dgg/`, `tests/test_dgg.py`, 15 gates). The surrounding history is reported, not certified.**

## What happened

In **July 2026**, Dmitry Rybin announced that **GPT-5.6 Pro**, given four
short prompts, produced a counterexample to the **Goemans cost conjecture**
on unsplittable flows — open since the 1990s.

The underlying theorem of Dinitz, Garg and Goemans is not in dispute: any
fractional single-source flow can be re-routed as an *unsplittable* flow
(each demand sent entirely along one path) while exceeding each arc's
capacity by at most `d_max`, the largest single demand. Goemans then
**conjectured** that this re-routing could always be done **without
increasing the cost**. The counterexample shows it cannot.

As of **2026-07-23** there is **no peer-reviewed write-up**. The working
sources are the announcement thread, secondary technical write-ups, and a
published 3-parameter generalisation of the instance.

## What `uma.dgg` verifies — exact integer arithmetic, exhaustive, no solver

The instance is a single-source network on **7 nodes and 9 arcs**. Each of
the three terminals has exactly **two** possible routes, so the unsplittable
routing space has exactly `2³ = 8` members — small enough to enumerate
**completely**. That matters: this is a proof for the instance, not a
sample of it.

| # | Claim | Method | Result |
|---|---|---|---|
| 1 | The fractional flow is **feasible** — conserves at u, v, w and meets every demand exactly | integer conservation check, flow = capacity on every arc | **VERIFIED** |
| 2 | Its cost is **58** | exact integer sum of cost × flow | **VERIFIED** |
| 3 | Every unsplittable routing within the DGG congestion allowance (`load ≤ capacity + d_max`) costs **at least 60** | exhaustive enumeration of all 8 routings | **VERIFIED** |
| 4 | Therefore the cost conjecture is **false** for this instance | (1) is the hypothesis; (3) denies the conclusion | **REFUTED** |

Claims 2 and 3 reproduce the announcement's published figures (58 and 60)
**independently**, from the instance's structure — they were not copied.

### Independent corroboration of the instance

The instance was reconstructed from a published 3-parameter family at
`(b, m, g) = (10, 5, 1)`. Three numbers not used in the reconstruction then
matched the reported instance exactly — the congestion thresholds
`capacity + d_max` on the spine arcs:

| arc | capacity | + d_max (15) | reported |
|---|---|---|---|
| s→u | 24 | **39** | 39 |
| u→v | 14 | **29** | 29 |
| v→w | 9 | **24** | 24 |

Three independent agreements is why this module treats the reconstruction
as the announced instance rather than merely *an* instance.

### A reconciliation worth recording

Under the published family's own cost convention the same instance costs
**290** fractional against **300** unsplittable. Those are the announcement's
58 and 60 **scaled by exactly 5**. The refutation is invariant under
positive cost scaling, so both accounts describe one counterexample; the
apparent disagreement was a normalisation, not an error. The suite records
both and asserts the scaling relation as a gate.

### The whole family, not one lucky instance

`uma.dgg.sweep()` enumerates **every** admissible `(b, m, g)` with `b ≤ 25`
— **456** instances — and verifies each one exhaustively:

```
admissible_instances_checked : 456
instances_refuting           : 456
all_refute                   : True
```

### Controls — the machinery must be able to fail

A gate that cannot fail proves nothing, so the battery includes:

- **inadmissible parameters raise** rather than silently verifying;
- **a perturbed capacity** (`v→w + 1`) is detected as an infeasible flow;
- **zero costs ⇒ no refutation**: with all costs set to 0 the verifier
  reports `refuted: False`, because nothing is then more expensive than the
  fractional flow;
- **the all-detour routing costs 0** — and is correctly rejected as exceeding
  the congestion allowance. The refutation depends on the DGG allowance, not
  on convenient accounting.

## What this suite does NOT claim

- It does not certify the **provenance** of the construction (Rybin's
  announcement and its attribution to GPT-5.6 Pro are reported as announced).
- It does not claim the instance is **minimal**.
- It does not resolve any other question in the unsplittable-flow
  literature; the Dinitz–Garg–Goemans *theorem* is untouched, and only
  Goemans' **cost** conjecture is refuted here.
- It does not substitute for **peer review**.

As with `uma/jacobian`, that last point is the reason to do this here:
whatever the eventual paper says, **a 7-node network whose fractional flow
costs 58 and whose every congestion-admissible unsplittable routing costs at
least 60 exists, and is checked here exactly** — zero floats, zero solver,
zero network, zero trust in anyone else's arithmetic.

## Reproduce

```
cd uma_build_v4
python3 -m pytest tests/test_dgg.py -v     # 15 gates
python3 -m uma.dgg                          # the certificate, as JSON
```

## Sources (as consulted 2026-07-23)

- Announcement: Dmitry Rybin (x.com/DmitryRybin1), July 2026 — GPT-5.6 Pro, four prompts
- 3-parameter generalisation used for the reconstruction: Hensen Juang (x.com/basedjensen)
- Technical write-up consulted for the reported instance figures: mathlab.drummerduck.com "Goemans' unsplittable-flow cost conjecture"
- Background theorem: Dinitz, Garg, Goemans, *Combinatorica* (1999)

## Relation to the rest of UMA

This is the suite's second pure-algebra/combinatorics member, after
`uma/jacobian`. Both follow the same discipline end to end: exact arithmetic
on the stamping path, controls that can fail, and refusal to certify beyond
what was computed. Together they answer one question the current moment
keeps raising — *an AI produced a mathematical claim; is the arithmetic
actually real?* — twice, in the same week, by the same standard.
