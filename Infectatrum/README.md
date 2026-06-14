# Infectatrum

A universal ambiguity / coherence engine, grounded in Juan Caramuel's *Primus Calamus
ob oculos ponens Metametricam* (Rome, 1663) — a 17th-century combinatorial computer
printed on paper.

## What it does

Its primitive object is the **reading spectrum**: the set of valid readings a structure
supports under a swappable Language. Over that object it performs three operations —
**Detect** (measure and localize the spectrum: |Σ|, Shannon entropy, mutual-information
localization, negative space), **Resolve** (collapse toward one reading by commitment or
minimal set-cover edits, with a full audit trail), and **Generate** (synthesize
structures bearing many simultaneous valid readings). Above the core sit the discovered
layers: origin-signature attribution, basis inference, the codifier, the translation
layer, and the emergent Infecticon vocabulary; plus an operational harness (time-bounded
solvers with an Escalate state, a topology-keyed cache, a deterministic K/U/Ω epistemic
export, an adversarial-ambiguity detector, and a tamper-evident MANIFEST).

## Run it

```
python3 infectatrum.py test      # 76 self-test gates
python3 infectatrum.py demo      # core engine on the SATOR fixture
python3 infectatrum.py plate --path corpus/plate_013.json   # one real plate
python3 infectatrum.py corpus --dir corpus                  # the whole atlas
python3 infectatrum.py attest --out MANIFEST.sha256         # rebuild attestation
```

Runs on the Python standard library alone; numpy/networkx/cltk/ortools are optional
accelerators behind pure-Python fallbacks.

## What's here

- `infectatrum.py` — the complete monolith (~1900 lines, 76 test gates).
- `corpus/` — all 21 transcribed labyrinth plates (TAB XIII–XXXIII) as graph-JSON
  records, each with per-node confidence, plus their source page images.
- `HONEST_ARTICULATION.md` — strengths and gaps named with precision; read this first.
- `MANIFEST.sha256` — chain of custody over the engine source and all 21 plate bundles.

## The honest frame

The engine is real and tested; the transcription is two-pass and confidence-gated, with
conjectures and engraver anomalies marked rather than corrected. The atlas count is
settled at 21 plates by reading every caption directly from the source. The corpus spans
six modes (Latin, Greek, Spanish, Chinese, musical notation, pictorial rebus), which is
the demonstration that the core is genuinely language-agnostic. See HONEST_ARTICULATION
for exactly what is solid, what is conjectural, and where the limits are.
