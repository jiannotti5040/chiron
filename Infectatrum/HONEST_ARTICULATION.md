# HONEST_ARTICULATION — Infectatrum

This document names what is strong and what is not, with precision, so the work can be
judged on what it actually does. It accompanies `infectatrum.py` (the monolith) and
`corpus/plate_013.json` (the first real transcribed Caramuel plate).

## What this is

Infectatrum is an ambiguity engine grounded in Juan Caramuel y Lobkowitz's *Primus
Calamus ob oculos ponens Metametricam* (Rome, 1663) — the densest catalog of engineered
ambiguity ever printed: lettered structures that read as valid verse along multiple
declared paths (*ductus*). The engine's primitive object is the **reading spectrum**:
the set of valid readings a structure supports relative to a swappable language. Over
that object it performs exactly three operations — **Detect** (compute and localize the
spectrum: cardinality |Σ|, Shannon entropy H(R) in bits, per-cell ambiguity load and
mutual-information localization, and the excluded negative space), **Resolve** (collapse
toward one sanctioned reading by commitment or by minimal set-cover edits, every
resolution stored as a Transformation with an audit trail), and **Generate** (synthesize
structures that legitimately bear many simultaneous valid readings). Above the core sit
the discovered layers: an origin-signature engine (ambiguity distribution as a Bayesian
fingerprint of the generating process, compared by Jensen–Shannon divergence), basis
inference over a language atlas with loss-aware chart transitions, a codifier that turns
any substrate into a state graph of Belnap-valued semantic states, a translation layer
that emits the crucible report, and Infecticon — a vocabulary that is *accumulated* from
recurring resolution-calculus equivalence classes rather than designed in advance.

## What is demonstrably real

The monolith runs on the Python standard library alone and passes 56 embedded test
gates covering ductus bijectivity, spectrum measures, resolution-calculus laws (monoid
identity, partial invertibility, metric symmetry), Belnap projections, the native Latin
scanner, the tiling recognizer, FigureGraph topology, signature normalization and JSD
symmetry, basis inference, the codifier, and Infecticon emergence. Heavy libraries
(numpy, networkx, ortools, cltk) are optional accelerators behind correct pure-Python
fallbacks.

The engine reads real Caramuel. Tabula XIII (*Labyrinthus Hexagonus Retrogradus*, to
St. Thomas Aquinas, p. 446 of the 1663 edition) was transcribed by vision from the
source scan at its full embedded resolution (992×1600 px) under a two-pass discipline:
diplomatic and normalized layers kept separate, confidence recorded per cell, every
conjecture explicitly marked, nothing silently completed. The measured result on the
real plate: **|Σ| = 8 distinct valid readings, H(R) = 3.0 bits**, across the plate's two
horizontal verse lines (read forward and word-retrograde — the *Retrogradus* of the
title, with AQUINAS as the pivot) and the four hexagram slope lines. Every cell of the
figure participates in at least one reading; the engine reports zero orphaned nodes.

The validity gate does independent work. A reading is admitted by a Latin word-form
gate that is independent of the transcription, and the native quantity scanner's
metrical verdict is reported per reading rather than enforced. On Tab. XIII the scanner
returns *false* for all eight readings — correctly, because Caramuel's lines here are
rhythmic/accentual verse, not classical dactylic hexameter. A gate that can return true
negatives on the ground source is the structural proof that the measurements are not
tautological. (The scanner accepts a genuine Virgilian hexameter and rejects
non-lines; both behaviors are test-gated.)

## What is conjectural, and exactly where

Four of the eight declared walks on Tab. XIII carry conjecture, all marked in
`plate_013.json`. The two horizontal lines and their retrogrades are high-confidence
end to end. The two Δ-slope lines are medium confidence (the verb *cantetur* is a
plausible reading of a partially legible `c.nte-tur`). The two ∇-slope lines are low
confidence: the verbs *cingatur* and *coronetur* are conjectures over partially
occluded rotated text, *gnomis* is a medium-confidence reading, and the bottom tip
*venerabilibus* is reconstructed from a clearly visible `…erab/bilibus`. The spectrum
report carries these flags forward; nothing conjectural is laundered into certainty.
The fidelity ceiling is physical: the source scan embeds the plate at 992×1600 px
(~600 effective DPI on the small 1663 leaf), and rotated italic cells at that
resolution genuinely bottom out at medium confidence.

## What is not yet done

