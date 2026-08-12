# Governance, all the way down

Most "AI governance" is a checkpoint bolted onto the outside of a system you
still can't see into: a policy filter on the input, a review step on the output,
a dashboard that reports what a black box claims it did. Chiron's governance is
different in kind. It runs on the **same exact-verification spine as the engine**,
so accountability is a property of how outputs are produced — not a layer you
switch on and hope holds.

## Three structural guarantees

**1. Unproven steps cannot advance.**
Chiron composes engines toward a goal through a gate that arbitrates every step.
A step that claims "verified" but cannot regenerate its own evidence is refused
by the gate — so a plan literally cannot build on an unproven result. A
hallucination is structurally incapable of moving the process forward.

**2. Irreversible or out-of-policy actions escalate by construction.**
When the system faces an action it cannot justify as reversible and within
policy, it escalates to a human — not because a rule says so (rules can be
switched off) but because the architecture will not execute what it cannot
justify. The propose / dispose / escalate contract is built into the decision
layer, not sprinkled on top.

**3. No stage can launder another stage's uncertainty.**
In a Chiron pipeline, a downstream component cannot upgrade an upstream "maybe"
into a "yes." The verification verdict is AND-of-required: the whole chain
verifies only if every required stage verified; any refusal or refutation makes
the chain abstain or fail. Confidence can only be lost, never manufactured.

## Why this is the differentiator

Ask who else has made governance **permeate** a system rather than wrap it. Most
answers are wrappers: a guardrail here, an eval there, a log you can turn off.
The hard version — where every decision carries its own lineage, every stamp is
falsifiable, and the structure itself refuses to advance the unproven — is rare
because it has to be designed in from the first primitive, not added before
launch.

For a compliance or risk team, this is the whole point. The question they cannot
answer today is: *"Can we prove this AI system behaved within defined boundaries,
and explain the behavior after the fact?"* Chiron is built so the answer is a
certificate, not a promise.

## What this project reviews, and what the licence permits

Apache-2.0 grants the right to use, modify, distribute, and commercially
exploit this code, including forks that change the verification path. Nothing
here restricts that, and this document does not attempt to.

What is reviewed is what enters *this* repository. Changes to the verification
and refusal path are reviewed before merging here, because a `VERIFIED` stamp
is only worth anything if it has one meaning across the line of work that
carries this project's name and certificates.

A fork is free to change the stamping rules. It is then making its own claim,
under its own name, and the certificates it issues are its own.
