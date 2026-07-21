# Architecture

Chiron is a set of independently-runnable engines that share one spine: exact
recovery, held-out verification, refusal, and a certificate carrying a self-hash. In the
licensed engine they are folded into **one self-contained deterministic file**
(`chiron_monolith.py`) that runs offline with nothing to install — the whole
system as a single drag-and-drop artifact, plus an operator dashboard.

## The layers

**The recovery core (Primus / invariant engine).**
Given a surface — a sequence, a structure, code — it searches a constrained space
of generators for the shortest rule that reproduces it (Minimum Description
Length), then verifies that rule on held-out evidence in exact arithmetic. This
is the `collapse` you see in the examples: recover → prove → verify-or-refuse.

**The certification brain (JDICert).**
Takes a claim or a decision through a partition of what is known, unknown, and
irreducible; applies reduction operators, world-models, counterfactual and
red-team suites; and produces a certificate with Merkle-chained lineage. It
carries governance and regulatory reference frames (EU AI Act, GDPR, NIST AI RMF,
ISO/IEC 42001) as first-class structure. On the current build its embedded suite
runs 280/280.

**The composer (pipeline).**
Wires the engines into whatever validation system you need — a chain, a team, or
a swarm — arbitrated by the one gate. The verdict is AND-of-required: verifies
only if every required stage verified; no stage can upgrade another's verdict.
This is how you build *your* checks out of Chiron's parts.

**The decision layer (governance / president).**
Applies the propose / dispose / escalate contract to actions: reversible and
in-policy decisions proceed; anything else escalates to a human by construction.

**The honesty scorer (Candor).**
Flags over-assertion — language that claims more than the evidence supports — so
the system's own reports are held to the same standard as its stamps.

**Supporting engines.** Semantic-invariant calculus (SEMIC), an ambiguity crucible
grounded in a 1663 combinatorial source (Infectatrum), a field substrate (UMA),
and more — each with its own gate battery.

## Determinism and provenance

Everything on the stamping path is deterministic: same input, same certificate,
same hash. There is no network in the core path. Every result can be regenerated
from its certificate, and every certificate names what would falsify it. That is
what makes Chiron auditable rather than merely observable.

## What's public vs. licensed

This public repository carries the thesis, real example output, a runnable
prototype, and these docs — enough to verify the claims. The full engine, the
folded monolith, the certification brain, the composer, and the dashboard are in
the licensed `chiron-vault`. See [PRICING](../PRICING.md).