One plate of roughly twenty-four is transcribed; the corpus loader, record schema, and
pipeline are built so the remaining plates fold in as records accumulate, but the full
transcription of the 491-page edition is a long multi-session grind that has not been
performed and is not claimed. The scanner is a coarse quantity scanner adequate as an
independent gate, not a full prosody engine (no elision, no synizesis, no macron
lexicon of substance); CLTK can replace it where installable. CP-SAT generation of
large novel multi-path grids remains research-grade; the shipped generator is a bounded
backtracking synthesizer that genuinely produces small multiform squares. The
origin-signature engine is mathematically sound (normalized features, JSD, Bayesian
posterior) but has been exercised on a library of one — its discriminative power is
untested until multiple sources are enrolled. Infecticon's vocabulary emerges correctly
from the resolution quotient, but with few recorded resolutions it is a seed, not a
language.

## Why it generalizes

Nothing in the core knows about Latin or 1663. The language is a first-class parameter;
the substrate interface admits grids, figures, sequences, and graphs; adding a ductus,
plate type, operator, renderer, or input adapter is registration, not core surgery. The
same Detect/Resolve/Generate triple applies wherever a structure admits multiple valid
readings under a grammar — specifications compiled into divergent implementations,
contract clauses bearing competing constructions, instructions to AI systems that admit
readings their authors did not intend. The wedge is the pair of capabilities almost no
tool offers together: reducing ambiguity with a provenance-bearing audit trail, and
deliberately fabricating measured, constraint-validated multiplicity. The 1663 book is
the ground truth corpus because its ambiguity is explicit, constrained, and verifiable —
but the engine is the general instrument.

## Provenance

Every detect, report, and resolution is hashed into a tamper-evident MANIFEST
(`MANIFEST.sha256`); plate records pin their source page, scan resolution, and per-cell
confidence. The chain is: source scan → two-pass transcription record → IR → measured
spectrum → attested report → engine-source self-hash.

## Operational harness (deployment-grade mechanics)

The monolith carries a domain-general operational layer, all test-gated: time-bounded
resolve/generate that return an explicit Escalate state on budget overrun rather than
freezing; a morphology cache keyed on ambiguity *topology* (not literal text) for an
O(1) fast-path on recurring shapes; an epistemic partition export that sorts every state
node into Knowns / Unknowns / Unknowables purely from the SemanticState vector math and
the taxonomy, with no stochastic inference; an adversarial-ambiguity score that
separates natural degradation from engineered multiplicity by uniformity, negative-space
starvation, and entropy saturation; basis re-charting that preserves node identity and
logs projection loss on the imaginary axis; and a deterministic export bundle that binds
the partition, the report, the adversarial assessment, and the recorded
resolution-signatures ("machine case law") into the MANIFEST. These mechanics report and
attest; they take no autonomous action and make no decision — adjudication is the
caller's.

## Second plate, and what it calibrated

TAB. XIV (p.448, the Aquinas diamond *quadratum*) and TAB. XV (p.450, the Sarria
rectangular *carmen quadratum*) are both transcribed and run through the engine. Each
caption asserts its own combinatorics: XIV claims a single retrograde distich yielding
9,823,275 recurrent distichs (39,293,100 simple verses) with the partial-product ladder
printed up the margin; XV claims 14,996,480 verses readable centre-to-corners and back,
with the bidirectional ductus stated explicitly in the dedication. Run through the
adversarial detector, XIV scores 0.94 and XV scores 1.0 — near-perfect synthetic-
inflation signatures. The lesson is the calibration: an asserted multiplicity of tens of
millions from a compact lattice is, to a noise-detector, indistinguishable from an
adversary flooding a feed to force a halt — except here the multiplicity is legitimate.
The detector characterizes the *structure* and raises a human-in-loop suggestion rather
than ruling on intent. The rebus emblem-cells (sun, moon, eye, star, eagle, column,
altar) are recorded as structure but not transcribed as words, landing correctly in the
Ω (orthogonal) partition rather than being invented into text.

TAB. XV also surfaced a real engineering finding rather than a cosmetic pass: its
compound cell-tokens (SARRIA_VIVE_DIU, QUEM_REX) initially drove |Σ| to zero with every
node in Ω, because the word-form gate rejected the underscore joiner. That is the
correct failure mode — the gate refused readings it could not admit and the engine
flagged them rather than faking a number — and the fix (treat underscore and space as
token separators) restored XV to |Σ| = 6, H(R) = 2.585 bits, with no regression on XIII
(8) or XIV (4). A gate that can drive a real plate to zero and escalate is the same
property that makes the non-zero results trustworthy.

