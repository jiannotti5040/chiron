# The Semantic Invariant Calculus in Chiron

*Chiron's spine — MDL minimal-generator recovery in exact arithmetic, certified by exact
held-out prediction, refused (`INCOMPRESSIBLE`) rather than laundered — lifted from integer
sequences to **meaning**. Pure standard library (`fractions.Fraction`, `decimal.Decimal`,
`itertools`, `hashlib`): no numpy, fully airgappable — the "dictionary" implementation the
architecture calls for. Engine: `semic.py` (56/56 gates; exact O(N·m) separable collapse, typed
classes H1–H5, constraint discovery). Chiron-side surface: `semic_bridge.py`; energy layer:
`semic_energy.py`.*

---

## Why it belongs in Chiron

Chiron asks *"what exact rule generates this surface?"* and refuses to guess. The Semantic
Invariant Calculus asks the identical question of language: given a family of surface
phrases, *what is the shared generator — the proverb with the English removed?* — recovered
by `argmin` over an exactly enumerable candidate space, and **refused** when the family shares
no invariant. Same discipline, same zero-false-positive gate, new domain.

```
"give a man a fish ... teach a man to-fish ... a lifetime"   ┐
"grant a person seed ... instruct a person to-build ... always" ┘
        │  collapse (MDL argmin over the exact subset lattice)
        ▼
   { TRANSFER → BOUNDED , CONSTRUCT → UNBOUNDED }     (the invariant; held-out-verified)
```

## Every piece, and where it lives

| Semic construct | What it is | In the system |
|---|---|---|
| `skeletonize` / `surface_skeleton` | text → role-edge set (`OPERATOR(object)→HORIZON`), a fixed inspectable lexicon+word-order rule, not a model | `semic.py`; complements `language.py`'s distributional layer |
| `collapse` / `L` / `residual` / `energy` | MDL two-part code over the exact candidate lattice — Chiron's `collapse`, lifted | `semic.py`; mirrors `chiron.collapse` |
| `certify` (held-out, exact) → `Verdict` | leave-one-out exact-equality gate; else `INCOMPRESSIBLE` | `semic.py`; `semic_bridge.recover` |
| Gibbs bridge (`gibbs`, `bridge_mass_on_argmin`) | deterministic MDL collapse = T→0 limit of the Gibbs sampler — one operator, two temperatures | `semic.py`; `semic_bridge.bridge_theorem`; ties to `density_emotion.py` |
| Class I–VIII taxonomy | representation / multiplicity / structural / recursive / temporal / domain / cognitive / **performative** as deterministic predicates | `semic.py` |
| Ollivier-Ricci curvature (exact `W₁` min-cost flow) | collapse-landscape geometry; attractor (proverb) vs fork (entendre) | `semic.py`; complements `significance.py` |
| **Signed** curvature (Congress barbell vs clique) | entendre = **negative-curvature bridge**; proverb = **positive-curvature clique** — exact, sign-bearing ambiguity | `semic_bridge.ambiguity`; complements `infectatrum_bridge.py` |
| Performatives / felicity (`World`, `perform`, Class VIII) | Austin speech-acts: an utterance with unmet preconditions **misfires** | `semic_bridge.felicity`; the semantic root of `govern.py`'s authority/ROE gate |
| Functors / naturality (Class VI) | `collapse(φ(s)) = collapse(s)`: domain-invariance as a verified naturality square | `semic.py` (`collapse_natural`) |
| Candor = epistemic conservation | reports discarded residual; self-audits reported == recomputed | `semic.py`; mirrors `candor_bridge.py` |
| Congress = a category | objects = surfaces, morphisms = recoveries; identity/composition/associativity verified | `semic.py`; mirrors Chiron's Congress |
| Compression ratio + free energy | ≈38× on the fish family; `F(T) → min E` (MDL) as `T→0` | `semic.py` |
| Action principle | the collapse trajectory is the least-action geodesic to the invariant | `semic.py` |
| Twin proof | maximally different surfaces → one generator over a combinatorial space (Caramuel anchor, lifted) | `semic.py`; `semic_bridge.twin`; ties to `discover.py` / Primus twins |
| Multi-family + meta-refusal | distinct phrase families certify within themselves; cross-family pools **refused** | `semic.py`; `semic_bridge.families` |
| Role induction / codec / analogy / idiom / cross-lingual | bootstrap roles from pools; `collapse(articulate(P))=P`; analogy transport; idiom vs literal; en/es invariance | `semic.py` (gates G36–G48) |

## The bridge surface (`semic_bridge.py`)

`recover(*phrases)` (invariant + certificate), `ambiguity()` (signed-curvature entendre/proverb
split), `felicity(act, arg, …)` (Class VIII → governance precondition), `bridge_theorem()`
(Gibbs T→0), `twin()`, `families()`, and `semantic_brief(*phrases)` — the meaning-domain
parallel of `actionable_intelligence.py`. Self-tested (14/14), zero-dependency.

## Role tagging and determinism

`skeletonize` is a deterministic lexicon + word-order rule. This preserves reproducibility and
airgapped operation, at the cost of covering only the phrase families it defines rather than
arbitrary prose. Any role-tagging that draws on an external model is confined to an optional
grow-stage adapter that proposes candidate role tags; the deterministic MDL gate remains
authoritative and certifies or refuses independently. The certified core carries no external
dependency.

## Limitations

`skeletonize` is a lexicon, not a parser; the role ontology is hand-built for the demonstrated
families; the two curvature readings (collapse-hypercube and Congress-graph) are complementary
and not yet unified. The entire pipeline is one deterministic function of the input text: two
independent runs recover identical invariants, verdicts, curvatures, and actions to the exact
`Fraction`.
