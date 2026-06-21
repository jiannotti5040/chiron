# Exploration — the Primus document, and native-language backing

*A working note, not a deliverable. Exploratory: nothing in the engines was changed
to produce it. It maps what Caramuel's* Primus Calamus *can still give the project,
what each unlock costs, and what C/C++/Rust would actually buy.*

---

## 1. What the source actually is

The file you added — *Ioannis Caramuelis Primus Calamus ob oculos ponens
Metametricam* (Rome, 1663) — is the **complete 888-page, 54 MB scanned facsimile**.
Its own title page is the system specification: *Metametrica*, which adorns
"multiform labyrinths" with verse-leads that are **currentium** (running forward),
**recurrentium** (retrograde / cancrine), **adscendentium** and **descendentium**
(ascending / descending acrostics), and **circumvolantium** (circling / spiral).
It is, literally, a combinatorial computer printed on paper in 1663.

One hard fact up front: the PDF is a **scanned image**, not digital text —
extraction yields ~70 characters of garbage per page. So "decoding the rest" is not
a parsing problem; it is an **OCR / transcription** problem followed by a
combinatorics problem. That distinction drives everything below.

## 2. What the project already has (more than I expected)

- **Chiron already contains the full labyrinth machinery**, not just two hardcoded
  poems. Inside `chiron.py`: a `FigureGraph` substrate (non-rectangular labyrinth
  topology — nodes carry tokens, named *walks* are the ductus paths exactly as
  Caramuel prints them), a ductus registry for the five title reading-paths,
  `op_proteus()` (proteus-verse permutation), and — importantly — a **real native
  Latin dactylic-hexameter scanner** (`scans_as_hexameter`, the "S8 meaning gate",
  CLTK-accelerated when present, pure-Python otherwise). So the engine can already
  *collapse* a labyrinth, *generate* permutations, and *meter-validate* the results.
- **Infectatrum already holds a transcribed atlas of 21 plates** (TAB XIII–XXXIII)
  as graph-JSON with per-node confidence and source scans, across six modes (Latin,
  Greek, Spanish, Chinese, musical notation, pictorial rebus). Each plate's
  `figure` block is `{tokens, walks}` — the *exact* shape Chiron's collapse expects.
- **Chiron itself only uses two of those plates** (TAB XXVI/XXVII, the IESUS SOL /
  MARIA STELLA twins) as built-in ground truth. The other 19 have never been run
  through Chiron's collapse / same-origin / cast / articulate / certificate path.

That last line is the headline: **most of the transcribed system is already on
disk and simply isn't wired into the flagship.**

## 3. A live probe (run during this exploration, not theory)

Feeding each Infectatrum plate's `figure` block straight into `chiron.collapse()`:

- **All 21 plates collapse and verify** as `labyrinth_topology` (node counts 8–39,
  3–8 ductus walks each).
- Running `same_structure` across every pair, Chiron flags **exactly one** twin
  pair — **TAB XXVI ⇔ XXVII** — and treats the other 19 as structurally distinct.

That is a genuine result: with a ~10-line adapter and no engine change, Chiron
operates on the entire transcribed atlas and *independently rediscovers* the one
famous twin pair while correctly declining to over-merge the rest. The machinery is
proven; the gap is wiring, not capability.

```python
# the entire adapter that produced the result above
import json, glob, chiron
for p in sorted(glob.glob("Infectatrum/corpus/plate_0*.json")):
    fig = json.load(open(p)).get("figure")
    if fig and "walks" in fig:
        inv = chiron.collapse(fig)          # FigureGraph path, already in the engine
        print(inv.model_class, inv.verified, inv.structure["n_nodes"])
```

## 4. What is still untapped — and what each costs

