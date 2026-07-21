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
| Browser demo core (`prototype/browser_core.py selftest`) | the [playground](playground/)'s verify-or-refuse core: exact arithmetic, stamp only on exact held-out prediction, h ≥ p evidence rule, floats refused not rounded — **strictly weaker than the licensed engine by design** (it refuses Tribonacci/Catalan/factorials the engine stamps) | this repo, one file, stdlib only — the same file the browser runs | **17/17** |
| **Public eval build** (`eval/grade.py`) | the engine's **headline property itself** — frozen engine outputs (12 terms shown, exact predictions for terms 13..20 or refusal) graded against oeis.org **live**; tamper-evident freeze (commit + sha256); `eval/challenge.py` lets you grade sequences **you** choose | this repo, stdlib only, no engine code | **22 stamped / 22 externally correct / 0 false stamps / 12 refusals** (freeze 2026-07-21) |

| Live engine endpoint (`eval/remote.py --url https://chiron-engine.onrender.com`) | the **real licensed engine** over HTTP — verify-or-refuse on any input you send; source never serialized, rate-limited, refuses over budget | a hosted demo instance (free tier; ~30 s cold start) | 18/18 endpoint gates |

That is the pre-purchase verification boundary today: the discipline, a
working core, the zero-false property verified on external data (including
data you pick), and — via the hosted endpoint — the real engine itself run
on arbitrary input you choose. The full engine source and its gate battery
still arrive only with a license.

## Tier 2 — the vault build (delivered with a license) — as most recently run, 2026-07-21

**Primus, the packaged seed engine:**

| Battery | Covers | Count |
|---|---|---|
| Invariant stress gates | recovery, refusal, adversarial input, the evidence rule | **55/55** |
| `primus selftest` | engine 4 + certificate layer 31 + guess-and-prove conjecture layer 16 | **51/51** |
| Certify fuzz | hostile input: floods, bombs, bounds, noise-stability, determinism | **16/16** |
| MCP handshake | the live server process over real stdio JSON-RPC | **11/11** |
| HTTP endpoint gates | the engine served as a live HTTP endpoint (`primus.engine_server`): verify/refuse round-trips, over-budget refusals at the certify bounds, rate limits, auth, and the no-leak rule (no traceback or source path in any hostile response) | **18/18** |
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

Tier 1 is verifiable before any money moves — and since 2026-07-21 that
includes the headline property itself: the [`eval/`](../eval/) build
grades the engine's frozen outputs against oeis.org live, with a
buyer-chosen challenge mode that removes the "author picked the corpus"
objection (protocol and residual assumptions stated plainly in
[`eval/README.md`](../eval/README.md)). Tier 2 is the thing being sold;
its numbers are reproduced on every change (`bin/chiron test` after
licensing). "Trust us, it's green in private" is exactly the claim this
project exists to reject; the eval build is that rejection made runnable.

*Single-file scope, precisely: the standalone 5/5 runs from one file with
no vault beside it; the 49/49 sweep includes modules (servers, packaged
seed, growth tooling) that need the full vault install. We do not claim
the servers run from the single file, because they don't.*
