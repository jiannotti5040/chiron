# The batteries map — every gate count, one table, no assembly required

**Author: Jacob Iannotti. PolyForm Noncommercial 1.0.0 (see LICENSE.md).**

Every "X/X green" figure across this project belongs to exactly one named
battery. This page is the single map: what each battery covers, **where it
runs**, **who can run it today**, and the count as of its listed date.
Counts grow as modules are added; this page is regenerated whenever they
do. If a number here disagrees with a number elsewhere, this page wins
and the other page is stale — tell us.

## Tier 1 — public: run it yourself, right now, from this repo

| Battery | Covers | Where | Count |
|---|---|---|---|
| Prototype selftest (`prototype/primus_prototype.py selftest`) | the recover / verify / **refuse** core discipline; the JDICert stub that structurally cannot say VERIFIED | this repo, one file, Python 3 + numpy | **26/26** |

That is the honest boundary of pre-purchase verification today: you can
verify the discipline and a working core, not the full engine.

## Tier 2 — the vault build (delivered with a license) — as most recently run, 2026-07-21

**Primus, the packaged seed engine:**

| Battery | Covers | Count |
|---|---|---|
| Invariant stress gates | recovery, refusal, adversarial input, the evidence rule | **55/55** |
| `primus selftest` | engine 4 + certificate layer 31 + guess-and-prove conjecture layer 16 | **51/51** |
| Certify fuzz | hostile input: floods, bombs, bounds, noise-stability, determinism | **16/16** |
| MCP handshake | the live server process over real stdio JSON-RPC | **11/11** |
| Twin cross-lock | exact combinatorial corpus agreement | **12/12** |
| Certify property grid | soundness invariant across a generated grid | pass, 0 violations |
| Internal benchmark | recovery + precision, zero false confidence | pass |
| **External OEIS validation** | live-fetched sequences the author didn't write; graded on exact prediction of unseen terms | **20 verified / 0 false / n=29** |
| Seed↔Chiron drift differential | the two engines may not silently disagree | **42 agree / 0 fail** |

**Chiron, the production spine:**

| Battery | Covers | Count |
|---|---|---|
| Chiron core gates | the organism's hard laws | **12/12** |
| Reproducibility harness | same input, same version ⇒ byte-identical results | digest-stable |
| Monolith standalone smoke | the certified core from ONE file, no vault beside it (semic 56/56, JDICert 280/280 inside) | **5/5** |
| Monolith full folded sweep | every selftest-bearing module, through the fold | **49/49** |
| Invariant-operation stress probes | recovery/refusal/cipher/structure (build of 2026-07-16) | **23/23** |
| Pipeline composer | chain/team/swarm compose; unknown component fails safe | **7/7** |
| Documented-command smoke | every command in the manual runs as written | **9/9** |

**UMA Suite (research package in the vault):**

| Battery | Covers | Count |
|---|---|---|
| UMA pytest suite | dynamics/RSLS/semantic + **exact verification of the 2026 Jacobian-conjecture counterexample** (det J ≡ −2 as a polynomial identity; exact two-point collision; controls) | **136/136** (3 `@slow` deselected) |

## How to read the two tiers honestly

Tier 1 is verifiable before any money moves. Tier 2 is the thing being
sold; its numbers are reproduced on every change (`bin/chiron test` after
licensing) and the **external** row — live-OEIS, zero false verifications
on data the author didn't produce — is the property the whole project is
named for. We know "trust us, it's green in private" is exactly the claim
this project exists to reject; closing that gap further (a runnable eval
build that demonstrates zero-false on a held-out public suite without
shipping the engine) is the roadmap's next credibility item, stated here
so the gap is at least never hidden.

*Single-file scope, precisely: the standalone 5/5 runs from one file with
no vault beside it; the 49/49 sweep includes modules (servers, packaged
seed, growth tooling) that need the full vault install. We do not claim
the servers run from the single file, because they don't.*
