# Exploration — how the engines work off each other, and what that opens

*A working note, grounded in the actual code paths (function names cited) and one
live probe, not the marketing. It maps the precise couplings between Chiron's engines
— where one engine's output becomes another's input — and the capabilities those
couplings open. Exploratory: nothing was changed to write it.*

---

## 0. The spine: one pipeline runs all the engines in order

Everything funnels through `Chiron.assimilate()`. In a single pass it:

```
ingest_text → process_record (certificate) → _engine_read = collapse (invariant engine)
   → _form_domain (file by subject) → record_growth (classify + reuse + cross-domain)
   → congress.seal (Merkle root) → human_report (what/why/falsify) + articulate (codec)
```

So the invariant engine, the certifier, the memory/Congress, the twin/transfer logic,
the wisdom report, and the codec are not separate programs you wire together by hand —
they are **one composition that already fires on every input**. That is the thing
worth understanding precisely, because the *couplings* are where the leverage is.

## 1. The keystone coupling — a fingerprint binds invariant + twin + memory

`record_growth()` is where three engines meet. When `collapse` verifies a rule it
produces two domain-agnostic fingerprints — `family_fingerprint` (model class +
structure) and `generator_fingerprint` (class + parameters). `record_growth` uses them
as the join key:

- **Reuse is O(1).** If `generator_fingerprint ∈ _gen_seen`, the law is recognized
  instantly — no re-derivation. Learning compounds instead of repeating.
- **Cross-domain transfer is automatic.** If a `family_fingerprint` first seen in
  domain A reappears in domain B, that *is* a cross-domain transfer — detected for
  free, because the fingerprint doesn't carry the domain.
- **It is governed.** Transfer only fires if the source domain's membrane is not
  `sealed` (`self.membranes`), so a private domain can be walled off and the
  composition respects it.

This is the single most important door: **a rule proven in one subject is reused or
recognized as a twin in any other, at zero extra cost.** It is what makes the whole
thing more than a calculator.

### Proof (live, this session)

Feeding the *same* generator under two different subjects:

```
assimilate "1 1 2 3 5 8 13 21 34"  domain=mathematics  -> integral
assimilate "1 1 2 3 5 8 13 21 34"  domain=biology       -> integral,
                                    cross_domain_transfer=True, reused=True
grow_concepts -> minted 1: concept:… spans [biology, mathematics] (linear_recurrence_order2)
```

The certificate and the spoken-back articulation were produced in the same pass. The
coupling is real and demonstrated, not theoretical.

## 2. Memory → self-growth: concepts minted from proof only

`grow_concepts()` reads `_fam_domain_sets` and mints a named **concept** for any
family verified in **≥ 2 distinct domains** — and *only* from already-verified laws.
That is the precise reason it "can't run buck wild": its self-extension is a function
of proof, not generation. The door: the system grows its own cross-domain ontology
(it names the abstract shape it keeps re-finding) without inventing anything unproven.

## 3. collapse ⇄ articulate: the codec runs both ways

`collapse` recovers a generator; `articulate` pushes a generator back *up* into a
surface (regenerate, extend, or re-voice into a new vocabulary), reporting round-trip
fidelity and carrying the source author. Coupling the two opens **synthesis, not just
analysis**: recover a rule in domain A, `cast` it into domain B's vocabulary, emit new
valid surfaces (the Caramuel "multiform labyrinth" generation; cipher-key transfer;
sequence extension).

## 4. Everything → certifier + wisdom: knowledge that audits itself

Every `assimilate` emits a certificate via `human_report` (*what was discovered, why
it is believed, what would falsify it*) over the engineer appendix, sealed into a
Merkle root, with the provenance source added to `ingested_sources`. The wisdom layer
(Candor) scores explanations and — through its "bridge" (Phase-5 epistemic export) —
makes provenance the cure for opacity. The door: a knowledge base where **every item
is reproducible and auditable by construction**, and the system can't quietly become
opaque as it grows.

## 5. Memory ↔ memory across instances: the swarm

