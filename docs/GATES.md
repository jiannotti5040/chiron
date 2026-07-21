# Gates — the proof, and how to read it

Chiron's claims are backed by gate batteries you can run, not by adjectives. This
page records the current results honestly, including their scope and limits.

## Current build — 2026-07-16, Python 3.14

| Gate battery | Result | What it proves |
|---|---|---|
| **Standalone core smoke** (the monolith as one file, no vault beside it) | **5/5** | semic 56/56 · chiron core (incl. JDICert 280/280) · density-emotion 8/8 · semic-energy 8/8 · epistemic 13/13 |
| **Full folded sweep** (in-repo) | **48/48** | every selftest-bearing module runs green through the fold (49/49 on the 2026-07-21 build — the sweep grows with the spine; the reconciled map of every battery lives in [BATTERIES.md](BATTERIES.md)) |
| **Invariant-operation stress probes** | **23/23** | recovery, refusal, adversarial inputs, cipher inversion, structural equivalence |
| **Pipeline composer** | **7/7** | chain/team/swarm compose correctly; an unknown component fails safe; never a false verify |
| **Documented-command smoke** | **9/9** | every command printed in the manual runs exactly as written |
| **TWIN PROOF** | identical fingerprint | two different poems (different vocabularies) collapse to one generator — 279,608,910,057,308,160 admissible verses each |

## How the standalone claim is scoped, precisely

The **standalone** number (5/5) is the certified core-engine battery running from
the single monolith file with no supporting tree. The broader in-repo sweep
(48/48) includes orchestration and serving modules — live servers, the packaged
seed, growth/state tooling — which need the full `chiron-vault` install to run.
We state the standalone claim as exactly what it is: the core engines, proven in
one file. We do not claim the servers run from the single file, because they
don't, and overclaiming is the one error this project cannot afford.

## The discipline behind the numbers

A gate that fails is information, not an obstacle. This project's best findings
came from gates catching real defects — a false stamp, a denial-of-service in a
sequence scanner, a Fibonacci dressed up as something it wasn't. The rule is:
investigate and fix the root cause; never widen a tolerance to turn a gate green.
Tolerances on the stamping path are zero by design.

## Reproduce it

License the engine and run the full battery yourself (`bin/chiron test`), or run
the public [`../prototype/`](../prototype/) for the recover/verify/refuse core
without a license. Every number above regenerates deterministically.
