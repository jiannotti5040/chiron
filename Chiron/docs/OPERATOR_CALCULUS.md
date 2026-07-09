# The Operator Calculus — a notation, realized in code

*The arrows were never decoration. They are operators — the dispersal of energy in and out
of a bounded substrate. This document promotes the ASCII to first-class objects and points
each one at the module that actually runs it. It is a **notation and a front-end** for the
engines already in this repo, not a claim of new mathematics.*

---

## 1. The operators (the arrows, promoted)

| Glyph | Operator | Meaning | Realized in |
|---|---|---|---|
| `-->` | directed transform | one-way propagation; information enters, transforms, exits forward | `intake.py`, the membrane itself |
| `==>` | projection | collapse to a lower-dimensional representation (lossy) | `projection_stack.py` |
| `<==` | recovery | reconstruct toward the prior representation; identity increases | `projection_stack.py`, `holographic.py` |
| `<-->` | resonance | bidirectional, mutual constraint; neither side independent | `discernment.py` (witness convergence) |
| `~` | uncertainty envelope | unresolved state around a representation | `operator_calculus.py` (the Mystery Vector) |
| `*` | constructive interaction | operators jointly generate new continuity | `discernment.py`, `actionable_intelligence.py` |
| `\|X\|` | bounded substrate | the object has bounded identity | every bridge (one-way membrane) |
| `(X)` | codified state | identity has entered symbolic form | `chiron.collapse` |

## 2. The substrate space

`Σ = { V, P, C, E, S, A }` — Void, Physical, Contextual, Emotive, Semantic, Abstract. Each is
a coordinate system on the same invariant, not a different object. The forward chain is

```
V --> P --> C --> E --> S --> A          (projection: away from the invariant)
A ==> S ==> E ==> C ==> P ==> V          (recovery:  toward the invariant)
```

Realized by `projection_stack.py` (the P→C→E→S core) over `cert_engine`'s
`EmotiveSubstrateProjectionStack`, with identity-preservation checked on every pass.

## 3. The four operators every substrate carries

For any substrate `X`: gradient `∇X` (rate of representational change), curvature `∇²X`
(instability / ambiguity — large curvature = contradiction, small = coherence), accumulation
`∫X` (recovery integrates evidence), projection `Π` (change of representation).

| Operator | What it measures | Realized in |
|---|---|---|
| `∇²S` semantic curvature | ambiguity vs stable identity | `significance.py` (Ollivier-Ricci curvature → significance) |
| `∇E` affect change | emotional instability | `density_emotion.py` (Lindblad evolution) |
| `Π` projection / `Π⁻¹` recovery | representation change, identity tracked | `projection_stack.py`, `holographic.py` |
| resistance `R = 1 − \|I_out\|/\|I_in\|` | where identity was degraded | `chiron` residual + `cross_examine.py` |

## 4. Orientation and the six epistemic operators

Every operation carries orientation: `σ = +1` forward (away from the invariant), `σ = −1`
recovery (toward it). Recovery is not mere inversion — it carries the opposite informational
orientation.

Reasoning itself is six operators acting on a **Mystery Vector** (the six species of the
unknown): Measure→ignorance, Reframe→paradox, Invent→transcendence, Model→emergence,
Dialogue→subjectivity, Explore→infinity. Realized in `operator_calculus.py` over
`cert_engine`'s `EpistemicOperatorAlgebra`: it reads a finding into the Mystery Vector, names
the dominant unknown, prescribes the operator that reduces it, and runs the reduction
sequence — progressive elimination of the unknown.

## 5. The principle (Chiron, in one line)

Chiron does not classify; it **recovers continuity**. The highest-confidence interpretation is
the one that minimizes cumulative projection resistance and representational curvature,
preserves identity under forward and inverse transformation, and survives perturbation across
every substrate. `discernment.py` is that principle assembled: independent witnesses over the
substrates, confidence by convergence.

## 6. Honest scope

This is a *language for organizing the engines that already exist* — a clean front-end over
`chiron.py` and the `cert_engine` bridges. It is deliberately **not** a pivot to "a new
mathematics." Where a glyph maps to a tested module, it is real; where it is only notation,
it is labeled as such.
