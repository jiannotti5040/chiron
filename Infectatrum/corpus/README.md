# corpus/ — transcribed Caramuel plate records (fed into infectatrum.py)

Each plate becomes one JSON record the engine loads via `load_plate_record()`.
Two shapes are accepted:

FigureGraph (non-rectangular: hexagram, spiral, altar, column) — e.g. Tab. XIII:
{
  "tabula": "XIII",
  "source": "Caramuel Primus Calamus p.446 Tab.XIII",
  "family": "figurata-geometric",
  "confidence": "med",
  "flags": ["greek-absent"],
  "figure": {
    "tokens": {"v0": "AQVINAS", "a0": "...", "c": "..."},
    "walks":  {"recurrens": ["v0","a0","c", "..."]}
  }
}

Rectangular lattice (carmina cancellata) — e.g. Tab. XXIII:
{
  "tabula": "XXIII",
  "source": "Caramuel Primus Calamus p.468 Tab.XXIII",
  "family": "cancellata-lattice",
  "confidence": "med",
  "grid": [["S","V","A", "..."], ["...", "..."]]
}

Transcription follows the Operating Manual: two-pass (diplomatic + marked-normalized),
confidence per cell, no silent completion, dims-before-cells, ductus traced last.
Records here are the ground truth the engine measures against — nothing is invented.
