# Curated Primus extras

Hand-entered marquee items from Caramuel's combinatorial poetics, kept deliberately
separate from the transcribed plate atlas and **clearly marked as curated** — these
are entered from scholarship and standard mathematics, **not** OCR-extracted from the
1663 scan. They demonstrate the *non-plate* side of the system pending true
page-level OCR (the deep frontier described in `../../PRIMUS_EXPLORATION.md`).

- **`tot_tibi.json`** — the canonical proteus verse *"Tot tibi sunt dotes, Virgo,
  quot sidera caelo."* Run it forward:
  `python3 ../primus_verses.py --proteus "Tot tibi sunt dotes Virgo quot sidera caelo" --max 40320`
- **`combinatorial_table.json`** — the n! permutation-count basis behind proteus
  enumeration. Chiron's `collapse` recovers its exact generator a(n) = n·a(n-1),
  held-out verified.

The honest frame: the verse count is scanner-dependent (the meter gate decides), and
the table values are standard. What is *not* yet done is transcribing Caramuel's own
printed tables and worked examples directly from the facsimile — that requires Latin
HTR/OCR or curated hand-transcription, and is the project's real Primus frontier.