**(A) Wire the 21-plate atlas into Chiron — cheap, high value.**
A small `primus_atlas.py` (the probe above, hardened) gives: collapse + certificate
per plate, cross-plate `same_generator`/`same_structure`, `cast` (move a plate's
generator onto a new vocabulary — Caramuel's own goal), and `articulate`
(regenerate the verses). Effort: hours. Risk: none (additive, reuses proven paths).

**(B) Count and generate the verses — the "run his machine forward" unlock.**
Each plate has a finite, exact **valid-verse yield** (the twins' famous
2.8 × 10¹⁷ is one such number; the other 19 are uncounted here). Using `op_proteus`
+ `scans_as_hexameter`, Chiron can enumerate or sample the readings a plate admits
and keep only those that scan — turning a static transcription into a generator.
Effort: low-moderate (machinery exists; needs a driver and per-plate lexicon care).

**(C) Cross-language structural twins — a real research question.**
Caramuel's implicit claim is that the *labyrinth* is language-independent. The atlas
spans six modes, so we can ask Chiron whether a Latin plate and a Chinese or musical
plate share a topology (a `same_structure` match across languages). The probe found
only the Latin XXVI/XXVII pair, but a deliberate study (normalizing topologies
before comparison) could surface or refute cross-mode twins. Effort: low; payoff:
genuinely novel and on-brand for the "one rule wearing many disguises" thesis.

**(D) The other ~866 pages — the deep, expensive frontier.**
The plates are the labyrinths; the rest of the book is the *treatise*: proteus-verse
worked examples, combinatorial tables (Caramuel was an early combinatorialist —
permutation/combination counts predating the usual histories), cancrine verses,
numeric/gematria schemes, and the Metametrica theory itself. Unlocking these needs
**OCR of 1663 Latin** (hard — mixed roman/italic, ligatures, math tables; general
OCR fails, and Latin-specific HTR is a project of its own) *or* targeted
hand-transcription of the highest-value pages. Pragmatic path: don't OCR 866 pages —
hand-transcribe a handful of marquee items (e.g., the classic proteus verse *"Tot
tibi sunt dotes, Virgo, quot sidera caelo"*, whose ~1022 scanning permutations
Chiron could reproduce exactly) and let those stand as showcases. Effort: high if
exhaustive, low if curated.

## 5. Would C / C++ / Rust help? Honest assessment

**Where native code genuinely helps:**
- **Proteus / verse enumeration + scansion at scale.** `op_proteus` is capped at
  5040 permutations today; real proteus spaces run 10³–10¹⁷. *Counting* is
  closed-form (no enumeration needed), but *generating, sampling, and
  meter-validating* millions of candidate verses is CPU-bound and embarrassingly
  parallel — a Rust kernel would be 10–100× and is the single biggest native win
  for the Primus direction.
- **Large-labyrinth / large-graph invariants** (Weisfeiler-Leman refinement, matrix
  walks) are pure-Python today; native helps once plates or graphs get big.
- **Bulk cipher cracking + English scoring** over large corpora.
- The **poly-degree hot path** is *already* an optional embedded-C kernel with a
  Python fallback — the pattern to copy.

**Where it does *not* help (important, so effort isn't wasted):**
- The **exact-arithmetic MDL core** runs on Python `Fraction`, which is already
  CPython's C big-integer layer; rewriting it buys almost nothing.
- The **field-cognition layer** already rides numpy/scipy (C/Fortran).
- The **grower** is network/IO-bound; native compute is irrelevant there.

**Recommendation: Rust, optional, behind the existing fallback pattern.** Add a
`chiron_fastops` Rust crate compiled on first use to a shared library beside the
script, with the pure-Python path always present — identical in spirit to the
current optional-C kernel, so the zero-install single-file property is never lost.
Rust over C/C++ because: memory safety (no UB in a portfolio engine), first-class
combinatorics and `num-bigint`, reproducible `cargo` builds, and — the kicker —
**Rust → WASM** would let the offline dashboard run real `collapse` and scansion
*in the browser*, which is a standout demo nothing else here offers.

**The honest caveat:** native backing is an **accelerator**, not a capability
unlock. The core value — exact recovery, honest abstention, zero false positives —
is bounded by *hypothesis-class coverage and transcription*, not by speed. So Rust
is worth it for "run Caramuel's machine forward at scale" and the WASM dashboard;
it is *not* worth it for the math core, and it must stay optional.

## 6. If you want to pursue it — ranked by value ÷ effort

1. **Wire the 21-plate atlas into Chiron** (`primus_atlas.py`). Proven feasible
   today; turns 2 plates into 21 and gives cross-plate twins + certificates. Hours.
2. **Per-plate verse count + generation** via `op_proteus` + the native scanner.
   Makes the transcriptions *live*. Low-moderate.
3. **Cross-language twin study** across the six modes. Novel, on-thesis. Low.
4. **A Rust `fastops` crate** (proteus/scansion/WL) with Python fallback, and a
   WASM build for the dashboard. Moderate; the scale + demo win.
5. **Curated transcription** of marquee non-plate items (the *Tot tibi* proteus
   verse; one combinatorial table). High value as showcase, but gated on hand
   work or Latin HTR — the only genuinely expensive item here.

Items 1–3 are essentially free given what already exists. Item 4 is the native
question answered concretely. Item 5 is the real frontier and the only one that
needs the 1663 pages themselves.

## 7. Built in this session (all five)

All five were implemented as additive tools — the engine (`chiron.py`) was not
changed, and its self-test stays green. They live in both `Chiron/` and
`Chiron-Refined/`.

```bash
python3 primus_atlas.py        # (1+3) collapse all 21 transcribed plates; cross-plate twins
python3 primus_verses.py       # (2)   run the labyrinth forward; proteus + scansion
python3 -c "import chiron,json; print(chiron.collapse(json.load(open('primus_extra/combinatorial_table.json'))['factorial']).model_class)"  # (5)
python3 fastops.py             # (4)   native hot-path self-test (pure-Python fallback here)
```

Results observed: **all 21 plates collapse and verify**; `same_structure` isolates
**exactly** the TAB XXVI⇔XXVII twin; the curated factorial table collapses to
`multiplicative_ratio` (verified); the proteus run is reported honestly as a
coarse-scanner **upper bound** (the motivation for the native strict scanner). The
Rust crate `chiron_fastops/` builds where `cargo` exists (cdylib + a WASM target);
`fastops.py` falls back to exact pure-Python everywhere else and agrees with the
engine's own `poly_degree`. Curated marquee items are in `primus_extra/`, marked as
hand-entered, not OCR. The remaining frontier is unchanged: page-level OCR of the
1663 source and a strict scanner to turn the proteus upper bounds into true counts.