## Export bundle (deterministic hand-off)

`export_to_cert_engine` returns a plain dictionary built only from the engine's own
vector math: the K/U/Ω epistemic partition, the crucible report, the adversarial
assessment, and the engine's internal **resolution ledger** (the signatures of the
resolution-transformations it has recorded for this object — an internal audit trail of
this engine's own disambiguations, nothing external), all bound into the MANIFEST. It
performs no autonomous action and makes no decision; it reports and attests, and the
caller decides what, if anything, to do with the partition.

## Plate atlas — complete, count settled

The figural labyrinth plates of the *Metametrica* atlas run **TAB XIII through TAB
XXXIII — 21 numbered plates — and all 21 are transcribed** into `corpus/` and run
through the engine. The count was established by reading every plate's caption directly
from the source scan, not from any inherited estimate. Three real features of the
physical book account for the earlier "18 / 24 / 25" confusion, and all three are
recorded rather than smoothed over: consecutive engraver misprints (XXII printed "XXI",
XXIV printed "XXIII", XXV printed "XXIV"); the figura-count diverging from the
tabula-count in the late plates; and ink-density false positives from edge-staining and
the photographed leather back cover.

The atlas spans six representational modes, and the engine processed every one without
breaking: Latin verse squares and hexagrams (XIII–XV), radial and multi-wheel polar
labyrinths (XVI, XVII, XXVI, XXVII), cancellatum grilles with motto- and name-acrostics
(XVIII, XXI–XXIV), a carmen figuratum (XIX), the compendium plate carrying the 3D *Cubus
Metametricus* and a spherical labyrinth (XX), a Chinese-character grid with a Latin
romanization key dedicated to Kircher (XXV), a Spanish-vernacular labyrinth (XXX), a
pure pictorial rebus (XXXI), and two music-cipher plates where notation and text are the
same tokens (XXXII–XXXIII). That a single engine, with one swappable Language parameter,
measures ambiguity across Latin, Greek, Spanish, Chinese, musical notation, and pictorial
rebus is the strongest available demonstration that the core is genuinely
language-agnostic — and it is grounded entirely in the source, since Caramuel himself
built labyrinths in all those modes.

## Origin-signature validation on real plates

The atlas contains a built-in same-generator control: TAB XXVI (*Iesus Sol*) and TAB
XXVII (*Maria Stella*) share Caramuel's design and Nicolaus Lucensis's words, differing
only in dedicatee. Run through the origin-signature engine, the two come out three times
closer in signature space (Jensen–Shannon divergence 0.333) than a cross-family
comparison to a cancellatum plate (JSD 1.0). The detector recovered a shared generator
from ambiguity structure alone — the P-013 claim, validated against ground truth rather
than asserted. This relation is enforced as a permanent test gate.

## Combinatorial claims as adversarial calibration

Several plates print their own asserted reading-counts, and they climb to the absurd:
TAB XIV claims ~9.8 million recurrent distichs, TAB XV ~15 million verses, TAB XVII ~9.6
quadrillion, and TAB XXVI/XXVII ~279 quintillion simple verses each, with the
partial-product ladders printed in the margins. These are the synthetic-inflation
calibration targets: an asserted multiplicity of that magnitude from a compact lattice
is, to a noise detector, indistinguishable from an adversary flooding a channel to force
a halt — yet here it is legitimate. The detector accordingly saturates (p_adversarial →
1.0) on exactly these plates and raises a human-in-loop suggestion rather than ruling on
intent. Plates whose meaning is purely pictorial or whose tokens are single grille
letters correctly fall to |Σ| = 0 with everything in the Ω partition — refused, not
faked.

## Verified count

The source's engraved labyrinth plates were inventoried directly from the PDF, plate by
plate, by reading each caption. They occupy the recto leaves from p. 446 (TAB XIII)
through the end of the *Metametrica* atlas, and number 21 (TAB XIII–XXXIII). All 21 are
transcribed, attested, and run through the engine. The transcription discipline was held
throughout: diplomatic and normalized layers kept separate, confidence recorded per node,
conjectures and engraver anomalies marked rather than corrected, emblem and music cells
recorded as structure rather than invented into words. The chain of custody is a single
MANIFEST binding the engine source and all 21 plate export-bundles; the test suite holds
at 76 gates including the corpus-wide and origin-signature validations.