`merge_laws()` unions another organism's verified laws **idempotently and
order-independently** — pooling intelligence without sharing raw data. Composed with
the public/private grow split, this is the door to a **federation**: many Chirons
(your private grow, the public grow, contributors) converge on a shared law library
while private domains and raw corpora never leave home.

## 6. Growth that never bloats

`compact()` keeps the durable core — every integral generator, domain summaries, bank
balances, the owner-signed root — and trims only raw bulk. Coupled with the grower's
auto-compaction, this opens **unbounded growth at bounded size**: the Congress can
ingest forever because what it keeps is generators, not transcripts.

## 7. The outward-facing engine, on a leash

The executive (President) is the only engine that reaches the world; it runs an OODA
loop, clears every decision through the Candor gate, bounds its action set, and
escalates anything irreversible. Self-modification has the same shape:
`apply_proposal` applies a self-patch **only** behind a reversible checkpoint and a
GREEN selftest, autonomous only under `CHIRON_ALLOW_SELF_EDIT=1`. The door: you can
let it *act* and even *edit itself* with bounded, provable safety.

## 8. Two newer couplings

- **Infectatrum ⊗ Chiron** (just built): Infectatrum measures the *reading spectrum*
  (ambiguity, entropy) of a structure; Chiron `collapse`s the *generator* beneath it.
  Run on one shared atlas, you get ambiguity quantification **and** exact rule
  recovery on the same object — two readings of one surface.
- **Field substrate (UMA / `FieldPosterior`)**: a Kalman-style Gaussian posterior with
  `predict`/`update`/friction provides the certification *dynamics* (world-model
  propagation under uncertainty). Honest framing: this is present in the same file and
  feeds the certification path, but the **tight** loop today is the exact-symbolic
  `assimilate` pipeline; deep coupling between exact-symbolic recovery and the
  probabilistic field layer is more available than exercised — a real frontier (§10).

## 9. The doors, summarized

1. **Learn once, reuse everywhere** — domain-agnostic fingerprints make transfer free
   and O(1) (§1, proven).
2. **It names its own cross-domain invariants** — concepts from proof only (§2).
3. **Analysis becomes synthesis** — the codec generates and transfers (§3).
4. **Self-auditing knowledge** — certificate + provenance + Merkle on every item (§4).
5. **Federation without data-sharing** — idempotent law merge (§5).
6. **Forever-growth, bounded size** — keep generators, trim raw (§6).
7. **Bounded action and self-edit** — gated executive + selftest-gated self-patch (§7).

## 10. Untapped compositions (where exploration could go)

- **Atlas-wide collapse → cast → certify**: generate *new* labyrinths/verses in a
  target language from recovered generators, each certified — Caramuel's own goal,
  automated end to end.
- **Concept mining over the full grown Congress**: run `grow_concepts` across math +
  law + Primus + code at once and let it surface families that span genuinely
  different subjects — the system reporting its own cross-domain invariants at scale.
- **A real swarm run**: two grows (public + private) that periodically `merge_laws`,
  demonstrating federation, not just supporting it.
- **Candor over the grown corpus**: audit every certificate the grower emits, flagging
  any that drift toward over-confidence or opacity — the wisdom layer policing growth.
- **Directed recovery + field posterior**: fold an operator's expected answer
  (`collapse_guided`) into a world-model propagated under uncertainty — a genuine
  decision-support loop, and the place the symbolic/field coupling (§8) would become
  real rather than parallel.
- **fastops/WASM in the dashboard**: native scansion/enumeration in-browser closes the
  proteus upper-bound gap from `PRIMUS_EXPLORATION.md` and makes the couplings live on
  a page.

## 11. The honest frame

What is tightly wired and demonstrated: the `assimilate` spine, the fingerprint-keyed
reuse/transfer, concept minting from proof, the codec, the certificate/Merkle trail,
idempotent law merge, bounded self-edit. What is present but loosely coupled: the
probabilistic field substrate vs. the exact-symbolic core — they share a file and a
certification story more than a tight runtime loop. The biggest unrealized value is
not a new engine; it is **running the couplings that already exist at full scale** —
the atlas, the swarm, the concept mining — and tightening the one loop (symbolic ⊗
field) that is currently more architectural than exercised.
